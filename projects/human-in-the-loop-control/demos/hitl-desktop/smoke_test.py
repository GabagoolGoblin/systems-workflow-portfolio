"""Scripted GUI smoke test for the clean-room desktop lab.

This module requires Tk and a display. Use test_hitl_core.py for headless checks.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

try:
    import tkinter  # noqa: F401
except ModuleNotFoundError:
    print(
        "BLOCKED: GUI smoke requires a Python interpreter with Tk support.",
        file=sys.stderr,
    )
    raise SystemExit(2)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from automate_hitl import run_automation, write_run_log  # noqa: E402
from hitl_core import (  # noqa: E402
    DEMO_CACHE,
    DUPLICATE_HOLD_STATUS,
    HELD_MANUAL_MENU_ITEM_ID,
    approve_lab_save,
    fixture_is_synthetic,
    fresh_rows,
    reread_staged_updates,
    resolve_from_cache,
    stage_price_updates,
    validate_held_row,
)
from mock_console import MockConsole  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log-path",
        type=Path,
        help="Optional summary-log path outside the project tree; no persistent log is written by default",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="hitl-smoke-") as temporary_directory:
        temporary = Path(temporary_directory)
        happy_log_path = temporary / "happy.log"
        fail_log_path = temporary / "fail.log"

        happy = MockConsole()
        happy.withdraw()
        hlog = run_automation(
            happy,
            force_fail=False,
            interactive=False,
            log_path=happy_log_path,
        )
        happy_ok = any("verify passed" in x.lower() or "OK: verify" in x for x in hlog)
        price_ok = happy.read_price("4000104") == "2.55"

        fail = MockConsole()
        fail.withdraw()
        flog = run_automation(
            fail,
            force_fail=True,
            interactive=False,
            log_path=fail_log_path,
        )
        hitl_ok = any("HITL" in x for x in flog)
        price_bad = fail.read_price("4000104") == "999.99"
        log_ok = (
            happy_log_path.is_file()
            and fail_log_path.is_file()
            and "HITL" in fail_log_path.read_text(encoding="utf-8")
        )

        happy.destroy()
        fail.destroy()

    explicit_log_ok = True
    if args.log_path is not None:
        written = write_run_log(
            [
                "HITL GUI SMOKE: PASS" if all((happy_ok, price_ok, hitl_ok, price_bad, log_ok)) else "HITL GUI SMOKE: FAIL",
                "Synthetic lab only; no production action.",
            ],
            args.log_path,
        )
        explicit_log_ok = written == args.log_path.expanduser().resolve() and written.is_file()

    tracked_log_absent = not (Path(__file__).resolve().parent / "last_run_log.txt").exists()

    rows = fresh_rows()
    cache = dict(DEMO_CACHE)
    hits, held = resolve_from_cache(rows, cache)
    cache_resolution_ok = hits == 3 and held == 2
    staging_blocked = False
    try:
        stage_price_updates(rows)
    except ValueError:
        staging_blocked = True
    held_row = next(
        row for row in rows if not row.menu_item_id and not row.duplicate_submission
    )
    validate_held_row(rows, cache, held_row.request_id, HELD_MANUAL_MENU_ITEM_ID)
    stage_price_updates(rows)
    verify_ok = reread_staged_updates(rows)
    approve_lab_save(rows)
    human_save_ok = all(
        row.status == "Saved after human approval (lab)"
        and row.current_price == row.requested_price
        for row in rows
        if not row.duplicate_submission
    )
    duplicate = next(row for row in rows if row.duplicate_submission)
    duplicate_held = bool(
        duplicate.status == DUPLICATE_HOLD_STATUS
        and not duplicate.menu_item_id
        and not duplicate.staged_price
        and not duplicate.reread_price
    )

    mismatch_rows = fresh_rows()
    mismatch_cache = dict(DEMO_CACHE)
    resolve_from_cache(mismatch_rows, mismatch_cache)
    held_row = next(
        row
        for row in mismatch_rows
        if not row.menu_item_id and not row.duplicate_submission
    )
    validate_held_row(
        mismatch_rows, mismatch_cache, held_row.request_id, HELD_MANUAL_MENU_ITEM_ID
    )
    stage_price_updates(mismatch_rows)
    mismatch_blocked = not reread_staged_updates(
        mismatch_rows, mismatch_request_id=mismatch_rows[0].request_id
    )
    save_blocked = False
    try:
        approve_lab_save(mismatch_rows)
    except ValueError:
        save_blocked = True

    synthetic_fixture_ok = fixture_is_synthetic()
    # Confirm every fixture source is explicitly synthetic.
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "synthetic_menu_batch.json"
    fixture_text = fixture_path.read_text(encoding="utf-8") if fixture_path.is_file() else ""
    fixture_data = json.loads(fixture_text)
    synthetic_sources_ok = all(
        item.get("source") == "synthetic_fixture"
        for item in fixture_data.get("requests", [])
    )
    sample_barcodes = [row.barcode for row in fresh_rows()]
    synthetic_id_shape = all(len(b) == 12 and b.isdigit() for b in sample_barcodes)

    print("happy_ok", happy_ok)
    print("price_ok", price_ok)
    print("hitl_ok", hitl_ok)
    print("price_bad", price_bad)
    print("log_ok", log_ok)
    print("explicit_log_ok", explicit_log_ok)
    print("tracked_log_absent", tracked_log_absent)
    print("cache_resolution_ok", cache_resolution_ok)
    print("staging_blocked", staging_blocked)
    print("verify_ok", verify_ok)
    print("human_save_ok", human_save_ok)
    print("duplicate_held", duplicate_held)
    print("mismatch_blocked", mismatch_blocked)
    print("save_blocked", save_blocked)
    print("synthetic_fixture_ok", synthetic_fixture_ok)
    print("synthetic_sources_ok", synthetic_sources_ok)
    print("synthetic_id_shape", synthetic_id_shape)
    print("sample_barcodes", sample_barcodes)
    print("--- happy ---")
    print("\n".join(hlog))
    print("--- fail ---")
    print("\n".join(flog))

    overall = all(
        (
            happy_ok,
            price_ok,
            hitl_ok,
            price_bad,
            log_ok,
            explicit_log_ok,
            tracked_log_absent,
            cache_resolution_ok,
            staging_blocked,
            verify_ok,
            human_save_ok,
            duplicate_held,
            mismatch_blocked,
            save_blocked,
            synthetic_fixture_ok,
            synthetic_sources_ok,
            synthetic_id_shape,
        )
    )
    print("OVERALL", "PASS" if overall else "FAIL")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
