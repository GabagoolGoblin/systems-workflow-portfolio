from __future__ import annotations

import re
import struct
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parents[1]
TEXT_FILES = [
    ROOT / "index.html",
    ROOT / "styles.css",
    ROOT / "app.js",
    ROOT / "README.md",
    ROOT / "PROVENANCE.md",
    ROOT / "CLAIMS_AND_BOUNDARIES.md",
]


class AppShellParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.html_lang = None
        self.ids: list[str] = []
        self.view_buttons: list[str] = []
        self.button_aria_labels: list[str] = []
        self.has_main = False
        self.has_nav = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "html":
            self.html_lang = attributes.get("lang")
        if "id" in attributes:
            self.ids.append(str(attributes["id"]))
        if tag == "main":
            self.has_main = True
        if tag == "nav":
            self.has_nav = True
        if tag == "button" and "data-view" in attributes:
            self.view_buttons.append(str(attributes["data-view"]))
        if tag == "button" and "aria-label" in attributes:
            self.button_aria_labels.append(str(attributes["aria-label"]))


class ProjectContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = {path.name: path.read_text(encoding="utf-8") for path in TEXT_FILES}

    def test_required_public_files_exist_and_are_nonempty(self) -> None:
        for path in TEXT_FILES:
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 100)

    def test_app_shell_has_landmarks_and_unique_ids(self) -> None:
        parser = AppShellParser()
        parser.feed(self.text["index.html"])
        self.assertIn(
            "INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION",
            self.text["index.html"],
        )
        self.assertEqual(parser.html_lang, "en")
        self.assertTrue(parser.has_main)
        self.assertTrue(parser.has_nav)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertEqual(parser.view_buttons, ["control", "diff", "approval", "audit"])
        self.assertIn("Demo reviewer profile", parser.button_aria_labels)
        avatar = re.search(
            r'<button class="avatar-button"[^>]*>([^<]+)</button>',
            self.text["index.html"],
        )
        self.assertIsNotNone(avatar)
        self.assertEqual(avatar.group(1), "RV")

    def test_all_four_renderers_and_query_views_exist(self) -> None:
        script = self.text["app.js"]
        for view in ("control", "diff", "approval", "audit"):
            with self.subTest(view=view):
                self.assertIn(f'{view}: "', script)
                self.assertRegex(script, rf"function render{view.title()}\(")
        self.assertIn('new URLSearchParams(window.location.search).get("view")', script)

    def test_fixture_counts_match_visible_summary(self) -> None:
        script = self.text["app.js"]
        record_block = script.split("records: [", 1)[1].split("],\n  queue:", 1)[0]
        ids = re.findall(r'id: "(SYN-\d{4})"', record_block)
        statuses = re.findall(r'status: "(verified|review|held)"', record_block)
        self.assertEqual(len(ids), 12)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(statuses.count("verified"), 9)
        self.assertEqual(statuses.count("review"), 1)
        self.assertEqual(statuses.count("held"), 2)
        self.assertIn('recordSummary: { total: 12, verified: 9, review: 1, held: 2 }', script)

    def test_unknown_state_is_explicit_and_never_guessed(self) -> None:
        script = self.text["app.js"]
        self.assertIn('after: "Unknown"', script)
        self.assertIn("the demo never guesses", script)
        self.assertIn("No destination is connected", script)
        self.assertIn("no external action occurred", script)

    def test_filter_selection_and_audit_trace_contracts_exist(self) -> None:
        script = self.text["app.js"]
        self.assertIn("!records.some(record => record.id === state.selectedId)", script)
        self.assertIn('data-audit-record="${event.recordId}"', script)
        self.assertIn('navigate("diff")', script)

    def test_runtime_has_no_external_network_primitives_or_remote_assets(self) -> None:
        runtime = self.text["index.html"] + self.text["styles.css"] + self.text["app.js"]
        forbidden = [
            r"https?://",
            r"\bfetch\s*\(",
            r"\bXMLHttpRequest\b",
            r"\bWebSocket\b",
            r"\bnavigator\.sendBeacon\b",
            r"<iframe\b",
            r"<img[^>]+src=[\"']//",
        ]
        for pattern in forbidden:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, runtime, re.IGNORECASE))

    def test_no_contact_details_or_source_map_markers(self) -> None:
        runtime = self.text["index.html"] + self.text["styles.css"] + self.text["app.js"]
        self.assertNotRegex(runtime, r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
        self.assertNotIn("sourceMappingURL", runtime)

    def test_user_controlled_search_is_escaped_before_html_render(self) -> None:
        script = self.text["app.js"]
        self.assertIn("function escapeHTML(value)", script)
        self.assertIn('value="${escapeHTML(state.search)}"', script)

    def test_public_claim_limits_are_documented(self) -> None:
        provenance = self.text["PROVENANCE.md"]
        readme = self.text["README.md"]
        claims = self.text["CLAIMS_AND_BOUNDARIES.md"]
        self.assertIn("No historical employer screenshot", provenance)
        self.assertIn("not an integration or production automation claim", readme)
        self.assertIn("Not supported", claims)
        self.assertIn(
            "Owner-created files are governed only by the repository root `LICENSE`.",
            readme,
        )
        self.assertIn(
            "No additional rights are granted beyond that notice, GitHub's Terms, or applicable law.",
            readme,
        )
        self.assertIn(
            "The root `LICENSE` governs owner-created material.",
            provenance,
        )
        stale = (
            "This override packet supplies no root license",
            "only after the owner installs an approved license",
            "becomes releasable only",
        )
        for phrase in stale:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, readme + provenance)

    def test_reduced_motion_and_focus_treatment_exist(self) -> None:
        css = self.text["styles.css"]
        self.assertIn(":focus-visible", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn(".visually-hidden", css)

    def test_selected_public_hero_is_full_size_png(self) -> None:
        path = REPOSITORY_ROOT / "assets" / "project-previews" / "catalog-lifecycle.png"
        payload = path.read_bytes()
        self.assertGreater(len(payload), 10_000)
        self.assertEqual(payload[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", payload[16:24]), (1440, 960))


if __name__ == "__main__":
    unittest.main()
