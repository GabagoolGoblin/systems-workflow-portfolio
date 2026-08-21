#!/usr/bin/env python3
"""Copy an exact manifest-bound release tree to a new directory without Git actions."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def safe(raw: str) -> PurePosixPath:
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe manifest path: {raw!r}")
    return path


def load_manifest(source: Path) -> list[tuple[str, str]]:
    manifest = source / "RELEASE_MANIFEST.sha256"
    entries: list[tuple[str, str]] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, separator, raw = line.partition("  ")
        if separator != "  " or len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            raise ValueError(f"malformed manifest line: {line!r}")
        relative = safe(raw).as_posix()
        path = source / relative
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError(f"source does not match manifest: {relative}")
        entries.append((relative, expected))
    if [item[0] for item in entries] != sorted(item[0] for item in entries):
        raise ValueError("manifest is not sorted")
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve()
    destination = args.destination.resolve(strict=False)
    if source == destination or source in destination.parents:
        raise SystemExit("destination must be outside the source tree")
    if destination in {Path("/"), Path.home(), Path.home() / "Documents"}:
        raise SystemExit("refusing broad destination")
    if destination.exists():
        raise SystemExit(f"destination already exists: {destination}")
    entries = load_manifest(source)
    if args.plan:
        print(f"PLAN: copy {len(entries) + 1} manifest-bound files to {destination}")
        return 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.export-", dir=destination.parent))
    try:
        for relative, expected in entries:
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, target)
            if digest(target) != expected:
                raise ValueError(f"copied digest mismatch: {relative}")
        shutil.copyfile(source / "RELEASE_MANIFEST.sha256", stage / "RELEASE_MANIFEST.sha256")
        os.replace(stage, destination)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    print(f"PASS: exported {len(entries) + 1} files; no Git, remote, or source mutation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
