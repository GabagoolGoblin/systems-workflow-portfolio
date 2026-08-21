from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from wcag_harness.cli import _run, main
from wcag_harness.engine import execute_suite
from wcag_harness.io_utils import canonical_json_bytes, sha256
from wcag_harness.model import ContractInputError
from wcag_harness.reports import verify_report_bundle

PROJECT = Path(__file__).resolve().parents[1]


class EngineAndAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name) / "project"
        shutil.copytree(PROJECT / "fixtures", self.project / "fixtures")
        self.manifest = self.project / "fixtures" / "manifest.json"
        self.output = self.project / "build"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _manifest_data(self) -> dict:
        return json.loads(self.manifest.read_text(encoding="utf-8"))

    def _write_manifest(self, value: dict) -> None:
        self.manifest.write_bytes(canonical_json_bytes(value, pretty=True))

    def test_reference_suite_matches_and_verifies(self) -> None:
        result, exit_code = _run(self.manifest, self.output)
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["status"], "matched")
        verified = verify_report_bundle(
            self.output / "audit.json", self.output / "audit.sha256"
        )
        self.assertEqual(verified["status"], "verified")
        self.assertEqual(verified["inputs_verified"], 4)
        self.assertEqual(verified["outputs_verified"], 3)
        boundary = "INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION"
        self.assertIn(boundary, (self.output / "report.html").read_text(encoding="utf-8"))
        self.assertIn(boundary, (PROJECT / "demo" / "index.html").read_text(encoding="utf-8"))

    def test_repeat_run_is_byte_stable(self) -> None:
        _run(self.manifest, self.output)
        first = {
            path.name: path.read_bytes()
            for path in self.output.iterdir()
            if path.is_file()
        }
        _run(self.manifest, self.output)
        second = {
            path.name: path.read_bytes()
            for path in self.output.iterdir()
            if path.is_file()
        }
        self.assertEqual(first, second)

    def test_changed_fixture_fails_audit_verification(self) -> None:
        _run(self.manifest, self.output)
        fixture = self.project / "fixtures/components/accessible-operations-panel.html"
        fixture.write_text(fixture.read_text() + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ContractInputError, "digest mismatch"):
            verify_report_bundle(self.output / "audit.json", self.output / "audit.sha256")

    def test_changed_report_fails_audit_verification(self) -> None:
        _run(self.manifest, self.output)
        report = self.output / "report.md"
        report.write_text("tampered\n", encoding="utf-8")
        with self.assertRaisesRegex(ContractInputError, "digest mismatch"):
            verify_report_bundle(self.output / "audit.json", self.output / "audit.sha256")

    def test_changed_audit_fails_seal_verification(self) -> None:
        _run(self.manifest, self.output)
        audit = self.output / "audit.json"
        audit.write_text(audit.read_text() + " ", encoding="utf-8")
        with self.assertRaisesRegex(ContractInputError, "seal"):
            verify_report_bundle(audit, self.output / "audit.sha256")

    def test_unknown_manifest_key_rejected_before_output(self) -> None:
        manifest = self._manifest_data()
        manifest["surprise"] = True
        self._write_manifest(manifest)
        with self.assertRaisesRegex(ContractInputError, "unknown"):
            _run(self.manifest, self.output)
        self.assertFalse(self.output.exists())

    def test_duplicate_manifest_key_rejected(self) -> None:
        raw = self.manifest.read_text(encoding="utf-8")
        self.manifest.write_text(
            raw.replace('  "cases": [', '  "cases": [],\n  "cases": [', 1),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ContractInputError, "duplicate object key"):
            execute_suite(self.manifest)

    def test_unknown_rule_rejected(self) -> None:
        manifest = self._manifest_data()
        manifest["rules"].append("browser-magic")
        self._write_manifest(manifest)
        with self.assertRaisesRegex(ContractInputError, "unknown rule"):
            execute_suite(self.manifest)

    def test_float_schema_version_is_rejected(self) -> None:
        manifest = self._manifest_data()
        manifest["schema_version"] = 1.0
        self._write_manifest(manifest)
        with self.assertRaisesRegex(ContractInputError, "integer 1"):
            execute_suite(self.manifest)

    def test_expected_fingerprint_mismatch_is_a_regression(self) -> None:
        manifest = self._manifest_data()
        manifest["cases"][1]["expected_violations"] = []
        self._write_manifest(manifest)
        result, exit_code = _run(self.manifest, self.output)
        self.assertEqual(exit_code, 1)
        self.assertEqual(result["status"], "regression")
        report = json.loads((self.output / "report.json").read_text())
        self.assertGreater(len(report["cases"][1]["unexpected"]), 0)

    def test_fixture_path_escape_rejected(self) -> None:
        manifest = self._manifest_data()
        manifest["cases"][0]["html"] = "../escape.html"
        self._write_manifest(manifest)
        with self.assertRaisesRegex(ContractInputError, "normalized relative"):
            execute_suite(self.manifest)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_fixture_symlink_rejected(self) -> None:
        original = self.project / "fixtures/components/accessible-operations-panel.html"
        target = self.project / "fixtures/components/real.html"
        original.rename(target)
        original.symlink_to(target.name)
        with self.assertRaisesRegex(ContractInputError, "symlink"):
            execute_suite(self.manifest)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_fixture_parent_symlink_rejected(self) -> None:
        components = self.project / "fixtures/components"
        real_components = self.project / "fixtures/real-components"
        components.rename(real_components)
        components.symlink_to(real_components.name, target_is_directory=True)
        with self.assertRaisesRegex(ContractInputError, "symlink"):
            execute_suite(self.manifest)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_output_directory_symlink_rejected(self) -> None:
        real_output = self.project / "real-build"
        real_output.mkdir()
        self.output.symlink_to(real_output.name, target_is_directory=True)
        with self.assertRaisesRegex(ContractInputError, "symlink"):
            _run(self.manifest, self.output)

    def test_matching_seal_does_not_make_unknown_audit_schema_valid(self) -> None:
        _run(self.manifest, self.output)
        audit_path = self.output / "audit.json"
        audit = json.loads(audit_path.read_text())
        audit["unknown"] = "field"
        raw = canonical_json_bytes(audit, pretty=True)
        audit_path.write_bytes(raw)
        (self.output / "audit.sha256").write_text(
            f"{sha256(raw)}  audit.json\n", encoding="ascii"
        )
        with self.assertRaisesRegex(ContractInputError, "unknown keys"):
            verify_report_bundle(audit_path, self.output / "audit.sha256")

    def test_matching_seal_does_not_make_float_audit_version_valid(self) -> None:
        _run(self.manifest, self.output)
        audit_path = self.output / "audit.json"
        audit = json.loads(audit_path.read_text())
        audit["schema_version"] = 1.0
        raw = canonical_json_bytes(audit, pretty=True)
        audit_path.write_bytes(raw)
        (self.output / "audit.sha256").write_text(
            f"{sha256(raw)}  audit.json\n", encoding="ascii"
        )
        with self.assertRaisesRegex(ContractInputError, "unsupported audit"):
            verify_report_bundle(audit_path, self.output / "audit.sha256")

    def test_resealed_report_with_unknown_key_is_rejected(self) -> None:
        _run(self.manifest, self.output)
        report_path = self.output / "report.json"
        report = json.loads(report_path.read_text())
        report["unknown"] = "field"
        report_raw = canonical_json_bytes(report, pretty=True)
        report_path.write_bytes(report_raw)

        audit_path = self.output / "audit.json"
        audit = json.loads(audit_path.read_text())
        report_digest = sha256(report_raw)
        audit["report_json_sha256"] = report_digest
        for item in audit["files"]:
            if item["role"] == "output" and item["path"].endswith("/report.json"):
                item["sha256"] = report_digest
        audit_raw = canonical_json_bytes(audit, pretty=True)
        audit_path.write_bytes(audit_raw)
        (self.output / "audit.sha256").write_text(
            f"{sha256(audit_raw)}  audit.json\n", encoding="ascii"
        )
        with self.assertRaisesRegex(ContractInputError, "report.*unknown keys"):
            verify_report_bundle(audit_path, self.output / "audit.sha256")

    def test_demo_rejects_non_loopback_and_open_without_serve_before_output(self) -> None:
        for extra in (["--serve", "--host", "0.0.0.0"], ["--open"]):
            with self.subTest(extra=extra):
                stream = StringIO()
                with redirect_stdout(stream), redirect_stderr(stream):
                    exit_code = main(
                        [
                            "demo",
                            "--manifest",
                            str(self.manifest),
                            "--out",
                            str(self.output),
                            *extra,
                        ]
                    )
                self.assertEqual(exit_code, 2)
                self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
