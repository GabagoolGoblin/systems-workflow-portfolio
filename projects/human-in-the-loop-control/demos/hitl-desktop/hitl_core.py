"""GUI-free state transitions for the clean-room automation lab."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DemoRow:
    """One invented request row as it moves through the lab workflow."""

    request_id: str
    barcode: str
    item_name: str
    current_price: str
    requested_price: str
    menu_item_id: str = ""
    staged_price: str = ""
    reread_price: str = ""
    status: str = "Pending"
    duplicate_submission: bool = False


DUPLICATE_HOLD_STATUS = "Held: duplicate barcode submission"


def _fixture_path() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "synthetic_menu_batch.json"


def _data_is_synthetic(data: dict[str, object]) -> bool:
    """Check the fixture declaration and structural clean-room invariants."""
    rows = data.get("requests") or []
    cache = data.get("cache") or {}
    if not isinstance(rows, list) or not isinstance(cache, dict):
        return False
    if not all(isinstance(row, dict) for row in rows):
        return False

    required_row_fields = (
        "request_id",
        "barcode",
        "item_name",
        "current_price",
        "requested_price",
        "source",
    )
    request_ids = [str(row.get("request_id", "")) for row in rows]
    barcodes = [str(row.get("barcode", "")) for row in rows]
    cache_keys = [str(key) for key in cache]
    cache_values = [str(value) for value in cache.values()]
    return bool(
        data.get("schema") == "synthetic-lab-v1"
        and data.get("synthetic_only")
        and data.get("invented_values_only")
        and data.get("no_external_records")
        and rows
        and all(
            all(
                isinstance(row.get(field), str) and row.get(field)
                for field in required_row_fields
            )
            for row in rows
        )
        and len(request_ids) == len(set(request_ids))
        and len(barcodes) > len(set(barcodes))
        and all(len(value) == 12 and value.isdigit() for value in barcodes)
        and all(row.get("source") == "synthetic_fixture" for row in rows)
        and len(cache_keys) == len(set(cache_keys))
        and len(cache_values) == len(set(cache_values))
        and all(key in barcodes for key in cache_keys)
        and all(len(key) == 12 and key.isdigit() for key in cache_keys)
        and all(value.isdigit() for value in cache_values)
        and str(data.get("held_manual_menu_item_id", "")).isdigit()
        and str(data.get("held_manual_menu_item_id", "")) not in cache_values
    )


def _load_fixture_batch() -> tuple[dict[str, str], list[DemoRow], str]:
    """Load the invented fixture batch; fall back to lab records if it is missing."""
    path = _fixture_path()
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and _data_is_synthetic(data):
            cache = {str(k): str(v) for k, v in (data.get("cache") or {}).items()}
            rows = [
                DemoRow(
                    request_id=str(item["request_id"]),
                    barcode=str(item["barcode"]),
                    item_name=str(item["item_name"]),
                    current_price=str(item["current_price"]),
                    requested_price=str(item["requested_price"]),
                )
                for item in data.get("requests") or []
            ]
            held_id = str(data.get("held_manual_menu_item_id") or "7001999")
            return cache, rows, held_id

    cache = {
        "100000000011": "7001001",
        "100000000028": "7001002",
        "100000000035": "7001003",
    }
    rows = [
        DemoRow("LAB-REQ-001", "100000000011", "Citrus Sparkler", "2.49", "2.69"),
        DemoRow("LAB-REQ-002", "100000000028", "Berry Iced Tea", "2.79", "2.99"),
        DemoRow("LAB-REQ-003", "100000000035", "Vanilla Cold Brew", "3.89", "4.19"),
        DemoRow("LAB-REQ-004", "100000000042", "Ginger Lime Soda", "2.59", "2.79"),
        DemoRow("LAB-REQ-005", "100000000011", "Citrus Sparkler", "2.49", "2.69"),
    ]
    return cache, rows, "7001999"


DEMO_CACHE, DEMO_REQUESTS, HELD_MANUAL_MENU_ITEM_ID = _load_fixture_batch()


def fresh_rows() -> list[DemoRow]:
    """Return a clean copy of the invented request batch."""
    return copy.deepcopy(DEMO_REQUESTS)


def fixture_is_synthetic() -> bool:
    """Validate the fixture's explicit clean-room invariants."""
    path = _fixture_path()
    if not path.is_file():
        return False

    data = json.loads(path.read_text(encoding="utf-8"))
    return isinstance(data, dict) and _data_is_synthetic(data)


def hold_duplicate_submissions(rows: list[DemoRow]) -> int:
    """Hold every repeated request barcode after its first submitted row."""
    seen: set[str] = set()
    held = 0
    for row in rows:
        row.duplicate_submission = row.barcode in seen
        seen.add(row.barcode)
        if row.duplicate_submission:
            row.menu_item_id = ""
            row.staged_price = ""
            row.reread_price = ""
            row.status = DUPLICATE_HOLD_STATUS
            held += 1
    return held


def resolve_from_cache(rows: list[DemoRow], cache: dict[str, str]) -> tuple[int, int]:
    """Resolve known identifiers while holding misses and repeated requests."""
    hold_duplicate_submissions(rows)
    hits = 0
    held = 0
    for row in rows:
        if row.duplicate_submission:
            held += 1
            continue
        menu_item_id = cache.get(row.barcode, "")
        if menu_item_id:
            row.menu_item_id = menu_item_id
            row.status = "Cache hit"
            hits += 1
        else:
            row.menu_item_id = ""
            row.status = "Held for manual lookup"
            held += 1
    return hits, held


def validate_held_row(
    rows: list[DemoRow], cache: dict[str, str], request_id: str, menu_item_id: str
) -> None:
    """Apply a person's lab-only mapping to one unresolved row."""
    hold_duplicate_submissions(rows)
    if not menu_item_id.isdigit():
        raise ValueError("The synthetic menu-item ID must be numeric.")
    if menu_item_id in cache.values():
        raise ValueError("The synthetic menu-item ID must be unique in the cache.")
    for row in rows:
        if row.request_id != request_id:
            continue
        if row.duplicate_submission:
            raise ValueError("A duplicate barcode submission cannot receive a menu-item ID.")
        if not row.menu_item_id:
            row.menu_item_id = menu_item_id
            row.status = "Manually validated"
            cache[row.barcode] = menu_item_id
            return
    raise ValueError("No held row matched that request ID.")


def stage_price_updates(rows: list[DemoRow]) -> None:
    """Stage eligible values while repeated request rows remain excluded."""
    hold_duplicate_submissions(rows)
    eligible = [row for row in rows if not row.duplicate_submission]
    if not eligible or any(not row.menu_item_id for row in eligible):
        raise ValueError("Resolve or manually validate every eligible held row before staging.")
    for row in eligible:
        row.staged_price = row.requested_price
        row.reread_price = ""
        row.status = "Staged, not saved"


def reread_staged_updates(rows: list[DemoRow], mismatch_request_id: str = "") -> bool:
    """Reread staged values and hold the batch on any mismatch."""
    hold_duplicate_submissions(rows)
    eligible = [row for row in rows if not row.duplicate_submission]
    if not eligible or any(not row.staged_price for row in eligible):
        raise ValueError("Stage the proposed updates before verification.")
    all_verified = True
    for row in eligible:
        row.reread_price = (
            "999.99" if row.request_id == mismatch_request_id else row.staged_price
        )
        if row.reread_price == row.requested_price:
            row.status = "Verified, awaiting approval"
        else:
            row.status = "Held: reread mismatch"
            all_verified = False
    return all_verified


def approve_lab_save(rows: list[DemoRow]) -> None:
    """Persist eligible synthetic values only after each passes reread review."""
    hold_duplicate_submissions(rows)
    eligible = [row for row in rows if not row.duplicate_submission]
    if not eligible or any(
        row.status != "Verified, awaiting approval" for row in eligible
    ):
        raise ValueError("Human approval is blocked until every staged row verifies.")
    for row in eligible:
        row.current_price = row.staged_price
        row.status = "Saved after human approval (lab)"
