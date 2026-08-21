from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = (ROOT / "README.md", ROOT / "CLAIMS_AND_BOUNDARIES.md", ROOT / "PROVENANCE.md")


class PublicContractTests(unittest.TestCase):
    def test_public_docs_are_present_and_have_persistent_boundary(self) -> None:
        text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for phrase in (
            "INDEPENDENT PORTFOLIO DEMO",
            "SYNTHETIC SUPPORT RECORDS",
            "NO AFFILIATION",
            "NO SEND ACTION",
        ):
            self.assertIn(phrase, text)

    def test_restrictive_project_license_is_not_carried_into_release(self) -> None:
        self.assertFalse((ROOT / "LICENSE").exists())
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("common root `LICENSE`", readme)
        self.assertNotIn("public inclusion remains blocked until", readme)
        self.assertNotIn("Source" + "-Available Hiring Review License", readme)

    def test_docs_have_no_contact_private_path_or_named_company(self) -> None:
        text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        self.assertIsNone(re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I))
        self.assertNotIn("/" + "home/", text)
        self.assertNotIn("job-" + "search", text.lower())
        self.assertNotIn("hospitality", text.lower())

    def test_publication_scanner_passes_public_tree(self) -> None:
        result = subprocess.run(
            ["python3", "-B", str(ROOT / "tools" / "publication_scan.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"ok": true', result.stdout)


if __name__ == "__main__":
    unittest.main()
