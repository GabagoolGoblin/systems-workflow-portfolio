#!/usr/bin/env python3
"""Build a sorted SHA-256 manifest over release bytes, excluding itself and Git."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path


FORBIDDEN_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def release_files(root: Path, manifest: Path) -> list[Path]:
    files: list[Path] = []
    casefolded: dict[str, str] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] == ".git":
            continue
        if path.is_symlink():
            raise ValueError(f"symlink is not release content: {relative.as_posix()}")
        if not path.is_file() or path == manifest:
            continue
        if FORBIDDEN_PARTS.intersection(relative.parts) or path.suffix in FORBIDDEN_SUFFIXES:
            raise ValueError(f"transient file is not release content: {relative.as_posix()}")
        folded = relative.as_posix().casefold()
        previous = casefolded.setdefault(folded, relative.as_posix())
        if previous != relative.as_posix():
            raise ValueError(f"case-fold path collision: {previous} / {relative.as_posix()}")
        files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", nargs="?", type=Path, default=Path("RELEASE_MANIFEST.sha256"))
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    manifest = args.manifest.resolve(strict=False)
    root = (args.root or manifest.parent).resolve()
    if manifest.parent != root:
        raise SystemExit("manifest must be directly inside the release root")
    lines = [f"{digest(path)}  {path.relative_to(root).as_posix()}" for path in release_files(root, manifest)]
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    descriptor, temporary = tempfile.mkstemp(prefix=".release-manifest-", dir=root)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, manifest)
    finally:
        Path(temporary).unlink(missing_ok=True)
    print(f"PASS: wrote {len(lines)} sorted entries to {manifest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
