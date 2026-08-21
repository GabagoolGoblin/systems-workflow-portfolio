from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from price_tool.audit import append_event, read_audit
from price_tool.core import canonical_json, sha256_bytes
from price_tool.errors import IntegrityError, StateConflictError, ValidationError
from price_tool.workflow import commit_stage, create_stage, dry_run, load_stage
from tests.support import write_catalog, write_changes

FIXED_TIME = "2026-01-15T12:00:00Z"


def fixed_clock() -> str:
    return FIXED_TIME


class WorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.catalog = self.root / "catalog.json"
        self.changes = self.root / "changes.csv"
        self.stage = self.root / "stage.json"
        self.audit = self.root / "audit.jsonl"
        write_catalog(self.catalog)
        write_changes(self.changes)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create_stage(self) -> dict[str, object]:
        return create_stage(
            self.catalog,
            self.changes,
            self.stage,
            self.audit,
            clock=fixed_clock,
        )

    def test_dry_run_writes_nothing(self) -> None:
        before = {path.name: path.read_bytes() for path in self.root.iterdir()}
        result = dry_run(self.catalog, self.changes)
        after = {path.name: path.read_bytes() for path in self.root.iterdir()}
        self.assertEqual(before, after)
        self.assertEqual("dry-run", result["mode"])

    def test_stage_is_hash_bound_and_audited(self) -> None:
        stage = self.create_stage()
        loaded = load_stage(self.stage)
        self.assertEqual(stage["stage_id"], loaded["stage_id"])
        events = read_audit(self.audit)
        self.assertEqual(["stage_created"], [event["event_type"] for event in events])
        self.assertEqual(stage["stage_id"], events[0]["stage_id"])

    def test_stage_refuses_overwrite(self) -> None:
        self.create_stage()
        with self.assertRaisesRegex(StateConflictError, "refusing to overwrite"):
            self.create_stage()
        self.assertEqual(1, len(read_audit(self.audit)))

    def test_same_inputs_and_time_produce_same_stage_id(self) -> None:
        first = self.create_stage()
        other_stage = self.root / "other-stage.json"
        other_audit = self.root / "other-audit.jsonl"
        second = create_stage(
            self.catalog,
            self.changes,
            other_stage,
            other_audit,
            clock=fixed_clock,
        )
        self.assertEqual(first["stage_id"], second["stage_id"])

    def test_tampered_stage_is_rejected(self) -> None:
        self.create_stage()
        value = json.loads(self.stage.read_text(encoding="utf-8"))
        value["updates"][0]["after_price"] = "3.55"
        self.stage.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "percent_change|content hash"):
            load_stage(self.stage)

    def test_rehashed_stage_with_invalid_timestamp_is_rejected(self) -> None:
        self.create_stage()
        value = json.loads(self.stage.read_text(encoding="utf-8"))
        value["created_at"] = "not-a-real-timeZ"
        unsigned = dict(value)
        del unsigned["stage_id"]
        value["stage_id"] = sha256_bytes(canonical_json(unsigned))
        self.stage.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "invalid UTC timestamp"):
            load_stage(self.stage)

    def test_rehashed_tamper_still_lacks_matching_audit_evidence(self) -> None:
        stage = self.create_stage()
        value = json.loads(self.stage.read_text(encoding="utf-8"))
        value["updates"][0]["reason"] = "Altered after review"
        unsigned = dict(value)
        del unsigned["stage_id"]
        value["stage_id"] = sha256_bytes(canonical_json(unsigned))
        self.stage.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(IntegrityError, "no matching stage_created"):
            commit_stage(
                self.catalog,
                self.stage,
                self.audit,
                value["stage_id"],
                clock=fixed_clock,
            )
        self.assertNotEqual(stage["stage_id"], value["stage_id"])

    def test_wrong_confirmation_does_not_start_commit(self) -> None:
        self.create_stage()
        catalog_before = self.catalog.read_bytes()
        with self.assertRaisesRegex(StateConflictError, "confirmation"):
            commit_stage(
                self.catalog,
                self.stage,
                self.audit,
                "0" * 64,
                clock=fixed_clock,
            )
        self.assertEqual(catalog_before, self.catalog.read_bytes())
        self.assertEqual(["stage_created"], [e["event_type"] for e in read_audit(self.audit)])

    def test_catalog_drift_is_rejected_before_commit_start(self) -> None:
        stage = self.create_stage()
        self.catalog.write_bytes(self.catalog.read_bytes() + b" \n")
        with self.assertRaisesRegex(StateConflictError, "changed after staging"):
            commit_stage(
                self.catalog,
                self.stage,
                self.audit,
                stage["stage_id"],
                clock=fixed_clock,
            )
        self.assertEqual(["stage_created"], [e["event_type"] for e in read_audit(self.audit)])

    def test_successful_commit_rereads_and_appends_verified_evidence(self) -> None:
        stage = self.create_stage()
        prefix = self.audit.read_bytes()
        result = commit_stage(
            self.catalog,
            self.stage,
            self.audit,
            stage["stage_id"],
            clock=fixed_clock,
        )
        self.assertTrue(result["verified"])
        prices = {
            item["sku"]: item["price"]
            for item in json.loads(self.catalog.read_text(encoding="utf-8"))["items"]
        }
        self.assertEqual("3.50", prices["BEV-1001"])
        self.assertEqual("12.25", prices["ENT-2001"])
        self.assertEqual("4.50", prices["SID-3001"])
        self.assertTrue(self.audit.read_bytes().startswith(prefix))
        self.assertEqual(
            ["stage_created", "commit_started", "commit_verified"],
            [event["event_type"] for event in read_audit(self.audit)],
        )

    def test_commit_uses_one_stage_snapshot_if_path_changes_after_read(self) -> None:
        stage = self.create_stage()
        original_read_bytes = Path.read_bytes
        stage_reads = 0

        def tracked_read_bytes(path: Path) -> bytes:
            nonlocal stage_reads
            content = original_read_bytes(path)
            if path.resolve() == self.stage.resolve():
                stage_reads += 1
                if stage_reads == 1:
                    path.write_bytes(content + b" ")
            return content

        with patch.object(Path, "read_bytes", tracked_read_bytes):
            result = commit_stage(
                self.catalog,
                self.stage,
                self.audit,
                stage["stage_id"],
                clock=fixed_clock,
            )

        self.assertTrue(result["verified"])
        self.assertEqual(1, stage_reads)

    def test_catalog_and_audit_path_alias_is_rejected_without_nested_lock(self) -> None:
        stage = self.create_stage()
        alias = self.root / "catalog-alias.json"
        alias.symlink_to(self.catalog)
        with self.assertRaisesRegex(ValidationError, "paths must be distinct"):
            commit_stage(
                self.catalog,
                self.stage,
                alias,
                stage["stage_id"],
                clock=fixed_clock,
            )

    def test_verified_stage_cannot_be_committed_twice(self) -> None:
        stage = self.create_stage()
        commit_stage(
            self.catalog,
            self.stage,
            self.audit,
            stage["stage_id"],
            clock=fixed_clock,
        )
        with self.assertRaisesRegex(StateConflictError, "already has verified"):
            commit_stage(
                self.catalog,
                self.stage,
                self.audit,
                stage["stage_id"],
                clock=fixed_clock,
            )

    def test_post_write_mismatch_restores_original_catalog(self) -> None:
        stage = self.create_stage()
        original = self.catalog.read_bytes()

        def corrupt_write(path: Path, target: dict[str, object]) -> bytes:
            expected = (json.dumps(target, sort_keys=True, indent=2) + "\n").encode("utf-8")
            bad = deepcopy(target)
            bad["items"][0]["price"] = "99.99"  # type: ignore[index]
            path.write_text(json.dumps(bad, sort_keys=True), encoding="utf-8")
            return expected

        with patch("price_tool.workflow._write_catalog_atomic", side_effect=corrupt_write):
            with self.assertRaisesRegex(IntegrityError, "reread catalog digest"):
                commit_stage(
                    self.catalog,
                    self.stage,
                    self.audit,
                    stage["stage_id"],
                    clock=fixed_clock,
                )
        self.assertEqual(original, self.catalog.read_bytes())
        events = read_audit(self.audit)
        self.assertEqual("commit_rolled_back", events[-1]["event_type"])
        self.assertTrue(events[-1]["evidence"]["catalog_restored"])

    def test_missing_stage_audit_is_rejected(self) -> None:
        stage = self.create_stage()
        empty_audit = self.root / "empty-audit.jsonl"
        with self.assertRaisesRegex(IntegrityError, "no matching stage_created"):
            commit_stage(
                self.catalog,
                self.stage,
                empty_audit,
                stage["stage_id"],
                clock=fixed_clock,
            )


class AuditTests(unittest.TestCase):
    def test_invalid_timestamp_is_rejected_before_audit_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            with self.assertRaisesRegex(IntegrityError, "invalid timestamp"):
                append_event(
                    path,
                    event_type="stage_created",
                    occurred_at="not-a-timeZ",
                    stage_id="c" * 64,
                    venue_id="demo-venue-alpha",
                    evidence={},
                )
            self.assertFalse(path.exists())

    def test_chain_tamper_is_detected_before_append(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            stage_id = "a" * 64
            append_event(
                path,
                event_type="stage_created",
                occurred_at=FIXED_TIME,
                stage_id=stage_id,
                venue_id="demo-venue-alpha",
                evidence={"update_count": 1},
            )
            line = json.loads(path.read_text(encoding="utf-8"))
            line["evidence"]["update_count"] = 2
            path.write_text(json.dumps(line) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(IntegrityError, "content hash mismatch"):
                read_audit(path)
            with self.assertRaises(IntegrityError):
                append_event(
                    path,
                    event_type="commit_started",
                    occurred_at=FIXED_TIME,
                    stage_id=stage_id,
                    venue_id="demo-venue-alpha",
                    evidence={},
                )

    def test_duplicate_json_fields_in_audit_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            append_event(
                path,
                event_type="stage_created",
                occurred_at=FIXED_TIME,
                stage_id="b" * 64,
                venue_id="demo-venue-alpha",
                evidence={},
            )
            line = path.read_text(encoding="utf-8")
            line = line.replace(
                '"event_type":"stage_created"',
                '"event_type":"stage_created","event_type":"stage_created"',
                1,
            )
            path.write_text(line, encoding="utf-8")
            with self.assertRaisesRegex(IntegrityError, "invalid JSON"):
                read_audit(path)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
