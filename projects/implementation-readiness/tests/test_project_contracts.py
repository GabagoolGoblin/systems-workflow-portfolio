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
    ROOT / "scripts" / "interaction_smoke.py",
    ROOT / "scripts" / "security_privacy_scan.py",
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


def section(script: str, start: str, end: str) -> str:
    return script.split(start, 1)[1].split(end, 1)[0]


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
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 20)

    def test_shell_has_permanent_four_part_boundary(self) -> None:
        html = self.runtime["index.html"]
        for phrase in BOUNDARY:
            self.assertIn(phrase, html)
        self.assertIn("does not determine or certify compliance", html)

    def test_semantic_shell_has_six_ordered_views_and_unique_ids(self) -> None:
        parser = ShellParser()
        parser.feed(self.runtime["index.html"])
        self.assertEqual(parser.lang, "en")
        self.assertTrue(parser.has_main and parser.has_nav and parser.has_live_region)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertEqual(parser.views, ["overview", "gaps", "evidence", "actions", "acceptance", "audit"])

    def test_six_renderers_and_three_scenarios_exist(self) -> None:
        script = self.runtime["app.js"]
        for name in ("Overview", "Gaps", "Evidence", "Actions", "Acceptance", "Audit"):
            self.assertIn(f"function render{name}()", script)
        self.assertIn('new URLSearchParams(window.location.search)', script)
        self.assertIn('["default", "activity", "ready"]', script)

    def test_fixture_ids_are_unique_and_complete(self) -> None:
        script = self.runtime["app.js"]
        blocks = {
            "controls": section(script, "controls: [", "],\n  evidence:"),
            "evidence": section(script, "evidence: [", "],\n  gaps:"),
            "gaps": section(script, "gaps: [", "],\n  actions:"),
            "actions": section(script, "actions: [", "],\n  audit:"),
        }
        expected = {
            "controls": ["IR-01", "IR-02", "IR-03", "IR-04", "IR-05", "IR-06"],
            "evidence": ["EV-101", "EV-102", "EV-104", "EV-108", "EV-109", "EV-112", "EV-115", "EV-118"],
            "gaps": ["GAP-07", "GAP-12", "GAP-18", "GAP-22"],
            "actions": ["ACT-197", "ACT-204", "ACT-211", "ACT-219", "ACT-223"],
        }
        for kind, ids in expected.items():
            actual = re.findall(r'^\s+id: "([A-Z]+-\d+)",$', blocks[kind], re.MULTILINE)
            self.assertEqual(actual, ids)
            self.assertEqual(len(actual), len(set(actual)))

    def test_evidence_states_and_gap_gate_are_explicit(self) -> None:
        script = self.runtime["app.js"]
        evidence = section(script, "evidence: [", "],\n  gaps:")
        states = re.findall(r'^\s+state: "(accepted|qualified|conflict|missing)",$', evidence, re.MULTILINE)
        self.assertEqual(sorted(set(states)), ["accepted", "conflict", "missing", "qualified"])
        self.assertIn('state.gapStatuses[action.gapId] = "review_ready"', script)
        self.assertNotIn('state.gapStatuses[action.gapId] = "accepted"', script)

    def test_human_acknowledgement_is_distinct_from_prerequisites(self) -> None:
        script = self.runtime["app.js"]
        block = section(script, "function acceptanceChecks(control) {", "\n}\n\nfunction prerequisitesPass")
        ids = re.findall(r'\{ id: "([a-z]+)"', block)
        self.assertEqual(ids, ["owner", "mapping", "locator", "conflict", "gaps", "actions", "ack"])
        self.assertIn("Record reviewer acknowledgment", script)
        self.assertIn("It does not mean compliant, certified, production-ready", script)

    def test_export_is_local_and_user_triggered(self) -> None:
        script = self.runtime["app.js"]
        for token in ("function exportAudit()", "new Blob", "URL.createObjectURL", 'data-export-audit', "no compliance conclusion"):
            self.assertIn(token, script)

    def test_runtime_has_no_network_or_persistence_primitive(self) -> None:
        for pattern in (
            r"https?://", r"\bfetch\s*\(", r"\bXMLHttpRequest\b", r"\bWebSocket\b",
            r"\bsendBeacon\b", r"\bEventSource\b", r"<iframe\b", r"\blocalStorage\b",
            r"\bsessionStorage\b", r"\bindexedDB\b", r"document\.cookie",
        ):
            self.assertIsNone(re.search(pattern, self.runtime_text, re.IGNORECASE), pattern)

    def test_operator_search_is_escaped(self) -> None:
        script = self.runtime["app.js"]
        self.assertIn("function escapeHTML(value)", script)
        self.assertIn('value="${escapeHTML(state.search)}"', script)
        self.assertNotIn('value="${state.search}"', script)

    def test_company_private_path_and_contact_markers_are_absent(self) -> None:
        for marker in ("secure" + "frame", "tex" + "ture", "e" + "mc", "/" + "home/", "job-" + "search", "source-" + "available"):
            self.assertNotIn(marker, self.public_text.lower())
        self.assertIsNone(re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", self.public_text, re.I))

    def test_public_docs_preserve_claim_limits(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        claims = (ROOT / "CLAIMS_AND_BOUNDARIES.md").read_text(encoding="utf-8")
        provenance = (ROOT / "PROVENANCE.md").read_text(encoding="utf-8")
        self.assertIn("not compliance, certification", readme)
        self.assertIn("No production deployment", claims)
        self.assertIn("No employer or customer code", provenance)

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
