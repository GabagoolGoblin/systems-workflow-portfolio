"""Append-only, hash-chained JSONL audit evidence."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .core import StrictJsonError, canonical_json, sha256_bytes, strict_json_loads
from .errors import IntegrityError
from .locking import advisory_lock

AUDIT_SCHEMA = "hospitality-price-audit/v1"
GENESIS_HASH = "0" * 64
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_EVENT_TYPES = {
    "stage_created",
    "commit_started",
    "commit_verified",
    "commit_rolled_back",
}
_EVENT_KEYS = {
    "schema_version",
    "sequence",
    "event_type",
    "occurred_at",
    "stage_id",
    "venue_id",
    "previous_hash",
    "evidence",
    "event_hash",
}


def _validate_event(event: Any, expected_sequence: int, previous_hash: str) -> None:
    if not isinstance(event, dict) or set(event) != _EVENT_KEYS:
        raise IntegrityError(f"audit event {expected_sequence}: invalid fields")
    if event["schema_version"] != AUDIT_SCHEMA:
        raise IntegrityError(f"audit event {expected_sequence}: invalid schema")
    if (
        isinstance(event["sequence"], bool)
        or not isinstance(event["sequence"], int)
        or event["sequence"] != expected_sequence
    ):
        raise IntegrityError(f"audit event {expected_sequence}: sequence mismatch")
    if event["event_type"] not in _EVENT_TYPES:
        raise IntegrityError(f"audit event {expected_sequence}: invalid event type")
    occurred_at = event["occurred_at"]
    if not isinstance(occurred_at, str) or not occurred_at.endswith("Z"):
        raise IntegrityError(f"audit event {expected_sequence}: invalid timestamp")
    try:
        parsed_time = datetime.fromisoformat(occurred_at[:-1] + "+00:00")
    except ValueError as exc:
        raise IntegrityError(f"audit event {expected_sequence}: invalid timestamp") from exc
    if parsed_time.utcoffset() is None or parsed_time.utcoffset().total_seconds() != 0:
        raise IntegrityError(f"audit event {expected_sequence}: timestamp is not UTC")
    if not isinstance(event["stage_id"], str) or not _SHA256_RE.fullmatch(event["stage_id"]):
        raise IntegrityError(f"audit event {expected_sequence}: invalid stage ID")
    if not isinstance(event["venue_id"], str) or not event["venue_id"]:
        raise IntegrityError(f"audit event {expected_sequence}: invalid venue ID")
    if event["previous_hash"] != previous_hash:
        raise IntegrityError(f"audit event {expected_sequence}: chain mismatch")
    if not isinstance(event["evidence"], dict):
        raise IntegrityError(f"audit event {expected_sequence}: evidence must be an object")
    unsigned = dict(event)
    event_hash = unsigned.pop("event_hash")
    if not isinstance(event_hash, str) or not _SHA256_RE.fullmatch(event_hash):
        raise IntegrityError(f"audit event {expected_sequence}: invalid event hash")
    if sha256_bytes(canonical_json(unsigned)) != event_hash:
        raise IntegrityError(f"audit event {expected_sequence}: content hash mismatch")


def _read_audit_unlocked(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        raw_lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise IntegrityError(f"audit: could not read valid UTF-8 JSONL: {exc}") from exc
    events: list[dict[str, Any]] = []
    previous_hash = GENESIS_HASH
    for line_number, line in enumerate(raw_lines, start=1):
        if not line:
            raise IntegrityError(f"audit event {line_number}: blank lines are not allowed")
        try:
            event = strict_json_loads(line)
        except (json.JSONDecodeError, StrictJsonError) as exc:
            raise IntegrityError(f"audit event {line_number}: invalid JSON") from exc
        _validate_event(event, line_number, previous_hash)
        events.append(event)
        previous_hash = event["event_hash"]
    return events


def read_audit(path: Path) -> list[dict[str, Any]]:
    with advisory_lock(path):
        return _read_audit_unlocked(path)


def append_event(
    path: Path,
    *,
    event_type: str,
    occurred_at: str,
    stage_id: str,
    venue_id: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    if event_type not in _EVENT_TYPES:
        raise IntegrityError(f"audit: unsupported event type {event_type}")
    with advisory_lock(path):
        events = _read_audit_unlocked(path)
        previous_hash = events[-1]["event_hash"] if events else GENESIS_HASH
        unsigned: dict[str, Any] = {
            "schema_version": AUDIT_SCHEMA,
            "sequence": len(events) + 1,
            "event_type": event_type,
            "occurred_at": occurred_at,
            "stage_id": stage_id,
            "venue_id": venue_id,
            "previous_hash": previous_hash,
            "evidence": evidence,
        }
        try:
            event_hash = sha256_bytes(canonical_json(unsigned))
        except (TypeError, ValueError) as exc:
            raise IntegrityError("audit: evidence is not JSON serializable") from exc
        event = {**unsigned, "event_hash": event_hash}
        _validate_event(event, len(events) + 1, previous_hash)
        line = canonical_json(event) + b"\n"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
            try:
                offset = 0
                while offset < len(line):
                    written = os.write(descriptor, line[offset:])
                    if written <= 0:
                        raise IntegrityError("audit: incomplete append")
                    offset += written
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError as exc:
            raise IntegrityError(f"audit: append failed: {exc.strerror or exc}") from exc
        verified = _read_audit_unlocked(path)
        if not verified or verified[-1]["event_hash"] != event_hash:
            raise IntegrityError("audit: appended event did not verify")
        return event
