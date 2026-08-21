from __future__ import annotations

import unittest

from wcag_harness.parser import parse_html
from wcag_harness.rules import RULES, run_rules


def document(body: str, *, lang: str = ""):
    language = f' lang="{lang}"' if lang else ""
    raw = (
        f"<!doctype html><html{language}><head><title>Rules</title></head>"
        f"<body>{body}</body></html>"
    ).encode()
    return parse_html(raw)


class RuleTests(unittest.TestCase):
    def test_every_rule_detects_its_synthetic_regression(self) -> None:
        fixture = document(
            """
            <main>
              <h2>First</h2><h4>Jump</h4>
              <div id="same"></div><div id="same"></div>
              <img src="x.svg">
              <a href="/x"></a>
              <form><input aria-describedby="missing"><button></button></form>
              <table><tr><td>Data</td></tr></table>
            </main>
            """
        )
        found = {item.rule_id for item in run_rules(fixture, list(RULES))}
        self.assertEqual(found, set(RULES))

    def test_known_good_name_sources_are_accepted(self) -> None:
        fixture = document(
            """
            <p id="help">Helpful text</p>
            <form>
              <label for="email">Email</label><input id="email" aria-describedby="help">
              <label>Region<select><option>West</option></select></label>
              <textarea aria-label="Notes"></textarea>
              <button type="button" aria-labelledby="button-label"></button>
              <span id="button-label">Save</span>
            </form>
            <a href="/next" title="Next"></a>
            <img src="grid.svg" alt="">
            """,
            lang="en-US",
        )
        self.assertEqual(run_rules(fixture, list(RULES)), [])

    def test_role_matching_and_text_name_use_the_same_case_normalization(self) -> None:
        fixture = document('<div role="BUTTON">Save</div>', lang="en")
        self.assertEqual(run_rules(fixture, ["interactive-name"]), [])

    def test_heading_rule_allows_first_heading_to_be_component_level(self) -> None:
        fixture = document("<section><h3>Card title</h3><h4>Detail</h4><h2>Peer</h2></section>", lang="en")
        violations = run_rules(fixture, ["heading-order"])
        self.assertEqual(violations, [])

    def test_heading_rule_flags_each_forward_jump(self) -> None:
        fixture = document("<h1>A</h1><h3>B</h3><h5>C</h5>", lang="en")
        violations = run_rules(fixture, ["heading-order"])
        self.assertEqual(len(violations), 2)

    def test_empty_alt_is_an_explicitly_accepted_decorative_contract(self) -> None:
        fixture = document('<img src="grid.svg" alt="">', lang="en")
        self.assertEqual(run_rules(fixture, ["image-alternative"]), [])

    def test_blank_and_duplicate_ids_are_separate_findings(self) -> None:
        fixture = document('<div id=" "></div><p id="x"></p><p id="x"></p>', lang="en")
        violations = run_rules(fixture, ["unique-id"])
        self.assertEqual([item.node for item in violations], [
            "html[1]/body[1]/div[1]",
            "html[1]/body[1]/p[2]",
        ])

    def test_whitespace_id_does_not_satisfy_aria_reference(self) -> None:
        fixture = document(
            '<p id=" target ">Label</p><button type="button" aria-labelledby="target"></button>',
            lang="en",
        )
        violations = run_rules(
            fixture,
            ["unique-id", "interactive-name", "aria-reference-integrity"],
        )
        self.assertEqual(
            {item.rule_id for item in violations},
            {"unique-id", "interactive-name", "aria-reference-integrity"},
        )

    def test_two_broken_aria_attributes_produce_one_fingerprint(self) -> None:
        fixture = document(
            '<input aria-label="Owner" aria-labelledby="missing-name" aria-describedby="missing-help">',
            lang="en",
        )
        violations = run_rules(fixture, ["aria-reference-integrity"])
        self.assertEqual(len(violations), 1)
        self.assertIn("aria-labelledby", violations[0].message)
        self.assertIn("aria-describedby", violations[0].message)

    def test_nested_table_header_does_not_satisfy_outer_table(self) -> None:
        fixture = document(
            """
            <table><tr><td>Outer
              <table><tr><th scope="col">Inner heading</th></tr><tr><td>Inner</td></tr></table>
            </td></tr></table>
            """,
            lang="en",
        )
        violations = run_rules(fixture, ["table-header-contract"])
        self.assertEqual(
            [item.node for item in violations], ["html[1]/body[1]/table[1]"]
        )

    def test_hidden_input_does_not_require_a_name(self) -> None:
        fixture = document('<input type="hidden" value="token">', lang="en")
        self.assertEqual(run_rules(fixture, ["form-control-name"]), [])

    def test_invalid_language_tag_is_detected_but_case_is_allowed(self) -> None:
        self.assertEqual(run_rules(document("", lang="en-US"), ["document-language"]), [])
        violations = run_rules(document("", lang="en_US"), ["document-language"])
        self.assertEqual(len(violations), 1)


if __name__ == "__main__":
    unittest.main()
