from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from migration_tool.core import (
    artifact_bytes,
    build_quarantine,
    canonical_json,
    load_source_snapshot,
    project_from_plan,
    sha256_bytes,
    validate_mapping,
    validate_plan,
    validate_quarantine,
    validate_source,
    validate_target,
)
from migration_tool.errors import IntegrityError, ValidationError
from tests.support import mapping, plan_for, source, target


class SchemaTests(unittest.TestCase):
    def test_source_schema_version_is_explicit(self) -> None:
        value = source()
        value["schema_version"] = "synthetic-hospitality-source/v9"
        with self.assertRaisesRegex(ValidationError, "schema_version"):
            validate_source(value)

    def test_target_schema_version_is_explicit(self) -> None:
        value = target()
        value["schema_version"] = "synthetic-hospitality-target/v1"
        with self.assertRaisesRegex(ValidationError, "schema_version"):
            validate_target(value)

    def test_mapping_schema_version_is_explicit(self) -> None:
        value = mapping()
        value["schema_version"] = "synthetic-hospitality-mapping/v2"
        with self.assertRaisesRegex(ValidationError, "schema_version"):
            validate_mapping(value)

    def test_duplicate_json_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"
            raw = artifact_bytes(source()).decode("utf-8")
            raw = raw.replace(
                '"currency": "USD"',
                '"currency": "USD",\n  "currency": "USD"',
                1,
            )
            path.write_text(raw, encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "duplicate JSON field"):
                load_source_snapshot(path)

    def test_target_referential_integrity_is_enforced(self) -> None:
        value = target()
        value["products"][0]["department_code"] = "DEPT-UNKNOWN"
        with self.assertRaisesRegex(ValidationError, "unknown target department"):
            validate_target(value)

    def test_duplicate_target_product_is_rejected(self) -> None:
        value = target()
        value["products"].append(deepcopy(value["products"][0]))
        with self.assertRaisesRegex(ValidationError, "duplicate"):
            validate_target(value)

    def test_exact_field_mapping_is_required(self) -> None:
        value = mapping()
        value["field_mappings"][0]["target_field"] = "name"
        with self.assertRaisesRegex(ValidationError, "exact source-to-target"):
            validate_mapping(value)


class PlanTests(unittest.TestCase):
    def test_reconciliation_counts_and_actions_are_exact(self) -> None:
        plan = plan_for()
        self.assertEqual(
            {
                "source_records": 5,
                "eligible_records": 3,
                "quarantined_records": 2,
                "inserts": 1,
                "updates": 1,
                "unchanged": 1,
                "target_before_records": 2,
                "target_after_records": 3,
            },
            plan["reconciliation"],
        )
        self.assertEqual(["update", "insert"], [item["action"] for item in plan["operations"]])
        self.assertEqual(["ITM-200"], plan["unchanged_product_codes"])

    def test_invalid_and_broken_reference_records_are_quarantined(self) -> None:
        plan = plan_for()
        self.assertEqual(
            ["broken_source_category_reference", "invalid_source_record"],
            [item["code"] for item in plan["exceptions"]],
        )
        self.assertEqual([4, 5], [item["source_record"] for item in plan["exceptions"]])

    def test_duplicate_source_ids_quarantine_every_duplicate(self) -> None:
        value = source()
        duplicate = deepcopy(value["items"][2])
        duplicate["display_name"] = "Second Duplicate"
        value["items"].append(duplicate)
        plan = plan_for(source_value=value)
        duplicate_exceptions = [
            item for item in plan["exceptions"] if item["code"] == "duplicate_source_id"
        ]
        self.assertEqual([3, 6], [item["source_record"] for item in duplicate_exceptions])
        self.assertNotIn("ITM-300", [item["product_code"] for item in plan["operations"]])

    def test_malformed_duplicate_also_blocks_its_valid_counterpart(self) -> None:
        value = source()
        malformed_duplicate = deepcopy(value["items"][2])
        malformed_duplicate["unit_price"] = "bad"
        value["items"].append(malformed_duplicate)
        plan = plan_for(source_value=value)
        exceptions = {
            item["source_record"]: item["code"] for item in plan["exceptions"]
        }
        self.assertEqual("duplicate_source_id", exceptions[3])
        self.assertEqual("invalid_source_record", exceptions[6])
        self.assertNotIn("ITM-300", [item["product_code"] for item in plan["operations"]])

    def test_plan_is_deterministic_for_identical_bytes(self) -> None:
        first = plan_for()
        second = plan_for()
        self.assertEqual(first, second)
        self.assertEqual(first["plan_id"], second["plan_id"])

    def test_mapping_must_cover_defined_source_categories(self) -> None:
        value = mapping()
        value["category_mappings"].pop()
        with self.assertRaisesRegex(ValidationError, "cover source categories exactly"):
            plan_for(mapping_value=value)

    def test_mapping_must_reference_existing_target_department(self) -> None:
        value = mapping()
        value["category_mappings"][0]["target_department"] = "DEPT-NOT-THERE"
        with self.assertRaisesRegex(ValidationError, "unknown target departments"):
            plan_for(mapping_value=value)

    def test_currency_mismatch_is_rejected(self) -> None:
        value = target()
        value["currency"] = "CAD"
        with self.assertRaisesRegex(ValidationError, "currencies differ"):
            plan_for(target_value=value)

    def test_plan_content_tamper_is_rejected(self) -> None:
        plan = plan_for()
        plan["operations"][0]["after"]["price"] = "3.50"
        with self.assertRaises(IntegrityError):
            validate_plan(plan)

    def test_plan_enforces_the_declared_identity_field_mapping(self) -> None:
        plan = plan_for()
        plan["operations"][0]["source_item_id"] = "ITM-999"
        unsigned = dict(plan)
        unsigned.pop("plan_id")
        plan["plan_id"] = sha256_bytes(canonical_json(unsigned))
        with self.assertRaisesRegex(ValidationError, "mapped product codes must match"):
            validate_plan(plan)

    def test_reconciliation_tamper_is_rejected(self) -> None:
        plan = plan_for()
        plan["reconciliation"]["updates"] = 2
        unsigned = dict(plan)
        unsigned.pop("plan_id")
        plan["plan_id"] = sha256_bytes(canonical_json(unsigned))
        with self.assertRaisesRegex(IntegrityError, "reconciliation counts"):
            validate_plan(plan)

    def test_projected_target_digest_is_recomputed(self) -> None:
        plan = plan_for()
        plan["projected_target_sha256"] = "0" * 64
        with self.assertRaisesRegex(IntegrityError, "projected target digest"):
            validate_plan(plan)

    def test_before_image_is_required_for_update(self) -> None:
        plan = plan_for()
        changed_target = target()
        changed_target["products"][0]["price"] = "3.30"
        with self.assertRaisesRegex(IntegrityError, "before-image mismatch"):
            project_from_plan(changed_target, plan)

    def test_quarantine_is_bound_to_exception_digest(self) -> None:
        quarantine = build_quarantine(plan_for())
        quarantine["exceptions"][0]["message"] = "altered"
        with self.assertRaisesRegex(IntegrityError, "exception digest"):
            validate_quarantine(quarantine)

    def test_valid_plan_and_quarantine_round_trip(self) -> None:
        plan = validate_plan(plan_for())
        quarantine = validate_quarantine(build_quarantine(plan))
        self.assertEqual(plan["plan_id"], quarantine["plan_id"])
        self.assertEqual(
            sha256_bytes(canonical_json(plan["exceptions"])),
            quarantine["exception_digest"],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
