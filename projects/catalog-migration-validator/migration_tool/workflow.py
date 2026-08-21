"""Read-only planning, review staging, and verified local application."""

from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from .audit import append_event, read_audit
from .core import (
    artifact_bytes,
    build_plan,
    build_quarantine,
    canonical_json,
    load_mapping_snapshot,
    load_plan_snapshot,
    load_quarantine_snapshot,
    load_source_snapshot,
    load_target_snapshot,
    project_from_plan,
    sha256_bytes,
)
from .errors import IntegrityError, MigrationError, StateConflictError, ValidationError
from .locking import locked_sidecar, resource_key

Clock = Callable[[], str]


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_exclusive(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise StateConflictError(f"stage: refusing to overwrite {path.name}") from exc
    try:
        try:
            offset = 0
            while offset < len(content):
                written = os.write(descriptor, content[offset:])
                if written <= 0:
                    raise IntegrityError(f"stage: incomplete write for {path.name}")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        _fsync_directory(path.parent)
    except Exception:
        try:
            path.unlink()
            _fsync_directory(path.parent)
        except OSError:
            pass
        raise


def _write_atomic(path: Path, content: bytes) -> None:
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
        _fsync_directory(path.parent)
    except Exception:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def _require_distinct(context: str, paths: dict[str, Path]) -> None:
    seen: dict[Path, str] = {}
    for label, path in paths.items():
        key = resource_key(path)
        if key in seen:
            raise ValidationError(
                f"{context}: {label} and {seen[key]} paths must be distinct"
            )
        seen[key] = label


def dry_run(
    source_path: Path,
    target_path: Path,
    mapping_path: Path,
) -> dict[str, Any]:
    source, _source_bytes, source_digest = load_source_snapshot(source_path)
    target, _target_bytes, target_digest = load_target_snapshot(target_path)
    mapping, _mapping_bytes, mapping_digest = load_mapping_snapshot(mapping_path)
    plan = build_plan(
        source,
        target,
        mapping,
        source_sha256=source_digest,
        target_sha256=target_digest,
        mapping_sha256=mapping_digest,
    )
    return {
        "mode": "dry-run",
        "plan": plan,
        "quarantine": build_quarantine(plan),
    }


def stage_plan(
    source_path: Path,
    target_path: Path,
    mapping_path: Path,
    plan_path: Path,
    quarantine_path: Path,
    audit_path: Path,
    *,
    clock: Clock = utc_now,
) -> dict[str, Any]:
    _require_distinct(
        "stage",
        {
            "source": source_path,
            "target": target_path,
            "mapping": mapping_path,
            "plan": plan_path,
            "quarantine": quarantine_path,
            "audit": audit_path,
        },
    )
    read_audit(audit_path)
    result = dry_run(source_path, target_path, mapping_path)
    plan = result["plan"]
    quarantine = result["quarantine"]
    plan_content = artifact_bytes(plan)
    quarantine_content = artifact_bytes(quarantine)
    _write_exclusive(plan_path, plan_content)
    try:
        _write_exclusive(quarantine_path, quarantine_content)
    except Exception:
        try:
            plan_path.unlink()
            _fsync_directory(plan_path.parent)
        except OSError:
            pass
        raise
    append_event(
        audit_path,
        event_type="plan_staged",
        occurred_at=clock(),
        plan_id=plan["plan_id"],
        property_id=plan["property_id"],
        evidence={
            "source_sha256": plan["source_sha256"],
            "target_before_sha256": plan["target_before_sha256"],
            "mapping_sha256": plan["mapping_sha256"],
            "plan_file_sha256": sha256_bytes(plan_content),
            "quarantine_file_sha256": sha256_bytes(quarantine_content),
            "eligible_records": plan["reconciliation"]["eligible_records"],
            "quarantined_records": plan["reconciliation"]["quarantined_records"],
        },
    )
    return {"plan": plan, "quarantine": quarantine}


def _require_staged_evidence(
    events: list[dict[str, Any]],
    plan: dict[str, Any],
    plan_file_sha256: str,
    quarantine_file_sha256: str,
) -> None:
    for event in events:
        evidence = event["evidence"]
        if (
            event["event_type"] == "plan_staged"
            and event["plan_id"] == plan["plan_id"]
            and event["property_id"] == plan["property_id"]
            and evidence.get("plan_file_sha256") == plan_file_sha256
            and evidence.get("quarantine_file_sha256") == quarantine_file_sha256
            and evidence.get("target_before_sha256") == plan["target_before_sha256"]
        ):
            return
    raise IntegrityError("apply: no matching plan_staged audit evidence")


def apply_plan(
    target_path: Path,
    plan_path: Path,
    quarantine_path: Path,
    audit_path: Path,
    confirmation: str,
    *,
    clock: Clock = utc_now,
) -> dict[str, Any]:
    _require_distinct(
        "apply",
        {
            "target": target_path,
            "plan": plan_path,
            "quarantine": quarantine_path,
            "audit": audit_path,
        },
    )
    with locked_sidecar(target_path):
        return _apply_locked(
            target_path,
            plan_path,
            quarantine_path,
            audit_path,
            confirmation,
            clock=clock,
        )


def _apply_locked(
    target_path: Path,
    plan_path: Path,
    quarantine_path: Path,
    audit_path: Path,
    confirmation: str,
    *,
    clock: Clock,
) -> dict[str, Any]:
    plan, _plan_bytes, plan_file_digest = load_plan_snapshot(plan_path)
    quarantine, _quarantine_bytes, quarantine_file_digest = load_quarantine_snapshot(
        quarantine_path
    )
    if confirmation != plan["plan_id"]:
        raise StateConflictError("apply: confirmation does not match the exact plan ID")
    if (
        quarantine["plan_id"] != plan["plan_id"]
        or quarantine["exception_digest"] != plan["exception_digest"]
        or canonical_json(quarantine["exceptions"]) != canonical_json(plan["exceptions"])
    ):
        raise IntegrityError("apply: quarantine does not match the plan")
    events = read_audit(audit_path)
    _require_staged_evidence(
        events,
        plan,
        plan_file_digest,
        quarantine_file_digest,
    )
    if any(
        event["event_type"] == "apply_verified" and event["plan_id"] == plan["plan_id"]
        for event in events
    ):
        raise StateConflictError("apply: this plan already has verified evidence")

    target, original_bytes, target_digest = load_target_snapshot(target_path)
    if target_digest != plan["target_before_sha256"]:
        raise StateConflictError("apply: target changed after planning")
    if target["property_id"] != plan["property_id"] or target["currency"] != plan["currency"]:
        raise StateConflictError("apply: target identity does not match the plan")
    if len(target["products"]) != plan["reconciliation"]["target_before_records"]:
        raise IntegrityError("apply: target record count does not match reconciliation")
    projected = project_from_plan(target, plan)

    append_event(
        audit_path,
        event_type="apply_started",
        occurred_at=clock(),
        plan_id=plan["plan_id"],
        property_id=plan["property_id"],
        evidence={
            "target_before_sha256": target_digest,
            "operation_count": len(plan["operations"]),
        },
    )

    write_attempted = False
    try:
        if target_path.read_bytes() != original_bytes:
            raise StateConflictError("apply: target changed while apply was starting")
        write_attempted = True
        expected_bytes = artifact_bytes(projected)
        _write_atomic(target_path, expected_bytes)
        verified_target, _verified_bytes, verified_digest = load_target_snapshot(target_path)
        if verified_digest != sha256_bytes(expected_bytes):
            raise IntegrityError("apply: reread target digest does not match the write")
        if canonical_json(verified_target) != canonical_json(projected):
            raise IntegrityError("apply: reread target content does not match the write")
        if verified_digest != plan["projected_target_sha256"]:
            raise IntegrityError("apply: reread target does not match the planned digest")
        append_event(
            audit_path,
            event_type="apply_verified",
            occurred_at=clock(),
            plan_id=plan["plan_id"],
            property_id=plan["property_id"],
            evidence={
                "target_before_sha256": target_digest,
                "target_after_sha256": verified_digest,
                "inserts": plan["reconciliation"]["inserts"],
                "updates": plan["reconciliation"]["updates"],
                "quarantined_records": plan["reconciliation"]["quarantined_records"],
            },
        )
    except Exception as exc:
        restored = False
        if write_attempted:
            try:
                _write_atomic(target_path, original_bytes)
                restored = target_path.read_bytes() == original_bytes
            except OSError:
                restored = False
        try:
            append_event(
                audit_path,
                event_type="apply_rolled_back",
                occurred_at=clock(),
                plan_id=plan["plan_id"],
                property_id=plan["property_id"],
                evidence={
                    "target_restored": restored,
                    "failure_code": (
                        exc.code if isinstance(exc, MigrationError) else "unexpected_error"
                    ),
                },
            )
        except MigrationError as audit_exc:
            raise IntegrityError(
                "apply failed; "
                f"target_restored={restored}; rollback audit failed: {audit_exc.message}"
            ) from exc
        if isinstance(exc, MigrationError):
            raise
        raise IntegrityError(f"apply failed; target_restored={restored}") from exc

    return {
        "mode": "apply",
        "plan_id": plan["plan_id"],
        "property_id": plan["property_id"],
        "verified": True,
        "target_after_sha256": verified_digest,
        "reconciliation": plan["reconciliation"],
    }
