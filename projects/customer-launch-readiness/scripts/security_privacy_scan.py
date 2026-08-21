#!/usr/bin/env python3
"""Deterministic offline security and privacy checks for the public demo."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "index.html", ROOT / "styles.css", ROOT / "app.js")

FORBIDDEN_RUNTIME_PATTERNS = {
    "remote URL": r"https?://",
    "network fetch": r"\bfetch\s*\(",
    "XMLHttpRequest": r"\bXMLHttpRequest\b",
    "WebSocket": r"\bWebSocket\b",
    "beacon": r"\bsendBeacon\b",
    "EventSource": r"\bEventSource\b",
    "iframe": r"<iframe\b",
    "form submission": r"<form\b",
    "local storage": r"\blocalStorage\b",
    "session storage": r"\bsessionStorage\b",
    "indexed database": r"\bindexedDB\b",
    "service worker": r"\bserviceWorker\b",
    "cookie access": r"document\.cookie",
    "dynamic code evaluation": r"\beval\s*\(|\bnew\s+Function\s*\(",
}

SECRET_PATTERNS = {
    "private key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "generic API key": r"(?i)(?:api[_-]?key|secret[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}",
    "bearer token": r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}",
    "GitHub token": r"gh[pousr]_[A-Za-z0-9]{20,}",
    "AWS access key": r"AKIA[0-9A-Z]{16}",
    "email": r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    "private path": r"/(?:home|Users)/[^\s`\"<>]+",
}


def check(label: str, passed: bool, detail: str) -> bool:
    print(f"{'PASS' if passed else 'FAIL'}: {label} — {detail}")
    return passed


def main() -> int:
    runtime = "\n".join(path.read_text(encoding="utf-8") for path in RUNTIME)
    project_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in ROOT.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.name != "RELEASE_MANIFEST.sha256"
    )

    results: list[bool] = []
    for label, pattern in FORBIDDEN_RUNTIME_PATTERNS.items():
        results.append(check(f"runtime has no {label}", re.search(pattern, runtime, re.I) is None, pattern))
    for label, pattern in SECRET_PATTERNS.items():
        results.append(check(f"project has no {label}", re.search(pattern, project_text, re.I) is None, pattern))

    boundaries = (
        "INDEPENDENT PORTFOLIO DEMO",
        "SYNTHETIC DATA",
        "NO AFFILIATION",
        "NO PRODUCTION ACTION",
    )
    shell = (ROOT / "index.html").read_text(encoding="utf-8")
    for phrase in boundaries:
        results.append(check(f"visible boundary includes {phrase}", phrase in shell, phrase))

    results.append(check("CSP blocks runtime connections", "connect-src 'none'" in shell, "connect-src 'none'"))
    results.append(check("runtime exports only after a user event", "data-export-audit" in runtime and "function exportAudit()" in runtime, "user-triggered Blob download"))
    results.append(check("fixture declares no production authority", "not_production_authority: true" in runtime, "export boundary"))

    passed = all(results)
    print(f"OVERALL: {'PASS' if passed else 'FAIL'} ({sum(results)}/{len(results)} checks)")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
