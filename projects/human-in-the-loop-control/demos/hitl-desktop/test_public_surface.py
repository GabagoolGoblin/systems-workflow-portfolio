from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DESKTOP = Path(__file__).resolve().parent
PREVIEW = PROJECT_ROOT / "preview"
BOUNDARY = (
    "INDEPENDENT PORTFOLIO DEMO",
    "SYNTHETIC DATA",
    "NO AFFILIATION",
    "NO PRODUCTION ACTION",
)


class PreviewParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.lang: str | None = None
        self.csp: str | None = None
        self.scripts: list[str] = []
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.lang = values.get("lang")
        if tag == "meta" and values.get("http-equiv") == "Content-Security-Policy":
            self.csp = values.get("content")
        if tag == "script" and values.get("src"):
            self.scripts.append(str(values["src"]))
        if values.get("id"):
            self.ids.append(str(values["id"]))


class PublicSurfaceTests(unittest.TestCase):
    def test_fresh_preview_is_executable_and_offline(self) -> None:
        html = (PREVIEW / "index.html").read_text(encoding="utf-8")
        script = (PREVIEW / "app.js").read_text(encoding="utf-8")
        css = (PREVIEW / "styles.css").read_text(encoding="utf-8")
        parser = PreviewParser()
        parser.feed(html)
        self.assertEqual(parser.lang, "en")
        self.assertEqual(parser.scripts, ["app.js"])
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertIn("connect-src 'none'", parser.csp or "")
        for action in (
            "holdDuplicateSubmissions",
            "resolveCache",
            "validateHeld",
            "stageValues",
            "verifyValues",
            "approveSave",
        ):
            self.assertIn(f"function {action}()", script)
        self.assertIn('data-request-id="${escapeHTML(row.requestId)}"', script)
        self.assertIn("Held: duplicate barcode submission", script)
        self.assertIn(":focus-visible", css)
        self.assertIn("prefers-reduced-motion", css)

    def test_boundary_is_visible_in_browser_and_both_tk_surfaces(self) -> None:
        texts = (
            (PREVIEW / "index.html").read_text(encoding="utf-8"),
            (DESKTOP / "barcode_cache_demo.py").read_text(encoding="utf-8"),
            (DESKTOP / "mock_console.py").read_text(encoding="utf-8"),
        )
        for text in texts:
            for phrase in BOUNDARY:
                self.assertIn(phrase, text)

    def test_public_carve_out_contains_no_legacy_visual_or_history_surface(self) -> None:
        forbidden_names = {
            "mock" + "ups",
            "gallery_preview.png",
            "ASSET_MANIFEST.sha256",
            "last_run_log.txt",
            "INTERVIEW_DEMO.md",
            "REVIEW_CHECKLIST.md",
            "EXCLUSIONS.md",
        }
        public_paths = {path.relative_to(PROJECT_ROOT).as_posix() for path in PROJECT_ROOT.rglob("*") if path.is_file()}
        for marker in forbidden_names:
            self.assertFalse(any(marker in path for path in public_paths), marker)
        self.assertFalse((PROJECT_ROOT / "docs").exists())

    def test_public_text_has_no_contact_private_path_or_image_provenance_marker(self) -> None:
        text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in PROJECT_ROOT.rglob("*")
            if path.is_file() and path.suffix.lower() in {".py", ".js", ".css", ".html", ".md", ".json"}
        )
        self.assertIsNone(re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I))
        self.assertNotIn("/" + "home/", text)
        self.assertNotIn("job-" + "search", text.lower())
        self.assertNotIn("c2" + "pa", text.lower())
        self.assertNotIn("source-" + "available", text.lower())

    def test_automation_has_no_default_tracked_tree_write(self) -> None:
        source = (DESKTOP / "automate_hitl.py").read_text(encoding="utf-8")
        self.assertIn("log_path: Path | None = None", source)
        self.assertIn("log path must be outside the project tree", source)
        self.assertNotIn('parent / "last_' + 'run_log.txt"', source)

    def test_smoke_accepts_only_an_explicit_external_summary_path(self) -> None:
        source = (DESKTOP / "smoke_test.py").read_text(encoding="utf-8")
        self.assertIn('"--log-path"', source)
        self.assertIn("write_run_log", source)
        self.assertIn("tracked_log_absent", source)


if __name__ == "__main__":
    unittest.main()
