#!/usr/bin/env python3
"""Deterministic security/privacy scan for this private offline lab."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (
    ROOT / "index.html",
    ROOT / "styles.css",
    ROOT / "app.js",
    ROOT / "data/demo_snapshot.js",
)

FORBIDDEN_RUNTIME = {
    "remote URL": r"https?://",
    "fetch": r"\bfetch\s*\(",
    "XMLHttpRequest": r"\bXMLHttpRequest\b",
    "WebSocket": r"\bWebSocket\b",
    "sendBeacon": r"\bsendBeacon\b",
    "EventSource": r"\bEventSource\b",
    "service worker": r"\bserviceWorker\b",
    "cookie access": r"document\.cookie",
    "local storage": r"\blocalStorage\b",
    "session storage": r"\bsessionStorage\b",
    "indexed database": r"\bindexedDB\b",
    "unsafe HTML sink": r"innerHTML|outerHTML|insertAdjacentHTML|document\.write",
    "dynamic code evaluation": r"\beval\s*\(|\bnew\s+Function\s*\(",
    "iframe": r"<iframe\b",
    "submittable form": r"<form\b",
}

FORBIDDEN_PROJECT = {
    "private key material": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "GitHub token": r"gh[pousr]_[A-Za-z0-9]{20,}",
    "AWS access key": r"AKIA[0-9A-Z]{16}",
    "bearer token": r"(?i)bearer\s+[A-Za-z0-9._-]{20,}",
    "email address": r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    "private IPv4 address": r"\b(?:10\.(?:\d{1,3}\.){2}\d{1,3}|192\.168\.(?:\d{1,3}\.)\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.(?:\d{1,3}\.)\d{1,3})\b",
    "absolute home path": r"/home/[A-Za-z0-9._-]+/",
}


def emit(label: str, passed: bool, detail: str) -> bool:
    print(f"{'PASS' if passed else 'FAIL'}: {label}: {detail}")
    return passed


def main() -> int:
    runtime = "\n".join(path.read_text(encoding="utf-8") for path in RUNTIME)
    project_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in ROOT.rglob("*")
        if path.is_file()
        and "artifacts/screenshots" not in path.as_posix()
        and "__pycache__" not in path.parts
        and path.name not in {"MANIFEST.sha256", "security_privacy_scan.py"}
    )
    results: list[bool] = []

    for label, pattern in FORBIDDEN_RUNTIME.items():
        results.append(emit(f"runtime has no {label}", re.search(pattern, runtime, re.IGNORECASE) is None, pattern))
    for label, pattern in FORBIDDEN_PROJECT.items():
        results.append(emit(f"project has no {label}", re.search(pattern, project_text) is None, pattern))

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "app.js").read_text(encoding="utf-8")
    boundary = "INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION"
    results.append(emit("visible boundary is exact", boundary in html, boundary))
    for phrase in ("SYNTHETIC DATA", "NO AFFILIATION", "NO PRODUCTION ACTION"):
        results.append(emit(f"visible boundary includes {phrase}", phrase in html, phrase))
    results.append(emit("CSP denies all runtime connections", "connect-src 'none'" in html, "connect-src 'none'"))
    results.append(emit("browser writes text through textContent", "node.textContent = text" in script, "textContent"))
    results.append(emit("visible token is not presented as authentication", script.lower().count("not authentication") >= 2, "explicit gate boundary"))
    results.append(emit("query parameters cannot advance human gate", 'query.get("scenario") ===' not in script, "gate starts false"))
    results.append(emit("synthetic public secret is explicitly labeled", "whsec_SYNTHETIC_PERSONAL_LAB_NOT_A_SECRET" in runtime, "known public demo value"))

    passed = all(results)
    print(f"OVERALL: {'PASS' if passed else 'FAIL'} ({sum(results)}/{len(results)} checks)")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
