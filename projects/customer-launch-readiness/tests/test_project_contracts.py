from __future__ import annotations

import re
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILES = (ROOT / "index.html", ROOT / "styles.css", ROOT / "app.js")
DOC_FILES = (
    ROOT / "README.md",
    ROOT / "CLAIMS_AND_BOUNDARIES.md",
    ROOT / "PROVENANCE.md",
    ROOT / "DEMO_SCRIPT.md",
)
SCRIPT_FILES = (
    ROOT / "scripts" / "security_privacy_scan.py",
    ROOT / "scripts" / "interaction_smoke.py",
)
BOUNDARY = (
    "INDEPENDENT PORTFOLIO DEMO",
    "SYNTHETIC DATA",
    "NO AFFILIATION",
    "NO PRODUCTION ACTION",
)


class ShellParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.lang: str | None = None
        self.ids: list[str] = []
        self.views: list[str] = []
        self.has_main = False
        self.has_nav = False
        self.has_live_region = False
        self.csp: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.lang = values.get("lang")
        if values.get("id"):
            self.ids.append(str(values["id"]))
        if tag == "main":
            self.has_main = True
        if tag == "nav":
            self.has_nav = True
        if values.get("aria-live"):
            self.has_live_region = True
        if tag == "button" and values.get("data-view"):
            self.views.append(str(values["data-view"]))
        if tag == "meta" and values.get("http-equiv") == "Content-Security-Policy":
            self.csp = values.get("content")


def section(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


class ProjectContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = {path.name: path.read_text(encoding="utf-8") for path in RUNTIME_FILES}
        cls.runtime_text = "\n".join(cls.runtime.values())
        cls.public_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (*RUNTIME_FILES, *DOC_FILES, *SCRIPT_FILES, ROOT / "Makefile")
        )

    def test_required_public_files_exist(self) -> None:
        for path in (*RUNTIME_FILES, *DOC_FILES, *SCRIPT_FILES, ROOT / "Makefile"):
            self.assertTrue(path.is_file(), path)
            self.assertGreater(path.stat().st_size, 20)

    def test_shell_has_permanent_four_part_boundary(self) -> None:
        html = self.runtime["index.html"]
        for phrase in BOUNDARY:
            self.assertIn(phrase, html)
        self.assertIn("does not represent vendor software", html)

    def test_semantic_shell_has_six_ordered_views_and_unique_ids(self) -> None:
        parser = ShellParser()
        parser.feed(self.runtime["index.html"])
        self.assertEqual(parser.lang, "en")
        self.assertTrue(parser.has_main and parser.has_nav and parser.has_live_region)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertEqual(parser.views, ["overview", "discovery", "readiness", "exceptions", "enablement", "acceptance"])
        script = self.runtime["app.js"]
        self.assertIn("function revealActiveNavigation()", script)
        self.assertIn('window.matchMedia("(max-width: 1050px)")', script)
        self.assertIn("nav.scrollLeft = Math.max(0, centered)", script)

    def test_content_security_policy_closes_connections_and_forms(self) -> None:
        parser = ShellParser()
        parser.feed(self.runtime["index.html"])
        self.assertIn("connect-src 'none'", parser.csp or "")
        self.assertIn("form-action 'none'", parser.csp or "")
        self.assertIn("object-src 'none'", parser.csp or "")

    def test_fixture_ids_are_unique_and_expected(self) -> None:
        expected = {
            "DS": ["DS-01", "DS-02", "DS-03", "DS-04"],
            "RD": [f"RD-{number:02d}" for number in range(1, 9)],
            "EX": ["EX-17", "EX-22", "EX-29"],
            "UAT": ["UAT-01", "UAT-02", "UAT-03", "UAT-04"],
            "TRN": ["TRN-01", "TRN-02", "TRN-03"],
            "HO": ["HO-01", "HO-02", "HO-03", "HO-04"],
        }
        declarations = re.findall(r'\bid: "((?:DS|RD|EX|UAT|TRN|HO)-\d+)"', self.runtime["app.js"])
        for prefix, ids in expected.items():
            actual = [value for value in declarations if value.startswith(f"{prefix}-")]
            self.assertEqual(actual, ids)
            self.assertEqual(len(actual), len(set(actual)))

    def test_three_scenarios_and_six_workflow_dimensions_exist(self) -> None:
        script = self.runtime["app.js"]
        self.assertIn('const SCENARIOS = ["baseline", "recovery", "review-ready"]', script)
        for phrase in (
            "Discovery + scope", "Integration readiness", "Customer-owner handoffs",
            "UAT + exceptions", "Training + adoption", "Go-live acceptance",
        ):
            self.assertIn(phrase, self.runtime_text)

    def test_readiness_and_exception_transitions_require_review(self) -> None:
        script = self.runtime["app.js"]
        readiness = section(script, "function advanceReadiness(id) {", "\n}\n\nfunction advanceException")
        exception = section(script, "function advanceException(id) {", "\n}\n\nfunction exportAudit")
        for block in (readiness, exception):
            self.assertIn('"review_ready"', block)
            self.assertIn("no automatic", block)
        self.assertIn('state.exceptionStatuses[id] = "accepted"', exception)

    def test_nine_acceptance_gates_and_human_boundary_exist(self) -> None:
        block = section(self.runtime["app.js"], "function acceptanceChecks() {", "\n}\n\nfunction renderAcceptance")
        ids = re.findall(r'\{ id: "([a-z_]+)", title:', block)
        self.assertEqual(ids, ["discovery", "readiness", "uat", "exceptions", "training", "handoff", "status", "first_value", "acceptance"])
        self.assertIn("checks.slice(0, -1).every", self.runtime["app.js"])
        self.assertIn("grants no production authority", self.runtime["app.js"])

    def test_export_is_explicit_local_and_scoped(self) -> None:
        script = self.runtime["app.js"]
        for token in (
            "function exportAudit()", "new Blob", "URL.createObjectURL",
            "generated_by_user_action: true", "runtime_network_used: false",
            "independent_portfolio_demo: true", "not_production_authority: true",
        ):
            self.assertIn(token, script)

    def test_runtime_has_no_network_persistence_or_embedding_primitive(self) -> None:
        for pattern in (
            r"https?://", r"\bfetch\s*\(", r"\bXMLHttpRequest\b", r"\bWebSocket\b",
            r"\bsendBeacon\b", r"\bEventSource\b", r"<iframe\b", r"\blocalStorage\b",
            r"\bsessionStorage\b", r"\bindexedDB\b", r"document\.cookie",
        ):
            self.assertIsNone(re.search(pattern, self.runtime_text, re.I), pattern)

    def test_operator_note_is_escaped_and_bounded(self) -> None:
        script = self.runtime["app.js"]
        self.assertIn("function escapeHTML(value)", script)
        self.assertIn("escapeHTML(state.discoveryNote)", script)
        self.assertIn("field.value.trim().slice(0, 280)", script)
        self.assertNotIn("${state.discoveryNote}", script)

    def test_company_job_search_contact_and_old_license_markers_are_absent(self) -> None:
        for marker in ("tex" + "ture", "secure" + "frame", "/" + "home/", "job-" + "search", "source-" + "available", "hiring " + "review"):
            self.assertNotIn(marker, self.public_text.lower())
        self.assertIsNone(re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", self.public_text, re.I))

    def test_public_docs_preserve_claim_and_provenance_limits(self) -> None:
        self.assertIn("No vendor product behavior", (ROOT / "CLAIMS_AND_BOUNDARIES.md").read_text(encoding="utf-8"))
        self.assertIn("No employer or customer code", (ROOT / "PROVENANCE.md").read_text(encoding="utf-8"))
        self.assertIn("not a deployment", (ROOT / "README.md").read_text(encoding="utf-8"))

    def test_security_scan_passes(self) -> None:
        result = subprocess.run(
            ["python3", "-B", str(ROOT / "scripts" / "security_privacy_scan.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OVERALL: PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
