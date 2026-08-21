"""Deterministic clean-room publication scan for this repository only."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {"", ".md", ".py", ".json", ".txt"}
IGNORED_PARTS = {".git", "out", "__pycache__", ".venv"}
LOCAL_MODULES = {"hospitality_workbench", "workbench"} | {
    path.stem for path in (ROOT / "hospitality_workbench").glob("*.py")
}
NETWORK_MODULES = {
    "aiohttp",
    "ftplib",
    "http",
    "requests",
    "socket",
    "urllib",
    "websockets",
}

SENSITIVE_PATTERNS = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    "url": re.compile(r"\bhttps?://[^\s`<>]+", re.IGNORECASE),
    "network_address": re.compile(r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])"),
    "private_unix_path": re.compile(r"/(?:home|Users)/[^\s`\"<>]+"),
    "private_windows_path": re.compile(r"[A-Z]:\\\\Users\\\\[^\s`\"<>]+", re.IGNORECASE),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "assigned_secret": re.compile(
        r"\b(?:api[_-]?key|password|token|secret)\s*[:=]\s*[\"']?[^\s,;\"']{8,}",
        re.IGNORECASE,
    ),
}


def _candidate_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        if path.is_symlink():
            continue
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            files.append(path)
    return sorted(files)


def _scan_text(errors: list[str], files: list[Path]) -> None:
    for path in files:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        for label, pattern in SENSITIVE_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{relative}: matched {label}")


def _scan_python(errors: list[str], files: list[Path]) -> None:
    for path in (item for item in files if item.suffix == ".py"):
        relative = path.relative_to(ROOT)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(relative))
        except SyntaxError as exc:
            errors.append(f"{relative}: syntax error: {exc}")
            continue
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add((node.module or "").split(".")[0])
        external = imports - set(sys.stdlib_module_names) - LOCAL_MODULES - {""}
        if external:
            errors.append(f"{relative}: non-stdlib imports: {sorted(external)}")
        network = imports.intersection(NETWORK_MODULES)
        if network:
            errors.append(f"{relative}: network imports: {sorted(network)}")


def _scan_structure(errors: list[str]) -> None:
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if ".git" in relative.parts:
            continue
        if path.is_symlink():
            errors.append(f"{relative}: symbolic link is not allowed")
        if path.is_file() and path.suffix in {".pyc", ".pyo"}:
            errors.append(f"{relative}: bytecode cache is not allowed")
        if path.is_dir() and path.name == "__pycache__":
            errors.append(f"{relative}: bytecode-cache directory is not allowed")


def _scan_fixture(errors: list[str]) -> int:
    fixture = ROOT / "fixtures" / "synthetic_tickets.json"
    try:
        payload = json.loads(fixture.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"fixture: invalid JSON: {exc}")
        return 0
    sys.path.insert(0, str(ROOT))
    from hospitality_workbench.schema import SchemaError, parse_synthetic_batch

    try:
        tickets = parse_synthetic_batch(payload)
    except SchemaError as exc:
        errors.append(f"fixture: strict schema failed: {exc}")
        return 0
    return len(tickets)


def main() -> int:
    errors: list[str] = []
    files = _candidate_files()
    _scan_text(errors, files)
    _scan_python(errors, files)
    _scan_structure(errors)
    ticket_count = _scan_fixture(errors)
    payload = {
        "ok": not errors,
        "errors": errors,
        "files_scanned": len(files),
        "synthetic_tickets": ticket_count,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
