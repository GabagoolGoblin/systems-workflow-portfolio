from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from migration_tool.core import (
    artifact_bytes,
    build_plan,
    sha256_bytes,
    validate_mapping,
    validate_source,
    validate_target,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


def fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def source() -> dict[str, Any]:
    return deepcopy(fixture("source.synthetic.json"))


def target() -> dict[str, Any]:
    return deepcopy(fixture("target.synthetic.json"))


def mapping() -> dict[str, Any]:
    return deepcopy(fixture("mapping.synthetic.json"))


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(artifact_bytes(value))


def plan_for(
    source_value: dict[str, Any] | None = None,
    target_value: dict[str, Any] | None = None,
    mapping_value: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_source = source_value if source_value is not None else source()
    raw_target = target_value if target_value is not None else target()
    raw_mapping = mapping_value if mapping_value is not None else mapping()
    return build_plan(
        validate_source(raw_source),
        validate_target(raw_target),
        validate_mapping(raw_mapping),
        source_sha256=sha256_bytes(artifact_bytes(raw_source)),
        target_sha256=sha256_bytes(artifact_bytes(raw_target)),
        mapping_sha256=sha256_bytes(artifact_bytes(raw_mapping)),
    )
