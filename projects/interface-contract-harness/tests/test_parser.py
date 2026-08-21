from __future__ import annotations

import unittest

from wcag_harness.model import ContractInputError
from wcag_harness.parser import MAX_HTML_BYTES, parse_html


def page(body: str, *, lang: str = ' lang="en"') -> bytes:
    return (
        "<!doctype html><html"
        + lang
        + "><head><title>Fixture</title></head><body>"
        + body
        + "</body></html>"
    ).encode()


class StrictParserTests(unittest.TestCase):
    def test_parses_complete_document_and_builds_stable_paths(self) -> None:
        document = parse_html(page("<main><div></div><div><span> X </span></div></main>"))
        elements = list(document.elements())
        second_div = [item for item in elements if item.tag == "div"][1]
        self.assertEqual(second_div.path(), "html[1]/body[1]/main[1]/div[2]")
        self.assertEqual(second_div.text_content(), "X")

    def test_rejects_missing_doctype(self) -> None:
        with self.assertRaisesRegex(ContractInputError, "missing <!doctype html>"):
            parse_html(b'<html lang="en"><head><title>x</title></head><body></body></html>')

    def test_rejects_mismatched_close_tag(self) -> None:
        with self.assertRaisesRegex(ContractInputError, "mismatched closing tag"):
            parse_html(page("<main><section></main></section>"))

    def test_rejects_unknown_element(self) -> None:
        with self.assertRaisesRegex(ContractInputError, "unknown element"):
            parse_html(page("<made-up-widget></made-up-widget>"))

    def test_rejects_duplicate_attribute(self) -> None:
        with self.assertRaisesRegex(ContractInputError, "duplicate attribute"):
            parse_html(page('<div id="one" ID="two"></div>'))

    def test_rejects_nonvoid_self_close(self) -> None:
        with self.assertRaisesRegex(ContractInputError, "only void elements"):
            parse_html(page("<div/>"))

    def test_accepts_void_self_close(self) -> None:
        document = parse_html(page('<img src="x" alt=""/>'))
        self.assertIn("img", [item.tag for item in document.elements()])

    def test_rejects_processing_instruction(self) -> None:
        with self.assertRaisesRegex(ContractInputError, "processing instructions"):
            parse_html(b'<?fixture x?><!doctype html><html lang="en"></html>')

    def test_rejects_nul_and_invalid_utf8(self) -> None:
        with self.assertRaisesRegex(ContractInputError, "NUL"):
            parse_html(page("<p>x\x00y</p>"))
        with self.assertRaisesRegex(ContractInputError, "valid UTF-8"):
            parse_html(b"\xff")

    def test_rejects_oversize_input(self) -> None:
        with self.assertRaisesRegex(ContractInputError, "exceeds"):
            parse_html(b"x" * (MAX_HTML_BYTES + 1))

    def test_rejects_text_after_root(self) -> None:
        with self.assertRaisesRegex(ContractInputError, "after </html>"):
            parse_html(page("") + b"tail")


if __name__ == "__main__":
    unittest.main()
