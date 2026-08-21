"""Pure parsing, validation, and price-plan construction."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from .errors import ValidationError

CATALOG_SCHEMA = "hospitality-catalog/v1"
PLAN_SCHEMA = "hospitality-price-plan/v1"
STAGE_SCHEMA = "hospitality-price-stage/v1"
CHANGE_HEADERS = ("venue_id", "sku", "new_price", "reason")

_MONEY_RE = re.compile(r"(?:0|[1-9][0-9]*)\.[0-9]{2}\Z")
_SKU_RE = re.compile(r"[A-Z0-9][A-Z0-9_-]{1,31}\Z")
_VENUE_RE = re.compile(r"[a-z0-9][a-z0-9-]{2,47}\Z")
_CATEGORY_RE = re.compile(r"[a-z][a-z0-9_-]{1,31}\Z")
_CURRENCY_RE = re.compile(r"[A-Z]{3}\Z")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def canonical_json(value: Any) -> bytes:
    """Return the one byte representation used for content hashes."""

    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class StrictJsonError(ValueError):
    """Raised when JSON uses a representation this tool refuses."""


class DuplicateJsonKeyError(StrictJsonError):
    """Raised when a JSON object repeats a field name."""


class NonFiniteJsonNumberError(StrictJsonError):
    """Raised for JSON NaN or infinity extensions."""


def strict_json_loads(raw: str) -> Any:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DuplicateJsonKeyError(f"duplicate JSON field {key}")
            result[key] = value
        return result

    def reject_nonfinite(value: str) -> None:
        raise NonFiniteJsonNumberError(f"non-finite JSON number {value}")

    return json.loads(
        raw,
        object_pairs_hook=reject_duplicates,
        parse_constant=reject_nonfinite,
    )


def _require_exact_keys(
    value: dict[str, Any], expected: set[str], context: str
) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        parts: list[str] = []
        if missing:
            parts.append(f"missing {', '.join(missing)}")
        if extra:
            parts.append(f"unexpected {', '.join(extra)}")
        raise ValidationError(f"{context}: {'; '.join(parts)}")


def parse_money(value: Any, context: str) -> Decimal:
    if not isinstance(value, str) or not _MONEY_RE.fullmatch(value):
        raise ValidationError(f"{context}: expected a nonnegative amount with two decimals")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:  # Defensive; the regular expression is stricter.
        raise ValidationError(f"{context}: invalid amount") from exc
    if not amount.is_finite():
        raise ValidationError(f"{context}: amount must be finite")
    return amount


def format_money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _parse_positive_decimal(value: Any, context: str) -> Decimal:
    amount = parse_money(value, context)
    if amount <= 0:
        raise ValidationError(f"{context}: must be greater than zero")
    return amount


def _parse_policy(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("catalog.policy: expected an object")
    _require_exact_keys(
        value,
        {"max_percent_change", "max_batch_size", "allowed_categories"},
        "catalog.policy",
    )
    max_percent = parse_money(value["max_percent_change"], "catalog.policy.max_percent_change")
    if max_percent <= 0 or max_percent > Decimal("100.00"):
        raise ValidationError(
            "catalog.policy.max_percent_change: must be greater than zero and at most 100.00"
        )
    max_batch_size = value["max_batch_size"]
    if isinstance(max_batch_size, bool) or not isinstance(max_batch_size, int):
        raise ValidationError("catalog.policy.max_batch_size: expected an integer")
    if not 1 <= max_batch_size <= 10_000:
        raise ValidationError("catalog.policy.max_batch_size: must be between 1 and 10000")
    categories = value["allowed_categories"]
    if not isinstance(categories, list) or not categories:
        raise ValidationError("catalog.policy.allowed_categories: expected a nonempty list")
    if any(not isinstance(category, str) or not _CATEGORY_RE.fullmatch(category) for category in categories):
        raise ValidationError(
            "catalog.policy.allowed_categories: every category must use lowercase letters, digits, _ or -"
        )
    if len(set(categories)) != len(categories):
        raise ValidationError("catalog.policy.allowed_categories: duplicate category")
    return {
        "max_percent_change": format_money(max_percent),
        "max_batch_size": max_batch_size,
        "allowed_categories": list(categories),
    }


def validate_catalog(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("catalog: expected a JSON object")
    _require_exact_keys(
        value,
        {"schema_version", "venue_id", "currency", "policy", "items"},
        "catalog",
    )
    if value["schema_version"] != CATALOG_SCHEMA:
        raise ValidationError(f"catalog.schema_version: expected {CATALOG_SCHEMA}")
    venue_id = value["venue_id"]
    if not isinstance(venue_id, str) or not _VENUE_RE.fullmatch(venue_id):
        raise ValidationError("catalog.venue_id: invalid identifier")
    currency = value["currency"]
    if not isinstance(currency, str) or not _CURRENCY_RE.fullmatch(currency):
        raise ValidationError("catalog.currency: expected a three-letter uppercase code")
    policy = _parse_policy(value["policy"])
    items = value["items"]
    if not isinstance(items, list) or not items:
        raise ValidationError("catalog.items: expected a nonempty list")

    normalized_items: list[dict[str, Any]] = []
    seen_skus: set[str] = set()
    for index, item in enumerate(items, start=1):
        context = f"catalog.items[{index}]"
        if not isinstance(item, dict):
            raise ValidationError(f"{context}: expected an object")
        _require_exact_keys(
            item,
            {"sku", "name", "category", "price", "active"},
            context,
        )
        sku = item["sku"]
        if not isinstance(sku, str) or not _SKU_RE.fullmatch(sku):
            raise ValidationError(f"{context}.sku: invalid identifier")
        if sku in seen_skus:
            raise ValidationError(f"{context}.sku: duplicate SKU {sku}")
        seen_skus.add(sku)
        name = item["name"]
        if not isinstance(name, str) or not name.strip() or len(name) > 120:
            raise ValidationError(f"{context}.name: expected 1 to 120 visible characters")
        if _CONTROL_RE.search(name):
            raise ValidationError(f"{context}.name: control characters are not allowed")
        category = item["category"]
        if not isinstance(category, str) or not _CATEGORY_RE.fullmatch(category):
            raise ValidationError(f"{context}.category: invalid category")
        price = _parse_positive_decimal(item["price"], f"{context}.price")
        active = item["active"]
        if not isinstance(active, bool):
            raise ValidationError(f"{context}.active: expected true or false")
        normalized_items.append(
            {
                "sku": sku,
                "name": name.strip(),
                "category": category,
                "price": format_money(price),
                "active": active,
            }
        )

    return {
        "schema_version": CATALOG_SCHEMA,
        "venue_id": venue_id,
        "currency": currency,
        "policy": policy,
        "items": normalized_items,
    }


def parse_catalog_bytes(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"catalog: invalid UTF-8: {exc}") from exc
    try:
        value = strict_json_loads(text)
    except (json.JSONDecodeError, StrictJsonError) as exc:
        raise ValidationError(f"catalog: invalid JSON: {exc}") from exc
    return validate_catalog(value)


def load_catalog_snapshot(path: Path) -> tuple[dict[str, Any], bytes, str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"catalog: could not read {path.name}: {exc.strerror or exc}") from exc
    return parse_catalog_bytes(raw), raw, sha256_bytes(raw)


def load_catalog(path: Path) -> dict[str, Any]:
    return load_catalog_snapshot(path)[0]


def load_changes(path: Path) -> list[dict[str, str]]:
    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise ValidationError(f"changes: could not read {path.name}: {exc.strerror or exc}") from exc
    with handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValidationError("changes: missing CSV header")
        if tuple(reader.fieldnames) != CHANGE_HEADERS:
            raise ValidationError(
                "changes: header must be exactly venue_id,sku,new_price,reason"
            )
        rows: list[dict[str, str]] = []
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValidationError(f"changes row {row_number}: too many columns")
            normalized = {key: (row.get(key) or "").strip() for key in CHANGE_HEADERS}
            if not any(normalized.values()):
                continue
            normalized["_row"] = str(row_number)
            rows.append(normalized)
    if not rows:
        raise ValidationError("changes: no update rows")
    return rows


def build_plan(catalog: dict[str, Any], changes: list[dict[str, str]]) -> dict[str, Any]:
    catalog = validate_catalog(catalog)
    policy = catalog["policy"]
    if len(changes) > policy["max_batch_size"]:
        raise ValidationError(
            f"changes: batch has {len(changes)} rows; limit is {policy['max_batch_size']}"
        )
    items_by_sku = {item["sku"]: item for item in catalog["items"]}
    allowed_categories = set(policy["allowed_categories"])
    max_percent = Decimal(policy["max_percent_change"])
    seen_updates: set[str] = set()
    updates: list[dict[str, Any]] = []

    for fallback_row, change in enumerate(changes, start=2):
        row_number = change.get("_row", str(fallback_row))
        venue_id = change.get("venue_id", "")
        sku = change.get("sku", "")
        new_price_text = change.get("new_price", "")
        reason = change.get("reason", "")
        context = f"changes row {row_number}"

        if venue_id != catalog["venue_id"]:
            raise ValidationError(
                f"{context}: venue_id must match catalog venue {catalog['venue_id']}"
            )
        if not isinstance(sku, str) or not _SKU_RE.fullmatch(sku):
            raise ValidationError(f"{context}: invalid SKU")
        if sku in seen_updates:
            raise ValidationError(f"{context}: duplicate update for SKU {sku}")
        seen_updates.add(sku)
        item = items_by_sku.get(sku)
        if item is None:
            raise ValidationError(f"{context}: unknown SKU {sku}")
        if not item["active"]:
            raise ValidationError(f"{context}: SKU {sku} is inactive")
        if item["category"] not in allowed_categories:
            raise ValidationError(
                f"{context}: category {item['category']} is not allowed by policy"
            )
        new_price = _parse_positive_decimal(new_price_text, f"{context}.new_price")
        old_price = Decimal(item["price"])
        if new_price == old_price:
            raise ValidationError(f"{context}: SKU {sku} would not change")
        percent = (abs(new_price - old_price) / old_price) * Decimal("100")
        if percent > max_percent:
            shown = percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            raise ValidationError(
                f"{context}: {shown}% change exceeds policy limit {policy['max_percent_change']}%"
            )
        if not isinstance(reason, str):
            raise ValidationError(
                f"{context}.reason: expected 1 to 200 visible characters"
            )
        reason = reason.strip()
        if not reason or len(reason) > 200 or _CONTROL_RE.search(reason):
            raise ValidationError(
                f"{context}.reason: expected 1 to 200 visible characters"
            )
        updates.append(
            {
                "sku": sku,
                "name": item["name"],
                "category": item["category"],
                "before_price": item["price"],
                "after_price": format_money(new_price),
                "percent_change": format_money(percent),
                "reason": reason,
            }
        )

    updates.sort(key=lambda update: update["sku"])
    before_total = sum(Decimal(update["before_price"]) for update in updates)
    after_total = sum(Decimal(update["after_price"]) for update in updates)
    return {
        "schema_version": PLAN_SCHEMA,
        "venue_id": catalog["venue_id"],
        "currency": catalog["currency"],
        "policy": policy,
        "updates": updates,
        "summary": {
            "update_count": len(updates),
            "before_total": format_money(before_total),
            "after_total": format_money(after_total),
            "net_change": format_money(after_total - before_total),
        },
    }


def apply_updates(catalog: dict[str, Any], updates: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a validated catalog with staged prices applied."""

    normalized = validate_catalog(catalog)
    by_sku = {update["sku"]: update for update in updates}
    updated_items: list[dict[str, Any]] = []
    for item in normalized["items"]:
        replacement = by_sku.get(item["sku"])
        if replacement is None:
            updated_items.append(dict(item))
            continue
        if item["price"] != replacement["before_price"]:
            raise ValidationError(
                f"SKU {item['sku']}: current price does not match staged before_price"
            )
        changed = dict(item)
        changed["price"] = replacement["after_price"]
        updated_items.append(changed)
    missing = sorted(set(by_sku) - {item["sku"] for item in normalized["items"]})
    if missing:
        raise ValidationError(f"stage contains unknown SKUs: {', '.join(missing)}")
    result = dict(normalized)
    result["items"] = updated_items
    return validate_catalog(result)


def validate_stage(value: Any) -> dict[str, Any]:
    """Validate a persisted stage and its self-hash."""

    if not isinstance(value, dict):
        raise ValidationError("stage: expected a JSON object")
    _require_exact_keys(
        value,
        {
            "schema_version",
            "stage_id",
            "created_at",
            "source_catalog_sha256",
            "venue_id",
            "currency",
            "policy",
            "updates",
            "summary",
        },
        "stage",
    )
    if value["schema_version"] != STAGE_SCHEMA:
        raise ValidationError(f"stage.schema_version: expected {STAGE_SCHEMA}")
    stage_id = value["stage_id"]
    if not isinstance(stage_id, str) or not _SHA256_RE.fullmatch(stage_id):
        raise ValidationError("stage.stage_id: expected a lowercase SHA-256 digest")
    source_digest = value["source_catalog_sha256"]
    if not isinstance(source_digest, str) or not _SHA256_RE.fullmatch(source_digest):
        raise ValidationError(
            "stage.source_catalog_sha256: expected a lowercase SHA-256 digest"
        )
    created_at = value["created_at"]
    if not isinstance(created_at, str) or not created_at.endswith("Z"):
        raise ValidationError("stage.created_at: expected a UTC timestamp ending in Z")
    try:
        parsed_time = datetime.fromisoformat(created_at[:-1] + "+00:00")
    except ValueError as exc:
        raise ValidationError("stage.created_at: invalid UTC timestamp") from exc
    if parsed_time.utcoffset() is None or parsed_time.utcoffset().total_seconds() != 0:
        raise ValidationError("stage.created_at: expected UTC")
    venue_id = value["venue_id"]
    if not isinstance(venue_id, str) or not _VENUE_RE.fullmatch(venue_id):
        raise ValidationError("stage.venue_id: invalid identifier")
    currency = value["currency"]
    if not isinstance(currency, str) or not _CURRENCY_RE.fullmatch(currency):
        raise ValidationError("stage.currency: expected a three-letter uppercase code")
    policy = _parse_policy(value["policy"])
    updates = value["updates"]
    if not isinstance(updates, list) or not updates:
        raise ValidationError("stage.updates: expected a nonempty list")
    if len(updates) > policy["max_batch_size"]:
        raise ValidationError("stage.updates: exceeds the staged policy batch limit")

    normalized_updates: list[dict[str, Any]] = []
    seen_skus: set[str] = set()
    for index, update in enumerate(updates, start=1):
        context = f"stage.updates[{index}]"
        if not isinstance(update, dict):
            raise ValidationError(f"{context}: expected an object")
        _require_exact_keys(
            update,
            {
                "sku",
                "name",
                "category",
                "before_price",
                "after_price",
                "percent_change",
                "reason",
            },
            context,
        )
        sku = update["sku"]
        if not isinstance(sku, str) or not _SKU_RE.fullmatch(sku):
            raise ValidationError(f"{context}.sku: invalid identifier")
        if sku in seen_skus:
            raise ValidationError(f"{context}.sku: duplicate SKU {sku}")
        seen_skus.add(sku)
        name = update["name"]
        if (
            not isinstance(name, str)
            or not name.strip()
            or len(name) > 120
            or _CONTROL_RE.search(name)
        ):
            raise ValidationError(f"{context}.name: invalid name")
        category = update["category"]
        if not isinstance(category, str) or category not in policy["allowed_categories"]:
            raise ValidationError(f"{context}.category: not allowed by staged policy")
        before = _parse_positive_decimal(update["before_price"], f"{context}.before_price")
        after = _parse_positive_decimal(update["after_price"], f"{context}.after_price")
        if before == after:
            raise ValidationError(f"{context}: before and after prices must differ")
        percent = parse_money(update["percent_change"], f"{context}.percent_change")
        expected_percent = (abs(after - before) / before) * Decimal("100")
        if format_money(expected_percent) != format_money(percent):
            raise ValidationError(f"{context}.percent_change: does not match prices")
        if expected_percent > Decimal(policy["max_percent_change"]):
            raise ValidationError(f"{context}: exceeds the staged policy change limit")
        reason = update["reason"]
        if (
            not isinstance(reason, str)
            or not reason
            or len(reason) > 200
            or _CONTROL_RE.search(reason)
        ):
            raise ValidationError(f"{context}.reason: invalid reason")
        normalized_updates.append(
            {
                "sku": sku,
                "name": name,
                "category": category,
                "before_price": format_money(before),
                "after_price": format_money(after),
                "percent_change": format_money(percent),
                "reason": reason,
            }
        )

    if [update["sku"] for update in normalized_updates] != sorted(seen_skus):
        raise ValidationError("stage.updates: entries must be sorted by SKU")
    summary = value["summary"]
    if not isinstance(summary, dict):
        raise ValidationError("stage.summary: expected an object")
    _require_exact_keys(
        summary,
        {"update_count", "before_total", "after_total", "net_change"},
        "stage.summary",
    )
    before_total = sum(Decimal(update["before_price"]) for update in normalized_updates)
    after_total = sum(Decimal(update["after_price"]) for update in normalized_updates)
    expected_summary = {
        "update_count": len(normalized_updates),
        "before_total": format_money(before_total),
        "after_total": format_money(after_total),
        "net_change": format_money(after_total - before_total),
    }
    if summary != expected_summary:
        raise ValidationError("stage.summary: does not match staged updates")

    unsigned = dict(value)
    del unsigned["stage_id"]
    if sha256_bytes(canonical_json(unsigned)) != stage_id:
        raise ValidationError("stage.stage_id: manifest content hash mismatch")
    return {
        **unsigned,
        "stage_id": stage_id,
        "policy": policy,
        "updates": normalized_updates,
        "summary": expected_summary,
    }
