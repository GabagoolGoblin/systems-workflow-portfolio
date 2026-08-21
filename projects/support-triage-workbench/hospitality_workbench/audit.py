"""Append-only, hash-linked JSONL audit for the offline demo."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


AUDIT_SCHEMA = "synthetic-support-audit-v1"
ZERO_HASH = "0" * 64
EVENT_TYPES = frozenset(
    {
        "ticket_received",
        "redaction_applied",
        "triage_completed",
        "approval_pending",
        "approval_blocked",
        "approval_granted",
    }
)


class AuditIntegrityError(ValueError):
    """Raised when an existing audit chain does not verify."""


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _entry_hash(entry_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(entry_without_hash)).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def verify_audit(path: Path, *, allow_missing: bool = False) -> dict[str, Any]:
    if not path.exists():
        if allow_missing:
            return {"ok": True, "entries": 0, "head_hash": ZERO_HASH}
        raise AuditIntegrityError("audit file does not exist")
    if not path.is_file():
        raise AuditIntegrityError("audit path is not a regular file")

    previous_hash = ZERO_HASH
    expected_sequence = 1
    entries = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise AuditIntegrityError(f"blank audit line at {line_number}")
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AuditIntegrityError(f"invalid JSON at line {line_number}") from exc
        if not isinstance(entry, dict):
            raise AuditIntegrityError(f"audit line {line_number} is not an object")
        supplied_hash = entry.pop("entry_hash", None)
        if entry.get("audit_schema") != AUDIT_SCHEMA:
            raise AuditIntegrityError(f"wrong schema at line {line_number}")
        if entry.get("sequence") != expected_sequence:
            raise AuditIntegrityError(f"sequence mismatch at line {line_number}")
        if entry.get("previous_hash") != previous_hash:
            raise AuditIntegrityError(f"chain mismatch at line {line_number}")
        calculated_hash = _entry_hash(entry)
        if supplied_hash != calculated_hash:
            raise AuditIntegrityError(f"hash mismatch at line {line_number}")
        previous_hash = calculated_hash
        expected_sequence += 1
        entries += 1
    return {"ok": True, "entries": entries, "head_hash": previous_hash}


class AuditLog:
    """Single-process append-only writer that verifies before every append."""

    def __init__(self, path: Path, now: Callable[[], str] = _utc_now) -> None:
        self.path = path
        self._now = now

    def append(self, event_type: str, ticket_id: str, details: dict[str, Any]) -> str:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unsupported audit event: {event_type}")
        verification = verify_audit(self.path, allow_missing=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "audit_schema": AUDIT_SCHEMA,
            "sequence": verification["entries"] + 1,
            "timestamp": self._now(),
            "event_type": event_type,
            "ticket_id": ticket_id,
            "details": details,
            "previous_hash": verification["head_hash"],
        }
        digest = _entry_hash(entry)
        complete_entry = {**entry, "entry_hash": digest}
        encoded = json.dumps(complete_entry, sort_keys=True, separators=(",", ":")) + "\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        return digest
