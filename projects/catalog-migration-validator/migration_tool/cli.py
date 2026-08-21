"""Command-line interface for planning, staging, applying, and auditing."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .audit import read_audit
from .errors import MigrationError
from .workflow import apply_plan, dry_run, stage_plan


def _path(value: str) -> Path:
    return Path(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hospitality-catalog-migration",
        description="Plan and verify a synthetic local catalog migration.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    preview = commands.add_parser("dry-run", help="validate and print a write-free plan")
    preview.add_argument("--source", type=_path, required=True)
    preview.add_argument("--target", type=_path, required=True)
    preview.add_argument("--mapping", type=_path, required=True)

    stage = commands.add_parser("stage", help="write review artifacts without overwriting")
    stage.add_argument("--source", type=_path, required=True)
    stage.add_argument("--target", type=_path, required=True)
    stage.add_argument("--mapping", type=_path, required=True)
    stage.add_argument("--plan", type=_path, required=True)
    stage.add_argument("--quarantine", type=_path, required=True)
    stage.add_argument("--audit", type=_path, required=True)

    apply = commands.add_parser("apply", help="apply one explicitly approved plan")
    apply.add_argument("--target", type=_path, required=True)
    apply.add_argument("--plan", type=_path, required=True)
    apply.add_argument("--quarantine", type=_path, required=True)
    apply.add_argument("--audit", type=_path, required=True)
    apply.add_argument("--confirm-plan-id", required=True)

    verify = commands.add_parser("verify-audit", help="verify the complete audit chain")
    verify.add_argument("--audit", type=_path, required=True)
    return parser


def _print(value: Any, *, stream: Any | None = None) -> None:
    destination = sys.stdout if stream is None else stream
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), file=destination)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "dry-run":
            result = dry_run(args.source, args.target, args.mapping)
        elif args.command == "stage":
            staged = stage_plan(
                args.source,
                args.target,
                args.mapping,
                args.plan,
                args.quarantine,
                args.audit,
            )
            plan = staged["plan"]
            result = {
                "mode": "stage",
                "plan_id": plan["plan_id"],
                "property_id": plan["property_id"],
                "plan_file": args.plan.name,
                "quarantine_file": args.quarantine.name,
                "reconciliation": plan["reconciliation"],
            }
        elif args.command == "apply":
            result = apply_plan(
                args.target,
                args.plan,
                args.quarantine,
                args.audit,
                args.confirm_plan_id,
            )
        else:
            events = read_audit(args.audit)
            result = {
                "mode": "verify-audit",
                "valid": True,
                "event_count": len(events),
                "last_event_hash": events[-1]["event_hash"] if events else None,
            }
    except MigrationError as exc:
        _print({"ok": False, "error": exc.code, "message": exc.message}, stream=sys.stderr)
        return 2
    except OSError as exc:
        _print(
            {"ok": False, "error": "io_error", "message": exc.strerror or str(exc)},
            stream=sys.stderr,
        )
        return 2
    _print({"ok": True, "result": result})
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
