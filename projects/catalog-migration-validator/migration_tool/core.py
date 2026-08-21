"""Strict schemas and deterministic migration-plan construction."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable

from .errors import IntegrityError, ValidationError

SOURCE_SCHEMA = "synthetic-hospitality-source/v1"
TARGET_SCHEMA = "synthetic-hospitality-target/v2"
MAPPING_SCHEMA = "synthetic-hospitality-mapping/v1"
PLAN_SCHEMA = "hospitality-catalog-migration-plan/v1"
QUARANTINE_SCHEMA = "hospitality-catalog-quarantine/v1"

_CODE_RE = re.compile(r"[A-Z][A-Z0-9_-]{1,31}\Z")
_LOCATION_RE = re.compile(r"[a-z0-9][a-z0-9-]{2,47}\Z")
_CURRENCY_RE = re.compile(r"[A-Z]{3}\Z")
_MONEY_RE = re.compile(r"(?:0|[1-9][0-9]*)\.[0-9]{2}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")

_SOURCE_FIELDS = {
    "item_id",
    "display_name",
    "category_code",
    "unit_price",
    "enabled",
}
_TARGET_FIELDS = {
    "product_code",
    "name",
    "department_code",
    "price",
    "active",
}
_REQUIRED_RENAMES = {
    "item_id": "product_code",
    "display_name": "name",
    "category_code": "department_code",
    "unit_price": "price",
    "enabled": "active",
}
_EXCEPTION_CODES = {
    "invalid_source_record",
    "duplicate_source_id",
    "broken_source_category_reference",
}


class StrictJsonError(ValueError):
    """Raised for ambiguous or non-standard JSON representations."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def artifact_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def strict_json_loads(raw: str) -> Any:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise StrictJsonError(f"duplicate JSON field {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise StrictJsonError(f"non-finite JSON number {value}")

    return json.loads(
        raw,
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )


def _exact_keys(value: dict[str, Any], expected: set[str], context: str) -> None:
    missing = sorted(expected - set(value))
    extra = sorted(set(value) - expected)
    if not missing and not extra:
        return
    details: list[str] = []
    if missing:
        details.append(f"missing {', '.join(missing)}")
    if extra:
        details.append(f"unexpected {', '.join(extra)}")
    raise ValidationError(f"{context}: {'; '.join(details)}")


def _visible_text(value: Any, context: str, maximum: int = 120) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValidationError(f"{context}: expected 1 to {maximum} visible characters")
    if _CONTROL_RE.search(value):
        raise ValidationError(f"{context}: control characters are not allowed")
    return value.strip()


def _code(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _CODE_RE.fullmatch(value):
        raise ValidationError(f"{context}: invalid code")
    return value


def _location(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _LOCATION_RE.fullmatch(value):
        raise ValidationError(f"{context}: invalid identifier")
    return value


def _currency(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _CURRENCY_RE.fullmatch(value):
        raise ValidationError(f"{context}: expected a three-letter uppercase code")
    return value


def _money(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _MONEY_RE.fullmatch(value):
        raise ValidationError(f"{context}: expected a positive amount with two decimals")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValidationError(f"{context}: invalid amount") from exc
    if not amount.is_finite() or amount <= 0:
        raise ValidationError(f"{context}: amount must be finite and greater than zero")
    return f"{amount:.2f}"


def _sha256(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValidationError(f"{context}: invalid SHA-256 digest")
    return value


def _read_json_snapshot(
    path: Path,
    context: str,
    validator: Callable[[Any], dict[str, Any]],
) -> tuple[dict[str, Any], bytes, str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValidationError(
            f"{context}: could not read {path.name}: {exc.strerror or exc}"
        ) from exc
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, StrictJsonError) as exc:
        raise ValidationError(f"{context}: invalid UTF-8 JSON: {exc}") from exc
    return validator(value), raw, sha256_bytes(raw)


def validate_source(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("source: expected an object")
    _exact_keys(
        value,
        {"schema_version", "venue_id", "currency", "categories", "items"},
        "source",
    )
    if value["schema_version"] != SOURCE_SCHEMA:
        raise ValidationError(f"source.schema_version: expected {SOURCE_SCHEMA}")
    venue_id = _location(value["venue_id"], "source.venue_id")
    currency = _currency(value["currency"], "source.currency")
    categories = value["categories"]
    if not isinstance(categories, list) or not categories:
        raise ValidationError("source.categories: expected a nonempty list")
    normalized_categories: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, category in enumerate(categories, start=1):
        context = f"source.categories[{index}]"
        if not isinstance(category, dict):
            raise ValidationError(f"{context}: expected an object")
        _exact_keys(category, {"category_code", "label"}, context)
        code = _code(category["category_code"], f"{context}.category_code")
        if code in seen:
            raise ValidationError(f"{context}.category_code: duplicate {code}")
        seen.add(code)
        normalized_categories.append(
            {"category_code": code, "label": _visible_text(category["label"], f"{context}.label")}
        )
    items = value["items"]
    if not isinstance(items, list) or not items:
        raise ValidationError("source.items: expected a nonempty list")
    return {
        "schema_version": SOURCE_SCHEMA,
        "venue_id": venue_id,
        "currency": currency,
        "categories": sorted(normalized_categories, key=lambda item: item["category_code"]),
        "items": list(items),
    }


def validate_source_item(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{context}: expected an object")
    _exact_keys(value, _SOURCE_FIELDS, context)
    enabled = value["enabled"]
    if not isinstance(enabled, bool):
        raise ValidationError(f"{context}.enabled: expected true or false")
    return {
        "item_id": _code(value["item_id"], f"{context}.item_id"),
        "display_name": _visible_text(value["display_name"], f"{context}.display_name"),
        "category_code": _code(value["category_code"], f"{context}.category_code"),
        "unit_price": _money(value["unit_price"], f"{context}.unit_price"),
        "enabled": enabled,
    }


def _validate_target_product(
    value: Any,
    context: str,
    departments: set[str],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{context}: expected an object")
    _exact_keys(value, _TARGET_FIELDS, context)
    product_code = _code(value["product_code"], f"{context}.product_code")
    department_code = _code(value["department_code"], f"{context}.department_code")
    if department_code not in departments:
        raise ValidationError(
            f"{context}.department_code: unknown target department {department_code}"
        )
    active = value["active"]
    if not isinstance(active, bool):
        raise ValidationError(f"{context}.active: expected true or false")
    return {
        "product_code": product_code,
        "name": _visible_text(value["name"], f"{context}.name"),
        "department_code": department_code,
        "price": _money(value["price"], f"{context}.price"),
        "active": active,
    }


def validate_target(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("target: expected an object")
    _exact_keys(
        value,
        {"schema_version", "property_id", "currency", "departments", "products"},
        "target",
    )
    if value["schema_version"] != TARGET_SCHEMA:
        raise ValidationError(f"target.schema_version: expected {TARGET_SCHEMA}")
    property_id = _location(value["property_id"], "target.property_id")
    currency = _currency(value["currency"], "target.currency")
    departments = value["departments"]
    if not isinstance(departments, list) or not departments:
        raise ValidationError("target.departments: expected a nonempty list")
    normalized_departments: list[dict[str, str]] = []
    department_codes: set[str] = set()
    for index, department in enumerate(departments, start=1):
        context = f"target.departments[{index}]"
        if not isinstance(department, dict):
            raise ValidationError(f"{context}: expected an object")
        _exact_keys(department, {"department_code", "label"}, context)
        code = _code(department["department_code"], f"{context}.department_code")
        if code in department_codes:
            raise ValidationError(f"{context}.department_code: duplicate {code}")
        department_codes.add(code)
        normalized_departments.append(
            {"department_code": code, "label": _visible_text(department["label"], f"{context}.label")}
        )
    products = value["products"]
    if not isinstance(products, list):
        raise ValidationError("target.products: expected a list")
    normalized_products: list[dict[str, Any]] = []
    product_codes: set[str] = set()
    for index, product in enumerate(products, start=1):
        normalized = _validate_target_product(
            product,
            f"target.products[{index}]",
            department_codes,
        )
        code = normalized["product_code"]
        if code in product_codes:
            raise ValidationError(f"target.products[{index}].product_code: duplicate {code}")
        product_codes.add(code)
        normalized_products.append(normalized)
    return {
        "schema_version": TARGET_SCHEMA,
        "property_id": property_id,
        "currency": currency,
        "departments": sorted(
            normalized_departments,
            key=lambda item: item["department_code"],
        ),
        "products": sorted(normalized_products, key=lambda item: item["product_code"]),
    }


def validate_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("mapping: expected an object")
    _exact_keys(
        value,
        {
            "schema_version",
            "source_venue_id",
            "target_property_id",
            "field_mappings",
            "category_mappings",
        },
        "mapping",
    )
    if value["schema_version"] != MAPPING_SCHEMA:
        raise ValidationError(f"mapping.schema_version: expected {MAPPING_SCHEMA}")
    field_mappings = value["field_mappings"]
    if not isinstance(field_mappings, list):
        raise ValidationError("mapping.field_mappings: expected a list")
    renames: dict[str, str] = {}
    normalized_fields: list[dict[str, str]] = []
    for index, field in enumerate(field_mappings, start=1):
        context = f"mapping.field_mappings[{index}]"
        if not isinstance(field, dict):
            raise ValidationError(f"{context}: expected an object")
        _exact_keys(field, {"source_field", "target_field"}, context)
        source_field = field["source_field"]
        target_field = field["target_field"]
        if source_field not in _SOURCE_FIELDS or target_field not in _TARGET_FIELDS:
            raise ValidationError(f"{context}: unsupported field mapping")
        if source_field in renames:
            raise ValidationError(f"{context}: duplicate source field {source_field}")
        renames[source_field] = target_field
        normalized_fields.append(
            {"source_field": source_field, "target_field": target_field}
        )
    if renames != _REQUIRED_RENAMES:
        raise ValidationError("mapping.field_mappings: exact source-to-target field map required")

    category_mappings = value["category_mappings"]
    if not isinstance(category_mappings, list) or not category_mappings:
        raise ValidationError("mapping.category_mappings: expected a nonempty list")
    normalized_categories: list[dict[str, str]] = []
    seen_sources: set[str] = set()
    for index, category in enumerate(category_mappings, start=1):
        context = f"mapping.category_mappings[{index}]"
        if not isinstance(category, dict):
            raise ValidationError(f"{context}: expected an object")
        _exact_keys(category, {"source_category", "target_department"}, context)
        source_category = _code(category["source_category"], f"{context}.source_category")
        target_department = _code(
            category["target_department"],
            f"{context}.target_department",
        )
        if source_category in seen_sources:
            raise ValidationError(f"{context}: duplicate source category {source_category}")
        seen_sources.add(source_category)
        normalized_categories.append(
            {
                "source_category": source_category,
                "target_department": target_department,
            }
        )
    return {
        "schema_version": MAPPING_SCHEMA,
        "source_venue_id": _location(value["source_venue_id"], "mapping.source_venue_id"),
        "target_property_id": _location(
            value["target_property_id"],
            "mapping.target_property_id",
        ),
        "field_mappings": sorted(
            normalized_fields,
            key=lambda item: item["source_field"],
        ),
        "category_mappings": sorted(
            normalized_categories,
            key=lambda item: item["source_category"],
        ),
    }


def load_source_snapshot(path: Path) -> tuple[dict[str, Any], bytes, str]:
    return _read_json_snapshot(path, "source", validate_source)


def load_target_snapshot(path: Path) -> tuple[dict[str, Any], bytes, str]:
    return _read_json_snapshot(path, "target", validate_target)


def load_mapping_snapshot(path: Path) -> tuple[dict[str, Any], bytes, str]:
    return _read_json_snapshot(path, "mapping", validate_mapping)


def _candidate_item_id(value: Any) -> str | None:
    if isinstance(value, dict):
        candidate = value.get("item_id")
        if isinstance(candidate, str) and _CODE_RE.fullmatch(candidate):
            return candidate
    return None


def _exception(
    record_number: int,
    item_id: str | None,
    code: str,
    message: str,
) -> dict[str, Any]:
    return {
        "source_record": record_number,
        "source_item_id": item_id,
        "code": code,
        "message": message,
    }


def build_plan(
    source: dict[str, Any],
    target: dict[str, Any],
    mapping: dict[str, Any],
    *,
    source_sha256: str,
    target_sha256: str,
    mapping_sha256: str,
) -> dict[str, Any]:
    source = validate_source(source)
    target = validate_target(target)
    mapping = validate_mapping(mapping)
    if source["venue_id"] != mapping["source_venue_id"]:
        raise ValidationError("mapping.source_venue_id: does not match source")
    if target["property_id"] != mapping["target_property_id"]:
        raise ValidationError("mapping.target_property_id: does not match target")
    if source["currency"] != target["currency"]:
        raise ValidationError("migration: source and target currencies differ")
    source_categories = {item["category_code"] for item in source["categories"]}
    category_map = {
        item["source_category"]: item["target_department"]
        for item in mapping["category_mappings"]
    }
    if set(category_map) != source_categories:
        raise ValidationError("mapping.category_mappings: must cover source categories exactly")
    target_departments = {item["department_code"] for item in target["departments"]}
    unknown_departments = sorted(set(category_map.values()) - target_departments)
    if unknown_departments:
        raise ValidationError(
            "mapping.category_mappings: unknown target departments "
            + ", ".join(unknown_departments)
        )

    candidate_counts = Counter(
        candidate
        for raw_item in source["items"]
        if (candidate := _candidate_item_id(raw_item)) is not None
    )
    duplicate_ids = {
        item_id for item_id, count in candidate_counts.items() if count > 1
    }
    parsed: list[tuple[int, dict[str, Any]]] = []
    exceptions: list[dict[str, Any]] = []
    for record_number, raw_item in enumerate(source["items"], start=1):
        try:
            item = validate_source_item(raw_item, f"source.items[{record_number}]")
        except ValidationError as exc:
            exceptions.append(
                _exception(
                    record_number,
                    _candidate_item_id(raw_item),
                    "invalid_source_record",
                    exc.message,
                )
            )
            continue
        parsed.append((record_number, item))

    eligible: list[tuple[int, dict[str, Any]]] = []
    for record_number, item in parsed:
        if item["item_id"] in duplicate_ids:
            exceptions.append(
                _exception(
                    record_number,
                    item["item_id"],
                    "duplicate_source_id",
                    f"source.items[{record_number}].item_id: duplicate {item['item_id']}",
                )
            )
        elif item["category_code"] not in source_categories:
            exceptions.append(
                _exception(
                    record_number,
                    item["item_id"],
                    "broken_source_category_reference",
                    (
                        f"source.items[{record_number}].category_code: unknown source "
                        f"category {item['category_code']}"
                    ),
                )
            )
        else:
            eligible.append((record_number, item))

    renames = {
        item["source_field"]: item["target_field"]
        for item in mapping["field_mappings"]
    }
    current_products = {item["product_code"]: item for item in target["products"]}
    operations: list[dict[str, Any]] = []
    unchanged: list[str] = []
    projected_products = dict(current_products)
    for _record_number, item in sorted(eligible, key=lambda pair: pair[1]["item_id"]):
        transformed: dict[str, Any] = {}
        for source_field, target_field in renames.items():
            field_value = item[source_field]
            if source_field == "category_code":
                field_value = category_map[field_value]
            transformed[target_field] = field_value
        product = _validate_target_product(
            transformed,
            f"mapped product {item['item_id']}",
            target_departments,
        )
        product_code = product["product_code"]
        previous = current_products.get(product_code)
        if previous is None:
            action = "insert"
        elif previous == product:
            unchanged.append(product_code)
            continue
        else:
            action = "update"
        operations.append(
            {
                "action": action,
                "source_item_id": item["item_id"],
                "product_code": product_code,
                "before": previous,
                "after": product,
            }
        )
        projected_products[product_code] = product

    operations.sort(key=lambda item: item["product_code"])
    exceptions.sort(key=lambda item: (item["source_record"], item["code"]))
    projected_target = validate_target(
        {
            **target,
            "products": sorted(
                projected_products.values(),
                key=lambda item: item["product_code"],
            ),
        }
    )
    inserts = sum(item["action"] == "insert" for item in operations)
    updates = sum(item["action"] == "update" for item in operations)
    reconciliation = {
        "source_records": len(source["items"]),
        "eligible_records": len(eligible),
        "quarantined_records": len(exceptions),
        "inserts": inserts,
        "updates": updates,
        "unchanged": len(unchanged),
        "target_before_records": len(target["products"]),
        "target_after_records": len(projected_target["products"]),
    }
    unsigned: dict[str, Any] = {
        "schema_version": PLAN_SCHEMA,
        "source_schema_version": SOURCE_SCHEMA,
        "target_schema_version": TARGET_SCHEMA,
        "mapping_schema_version": MAPPING_SCHEMA,
        "source_sha256": _sha256(source_sha256, "plan.source_sha256"),
        "target_before_sha256": _sha256(target_sha256, "plan.target_before_sha256"),
        "mapping_sha256": _sha256(mapping_sha256, "plan.mapping_sha256"),
        "projected_target_sha256": sha256_bytes(artifact_bytes(projected_target)),
        "exception_digest": sha256_bytes(canonical_json(exceptions)),
        "property_id": target["property_id"],
        "currency": target["currency"],
        "operations": operations,
        "unchanged_product_codes": sorted(unchanged),
        "exceptions": exceptions,
        "reconciliation": reconciliation,
        "projected_target": projected_target,
    }
    return {**unsigned, "plan_id": sha256_bytes(canonical_json(unsigned))}


def _validate_exception(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{context}: expected an object")
    _exact_keys(value, {"source_record", "source_item_id", "code", "message"}, context)
    record = value["source_record"]
    if isinstance(record, bool) or not isinstance(record, int) or record < 1:
        raise ValidationError(f"{context}.source_record: expected a positive integer")
    item_id = value["source_item_id"]
    if item_id is not None:
        item_id = _code(item_id, f"{context}.source_item_id")
    code = value["code"]
    if code not in _EXCEPTION_CODES:
        raise ValidationError(f"{context}.code: unsupported exception code")
    return {
        "source_record": record,
        "source_item_id": item_id,
        "code": code,
        "message": _visible_text(value["message"], f"{context}.message", 300),
    }


def validate_plan(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("plan: expected an object")
    expected = {
        "schema_version",
        "plan_id",
        "source_schema_version",
        "target_schema_version",
        "mapping_schema_version",
        "source_sha256",
        "target_before_sha256",
        "mapping_sha256",
        "projected_target_sha256",
        "exception_digest",
        "property_id",
        "currency",
        "operations",
        "unchanged_product_codes",
        "exceptions",
        "reconciliation",
        "projected_target",
    }
    _exact_keys(value, expected, "plan")
    if value["schema_version"] != PLAN_SCHEMA:
        raise ValidationError(f"plan.schema_version: expected {PLAN_SCHEMA}")
    if value["source_schema_version"] != SOURCE_SCHEMA:
        raise ValidationError("plan.source_schema_version: unsupported schema")
    if value["target_schema_version"] != TARGET_SCHEMA:
        raise ValidationError("plan.target_schema_version: unsupported schema")
    if value["mapping_schema_version"] != MAPPING_SCHEMA:
        raise ValidationError("plan.mapping_schema_version: unsupported schema")
    for field in (
        "source_sha256",
        "target_before_sha256",
        "mapping_sha256",
        "projected_target_sha256",
        "exception_digest",
    ):
        _sha256(value[field], f"plan.{field}")
    projected_target = validate_target(value["projected_target"])
    property_id = _location(value["property_id"], "plan.property_id")
    currency = _currency(value["currency"], "plan.currency")
    if projected_target["property_id"] != property_id or projected_target["currency"] != currency:
        raise ValidationError("plan.projected_target: identity mismatch")
    expected_target_digest = sha256_bytes(artifact_bytes(projected_target))
    if value["projected_target_sha256"] != expected_target_digest:
        raise IntegrityError("plan: projected target digest mismatch")

    departments = {item["department_code"] for item in projected_target["departments"]}
    operations = value["operations"]
    if not isinstance(operations, list):
        raise ValidationError("plan.operations: expected a list")
    normalized_operations: list[dict[str, Any]] = []
    operated_codes: set[str] = set()
    source_ids: set[str] = set()
    for index, operation in enumerate(operations, start=1):
        context = f"plan.operations[{index}]"
        if not isinstance(operation, dict):
            raise ValidationError(f"{context}: expected an object")
        _exact_keys(
            operation,
            {"action", "source_item_id", "product_code", "before", "after"},
            context,
        )
        action = operation["action"]
        if action not in {"insert", "update"}:
            raise ValidationError(f"{context}.action: expected insert or update")
        source_id = _code(operation["source_item_id"], f"{context}.source_item_id")
        product_code = _code(operation["product_code"], f"{context}.product_code")
        if source_id != product_code:
            raise ValidationError(
                f"{context}: source item and mapped product codes must match"
            )
        if source_id in source_ids or product_code in operated_codes:
            raise ValidationError(f"{context}: duplicate operation identity")
        source_ids.add(source_id)
        operated_codes.add(product_code)
        before = operation["before"]
        if action == "insert":
            if before is not None:
                raise ValidationError(f"{context}.before: insert requires null")
        else:
            before = _validate_target_product(before, f"{context}.before", departments)
        after = _validate_target_product(operation["after"], f"{context}.after", departments)
        if after["product_code"] != product_code:
            raise ValidationError(f"{context}: product code mismatch")
        normalized_operations.append(
            {
                "action": action,
                "source_item_id": source_id,
                "product_code": product_code,
                "before": before,
                "after": after,
            }
        )
    if normalized_operations != sorted(
        normalized_operations,
        key=lambda item: item["product_code"],
    ):
        raise ValidationError("plan.operations: expected product-code order")

    unchanged = value["unchanged_product_codes"]
    if (
        not isinstance(unchanged, list)
        or any(not isinstance(item, str) or not _CODE_RE.fullmatch(item) for item in unchanged)
        or unchanged != sorted(set(unchanged))
    ):
        raise ValidationError("plan.unchanged_product_codes: expected unique sorted codes")
    if operated_codes.intersection(unchanged):
        raise ValidationError("plan: operated and unchanged product codes overlap")

    raw_exceptions = value["exceptions"]
    if not isinstance(raw_exceptions, list):
        raise ValidationError("plan.exceptions: expected a list")
    exceptions = [
        _validate_exception(item, f"plan.exceptions[{index}]")
        for index, item in enumerate(raw_exceptions, start=1)
    ]
    if exceptions != sorted(exceptions, key=lambda item: (item["source_record"], item["code"])):
        raise ValidationError("plan.exceptions: expected source-record order")
    if len({item["source_record"] for item in exceptions}) != len(exceptions):
        raise ValidationError("plan.exceptions: duplicate source record")
    if value["exception_digest"] != sha256_bytes(canonical_json(exceptions)):
        raise IntegrityError("plan: exception digest mismatch")

    reconciliation = value["reconciliation"]
    reconciliation_keys = {
        "source_records",
        "eligible_records",
        "quarantined_records",
        "inserts",
        "updates",
        "unchanged",
        "target_before_records",
        "target_after_records",
    }
    if not isinstance(reconciliation, dict):
        raise ValidationError("plan.reconciliation: expected an object")
    _exact_keys(reconciliation, reconciliation_keys, "plan.reconciliation")
    if any(
        isinstance(reconciliation[key], bool)
        or not isinstance(reconciliation[key], int)
        or reconciliation[key] < 0
        for key in reconciliation_keys
    ):
        raise ValidationError("plan.reconciliation: counts must be nonnegative integers")
    inserts = sum(item["action"] == "insert" for item in normalized_operations)
    updates = sum(item["action"] == "update" for item in normalized_operations)
    expected_counts = {
        "source_records": len(normalized_operations) + len(unchanged) + len(exceptions),
        "eligible_records": len(normalized_operations) + len(unchanged),
        "quarantined_records": len(exceptions),
        "inserts": inserts,
        "updates": updates,
        "unchanged": len(unchanged),
        "target_before_records": reconciliation["target_before_records"],
        "target_after_records": len(projected_target["products"]),
    }
    if reconciliation != expected_counts:
        raise IntegrityError("plan: reconciliation counts mismatch")
    if reconciliation["target_after_records"] != reconciliation["target_before_records"] + inserts:
        raise IntegrityError("plan: target record-count reconciliation mismatch")

    unsigned = dict(value)
    plan_id = unsigned.pop("plan_id")
    _sha256(plan_id, "plan.plan_id")
    normalized_unsigned = {
        **unsigned,
        "property_id": property_id,
        "currency": currency,
        "operations": normalized_operations,
        "unchanged_product_codes": list(unchanged),
        "exceptions": exceptions,
        "reconciliation": dict(reconciliation),
        "projected_target": projected_target,
    }
    if sha256_bytes(canonical_json(normalized_unsigned)) != plan_id:
        raise IntegrityError("plan: content hash does not match plan ID")
    return {**normalized_unsigned, "plan_id": plan_id}


def load_plan_snapshot(path: Path) -> tuple[dict[str, Any], bytes, str]:
    return _read_json_snapshot(path, "plan", validate_plan)


def build_quarantine(plan: dict[str, Any]) -> dict[str, Any]:
    plan = validate_plan(plan)
    return {
        "schema_version": QUARANTINE_SCHEMA,
        "plan_id": plan["plan_id"],
        "exception_digest": plan["exception_digest"],
        "quarantined_count": len(plan["exceptions"]),
        "exceptions": plan["exceptions"],
    }


def validate_quarantine(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("quarantine: expected an object")
    _exact_keys(
        value,
        {"schema_version", "plan_id", "exception_digest", "quarantined_count", "exceptions"},
        "quarantine",
    )
    if value["schema_version"] != QUARANTINE_SCHEMA:
        raise ValidationError(f"quarantine.schema_version: expected {QUARANTINE_SCHEMA}")
    plan_id = _sha256(value["plan_id"], "quarantine.plan_id")
    digest = _sha256(value["exception_digest"], "quarantine.exception_digest")
    count = value["quarantined_count"]
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValidationError("quarantine.quarantined_count: expected a nonnegative integer")
    raw_exceptions = value["exceptions"]
    if not isinstance(raw_exceptions, list):
        raise ValidationError("quarantine.exceptions: expected a list")
    exceptions = [
        _validate_exception(item, f"quarantine.exceptions[{index}]")
        for index, item in enumerate(raw_exceptions, start=1)
    ]
    if count != len(exceptions):
        raise IntegrityError("quarantine: count mismatch")
    if digest != sha256_bytes(canonical_json(exceptions)):
        raise IntegrityError("quarantine: exception digest mismatch")
    return {
        "schema_version": QUARANTINE_SCHEMA,
        "plan_id": plan_id,
        "exception_digest": digest,
        "quarantined_count": count,
        "exceptions": exceptions,
    }


def load_quarantine_snapshot(path: Path) -> tuple[dict[str, Any], bytes, str]:
    return _read_json_snapshot(path, "quarantine", validate_quarantine)


def project_from_plan(target: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """Apply plan operations in memory while verifying every before-image."""

    target = validate_target(target)
    plan = validate_plan(plan)
    products = {item["product_code"]: item for item in target["products"]}
    for operation in plan["operations"]:
        code = operation["product_code"]
        current = products.get(code)
        if operation["action"] == "insert":
            if current is not None:
                raise IntegrityError(f"plan operation {code}: insert target already exists")
        elif current != operation["before"]:
            raise IntegrityError(f"plan operation {code}: before-image mismatch")
        products[code] = operation["after"]
    projected = validate_target(
        {
            **target,
            "products": sorted(products.values(), key=lambda item: item["product_code"]),
        }
    )
    if canonical_json(projected) != canonical_json(plan["projected_target"]):
        raise IntegrityError("plan: operations do not reconcile to projected target")
    return projected
