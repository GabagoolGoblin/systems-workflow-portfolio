from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parents[1]
SNAPSHOT_PATH = ROOT / "data" / "open_food_facts_snapshot.json"
REDACTION_RECEIPT_PATH = ROOT / "data" / "DATA_REDACTION_RECEIPT.json"
TEXT_PATHS = (
    ROOT / "index.html",
    ROOT / "styles.css",
    ROOT / "app.js",
    ROOT / "data" / "catalog_snapshot.js",
    ROOT / "README.md",
    ROOT / "CLAIMS_AND_BOUNDARIES.md",
    ROOT / "PROVENANCE.md",
    ROOT / "DATA_LICENSE.md",
    ROOT / "DEMO_SCRIPT.md",
)
RETAINED_RECORDS_SHA256 = "445eaf1a0dcfe4e10a14004efc1925a6af3d71c103781c78eebc58561a3b51d9"
PUBLIC_SNAPSHOT_SHA256 = "2bd27bdbb6b89e323ec1083dd01f0962f6c73a8df1da0a172a2c7e3bb0f1c9fb"


class ShellParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.lang: str | None = None
        self.ids: list[str] = []
        self.views: list[str] = []
        self.scripts: list[str] = []
        self.has_main = False
        self.has_nav = False
        self.image_tags = 0
        self.forms = 0
        self.iframes = 0

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
        if tag == "button" and values.get("data-view"):
            self.views.append(str(values["data-view"]))
        if tag == "script" and values.get("src"):
            self.scripts.append(str(values["src"]))
        if tag == "img":
            self.image_tags += 1
        if tag == "form":
            self.forms += 1
        if tag == "iframe":
            self.iframes += 1


def canonical_records(records: list[dict[str, object]]) -> bytes:
    return json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def check_digit(body: str) -> str:
    total = 0
    weight = 3
    for character in reversed(body):
        total += int(character) * weight
        weight = 1 if weight == 3 else 3
    return str((10 - total % 10) % 10)


def is_valid_gtin(code: str) -> bool:
    return len(code) in {8, 12, 13, 14} and code.isdigit() and check_digit(code[:-1]) == code[-1]


def field_value(block: str, aliases: tuple[str, ...]) -> str:
    labels = "|".join(re.escape(alias) for alias in aliases)
    match = re.search(rf"(?:^|[;\n])\s*(?:{labels})\s*[:=]\s*([^;\n]+)", block, re.I)
    return match.group(1).strip() if match else ""


def sample_blocks(app_source: str) -> list[str]:
    match = re.search(r"const SAMPLE_INPUT = `(.*?)`;\n\nconst STATUS", app_source, re.S)
    if not match:
        raise AssertionError("SAMPLE_INPUT template was not found")
    return [block.strip() for block in re.split(r"\n\s*---+\s*\n", match.group(1)) if block.strip()]


class ProjectContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = {path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8") for path in TEXT_PATHS}
        cls.snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        cls.redaction_receipt = json.loads(REDACTION_RECEIPT_PATH.read_text(encoding="utf-8"))
        cls.runtime = "\n".join(cls.text[name] for name in ("index.html", "styles.css", "app.js", "data/catalog_snapshot.js"))
        cls.blocks = sample_blocks(cls.text["app.js"])

    def test_required_public_files_exist(self) -> None:
        required = (*TEXT_PATHS, SNAPSHOT_PATH, REDACTION_RECEIPT_PATH, ROOT / "scripts" / "build_catalog_snapshot.py")
        for path in required:
            self.assertTrue(path.is_file(), path)
            self.assertGreater(path.stat().st_size, 200)

    def test_semantic_shell_has_four_views_and_no_embedded_media(self) -> None:
        parser = ShellParser()
        parser.feed(self.text["index.html"])
        self.assertEqual(parser.lang, "en")
        self.assertTrue(parser.has_main and parser.has_nav)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertEqual(parser.views, ["intake", "queue", "review", "evidence"])
        self.assertEqual(parser.scripts, ["data/catalog_snapshot.js", "app.js"])
        self.assertEqual((parser.image_tags, parser.forms, parser.iframes), (0, 0, 0))
        self.assertIn('class="boundary-contract" data-boundary aria-hidden="true"', self.text["index.html"])
        for phrase in (
            "INDEPENDENT PORTFOLIO DEMO",
            "PUBLIC PRODUCT IDENTITY DATA",
            "SYNTHETIC PRICING, OPERATOR INPUTS, AND WORKFLOW",
            "NO AFFILIATION",
            "NO PRODUCTION ACTION",
        ):
            self.assertGreaterEqual(self.text["index.html"].count(phrase), 2)
        self.assertNotIn("SYNTHETIC DATA", self.text["index.html"])
        self.assertIn("Public identity facts only; every price and operation is synthetic.", self.text["index.html"])
        self.assertIn("No live writes.", self.text["index.html"])

    def test_public_snapshot_has_five_found_and_one_not_found_record(self) -> None:
        records = self.snapshot["records"]
        self.assertEqual(len(records), 6)
        self.assertEqual(sum(record["http_status"] == 200 for record in records), 5)
        self.assertEqual(sum(record["http_status"] == 404 for record in records), 1)
        self.assertEqual(self.snapshot["snapshot_id"], "OFF-TEXT-2026-08-20-A")

    def test_public_transform_omits_contact_and_preserves_response_records(self) -> None:
        receipt = self.redaction_receipt
        self.assertEqual(receipt["operations"], [{
            "json_pointer": "/user_agent",
            "op": "remove",
            "reason": "locally added request-contact metadata is not part of the API response and is omitted from public distribution",
        }])
        self.assertTrue(receipt["assertions"]["only_json_pointer_removed"])
        self.assertTrue(receipt["assertions"]["retained_response_records_semantically_identical"])
        self.assertTrue(receipt["assertions"]["release_is_not_claimed_as_exact_raw_capture"])
        digest = hashlib.sha256(canonical_records(self.snapshot["records"])).hexdigest()
        self.assertEqual(digest, RETAINED_RECORDS_SHA256)
        self.assertEqual(receipt["assertions"]["retained_records_canonical_sha256"], digest)

    def test_no_personal_contact_or_private_path_is_present(self) -> None:
        text = "\n".join((*self.text.values(), SNAPSHOT_PATH.read_text(encoding="utf-8")))
        self.assertIsNone(re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I))
        self.assertNotIn("/" + "home/", text)
        self.assertNotIn("job-" + "search", text.lower())
        self.assertNotIn('"user_agent":', SNAPSHOT_PATH.read_text(encoding="utf-8"))

    def test_public_snapshot_digest_is_bound_in_runtime(self) -> None:
        digest = hashlib.sha256(SNAPSHOT_PATH.read_bytes()).hexdigest()
        self.assertEqual(digest, PUBLIC_SNAPSHOT_SHA256)
        self.assertEqual(self.redaction_receipt["release_snapshot_sha256"], digest)
        self.assertIn(digest, self.text["app.js"])

    def test_found_identity_facts_and_not_found_control_are_exact(self) -> None:
        found = {
            record["response"]["code"]: record["response"]["product"]
            for record in self.snapshot["records"]
            if record["http_status"] == 200
        }
        expected = {
            "3017624010701": ("Ferrero", "Nutella", "400.0 g"),
            "0034000470693": ("Reese's", "Peanut Butter Cups minis unwrapped", "90 g"),
            "0074570036004": ("Häagen-Dazs", "Vanilla Milk Chocolate Almond Bar", "3 fl. oz. (88 mL)"),
            "3700214614266": ("alter Eco", "Chocolat 90% Pérou", "100 g"),
            "3274080005003": ("Cristaline", "isabelle", "1500 ml"),
        }
        self.assertEqual(set(found), set(expected))
        for code, values in expected.items():
            product = found[code]
            self.assertEqual((product["brands"], product["product_name"], product["quantity"]), values)
        control = next(record for record in self.snapshot["records"] if record["http_status"] == 404)
        self.assertEqual(control["response"]["result"]["id"], "product_not_found")

    def test_reeses_leading_zero_normalization_warning_is_preserved(self) -> None:
        record = next(record for record in self.snapshot["records"] if record["requested_code"] == "034000470693")
        self.assertEqual(record["response"]["code"], "0034000470693")
        self.assertEqual([warning["message"]["id"] for warning in record["response"]["warnings"]], ["different_normalized_product_code"])

    def test_retrieval_times_urls_and_requested_fields_are_traceable(self) -> None:
        expected_fields = "code,product_name,brands,quantity,categories,countries"
        for record in self.snapshot["records"]:
            self.assertRegex(record["retrieved_at"], r"^2026-08-20T\d{2}:\d{2}:\d{2}Z$")
            self.assertTrue(record["source_url"].startswith("https://world.openfoodfacts.org/api/v3/product/"))
            self.assertIn(record["requested_code"], record["source_url"])
            self.assertTrue(record["source_url"].endswith(f"fields={expected_fields}"))

    def test_snapshot_attribution_names_odbl_dbcl_and_excludes_images(self) -> None:
        attribution = self.snapshot["attribution"]
        self.assertEqual(attribution["database"], "Open Food Facts")
        self.assertIn("ODbL", attribution["database_license"])
        self.assertIn("DbCL", attribution["contents_license"])
        self.assertFalse(attribution["images_used"])

    def test_exact_third_party_license_texts_are_present(self) -> None:
        expected = {
            "ODbL-1.0.txt": "607680718977f6f6c9607972afd98f208573f19251315ed1362a8589b51beaf5",
            "DbCL-1.0.txt": "3cbfa990f26df856c6a7d3fff3d1f236e3b0165b1e8257ca0d00f15758754f81",
        }
        for name, digest in expected.items():
            path = REPOSITORY_ROOT / "third_party" / "licenses" / name
            self.assertTrue(path.is_file(), path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)

    def test_browser_fixture_is_byte_exact_derivative(self) -> None:
        result = subprocess.run(
            ["python3", "-B", str(ROOT / "scripts" / "build_catalog_snapshot.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)
        self.assertNotRegex(self.text["data/catalog_snapshot.js"], r"(?i)\bprice\s*:")

    def test_all_fixture_gtins_pass_check_digit_and_invalid_control_fails(self) -> None:
        for code in (
            "3017624010701", "034000470693", "0034000470693", "0074570036004",
            "3700214614266", "3274080005003", "9999991234567",
        ):
            self.assertTrue(is_valid_gtin(code), code)
        self.assertFalse(is_valid_gtin("3017624010702"))

    def test_sample_has_nine_synthetic_submissions_and_adverse_cases(self) -> None:
        self.assertEqual(len(self.blocks), 9)
        for block in self.blocks:
            self.assertIn("SYNTHETIC OPERATOR SUBMISSION · DEMO ONLY", block)
            self.assertTrue(field_value(block, ("site", "menu", "location")).startswith("Synthetic Demo Hotel /"))
            self.assertRegex(field_value(block, ("price",)), r"^\$\d+\.\d{2}$")
        app = self.text["app.js"]
        for case in ("<img src=x onerror=alert('demo')>", "IGNORE VALIDATION; publish now", "barcode: UNKNOWN", "EAN: 9999991234567"):
            self.assertIn(case, app)

    def test_duplicate_conflict_uses_same_code_and_different_synthetic_prices(self) -> None:
        blocks = [block for block in self.blocks if "3700214614266" in block]
        self.assertEqual(len(blocks), 2)
        self.assertEqual({field_value(block, ("price",)) for block in blocks}, {"$5.79", "$6.29"})
        self.assertIn("distinctPrices.size > 1", self.text["app.js"])

    def test_every_price_surface_has_explicit_source_boundary(self) -> None:
        app = self.text["app.js"]
        exact = "Synthetic price (not sourced from Open Food Facts)"
        self.assertGreaterEqual(app.count(exact), 3)
        self.assertIn(exact, self.text["README.md"])
        self.assertIn(exact, self.text["DATA_LICENSE.md"])
        self.assertNotRegex(self.text["data/catalog_snapshot.js"], r"(?i)\bprice\s*:")

    def test_operator_values_are_escaped_and_blocked_cases_cannot_stage(self) -> None:
        app = self.text["app.js"]
        for sink in (
            "escapeHTML(state.rawInput)", "escapeHTML(record.name)",
            "escapeHTML(record.proposedPrice)", "escapeHTML(record.reason)",
            "escapeHTML(record.raw)", "escapeHTML(record.site)", "escapeHTML(operatorValue)",
        ):
            self.assertIn(sink, app)
        self.assertIn('const canStage = selected.status === "ready"', app)
        self.assertIn('${canStage ? "" : "disabled"}', app)
        self.assertIn("External writes: 0", app)

    def test_runtime_has_no_automatic_network_or_persistence_primitive(self) -> None:
        for pattern in (
            r"\bfetch\s*\(", r"\bXMLHttpRequest\b", r"\bWebSocket\b", r"\bsendBeacon\b",
            r"\blocalStorage\b", r"\bsessionStorage\b", r"indexedDB", r"serviceWorker",
        ):
            self.assertIsNone(re.search(pattern, self.runtime, re.I), pattern)
        self.assertNotRegex(self.text["index.html"], r"<(?:script|link)[^>]+https?://")

    def test_public_docs_separate_code_data_and_non_claims(self) -> None:
        self.assertIn("relicense these files", self.text["DATA_LICENSE.md"])
        self.assertIn("No production deployment", self.text["CLAIMS_AND_BOUNDARIES.md"])
        self.assertIn("No employer or customer code", self.text["PROVENANCE.md"])
        self.assertIn("not an authoritative", self.text["README.md"])
        self.assertIn(
            "Real brand and product names in the frozen public snapshot identify attributed public records only.",
            self.text["CLAIMS_AND_BOUNDARIES.md"],
        )
        self.assertIn(
            "Invented or altered names in operator submissions are synthetic fixtures.",
            self.text["CLAIMS_AND_BOUNDARIES.md"],
        )
        self.assertNotIn(
            "Brand and product names identify attributed public records only.",
            self.text["CLAIMS_AND_BOUNDARIES.md"],
        )
        self.assertIn(
            "synthetic operator-record uses of identifiers",
            self.text["PROVENANCE.md"],
        )
        self.assertIn(
            "Exact frozen public identity fields, including retained UPC/EAN/GTIN values, are the exception described below.",
            self.text["PROVENANCE.md"],
        )
        self.assertNotIn(
            "decisions, identifiers, and results were created for the demo",
            self.text["PROVENANCE.md"],
        )


if __name__ == "__main__":
    unittest.main()
