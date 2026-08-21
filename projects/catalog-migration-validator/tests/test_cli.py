from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from migration_tool.cli import main
from tests.support import mapping, source, target, write_json


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.json"
        self.target = self.root / "target.json"
        self.mapping = self.root / "mapping.json"
        write_json(self.source, source())
        write_json(self.target, target())
        write_json(self.mapping, mapping())

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_dry_run_emits_machine_readable_reconciliation(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(
                [
                    "dry-run",
                    "--source",
                    str(self.source),
                    "--target",
                    str(self.target),
                    "--mapping",
                    str(self.mapping),
                ]
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(0, code)
        self.assertTrue(payload["ok"])
        self.assertEqual(1, payload["result"]["plan"]["reconciliation"]["inserts"])
        self.assertEqual(2, payload["result"]["quarantine"]["quarantined_count"])

    def test_validation_error_is_machine_readable(self) -> None:
        value = mapping()
        value["field_mappings"].pop()
        write_json(self.mapping, value)
        errors = io.StringIO()
        with redirect_stderr(errors):
            code = main(
                [
                    "dry-run",
                    "--source",
                    str(self.source),
                    "--target",
                    str(self.target),
                    "--mapping",
                    str(self.mapping),
                ]
            )
        payload = json.loads(errors.getvalue())
        self.assertEqual(2, code)
        self.assertEqual("validation_error", payload["error"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
