from __future__ import annotations

import csv
import json
from copy import deepcopy
from pathlib import Path
from typing import Any


def catalog() -> dict[str, Any]:
    return {
        "schema_version": "hospitality-catalog/v1",
        "venue_id": "demo-venue-alpha",
        "currency": "USD",
        "policy": {
            "max_percent_change": "20.00",
            "max_batch_size": 100,
            "allowed_categories": ["beverage", "entree", "side", "dessert"],
        },
        "items": [
            {
                "sku": "BEV-1001",
                "name": "Citrus Sparkler",
                "category": "beverage",
                "price": "3.25",
                "active": True,
            },
            {
                "sku": "ENT-2001",
                "name": "Garden Grain Bowl",
                "category": "entree",
                "price": "11.50",
                "active": True,
            },
            {
                "sku": "SID-3001",
                "name": "Herbed Potato Cup",
                "category": "side",
                "price": "4.20",
                "active": True,
            },
            {
                "sku": "DES-4001",
                "name": "Seasonal Orchard Tart",
                "category": "dessert",
                "price": "5.75",
                "active": False,
            },
        ],
    }


def changes() -> list[dict[str, str]]:
    return [
        {
            "venue_id": "demo-venue-alpha",
            "sku": "BEV-1001",
            "new_price": "3.50",
            "reason": "Seasonal ingredient adjustment",
            "_row": "2",
        },
        {
            "venue_id": "demo-venue-alpha",
            "sku": "ENT-2001",
            "new_price": "12.25",
            "reason": "Quarterly menu review",
            "_row": "3",
        },
        {
            "venue_id": "demo-venue-alpha",
            "sku": "SID-3001",
            "new_price": "4.50",
            "reason": "Supplier cost adjustment",
            "_row": "4",
        },
    ]


def one_change(**overrides: str) -> list[dict[str, str]]:
    row = deepcopy(changes()[0])
    row.update(overrides)
    return [row]


def write_catalog(path: Path, value: dict[str, Any] | None = None) -> None:
    path.write_text(
        json.dumps(value if value is not None else catalog(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_changes(path: Path, rows: list[dict[str, str]] | None = None) -> None:
    selected = rows if rows is not None else changes()
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["venue_id", "sku", "new_price", "reason"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(selected)
