from __future__ import annotations

import re
import unittest

from tests.support import ROOT


class ProjectContractTests(unittest.TestCase):
    def test_required_project_files_exist(self) -> None:
        required = (
            "README.md",
            "DEMO_SCRIPT.md",
            "ARCHITECTURE.md",
            "CLAIMS_AND_BOUNDARIES.md",
            "PROVENANCE.md",
            "index.html",
            "styles.css",
            "app.js",
            "fixtures/synthetic_contract.json",
            "fixtures/synthetic_run.json",
            "artifacts/synthetic_receipt.json",
        )
        self.assertEqual([], [path for path in required if not (ROOT / path).is_file()])

    def test_permanent_four_part_boundary_is_visible(self) -> None:
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn(
            "INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION",
            html,
        )

    def test_six_workflow_screens_are_declared_once(self) -> None:
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertEqual(
            ["overview", "exchange", "inbox", "quarantine", "gate", "audit"],
            re.findall(r'data-view="([a-z]+)"', html),
        )

    def test_query_parameters_cannot_prefill_or_advance_gate(self) -> None:
        script = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn('let gateToken = "";', script)
        self.assertIn("let gateAcknowledged = false;", script)
        self.assertIn("let promoted = false;", script)
        self.assertNotRegex(script, r'query\.get\("scenario"\)\s*===')

    def test_review_token_is_explicitly_not_authentication(self) -> None:
        script = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertGreaterEqual(script.lower().count("not authentication"), 2)

    def test_runtime_uses_text_nodes_and_no_unsafe_html_sink(self) -> None:
        script = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn("node.textContent = text", script)
        self.assertNotRegex(script, r"innerHTML|outerHTML|insertAdjacentHTML|document\.write")

    def test_csp_denies_connections_forms_objects_and_frames(self) -> None:
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        for directive in ("connect-src 'none'", "form-action 'none'", "object-src 'none'", "frame-src 'none'"):
            self.assertIn(directive, html)

    def test_project_has_no_nested_repository_or_bytecode_cache(self) -> None:
        self.assertFalse((ROOT / ".git").exists())
        self.assertEqual([], list(ROOT.rglob("__pycache__")))
        self.assertEqual([], list(ROOT.rglob("*.pyc")))


if __name__ == "__main__":
    unittest.main()
