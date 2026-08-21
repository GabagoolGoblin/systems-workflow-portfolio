"""Deterministic release-safety checks for the public portfolio project."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOTS = [PROJECT_ROOT / "src", PROJECT_ROOT / "tests", PROJECT_ROOT / "tools"]
PACKAGE_ROOT = "claim_evidence_contract_linter"
LOCAL_TEST_ROOTS = {"support"}
FORBIDDEN_IMPORT_ROOTS = {
    "aiohttp",
    "ftplib",
    "http",
    "httpx",
    "imaplib",
    "paramiko",
    "poplib",
    "requests",
    "smtplib",
    "socket",
    "telnetlib",
    "urllib",
    "webbrowser",
    "websockets",
}
PRIVATE_MARKERS = (
    "@gmail.com",
    "@outlook.com",
    "@pro" + "ton.me",
    "bearer ",
    "api_key",
    "password=",
)


def python_files() -> list[Path]:
    return sorted(path for root in PYTHON_ROOTS for path in root.rglob("*.py"))


def audit_imports(errors: list[str]) -> None:
    for path in python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for name in names:
                root = name.split(".", 1)[0]
                if root in FORBIDDEN_IMPORT_ROOTS:
                    errors.append(f"forbidden network-capable import {name!r} in {path}")
                if root != PACKAGE_ROOT and root not in LOCAL_TEST_ROOTS and root not in sys.stdlib_module_names:
                    errors.append(f"non-stdlib import {name!r} in {path}")


def audit_fixtures(errors: list[str]) -> None:
    for path in sorted((PROJECT_ROOT / "demo").glob("*.json")):
        data = path.read_text(encoding="utf-8")
        lowered = data.casefold()
        for marker in PRIVATE_MARKERS:
            if marker in lowered:
                errors.append(f"private/credential marker {marker!r} in {path}")
        try:
            json.loads(data)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid demo JSON in {path}: {exc}")


def audit_repository_state(errors: list[str]) -> None:
    if list(PROJECT_ROOT.rglob("__pycache__")) or list(PROJECT_ROOT.rglob("*.pyc")):
        errors.append("bytecode artifacts present")
    if (PROJECT_ROOT / ".git").exists():
        errors.append("nested Git metadata present")
    if list(PROJECT_ROOT.glob("LICENSE*")) or list(PROJECT_ROOT.glob("COPYING*")):
        errors.append("conflicting project-local license present")
    for name in ("README.md", "CLAIMS_AND_BOUNDARIES.md", "PROVENANCE.md"):
        if not (PROJECT_ROOT / name).is_file():
            errors.append(f"required public document missing: {name}")


def main() -> int:
    errors: list[str] = []
    audit_imports(errors)
    audit_fixtures(errors)
    audit_repository_state(errors)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(
        f"PASS: {len(python_files())} Python files; standard-library runtime; "
        "synthetic fixtures; public boundary documents; no nested metadata/cache"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
