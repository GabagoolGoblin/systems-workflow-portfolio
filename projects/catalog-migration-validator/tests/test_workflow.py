from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from migration_tool.audit import append_event, read_audit
from migration_tool.core import artifact_bytes
from migration_tool.errors import IntegrityError, StateConflictError, ValidationError
from migration_tool.workflow import apply_plan, dry_run, stage_plan
from tests.support import mapping, source, target, write_json

FIXED_TIME = "2026-02-10T08:30:00Z"


def fixed_clock() -> str:
    return FIXED_TIME


class WorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source_path = self.root / "source.json"
        self.target_path = self.root / "target.json"
        self.mapping_path = self.root / "mapping.json"
        self.plan_path = self.root / "plan.json"
        self.quarantine_path = self.root / "quarantine.json"
        self.audit_path = self.root / "audit.jsonl"
        write_json(self.source_path, source())
        write_json(self.target_path, target())
        write_json(self.mapping_path, mapping())

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def stage(self) -> dict[str, object]:
        return stage_plan(
            self.source_path,
            self.target_path,
            self.mapping_path,
            self.plan_path,
            self.quarantine_path,
            self.audit_path,
            clock=fixed_clock,
        )

    def apply(self, plan_id: str) -> dict[str, object]:
        return apply_plan(
            self.target_path,
            self.plan_path,
            self.quarantine_path,
            self.audit_path,
            plan_id,
            clock=fixed_clock,
        )

    def test_dry_run_is_write_free(self) -> None:
        before = {path.name: path.read_bytes() for path in self.root.iterdir()}
        result = dry_run(self.source_path, self.target_path, self.mapping_path)
        after = {path.name: path.read_bytes() for path in self.root.iterdir()}
        self.assertEqual(before, after)
        self.assertEqual("dry-run", result["mode"])
        self.assertEqual(2, result["quarantine"]["quarantined_count"])

    def test_stage_writes_review_artifacts_and_audit_evidence(self) -> None:
        staged = self.stage()
        self.assertTrue(self.plan_path.exists())
        self.assertTrue(self.quarantine_path.exists())
        plan = json.loads(self.plan_path.read_text(encoding="utf-8"))
        quarantine = json.loads(self.quarantine_path.read_text(encoding="utf-8"))
        self.assertEqual(staged["plan"]["plan_id"], plan["plan_id"])
        self.assertEqual(plan["plan_id"], quarantine["plan_id"])
        events = read_audit(self.audit_path)
        self.assertEqual(["plan_staged"], [event["event_type"] for event in events])
        self.assertEqual(2, events[0]["evidence"]["quarantined_records"])

    def test_stage_refuses_to_overwrite_review_artifacts(self) -> None:
        self.stage()
        plan_before = self.plan_path.read_bytes()
        with self.assertRaisesRegex(StateConflictError, "refusing to overwrite"):
            self.stage()
        self.assertEqual(plan_before, self.plan_path.read_bytes())
        self.assertEqual(1, len(read_audit(self.audit_path)))

    def test_partial_stage_is_cleaned_if_quarantine_is_reserved(self) -> None:
        self.quarantine_path.write_text("reserved\n", encoding="utf-8")
        with self.assertRaisesRegex(StateConflictError, "refusing to overwrite"):
            self.stage()
        self.assertFalse(self.plan_path.exists())
        self.assertEqual(b"reserved\n", self.quarantine_path.read_bytes())

    def test_wrong_human_confirmation_changes_nothing(self) -> None:
        self.stage()
        before = self.target_path.read_bytes()
        with self.assertRaisesRegex(StateConflictError, "confirmation"):
            self.apply("0" * 64)
        self.assertEqual(before, self.target_path.read_bytes())
        self.assertEqual(["plan_staged"], [event["event_type"] for event in read_audit(self.audit_path)])

    def test_target_drift_is_rejected_before_apply_start(self) -> None:
        staged = self.stage()
        self.target_path.write_bytes(self.target_path.read_bytes() + b" ")
        with self.assertRaisesRegex(StateConflictError, "changed after planning"):
            self.apply(staged["plan"]["plan_id"])
        self.assertEqual(["plan_staged"], [event["event_type"] for event in read_audit(self.audit_path)])

    def test_tampered_plan_is_rejected(self) -> None:
        staged = self.stage()
        value = json.loads(self.plan_path.read_text(encoding="utf-8"))
        value["operations"][0]["after"]["price"] = "9.99"
        write_json(self.plan_path, value)
        with self.assertRaises(IntegrityError):
            self.apply(staged["plan"]["plan_id"])

    def test_tampered_quarantine_is_rejected(self) -> None:
        staged = self.stage()
        value = json.loads(self.quarantine_path.read_text(encoding="utf-8"))
        value["exceptions"][0]["message"] = "changed after review"
        write_json(self.quarantine_path, value)
        with self.assertRaisesRegex(IntegrityError, "exception digest"):
            self.apply(staged["plan"]["plan_id"])

    def test_missing_staged_audit_evidence_is_rejected(self) -> None:
        staged = self.stage()
        other_audit = self.root / "other-audit.jsonl"
        with self.assertRaisesRegex(IntegrityError, "no matching plan_staged"):
            apply_plan(
                self.target_path,
                self.plan_path,
                self.quarantine_path,
                other_audit,
                staged["plan"]["plan_id"],
                clock=fixed_clock,
            )

    def test_successful_apply_reconciles_writes_and_rereads(self) -> None:
        staged = self.stage()
        prefix = self.audit_path.read_bytes()
        result = self.apply(staged["plan"]["plan_id"])
        self.assertTrue(result["verified"])
        written = json.loads(self.target_path.read_text(encoding="utf-8"))
        products = {item["product_code"]: item for item in written["products"]}
        self.assertEqual("3.40", products["ITM-100"]["price"])
        self.assertEqual("4.25", products["ITM-300"]["price"])
        self.assertEqual(3, len(products))
        self.assertTrue(self.audit_path.read_bytes().startswith(prefix))
        self.assertEqual(
            ["plan_staged", "apply_started", "apply_verified"],
            [event["event_type"] for event in read_audit(self.audit_path)],
        )

    def test_verified_plan_cannot_be_applied_twice(self) -> None:
        staged = self.stage()
        plan_id = staged["plan"]["plan_id"]
        self.apply(plan_id)
        with self.assertRaisesRegex(StateConflictError, "already has verified"):
            self.apply(plan_id)

    def test_post_write_mismatch_restores_original_target(self) -> None:
        staged = self.stage()
        original = self.target_path.read_bytes()
        import migration_tool.workflow as workflow_module

        original_atomic = workflow_module._write_atomic
        calls = 0

        def corrupt_first_write(path: Path, content: bytes) -> None:
            nonlocal calls
            calls += 1
            if calls == 1:
                value = json.loads(content.decode("utf-8"))
                value["products"][0]["price"] = "99.99"
                original_atomic(path, artifact_bytes(value))
            else:
                original_atomic(path, content)

        with patch.object(workflow_module, "_write_atomic", corrupt_first_write):
            with self.assertRaisesRegex(IntegrityError, "reread target digest"):
                self.apply(staged["plan"]["plan_id"])
        self.assertEqual(original, self.target_path.read_bytes())
        events = read_audit(self.audit_path)
        self.assertEqual("apply_rolled_back", events[-1]["event_type"])
        self.assertTrue(events[-1]["evidence"]["target_restored"])

    def test_plan_is_parsed_and_hashed_from_one_snapshot(self) -> None:
        staged = self.stage()
        original_read_bytes = Path.read_bytes
        plan_reads = 0

        def change_path_after_snapshot(path: Path) -> bytes:
            nonlocal plan_reads
            content = original_read_bytes(path)
            if path.resolve() == self.plan_path.resolve():
                plan_reads += 1
                if plan_reads == 1:
                    path.write_bytes(content + b" ")
            return content

        with patch.object(Path, "read_bytes", change_path_after_snapshot):
            result = self.apply(staged["plan"]["plan_id"])
        self.assertTrue(result["verified"])
        self.assertEqual(1, plan_reads)

    def test_path_alias_is_rejected_before_nested_locking(self) -> None:
        staged = self.stage()
        target_alias = self.root / "target-alias.json"
        target_alias.symlink_to(self.target_path)
        with self.assertRaisesRegex(ValidationError, "paths must be distinct"):
            apply_plan(
                self.target_path,
                self.plan_path,
                self.quarantine_path,
                target_alias,
                staged["plan"]["plan_id"],
                clock=fixed_clock,
            )


class AuditTests(unittest.TestCase):
    def test_hash_chain_tamper_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            append_event(
                path,
                event_type="plan_staged",
                occurred_at=FIXED_TIME,
                plan_id="a" * 64,
                property_id="demo-target-lodge",
                evidence={"count": 1},
            )
            event = json.loads(path.read_text(encoding="utf-8"))
            event["evidence"]["count"] = 2
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(IntegrityError, "content hash mismatch"):
                read_audit(path)

    def test_invalid_timestamp_is_rejected_before_audit_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            with self.assertRaisesRegex(IntegrityError, "invalid UTC timestamp"):
                append_event(
                    path,
                    event_type="plan_staged",
                    occurred_at="not-a-timeZ",
                    plan_id="b" * 64,
                    property_id="demo-target-lodge",
                    evidence={},
                )
            self.assertFalse(path.exists())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
