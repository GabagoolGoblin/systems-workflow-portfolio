"""Headless tests for the offline synthetic support workbench."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hospitality_workbench.audit import AuditIntegrityError, AuditLog, verify_audit
from hospitality_workbench.pipeline import process_tickets
from hospitality_workbench.redaction import redact_text, redact_ticket
from hospitality_workbench.schema import (
    SchemaError,
    load_synthetic_batch,
    parse_synthetic_batch,
    parse_ticket,
)
from hospitality_workbench.triage import (
    APPROVAL_CONFIRMATION,
    ApprovalError,
    DuplicateIndex,
    approve_triage,
    triage_ticket,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "synthetic_tickets.json"


class SchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_loads_only_strict_synthetic_tickets(self) -> None:
        tickets = load_synthetic_batch(FIXTURE)
        self.assertEqual(len(tickets), 6)
        self.assertTrue(all(ticket.ticket_id.startswith("LAB-TKT-") for ticket in tickets))
        self.assertTrue(
            all(site.startswith("LAB-SITE-") for ticket in tickets for site in ticket.site_codes)
        )

    def test_unknown_field_is_rejected(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["tickets"][0]["unexpected"] = "invented"
        with self.assertRaisesRegex(SchemaError, "unknown fields"):
            parse_synthetic_batch(payload)

    def test_non_lab_identifier_is_rejected(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["tickets"][0]["ticket_id"] = "REAL-TKT-001"
        with self.assertRaisesRegex(SchemaError, "synthetic format"):
            parse_synthetic_batch(payload)

    def test_false_synthetic_declaration_is_rejected(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["synthetic_only"] = False
        with self.assertRaisesRegex(SchemaError, "must be true"):
            parse_synthetic_batch(payload)

    def test_malformed_observation_is_rejected(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["tickets"][0]["observations"][0]["extra"] = "not allowed"
        with self.assertRaisesRegex(SchemaError, "unknown fields"):
            parse_synthetic_batch(payload)


class RedactionTests(unittest.TestCase):
    def test_structured_sensitive_values_are_redacted(self) -> None:
        email = "lab.user" + chr(64) + "example.invalid"
        phone = "602" + "-555-" + "0147"
        address = "192" + ".0.2.25"
        secret = "api_" + "key=LABVALUE"
        text = f"Contact {email}, {phone}; address {address}; {secret}"

        result = redact_text(text)

        self.assertEqual(result.count, 4)
        self.assertNotIn(email, result.text)
        self.assertNotIn(phone, result.text)
        self.assertNotIn(address, result.text)
        self.assertNotIn("LABVALUE", result.text)
        self.assertIn("[REDACTED_EMAIL]", result.text)
        self.assertIn("[REDACTED_SECRET]", result.text)

    def test_ticket_redaction_precedes_triage(self) -> None:
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))["tickets"][0]
        raw = copy.deepcopy(raw)
        email = "operator" + chr(64) + "example.invalid"
        raw["description"] += f" Contact reference: {email}."
        ticket = parse_ticket(raw)

        result = redact_ticket(ticket)

        self.assertEqual(result.count, 1)
        self.assertNotIn(email, result.ticket.description)


class TriageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tickets = load_synthetic_batch(FIXTURE)

    def test_deterministic_severity_category_and_ownership(self) -> None:
        first = triage_ticket(self.tickets[0], DuplicateIndex())
        second = triage_ticket(self.tickets[1], DuplicateIndex())

        self.assertEqual((first.severity, first.category, first.ownership), (
            "medium",
            "configuration",
            "application_support",
        ))
        self.assertEqual(second.severity, "critical")
        self.assertEqual((second.category, second.ownership), (
            "integration",
            "integration_support",
        ))

    def test_completeness_holds_block_incomplete_intake(self) -> None:
        result = triage_ticket(self.tickets[2], DuplicateIndex())

        self.assertIn("impact_not_confirmed", result.completeness_holds)
        self.assertIn("observations_missing", result.completeness_holds)
        self.assertEqual(result.approval_state, "blocked_by_holds")
        self.assertTrue(result.response_outline.open_questions)

    def test_duplicate_detection_holds_normalized_repeat(self) -> None:
        index = DuplicateIndex()
        first = triage_ticket(self.tickets[0], index)
        repeated = triage_ticket(self.tickets[3], index)

        self.assertIsNone(first.duplicate_of)
        self.assertEqual(repeated.duplicate_of, self.tickets[0].ticket_id)
        self.assertTrue(repeated.duplicate_holds[0].startswith("possible_duplicate:"))

    def test_ambiguity_and_safety_signals_hold_for_human_review(self) -> None:
        ambiguous = triage_ticket(self.tickets[4], DuplicateIndex())
        safety = triage_ticket(self.tickets[5], DuplicateIndex())

        self.assertIn("access_signal_workflow_conflict", ambiguous.ambiguity_holds)
        self.assertIn("safety_signal_requires_review", safety.ambiguity_holds)
        self.assertEqual(safety.severity, "critical")

    def test_response_outline_never_fabricates_resolution(self) -> None:
        result = triage_ticket(self.tickets[0], DuplicateIndex())
        outline = result.response_outline.to_dict()

        self.assertEqual(outline["resolution_status"], "not_verified")
        self.assertIn("No resolution is claimed", outline["resolution_statement"])
        self.assertEqual(len(outline["evidence"]), len(self.tickets[0].observations))

    def test_explicit_human_approval_gate(self) -> None:
        eligible = triage_ticket(self.tickets[0], DuplicateIndex())
        held = triage_ticket(self.tickets[2], DuplicateIndex())

        with self.assertRaises(ApprovalError):
            approve_triage(eligible, "")
        approved = approve_triage(eligible, APPROVAL_CONFIRMATION)
        self.assertEqual(approved.approval_state, "approved_by_human")
        self.assertIn("No resolution has been verified", approved.approved_reply or "")
        with self.assertRaises(ApprovalError):
            approve_triage(held, APPROVAL_CONFIRMATION)


class AuditAndPipelineTests(unittest.TestCase):
    def test_missing_audit_is_not_reported_as_a_valid_existing_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "missing.jsonl"
            with self.assertRaisesRegex(AuditIntegrityError, "does not exist"):
                verify_audit(path)

    def test_append_only_audit_chain_verifies_and_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "audit.jsonl"
            clock = lambda: "2026-01-15T12:00:00Z"  # noqa: E731
            audit = AuditLog(path, now=clock)
            audit.append("ticket_received", "LAB-TKT-1001", {"synthetic": True})
            first_size = path.stat().st_size
            audit.append("approval_pending", "LAB-TKT-1001", {"hold_count": 0})

            verification = verify_audit(path)
            self.assertTrue(verification["ok"])
            self.assertEqual(verification["entries"], 2)
            self.assertGreater(path.stat().st_size, first_size)

            lines = path.read_text(encoding="utf-8").splitlines()
            lines[0] = lines[0].replace("ticket_received", "triage_completed")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaises(AuditIntegrityError):
                verify_audit(path)

    def test_pipeline_outputs_json_ready_records_and_approval_counts(self) -> None:
        tickets = load_synthetic_batch(FIXTURE)
        payload = process_tickets(tickets, approve_eligible=True)

        self.assertTrue(payload["synthetic_only"])
        self.assertTrue(payload["offline_only"])
        self.assertEqual(payload["summary"]["ticket_count"], 6)
        self.assertEqual(payload["summary"]["approval_counts"]["approved_by_human"], 2)
        json.dumps(payload)

    def test_cli_writes_json_and_verifiable_append_only_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary = Path(temporary_directory)
            audit_path = temporary / "audit.jsonl"
            output_path = temporary / "output.json"
            command = [
                sys.executable,
                "-B",
                str(ROOT / "workbench.py"),
                "triage",
                str(FIXTURE),
                "--audit",
                str(audit_path),
                "--output",
                str(output_path),
            ]
            completed = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["ticket_count"], 6)
            self.assertEqual(payload["summary"]["approval_counts"]["pending_human_approval"], 2)
            self.assertTrue(verify_audit(audit_path)["ok"])


if __name__ == "__main__":
    unittest.main()
