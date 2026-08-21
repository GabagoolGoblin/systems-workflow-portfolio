"""Command-line interface for the offline synthetic workbench."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .audit import AuditIntegrityError, AuditLog, verify_audit
from .pipeline import process_tickets
from .schema import SchemaError, load_synthetic_batch


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hospitality-support-workbench",
        description="Offline processing for strict synthetic support tickets.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    triage = subparsers.add_parser("triage", help="triage a synthetic ticket batch")
    triage.add_argument("input", type=Path, help="synthetic batch JSON")
    triage.add_argument("--audit", type=Path, required=True, help="append-only audit JSONL")
    triage.add_argument("--output", type=str, default="-", help="output JSON path or -")
    triage.add_argument(
        "--approve-eligible",
        action="store_true",
        help="explicitly approve only outlines with no holds",
    )

    verify = subparsers.add_parser("verify-audit", help="verify an audit hash chain")
    verify.add_argument("audit", type=Path)
    return parser


def _write_json(payload: object, output: str) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output == "-":
        sys.stdout.write(rendered)
        return
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "verify-audit":
            _write_json(verify_audit(args.audit), "-")
            return 0

        output_path = None if args.output == "-" else Path(args.output).resolve()
        if output_path is not None and output_path == args.audit.resolve():
            raise ValueError("output and audit paths must be different")
        tickets = load_synthetic_batch(args.input)
        payload = process_tickets(
            tickets,
            audit_log=AuditLog(args.audit),
            approve_eligible=args.approve_eligible,
        )
        _write_json(payload, args.output)
        return 0
    except SchemaError as exc:
        sys.stderr.write(json.dumps(exc.to_dict(), sort_keys=True) + "\n")
        return 2
    except AuditIntegrityError as exc:
        sys.stderr.write(
            json.dumps({"error": "audit_integrity_error", "message": str(exc)}, sort_keys=True)
            + "\n"
        )
        return 3
    except (OSError, ValueError) as exc:
        sys.stderr.write(
            json.dumps({"error": "workbench_error", "message": str(exc)}, sort_keys=True)
            + "\n"
        )
        return 4


if __name__ == "__main__":
    raise SystemExit(main())

