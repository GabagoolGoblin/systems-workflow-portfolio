#!/usr/bin/env python3
"""Render the browser fixture deterministically from the public JSON snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "open_food_facts_snapshot.json"
TARGET = ROOT / "data" / "catalog_snapshot.js"


def quoted(value: object) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def render(snapshot: dict[str, object]) -> str:
    records = snapshot["records"]
    if not isinstance(records, list) or len(records) != 6:
        raise ValueError("expected exactly six retained records")
    found = [record for record in records if record["http_status"] == 200]
    not_found = [record for record in records if record["http_status"] == 404]
    if len(found) != 5 or len(not_found) != 1:
        raise ValueError("expected five found records and one not-found control")

    lines = [
        '"use strict";',
        "",
        "// Generated from open_food_facts_snapshot.json. Public identity facts are",
        "// attributed in DATA_LICENSE.md; this file contains no price field.",
        "window.CATALOG_SNAPSHOT = Object.freeze({",
        f"  id: {quoted(snapshot['snapshot_id'])},",
        f"  capturedOn: {quoted(snapshot['captured_on'])},",
        f"  runtimeRequests: {int(snapshot['capture_policy']['runtime_requests'])},",
        "  products: Object.freeze([",
    ]
    for record in found:
        response = record["response"]
        product = response["product"]
        warning_ids = [warning["message"]["id"] for warning in response.get("warnings", [])]
        state = "found_with_normalization_warning" if "different_normalized_product_code" in warning_ids else "found"
        lines.extend(
            [
                "    Object.freeze({",
                f"      requestedCode: {quoted(record['requested_code'])},",
                f"      code: {quoted(product['code'])},",
                f"      brand: {quoted(product['brands'])},",
                f"      name: {quoted(product['product_name'])},",
                f"      quantity: {quoted(product['quantity'])},",
                f"      category: {quoted(product['categories'])},",
                f"      countries: {quoted(product['countries'])},",
                f"      retrievedAt: {quoted(record['retrieved_at'])},",
                f"      sourceUrl: {quoted(record['source_url'])},",
                f"      sourceState: {quoted(state)},",
                "    }),",
            ]
        )
    record = not_found[0]
    lines.extend(
        [
            "  ]),",
            "  notFound: Object.freeze({",
            f"    requestedCode: {quoted(record['requested_code'])},",
            f"    code: {quoted(record['response']['code'])},",
            f"    retrievedAt: {quoted(record['retrieved_at'])},",
            f"    sourceUrl: {quoted(record['source_url'])},",
            f"    sourceState: {quoted(record['response']['result']['id'])},",
            f"    httpStatus: {int(record['http_status'])},",
            "  }),",
            "});",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Replace the checked-in derived fixture")
    args = parser.parse_args()
    rendered = render(json.loads(SOURCE.read_text(encoding="utf-8")))
    if args.write:
        TARGET.write_text(rendered, encoding="utf-8")
        print(f"WROTE: {TARGET}")
        return 0
    if not TARGET.is_file() or TARGET.read_text(encoding="utf-8") != rendered:
        print("FAIL: data/catalog_snapshot.js is stale")
        return 1
    print("PASS: data/catalog_snapshot.js matches the public JSON snapshot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
