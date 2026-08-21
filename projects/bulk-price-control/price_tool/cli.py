"""Command-line interface for the price update workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .audit import read_audit
from .errors import PriceToolError
from .workflow import commit_stage, create_stage, dry_run


def _path(value: str) -> Path:
    return Path(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hospitality-price-tool",
        description="Validate, stage, commit, and reread bulk menu price updates.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    dry = subparsers.add_parser("dry-run", help="validate and preview without writing files")
    dry.add_argument("--catalog", type=_path, required=True)
    dry.add_argument("--changes", type=_path, required=True)

    stage = subparsers.add_parser("stage", help="freeze a validated, hash-bound stage")
    stage.add_argument("--catalog", type=_path, required=True)
    stage.add_argument("--changes", type=_path, required=True)
    stage.add_argument("--stage", dest="stage_path", type=_path, required=True)
    stage.add_argument("--audit", type=_path, required=True)

    commit = subparsers.add_parser("commit", help="commit and reread an exact stage")
    commit.add_argument("--catalog", type=_path, required=True)
    commit.add_argument("--stage", dest="stage_path", type=_path, required=True)
    commit.add_argument("--audit", type=_path, required=True)
    commit.add_argument("--confirm-stage-id", required=True)

    verify = subparsers.add_parser("verify-audit", help="verify the full audit hash chain")
    verify.add_argument("--audit", type=_path, required=True)
    return parser


def _print(value: Any, *, stream: Any | None = None) -> None:
    destination = sys.stdout if stream is None else stream
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2), file=destination)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "dry-run":
            result = dry_run(args.catalog, args.changes)
        elif args.command == "stage":
            stage = create_stage(
                args.catalog,
                args.changes,
                args.stage_path,
                args.audit,
            )
            result = {
                "mode": "stage",
                "stage_id": stage["stage_id"],
                "venue_id": stage["venue_id"],
                "update_count": stage["summary"]["update_count"],
                "stage_file": args.stage_path.name,
            }
        elif args.command == "commit":
            result = commit_stage(
                args.catalog,
                args.stage_path,
                args.audit,
                args.confirm_stage_id,
            )
        else:
            events = read_audit(args.audit)
            result = {
                "mode": "verify-audit",
                "valid": True,
                "event_count": len(events),
                "last_event_hash": events[-1]["event_hash"] if events else None,
            }
    except PriceToolError as exc:
        _print({"ok": False, "error": exc.code, "message": exc.message}, stream=sys.stderr)
        return 2
    except OSError as exc:
        _print(
            {
                "ok": False,
                "error": "io_error",
                "message": exc.strerror or str(exc),
            },
            stream=sys.stderr,
        )
        return 2
    _print({"ok": True, "result": result})
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
