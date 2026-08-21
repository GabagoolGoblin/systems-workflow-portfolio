#!/usr/bin/env python3
"""Rebuild the exact synthetic receipt and browser snapshot with an explicit token."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from integration_lab.core import evaluate_files, load_json_file


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "fixtures" / "synthetic_contract.json"
RUN = ROOT / "fixtures" / "synthetic_run.json"
RECEIPT = ROOT / "artifacts" / "synthetic_receipt.json"
SNAPSHOT = ROOT / "data" / "demo_snapshot.js"
CONFIRMATION = "SYNTHETIC_ARTIFACTS"


def atomic_replace(path: Path, content: bytes) -> None:
    if path.is_symlink():
        raise SystemExit(f"refusing symlink output: {path}")
    temp = path.with_name(f".{path.name}.tmp")
    if temp.exists() or temp.is_symlink():
        raise SystemExit(f"refusing existing temporary path: {temp}")
    descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        try:
            temp.unlink(missing_ok=True)
        finally:
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if args.confirm != CONFIRMATION:
        raise SystemExit(f"exact confirmation required: {CONFIRMATION}")

    report = evaluate_files(CONTRACT, RUN)
    json_text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    contract, _ = load_json_file(CONTRACT, "contract")
    run, _ = load_json_file(RUN, "run")
    browser_snapshot = {"report": report, "contract": contract, "run": run}
    js_text = (
        '"use strict";\n'
        "// Generated from the exact synthetic fixture by scripts/build_artifacts.py.\n"
        "window.API_LAB_SNAPSHOT = "
        + json.dumps(browser_snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + ";\n"
    )
    atomic_replace(RECEIPT, json_text.encode("utf-8"))
    atomic_replace(SNAPSHOT, js_text.encode("utf-8"))
    print(f"wrote {RECEIPT.relative_to(ROOT)} ({len(json_text.encode('utf-8'))} bytes)")
    print(f"wrote {SNAPSHOT.relative_to(ROOT)} ({len(js_text.encode('utf-8'))} bytes)")
    print(f"receipt_digest {report['receipt_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
