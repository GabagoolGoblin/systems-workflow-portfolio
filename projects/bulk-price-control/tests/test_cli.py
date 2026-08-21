from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from price_tool.cli import main
from tests.support import write_catalog, write_changes


class CliTests(unittest.TestCase):
    def test_dry_run_emits_machine_readable_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = root / "catalog.json"
            changes = root / "changes.csv"
            write_catalog(catalog)
            write_changes(changes)
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(
                    [
                        "dry-run",
                        "--catalog",
                        str(catalog),
                        "--changes",
                        str(changes),
                    ]
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(0, code)
            self.assertTrue(payload["ok"])
            self.assertEqual(
                "hospitality-price-plan/v1",
                payload["result"]["schema_version"],
            )
            self.assertEqual(3, payload["result"]["summary"]["update_count"])

    def test_validation_failure_is_json_on_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = root / "catalog.json"
            changes = root / "changes.csv"
            write_catalog(catalog)
            changes.write_text("bad,header\n", encoding="utf-8")
            errors = io.StringIO()
            with redirect_stderr(errors):
                code = main(
                    [
                        "dry-run",
                        "--catalog",
                        str(catalog),
                        "--changes",
                        str(changes),
                    ]
                )
            payload = json.loads(errors.getvalue())
            self.assertEqual(2, code)
            self.assertEqual("validation_error", payload["error"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
