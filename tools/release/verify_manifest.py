#!/usr/bin/env python3
"""Verify exact manifest membership, path safety, ordering, and SHA-256 digests."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path, PurePosixPath


LINE = re.compile(r"^([0-9a-f]{64})  (.+)$")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def safe_path(raw: str) -> PurePosixPath:
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe manifest path: {raw!r}")
    if path.as_posix() != raw:
        raise ValueError(f"non-canonical manifest path: {raw!r}")
    return path


def actual_files(root: Path, manifest: Path) -> set[str]:
    result: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] == ".git":
            continue
        if path.is_symlink():
            raise ValueError(f"symlink present: {relative.as_posix()}")
        if path.is_file() and path != manifest:
            result.add(relative.as_posix())
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    manifest = args.manifest.resolve()
    root = manifest.parent
    lines = manifest.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise SystemExit("FAIL: manifest is empty")
    entries: dict[str, str] = {}
    folded: dict[str, str] = {}
    errors: list[str] = []
    for number, line in enumerate(lines, 1):
        match = LINE.fullmatch(line)
        if not match:
            errors.append(f"line {number}: malformed entry")
            continue
        expected, raw = match.groups()
        try:
            relative = safe_path(raw)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if raw == manifest.name:
            errors.append("manifest recursively lists itself")
        if raw in entries:
            errors.append(f"duplicate path: {raw}")
        prior = folded.setdefault(raw.casefold(), raw)
        if prior != raw:
            errors.append(f"case-fold path collision: {prior} / {raw}")
        entries[relative.as_posix()] = expected
    if list(entries) != sorted(entries):
        errors.append("manifest entries are not sorted by repository-relative path")
    try:
        actual = actual_files(root, manifest)
    except ValueError as exc:
        errors.append(str(exc))
        actual = set()
    missing = sorted(set(entries) - actual)
    extra = sorted(actual - set(entries))
    errors.extend(f"listed file missing: {item}" for item in missing)
    errors.extend(f"unlisted file present: {item}" for item in extra)
    for raw, expected in entries.items():
        path = root / raw
        if path.is_file() and not path.is_symlink():
            observed = digest(path)
            if observed != expected:
                errors.append(f"digest mismatch: {raw}")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"PASS: {len(entries)} manifest entries; exact membership and SHA-256 verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
