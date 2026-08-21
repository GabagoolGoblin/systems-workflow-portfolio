"""Headless standard-library tests for the clean-room workflow core."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from automate_hitl import PROJECT_ROOT, write_run_log

from hitl_core import (
    DEMO_CACHE,
    HELD_MANUAL_MENU_ITEM_ID,
    approve_lab_save,
    fixture_is_synthetic,
    fresh_rows,
    reread_staged_updates,
    resolve_from_cache,
    stage_price_updates,
    validate_held_row,
)


class HitlCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = fresh_rows()
        self.cache = dict(DEMO_CACHE)

    def resolve_and_validate_held_row(self) -> None:
        hits, held = resolve_from_cache(self.rows, self.cache)
        self.assertEqual((hits, held), (3, 1))
        held_row = next(row for row in self.rows if not row.menu_item_id)
        validate_held_row(
            self.rows,
            self.cache,
            held_row.barcode,
            HELD_MANUAL_MENU_ITEM_ID,
        )

    def test_fixture_declares_and_satisfies_synthetic_invariants(self) -> None:
        self.assertTrue(fixture_is_synthetic())

    def test_cache_hits_and_unknown_hold(self) -> None:
        hits, held = resolve_from_cache(self.rows, self.cache)

        self.assertEqual((hits, held), (3, 1))
        self.assertEqual(
            [row.status for row in self.rows].count("Cache hit"),
            3,
        )
        unresolved = [row for row in self.rows if not row.menu_item_id]
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0].status, "Held for manual lookup")

    def test_person_can_validate_one_held_identifier(self) -> None:
        resolve_from_cache(self.rows, self.cache)
        held_row = next(row for row in self.rows if not row.menu_item_id)

        validate_held_row(
            self.rows,
            self.cache,
            held_row.barcode,
            HELD_MANUAL_MENU_ITEM_ID,
        )

        self.assertEqual(held_row.menu_item_id, HELD_MANUAL_MENU_ITEM_ID)
        self.assertEqual(held_row.status, "Manually validated")
        self.assertEqual(self.cache[held_row.barcode], HELD_MANUAL_MENU_ITEM_ID)

    def test_staging_is_blocked_while_an_identifier_is_unresolved(self) -> None:
        resolve_from_cache(self.rows, self.cache)

        with self.assertRaisesRegex(ValueError, "every held row"):
            stage_price_updates(self.rows)

        self.assertTrue(all(not row.staged_price for row in self.rows))

    def test_reread_passes_when_every_staged_value_matches(self) -> None:
        self.resolve_and_validate_held_row()
        stage_price_updates(self.rows)

        self.assertTrue(reread_staged_updates(self.rows))
        self.assertTrue(
            all(row.status == "Verified, awaiting approval" for row in self.rows)
        )
        self.assertTrue(
            all(row.reread_price == row.requested_price for row in self.rows)
        )

    def test_reread_mismatch_blocks_approval(self) -> None:
        self.resolve_and_validate_held_row()
        stage_price_updates(self.rows)
        mismatch = self.rows[0]

        self.assertFalse(
            reread_staged_updates(self.rows, mismatch_barcode=mismatch.barcode)
        )
        self.assertEqual(mismatch.status, "Held: reread mismatch")
        with self.assertRaisesRegex(ValueError, "every staged row verifies"):
            approve_lab_save(self.rows)

    def test_approval_requires_verified_rows_then_saves_synthetic_state(self) -> None:
        self.resolve_and_validate_held_row()
        stage_price_updates(self.rows)

        with self.assertRaisesRegex(ValueError, "every staged row verifies"):
            approve_lab_save(self.rows)

        reread_staged_updates(self.rows)
        approve_lab_save(self.rows)

        self.assertTrue(
            all(row.status == "Saved after human approval (lab)" for row in self.rows)
        )
        self.assertTrue(
            all(row.current_price == row.requested_price for row in self.rows)
        )

    def test_log_writer_is_inert_without_an_explicit_path(self) -> None:
        before = {path for path in PROJECT_ROOT.rglob("*") if path.is_file()}
        self.assertIsNone(write_run_log(["synthetic event"], None))
        after = {path for path in PROJECT_ROOT.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_log_writer_accepts_temp_path_and_rejects_project_tree(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hitl-log-test-") as temporary_directory:
            path = Path(temporary_directory) / "run.log"
            self.assertEqual(write_run_log(["synthetic event"], path), path.resolve())
            self.assertEqual(path.read_text(encoding="utf-8"), "synthetic event\n")

        with self.assertRaisesRegex(ValueError, "outside the project tree"):
            write_run_log(["must not write"], PROJECT_ROOT / "forbidden.log")
        self.assertFalse((PROJECT_ROOT / "forbidden.log").exists())


if __name__ == "__main__":
    unittest.main()
