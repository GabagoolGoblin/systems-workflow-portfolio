from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import CONTRACT_PATH, EVIDENCE_PATH, PROJECT_ROOT


class CLITests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
        return subprocess.run(
            [sys.executable, "-B", "-m", "claim_evidence_contract_linter", *arguments],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_demo_is_dry_run_and_returns_findings_exit(self):
        result = self.run_cli("demo")
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["summary"]["finding_count"], 2)
        self.assertEqual(result.stderr, "")

    def test_explicit_lint_matches_demo_digest(self):
        demo = self.run_cli("demo")
        lint = self.run_cli(
            "lint",
            "--contract",
            str(CONTRACT_PATH),
            "--evidence",
            str(EVIDENCE_PATH),
        )
        self.assertEqual(lint.returncode, 1)
        self.assertEqual(
            json.loads(demo.stdout)["report_digest"],
            json.loads(lint.stdout)["report_digest"],
        )

    def test_output_requires_exact_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            result = self.run_cli("demo", "--output", str(output))
            self.assertEqual(result.returncode, 2)
            self.assertIn("INVALID_INPUT", result.stderr)
            self.assertFalse(output.exists())

    def test_confirmation_without_output_is_invalid(self):
        result = self.run_cli("demo", "--confirm-local-write", "LOCAL_ONLY")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid without --output", result.stderr)

    def test_wrong_confirmation_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            result = self.run_cli(
                "demo",
                "--output",
                str(output),
                "--confirm-local-write",
                "local_only",
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())

    def test_confirmed_write_creates_private_report_and_returns_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            result = self.run_cli(
                "demo",
                "--output",
                str(output),
                "--confirm-local-write",
                "LOCAL_ONLY",
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            status = json.loads(result.stdout)
            self.assertEqual(status["finding_count"], 2)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertIn("report_digest", json.loads(output.read_text(encoding="utf-8")))

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            output.write_text("sentinel", encoding="utf-8")
            result = self.run_cli(
                "demo",
                "--output",
                str(output),
                "--confirm-local-write",
                "LOCAL_ONLY",
            )
            self.assertEqual(result.returncode, 4)
            self.assertIn("LOCAL_IO_ERROR", result.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "sentinel")

    def test_saved_report_verifies(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            write = self.run_cli(
                "demo",
                "--output",
                str(output),
                "--confirm-local-write",
                "LOCAL_ONLY",
            )
            self.assertEqual(write.returncode, 1)
            verify = self.run_cli(
                "verify",
                "--report",
                str(output),
                "--contract",
                str(CONTRACT_PATH),
                "--evidence",
                str(EVIDENCE_PATH),
            )
            self.assertEqual(verify.returncode, 0, verify.stderr)
            self.assertTrue(json.loads(verify.stdout)["verified"])

    def test_tampered_saved_report_returns_audit_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            self.run_cli(
                "demo",
                "--output",
                str(output),
                "--confirm-local-write",
                "LOCAL_ONLY",
            )
            report = json.loads(output.read_text(encoding="utf-8"))
            report["summary"]["supported"] = 500
            output.write_text(json.dumps(report), encoding="utf-8")
            verify = self.run_cli(
                "verify",
                "--report",
                str(output),
                "--contract",
                str(CONTRACT_PATH),
                "--evidence",
                str(EVIDENCE_PATH),
            )
            self.assertEqual(verify.returncode, 3)
            self.assertIn("AUDIT_MISMATCH", verify.stderr)

    def test_exact_input_byte_drift_returns_audit_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            changed_contract = Path(directory) / "contract.json"
            self.run_cli(
                "demo",
                "--output",
                str(output),
                "--confirm-local-write",
                "LOCAL_ONLY",
            )
            changed_contract.write_bytes(CONTRACT_PATH.read_bytes() + b" ")
            verify = self.run_cli(
                "verify",
                "--report",
                str(output),
                "--contract",
                str(changed_contract),
                "--evidence",
                str(EVIDENCE_PATH),
            )
            self.assertEqual(verify.returncode, 3)
            self.assertIn("does not exactly match", verify.stderr)

    def test_missing_input_is_local_io_exit(self):
        result = self.run_cli(
            "lint",
            "--contract",
            "/definitely/not/here/contract.json",
            "--evidence",
            str(EVIDENCE_PATH),
        )
        self.assertEqual(result.returncode, 4)
        self.assertIn("LOCAL_IO_ERROR", result.stderr)

    def test_invalid_json_is_invalid_input_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "invalid.json"
            invalid.write_text('{"broken":', encoding="utf-8")
            result = self.run_cli(
                "lint",
                "--contract",
                str(invalid),
                "--evidence",
                str(EVIDENCE_PATH),
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("INVALID_INPUT", result.stderr)


if __name__ == "__main__":
    unittest.main()

