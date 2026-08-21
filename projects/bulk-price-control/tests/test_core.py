from __future__ import annotations

import tempfile
import unittest
import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from price_tool.core import (
    apply_updates,
    build_plan,
    load_catalog,
    load_changes,
    parse_money,
    validate_catalog,
)
from price_tool.errors import ValidationError
from tests.support import catalog, changes, one_change


class PlanTests(unittest.TestCase):
    def test_valid_plan_is_sorted_and_totals_are_exact(self) -> None:
        plan = build_plan(catalog(), list(reversed(changes())))
        self.assertEqual(["BEV-1001", "ENT-2001", "SID-3001"], [u["sku"] for u in plan["updates"]])
        self.assertEqual("18.95", plan["summary"]["before_total"])
        self.assertEqual("20.25", plan["summary"]["after_total"])
        self.assertEqual("1.30", plan["summary"]["net_change"])
        self.assertEqual(["7.69", "6.52", "7.14"], [u["percent_change"] for u in plan["updates"]])

    def test_apply_updates_preserves_unselected_items(self) -> None:
        source = catalog()
        plan = build_plan(source, one_change())
        result = apply_updates(source, plan["updates"])
        prices = {item["sku"]: item["price"] for item in result["items"]}
        self.assertEqual("3.50", prices["BEV-1001"])
        self.assertEqual("11.50", prices["ENT-2001"])
        self.assertEqual("3.25", source["items"][0]["price"])

    def assert_rejected(self, rows: list[dict[str, str]], phrase: str) -> None:
        with self.assertRaisesRegex(ValidationError, phrase):
            build_plan(catalog(), rows)

    def test_wrong_venue_is_rejected(self) -> None:
        self.assert_rejected(one_change(venue_id="another-venue"), "venue_id must match")

    def test_unknown_sku_is_rejected(self) -> None:
        self.assert_rejected(one_change(sku="BEV-9999"), "unknown SKU")

    def test_duplicate_update_is_rejected(self) -> None:
        rows = one_change() * 2
        rows[1] = dict(rows[1], _row="3")
        self.assert_rejected(rows, "duplicate update")

    def test_inactive_item_is_rejected(self) -> None:
        self.assert_rejected(one_change(sku="DES-4001", new_price="6.00"), "inactive")

    def test_disallowed_category_is_rejected(self) -> None:
        value = catalog()
        value["policy"]["allowed_categories"].remove("beverage")
        with self.assertRaisesRegex(ValidationError, "not allowed"):
            build_plan(value, one_change())

    def test_excessive_increase_is_rejected(self) -> None:
        self.assert_rejected(one_change(new_price="4.00"), "exceeds policy limit")

    def test_excessive_decrease_is_rejected(self) -> None:
        self.assert_rejected(one_change(new_price="2.50"), "exceeds policy limit")

    def test_zero_negative_and_malformed_money_are_rejected(self) -> None:
        for bad in ("0.00", "-1.00", "3.5", "3.500", "3,50", "NaN"):
            with self.subTest(value=bad):
                with self.assertRaises(ValidationError):
                    build_plan(catalog(), one_change(new_price=bad))

    def test_noop_is_rejected(self) -> None:
        self.assert_rejected(one_change(new_price="3.25"), "would not change")

    def test_blank_and_control_character_reasons_are_rejected(self) -> None:
        for reason in ("", "  ", "line\nbreak"):
            with self.subTest(reason=reason):
                with self.assertRaises(ValidationError):
                    build_plan(catalog(), one_change(reason=reason))

    def test_batch_limit_is_rejected(self) -> None:
        value = catalog()
        value["policy"]["max_batch_size"] = 1
        with self.assertRaisesRegex(ValidationError, "limit is 1"):
            build_plan(value, changes()[:2])


class CatalogTests(unittest.TestCase):
    def test_duplicate_catalog_sku_is_rejected(self) -> None:
        value = catalog()
        value["items"].append(deepcopy(value["items"][0]))
        with self.assertRaisesRegex(ValidationError, "duplicate SKU"):
            validate_catalog(value)

    def test_extra_catalog_field_is_rejected(self) -> None:
        value = catalog()
        value["private_note"] = "not accepted"
        with self.assertRaisesRegex(ValidationError, "unexpected private_note"):
            validate_catalog(value)

    def test_boolean_batch_limit_is_rejected(self) -> None:
        value = catalog()
        value["policy"]["max_batch_size"] = True
        with self.assertRaisesRegex(ValidationError, "expected an integer"):
            validate_catalog(value)

    def test_money_parser_returns_decimal(self) -> None:
        self.assertEqual(Decimal("12.50"), parse_money("12.50", "test"))

    def test_duplicate_json_fields_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(
                '{"schema_version":"hospitality-catalog/v1",'
                '"schema_version":"hospitality-catalog/v1"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValidationError, "duplicate JSON field"):
                load_catalog(path)

    def test_nonfinite_json_number_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            value = catalog()
            value["policy"]["max_batch_size"] = float("nan")
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "non-finite JSON number"):
                load_catalog(path)


class CsvTests(unittest.TestCase):
    def test_exact_header_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "changes.csv"
            path.write_text("sku,new_price\nBEV-1001,3.50\n", encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "header must be exactly"):
                load_changes(path)

    def test_extra_column_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "changes.csv"
            path.write_text(
                "venue_id,sku,new_price,reason\n"
                "demo-venue-alpha,BEV-1001,3.50,Review,extra\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValidationError, "too many columns"):
                load_changes(path)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
