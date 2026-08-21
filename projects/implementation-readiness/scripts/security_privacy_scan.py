#!/usr/bin/env python3
"""Deterministic, dependency-free security and privacy scan for the demo."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILES = (ROOT / "index.html", ROOT / "styles.css", ROOT / "app.js")
ALL_TEXT_FILES = tuple(
    path
    for path in ROOT.rglob("*")
    if path.is_file()
    and path.suffix.lower() in {".html", ".css", ".js", ".md", ".py", ".txt"}
    and "artifacts" not in path.parts
)

RUNTIME_FORBIDDEN = {
    "remote URL": r"https?://",
    "fetch": r"\bfetch\s*\(",
    "XMLHttpRequest": r"\bXMLHttpRequest\b",
    "WebSocket": r"\bWebSocket\b",
    "sendBeacon": r"\bsendBeacon\b",
    "EventSource": r"\bEventSource\b",
    "iframe": r"<iframe\b",
    "remote script": r"<script[^>]+src=[\"']//",
    "remote image": r"<img[^>]+src=[\"']//",
}

SECRET_PATTERNS = {
    "private key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "generic API token": r"(?i)\b(?:api[_-]?key|secret|access[_-]?token)\s*[:=]\s*[\"'][A-Za-z0-9_\-]{16,}",
    "AWS access key": r"\bAKIA[0-9A-Z]{16}\b",
    "email address": r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
    "non-loopback IPv4 address": r"\b(?!127\.0\.0\.1\b)(?:\d{1,3}\.){3}\d{1,3}\b",
}

PRIVATE_MARKERS = (
    "Com" + "pass Gr" + "oup",
    "PRIVATE_EMPLOYER_RECORD",
    "historical employer screenshot path",
    "production customer record",
)


def scan() -> list[str]:
    failures: list[str] = []
    runtime = "\n".join(path.read_text(encoding="utf-8") for path in RUNTIME_FILES)
    for label, pattern in RUNTIME_FORBIDDEN.items():
        if re.search(pattern, runtime, re.IGNORECASE):
            failures.append(f"runtime contains {label}")

    for path in ALL_TEXT_FILES:
        text = path.read_text(encoding="utf-8")
        for label, pattern in SECRET_PATTERNS.items():
            if re.search(pattern, text):
                failures.append(f"{path.relative_to(ROOT)} contains {label}")
        if path in RUNTIME_FILES:
            for marker in PRIVATE_MARKERS:
                if marker.lower() in text.lower():
                    failures.append(f"{path.relative_to(ROOT)} contains private marker: {marker}")

    return failures


def main() -> int:
    failures = scan()
    print(f"scanned {len(RUNTIME_FILES)} runtime files and {len(ALL_TEXT_FILES)} text files")
    print("network primitives: PASS" if not any("runtime contains" in item for item in failures) else "network primitives: FAIL")
    print("secret/contact patterns: PASS" if not any("contains" in item and "runtime contains" not in item for item in failures) else "secret/contact patterns: FAIL")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
