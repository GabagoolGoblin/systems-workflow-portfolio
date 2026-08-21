from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from integration_lab.core import ACKNOWLEDGEMENT, evaluate_files, verify_receipt
from tests.support import CONTRACT_PATH, ROOT, RUN_PATH


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [sys.executable, "-B", "-m", "integration_lab", *arguments],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )


class CliAndArtifactTests(unittest.TestCase):
    def test_demo_command_emits_verified_receipt(self) -> None:
        result = run_cli("demo")
        self.assertEqual(0, result.returncode, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertTrue(verify_receipt(receipt))
        self.assertFalse(receipt["production_claim"])

    def test_verify_command_accepts_exact_generated_receipt(self) -> None:
        result = run_cli("verify", "artifacts/synthetic_receipt.json")
        self.assertEqual(0, result.returncode, result.stderr)
        message = json.loads(result.stdout)
        self.assertTrue(message["ok"])
        self.assertEqual(11, message["audit_events"])

    def test_verify_command_rejects_tampered_receipt(self) -> None:
        receipt = json.loads((ROOT / "artifacts/synthetic_receipt.json").read_text(encoding="utf-8"))
        receipt["exchange"]["network_calls"] = 1
        with tempfile.TemporaryDirectory(prefix="api-contract-test-") as directory:
            path = Path(directory) / "tampered-receipt.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            result = run_cli("verify", str(path))
        self.assertEqual(2, result.returncode)
        self.assertFalse(json.loads(result.stdout)["ok"])

    def test_promote_command_requires_exact_gate_material(self) -> None:
        base = evaluate_files(CONTRACT_PATH, RUN_PATH)
        result = run_cli(
            "promote",
            "--confirm-token",
            base["promotion_gate"]["confirm_token"],
            "--acknowledge",
            ACKNOWLEDGEMENT,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        promoted = json.loads(result.stdout)
        self.assertEqual("simulated_promoted", promoted["promotion_gate"]["state"])
        self.assertFalse(promoted["promotion_gate"]["production_write"])
        self.assertTrue(verify_receipt(promoted))

    def test_promote_command_fails_closed_on_wrong_token(self) -> None:
        result = run_cli(
            "promote",
            "--confirm-token",
            "review_0000000000000000",
            "--acknowledge",
            ACKNOWLEDGEMENT,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("exact review token required", json.loads(result.stdout)["error"])

    def test_generated_receipt_is_exact_current_evaluation(self) -> None:
        generated = json.loads((ROOT / "artifacts/synthetic_receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(evaluate_files(CONTRACT_PATH, RUN_PATH), generated)

    def test_browser_snapshot_is_exact_current_fixture_and_report(self) -> None:
        raw = (ROOT / "data/demo_snapshot.js").read_text(encoding="utf-8")
        prefix = '"use strict";\n// Generated from the exact synthetic fixture by scripts/build_artifacts.py.\nwindow.API_LAB_SNAPSHOT = '
        self.assertTrue(raw.startswith(prefix))
        self.assertTrue(raw.endswith(";\n"))
        snapshot = json.loads(raw[len(prefix) : -2])
        self.assertEqual(evaluate_files(CONTRACT_PATH, RUN_PATH), snapshot["report"])
        self.assertEqual(json.loads(CONTRACT_PATH.read_text(encoding="utf-8")), snapshot["contract"])
        self.assertEqual(json.loads(RUN_PATH.read_text(encoding="utf-8")), snapshot["run"])

    def test_artifact_builder_requires_explicit_confirmation(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONPATH"] = str(ROOT)
        result = subprocess.run(
            [sys.executable, "-B", "scripts/build_artifacts.py", "--confirm", "WRONG"],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("SYNTHETIC_ARTIFACTS", result.stderr)


if __name__ == "__main__":
    unittest.main()
