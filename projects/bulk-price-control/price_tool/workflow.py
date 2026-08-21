"""Dry-run, stage, commit, and post-write verification workflows."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from .audit import append_event, read_audit
from .core import (
    apply_updates,
    build_plan,
    canonical_json,
    load_catalog_snapshot,
    load_changes,
    sha256_bytes,
    STAGE_SCHEMA,
    strict_json_loads,
    validate_stage,
)
from .errors import IntegrityError, PriceToolError, StateConflictError, ValidationError
from .locking import advisory_lock, lock_path_for

Clock = Callable[[], str]


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def _write_new_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise StateConflictError(f"refusing to overwrite existing stage file {path.name}") from exc
    try:
        offset = 0
        while offset < len(content):
            written = os.write(descriptor, content[offset:])
            if written <= 0:
                raise IntegrityError("stage: incomplete write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_bytes_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def _write_catalog_atomic(path: Path, catalog: dict[str, Any]) -> bytes:
    content = _json_bytes(catalog)
    _write_bytes_atomic(path, content)
    return content


def dry_run(catalog_path: Path, changes_path: Path) -> dict[str, Any]:
    catalog, _catalog_bytes, catalog_digest = load_catalog_snapshot(catalog_path)
    plan = build_plan(catalog, load_changes(changes_path))
    return {
        "mode": "dry-run",
        "source_catalog_sha256": catalog_digest,
        **plan,
    }


def create_stage(
    catalog_path: Path,
    changes_path: Path,
    stage_path: Path,
    audit_path: Path,
    *,
    clock: Clock = utc_now,
) -> dict[str, Any]:
    read_audit(audit_path)  # Fail before writing if the existing chain is corrupt.
    catalog, _catalog_bytes, catalog_digest = load_catalog_snapshot(catalog_path)
    plan = build_plan(catalog, load_changes(changes_path))
    unsigned = {
        **plan,
        "schema_version": STAGE_SCHEMA,
        "created_at": clock(),
        "source_catalog_sha256": catalog_digest,
    }
    stage_id = sha256_bytes(canonical_json(unsigned))
    stage = {**unsigned, "stage_id": stage_id}
    stage = validate_stage(stage)
    content = _json_bytes(stage)
    _write_new_file(stage_path, content)
    append_event(
        audit_path,
        event_type="stage_created",
        occurred_at=clock(),
        stage_id=stage_id,
        venue_id=stage["venue_id"],
        evidence={
            "source_catalog_sha256": stage["source_catalog_sha256"],
            "stage_file_sha256": sha256_bytes(content),
            "update_count": stage["summary"]["update_count"],
        },
    )
    return stage


def load_stage_snapshot(path: Path) -> tuple[dict[str, Any], bytes, str]:
    """Parse and hash one immutable-in-memory snapshot of a stage file."""

    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"stage: could not read {path.name}: {exc.strerror or exc}") from exc
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise ValidationError(f"stage: invalid UTF-8 JSON: {exc}") from exc
    return validate_stage(value), raw, sha256_bytes(raw)


def load_stage(path: Path) -> dict[str, Any]:
    stage, _raw, _digest = load_stage_snapshot(path)
    return stage


def _require_stage_audit(
    events: list[dict[str, Any]], stage: dict[str, Any], stage_file_sha256: str
) -> None:
    for event in events:
        evidence = event["evidence"]
        if (
            event["event_type"] == "stage_created"
            and event["stage_id"] == stage["stage_id"]
            and event["venue_id"] == stage["venue_id"]
            and evidence.get("source_catalog_sha256") == stage["source_catalog_sha256"]
            and evidence.get("stage_file_sha256") == stage_file_sha256
        ):
            return
    raise IntegrityError("commit: no matching stage_created audit evidence")


def commit_stage(
    catalog_path: Path,
    stage_path: Path,
    audit_path: Path,
    confirmation: str,
    *,
    clock: Clock = utc_now,
) -> dict[str, Any]:
    if lock_path_for(catalog_path) == lock_path_for(audit_path):
        raise ValidationError("commit: catalog and audit paths must be distinct")
    with advisory_lock(catalog_path):
        return _commit_stage_locked(
            catalog_path,
            stage_path,
            audit_path,
            confirmation,
            clock=clock,
        )


def _commit_stage_locked(
    catalog_path: Path,
    stage_path: Path,
    audit_path: Path,
    confirmation: str,
    *,
    clock: Clock,
) -> dict[str, Any]:
    stage, _stage_bytes, stage_file_sha256 = load_stage_snapshot(stage_path)
    if confirmation != stage["stage_id"]:
        raise StateConflictError("commit: confirmation does not match the exact stage ID")
    events = read_audit(audit_path)
    _require_stage_audit(events, stage, stage_file_sha256)
    if any(
        event["event_type"] == "commit_verified" and event["stage_id"] == stage["stage_id"]
        for event in events
    ):
        raise StateConflictError("commit: this stage already has verified commit evidence")

    catalog, original_bytes, current_digest = load_catalog_snapshot(catalog_path)
    if current_digest != stage["source_catalog_sha256"]:
        raise StateConflictError("commit: catalog changed after staging")
    if catalog["venue_id"] != stage["venue_id"] or catalog["currency"] != stage["currency"]:
        raise StateConflictError("commit: catalog identity does not match the stage")
    target = apply_updates(catalog, stage["updates"])

    append_event(
        audit_path,
        event_type="commit_started",
        occurred_at=clock(),
        stage_id=stage["stage_id"],
        venue_id=stage["venue_id"],
        evidence={
            "catalog_before_sha256": current_digest,
            "update_count": stage["summary"]["update_count"],
        },
    )

    write_started = False
    try:
        if catalog_path.read_bytes() != original_bytes:
            raise StateConflictError("commit: catalog changed while commit was starting")
        write_started = True
        expected_bytes = _write_catalog_atomic(catalog_path, target)
        expected_digest = sha256_bytes(expected_bytes)
        verified_catalog, _verified_bytes, actual_digest = load_catalog_snapshot(catalog_path)
        if actual_digest != expected_digest:
            raise IntegrityError("commit: reread catalog digest does not match the write")
        if canonical_json(verified_catalog) != canonical_json(target):
            raise IntegrityError("commit: reread catalog content does not match the write")
        verified_by_sku = {item["sku"]: item for item in verified_catalog["items"]}
        for update in stage["updates"]:
            actual = verified_by_sku.get(update["sku"])
            if actual is None or actual["price"] != update["after_price"]:
                raise IntegrityError(f"commit: reread verification failed for SKU {update['sku']}")
        append_event(
            audit_path,
            event_type="commit_verified",
            occurred_at=clock(),
            stage_id=stage["stage_id"],
            venue_id=stage["venue_id"],
            evidence={
                "catalog_before_sha256": current_digest,
                "catalog_after_sha256": actual_digest,
                "verified_skus": [update["sku"] for update in stage["updates"]],
            },
        )
    except Exception as exc:
        restored = False
        if write_started:
            try:
                _write_bytes_atomic(catalog_path, original_bytes)
                restored = catalog_path.read_bytes() == original_bytes
            except OSError:
                restored = False
        try:
            append_event(
                audit_path,
                event_type="commit_rolled_back",
                occurred_at=clock(),
                stage_id=stage["stage_id"],
                venue_id=stage["venue_id"],
                evidence={
                    "catalog_restored": restored,
                    "failure_code": exc.code if isinstance(exc, PriceToolError) else "unexpected_error",
                },
            )
        except PriceToolError as audit_exc:
            raise IntegrityError(
                f"commit failed; catalog_restored={restored}; rollback audit also failed: {audit_exc.message}"
            ) from exc
        if isinstance(exc, PriceToolError):
            raise
        raise IntegrityError(f"commit failed after write; catalog_restored={restored}") from exc

    return {
        "mode": "commit",
        "stage_id": stage["stage_id"],
        "venue_id": stage["venue_id"],
        "verified": True,
        "verified_skus": [update["sku"] for update in stage["updates"]],
        "catalog_after_sha256": actual_digest,
    }
