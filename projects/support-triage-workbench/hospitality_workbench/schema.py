"""Strict schema for invented support tickets."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


BATCH_SCHEMA = "synthetic-support-batch-v1"
TICKET_SCHEMA = "synthetic-support-ticket-v1"

REQUESTER_ROLES = frozenset(
    {"site_operator", "regional_support", "implementation_specialist"}
)
IMPACTS = frozenset({"single_user", "single_site", "multiple_sites", "unknown"})
WORKFLOWS = frozenset(
    {"menu_configuration", "order_flow", "access", "reporting", "device_sync", "other"}
)
SIGNALS = frozenset(
    {
        "workflow_blocked",
        "data_mismatch",
        "intermittent",
        "access_denied",
        "error_visible",
        "workaround_available",
        "safety_concern",
        "performance_degraded",
    }
)
OBSERVATION_KINDS = frozenset(
    {
        "error_text",
        "timestamp",
        "expected_behavior",
        "observed_behavior",
        "scope_note",
    }
)

TICKET_ID_RE = re.compile(r"LAB-TKT-[0-9]{4}\Z")
SITE_CODE_RE = re.compile(r"LAB-SITE-[0-9]{3}\Z")

TICKET_FIELDS = frozenset(
    {
        "schema_version",
        "ticket_id",
        "created_at",
        "requester_role",
        "site_codes",
        "subject",
        "description",
        "impact",
        "affected_workflow",
        "signals",
        "observations",
        "attempted_steps",
    }
)


class SchemaError(ValueError):
    """Raised when an input fails the clean-room ticket contract."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")

    def to_dict(self) -> dict[str, str]:
        return {"error": "schema_error", "path": self.path, "message": self.message}


@dataclass(frozen=True)
class Observation:
    kind: str
    value: str

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "value": self.value}


@dataclass(frozen=True)
class Ticket:
    schema_version: str
    ticket_id: str
    created_at: str
    requester_role: str
    site_codes: tuple[str, ...]
    subject: str
    description: str
    impact: str
    affected_workflow: str
    signals: tuple[str, ...]
    observations: tuple[Observation, ...]
    attempted_steps: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "ticket_id": self.ticket_id,
            "created_at": self.created_at,
            "requester_role": self.requester_role,
            "site_codes": list(self.site_codes),
            "subject": self.subject,
            "description": self.description,
            "impact": self.impact,
            "affected_workflow": self.affected_workflow,
            "signals": list(self.signals),
            "observations": [item.to_dict() for item in self.observations],
            "attempted_steps": list(self.attempted_steps),
        }


def _strict_object(value: object, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SchemaError(path, "must be a JSON object")
    return value


def _require_exact_fields(raw: dict[str, Any], expected: frozenset[str], path: str) -> None:
    keys = frozenset(raw)
    missing = sorted(expected - keys)
    unknown = sorted(keys - expected)
    if missing:
        raise SchemaError(path, f"missing fields: {', '.join(missing)}")
    if unknown:
        raise SchemaError(path, f"unknown fields: {', '.join(unknown)}")


def _require_text(
    raw: dict[str, Any],
    key: str,
    path: str,
    *,
    minimum: int,
    maximum: int,
    allowed: frozenset[str] | None = None,
    pattern: re.Pattern[str] | None = None,
) -> str:
    value = raw[key]
    field_path = f"{path}.{key}"
    if not isinstance(value, str):
        raise SchemaError(field_path, "must be a string")
    if value != value.strip():
        raise SchemaError(field_path, "must not have leading or trailing whitespace")
    if not minimum <= len(value) <= maximum:
        raise SchemaError(field_path, f"length must be between {minimum} and {maximum}")
    if allowed is not None and value not in allowed:
        raise SchemaError(field_path, f"unsupported value: {value}")
    if pattern is not None and pattern.fullmatch(value) is None:
        raise SchemaError(field_path, "must use the documented synthetic format")
    return value


def _require_string_list(
    raw: dict[str, Any],
    key: str,
    path: str,
    *,
    minimum: int,
    maximum: int,
    item_minimum: int,
    item_maximum: int,
    allowed: frozenset[str] | None = None,
    pattern: re.Pattern[str] | None = None,
) -> tuple[str, ...]:
    value = raw[key]
    field_path = f"{path}.{key}"
    if not isinstance(value, list):
        raise SchemaError(field_path, "must be an array")
    if not minimum <= len(value) <= maximum:
        raise SchemaError(field_path, f"item count must be between {minimum} and {maximum}")
    items: list[str] = []
    for index, item in enumerate(value):
        item_path = f"{field_path}[{index}]"
        if not isinstance(item, str):
            raise SchemaError(item_path, "must be a string")
        if item != item.strip() or not item_minimum <= len(item) <= item_maximum:
            raise SchemaError(item_path, "has invalid whitespace or length")
        if allowed is not None and item not in allowed:
            raise SchemaError(item_path, f"unsupported value: {item}")
        if pattern is not None and pattern.fullmatch(item) is None:
            raise SchemaError(item_path, "must use the documented synthetic format")
        items.append(item)
    if len(items) != len(set(items)):
        raise SchemaError(field_path, "must not contain duplicates")
    return tuple(items)


def _parse_observations(raw: dict[str, Any], path: str) -> tuple[Observation, ...]:
    value = raw["observations"]
    field_path = f"{path}.observations"
    if not isinstance(value, list):
        raise SchemaError(field_path, "must be an array")
    if len(value) > 12:
        raise SchemaError(field_path, "must contain at most 12 observations")
    observations: list[Observation] = []
    for index, item in enumerate(value):
        item_path = f"{field_path}[{index}]"
        item_raw = _strict_object(item, item_path)
        _require_exact_fields(item_raw, frozenset({"kind", "value"}), item_path)
        kind = _require_text(
            item_raw,
            "kind",
            item_path,
            minimum=1,
            maximum=40,
            allowed=OBSERVATION_KINDS,
        )
        text = _require_text(
            item_raw,
            "value",
            item_path,
            minimum=1,
            maximum=500,
        )
        observations.append(Observation(kind=kind, value=text))
    return tuple(observations)


def parse_ticket(value: object, path: str = "$.ticket") -> Ticket:
    raw = _strict_object(value, path)
    _require_exact_fields(raw, TICKET_FIELDS, path)

    schema_version = _require_text(
        raw,
        "schema_version",
        path,
        minimum=len(TICKET_SCHEMA),
        maximum=len(TICKET_SCHEMA),
        allowed=frozenset({TICKET_SCHEMA}),
    )
    ticket_id = _require_text(
        raw, "ticket_id", path, minimum=12, maximum=12, pattern=TICKET_ID_RE
    )
    created_at = _require_text(raw, "created_at", path, minimum=20, maximum=20)
    try:
        parsed_created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise SchemaError(f"{path}.created_at", "must use UTC YYYY-MM-DDTHH:MM:SSZ") from exc
    if parsed_created_at.year < 2020:
        raise SchemaError(f"{path}.created_at", "year is outside the lab fixture range")

    requester_role = _require_text(
        raw,
        "requester_role",
        path,
        minimum=1,
        maximum=40,
        allowed=REQUESTER_ROLES,
    )
    site_codes = _require_string_list(
        raw,
        "site_codes",
        path,
        minimum=1,
        maximum=10,
        item_minimum=12,
        item_maximum=12,
        pattern=SITE_CODE_RE,
    )
    subject = _require_text(raw, "subject", path, minimum=5, maximum=160)
    description = _require_text(raw, "description", path, minimum=20, maximum=2000)
    impact = _require_text(
        raw, "impact", path, minimum=1, maximum=30, allowed=IMPACTS
    )
    affected_workflow = _require_text(
        raw,
        "affected_workflow",
        path,
        minimum=1,
        maximum=40,
        allowed=WORKFLOWS,
    )
    signals = _require_string_list(
        raw,
        "signals",
        path,
        minimum=0,
        maximum=len(SIGNALS),
        item_minimum=1,
        item_maximum=40,
        allowed=SIGNALS,
    )
    observations = _parse_observations(raw, path)
    attempted_steps = _require_string_list(
        raw,
        "attempted_steps",
        path,
        minimum=0,
        maximum=12,
        item_minimum=3,
        item_maximum=300,
    )

    return Ticket(
        schema_version=schema_version,
        ticket_id=ticket_id,
        created_at=created_at,
        requester_role=requester_role,
        site_codes=site_codes,
        subject=subject,
        description=description,
        impact=impact,
        affected_workflow=affected_workflow,
        signals=signals,
        observations=observations,
        attempted_steps=attempted_steps,
    )


def parse_synthetic_batch(value: object) -> tuple[Ticket, ...]:
    raw = _strict_object(value, "$")
    expected = frozenset({"schema_version", "synthetic_only", "tickets"})
    _require_exact_fields(raw, expected, "$")
    if raw["schema_version"] != BATCH_SCHEMA:
        raise SchemaError("$.schema_version", f"must equal {BATCH_SCHEMA}")
    if raw["synthetic_only"] is not True:
        raise SchemaError("$.synthetic_only", "must be true")
    tickets_raw = raw["tickets"]
    if not isinstance(tickets_raw, list):
        raise SchemaError("$.tickets", "must be an array")
    if not 1 <= len(tickets_raw) <= 100:
        raise SchemaError("$.tickets", "must contain between 1 and 100 tickets")
    return tuple(
        parse_ticket(item, path=f"$.tickets[{index}]")
        for index, item in enumerate(tickets_raw)
    )


def load_synthetic_batch(path: Path) -> tuple[Ticket, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SchemaError("$", f"unable to read valid JSON: {exc}") from exc
    return parse_synthetic_batch(payload)

