#!/usr/bin/env python3
"""Verify the exported inventory against policy and every classified payload byte."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


META_PATHS = {
    "RELEASE_MANIFEST.sha256",
    "release-inventory.json",
}
ORIGIN_KINDS = {
    "copy_candidate",
    "generated_example",
    "hero_asset",
    "reviewed_public_override",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def safe(raw: str) -> PurePosixPath:
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe inventory path: {raw!r}")
    if path.as_posix() != raw:
        raise ValueError(f"non-canonical inventory path: {raw!r}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", required=True, type=Path)
    args = parser.parse_args()
    inventory_path = args.check.resolve()
    root = inventory_path.parent
    errors: list[str] = []
    try:
        data = json.loads(inventory_path.read_text(encoding="utf-8"))
        policy = json.loads((root / "release-policy.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: invalid inventory or policy: {exc}")
        return 1

    if data.get("schema") != "systems-workflow-portfolio-release-inventory/v1":
        errors.append("wrong inventory schema")
    mode = policy.get("mode")
    if mode not in {"wave1", "all12"} or data.get("mode") != mode:
        errors.append("inventory mode does not match release policy")
    expected_projects = policy.get("decision_project_ids")
    actual_projects = data.get("selected_projects")
    if not isinstance(expected_projects, list) or len(expected_projects) != len(set(expected_projects)):
        errors.append("policy decision project IDs are malformed or duplicated")
        expected_projects = []
    if not isinstance(actual_projects, list) or len(actual_projects) != len(set(actual_projects)):
        errors.append("inventory selected projects are malformed or duplicated")
        actual_projects = []
    if set(actual_projects) != set(expected_projects):
        errors.append("inventory selected projects do not match release policy")

    files = data.get("files")
    if not isinstance(files, list):
        errors.append("files must be a list")
        files = []
    entries: dict[str, dict[str, object]] = {}
    folded: dict[str, str] = {}
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            errors.append("malformed file inventory entry")
            continue
        raw = item["path"]
        try:
            safe(raw)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if raw in entries:
            errors.append(f"duplicate inventory path: {raw}")
        prior = folded.setdefault(raw.casefold(), raw)
        if prior != raw:
            errors.append(f"case-fold path collision: {prior} / {raw}")
        entries[raw] = item
        origin = item.get("origin")
        if not isinstance(origin, dict) or origin.get("kind") not in ORIGIN_KINDS:
            errors.append(f"missing/unknown origin classification: {raw}")
    if list(entries) != sorted(entries):
        errors.append("inventory entries are not sorted")

    actual: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] == ".git":
            continue
        if path.is_symlink():
            errors.append(f"symlink present: {relative.as_posix()}")
            continue
        if path.is_file() and relative.as_posix() not in META_PATHS:
            actual.add(relative.as_posix())
    errors.extend(f"inventory entry missing from tree: {item}" for item in sorted(set(entries) - actual))
    errors.extend(f"unclassified tree file: {item}" for item in sorted(actual - set(entries)))
    for raw, item in entries.items():
        path = root / raw
        if not path.is_file() or path.is_symlink():
            continue
        if item.get("bytes") != path.stat().st_size:
            errors.append(f"byte-count mismatch: {raw}")
        if item.get("sha256") != digest(path):
            errors.append(f"SHA-256 mismatch: {raw}")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"PASS: {len(entries)} classified payload files match {mode} inventory and release policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
