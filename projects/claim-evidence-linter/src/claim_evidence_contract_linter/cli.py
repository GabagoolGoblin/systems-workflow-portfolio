"""Local-only command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .canonical import pretty_json_bytes
from .engine import build_report, verify_report
from .errors import AuditMismatch, InputError, LinterError, LocalIOError
from .local_io import load_json_file, write_new_private_file

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_INVALID = 2
EXIT_AUDIT_MISMATCH = 3
EXIT_IO = 4
LOCAL_WRITE_CONFIRMATION = "LOCAL_ONLY"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _add_lint_arguments(parser: argparse.ArgumentParser, *, demo_defaults: bool) -> None:
    if demo_defaults:
        parser.add_argument(
            "--contract",
            default=str(_project_root() / "demo" / "synthetic_contract.json"),
        )
        parser.add_argument(
            "--evidence",
            default=str(_project_root() / "demo" / "synthetic_evidence.json"),
        )
    else:
        parser.add_argument("--contract", required=True)
        parser.add_argument("--evidence", required=True)
    parser.add_argument(
        "--output",
        help="Create a new local report file; existing paths are never overwritten",
    )
    parser.add_argument(
        "--confirm-local-write",
        metavar="LOCAL_ONLY",
        help="Required exact confirmation token when --output is used",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claim-contract-lint",
        description="Deterministic, network-free claim-to-evidence contract linter",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    lint_parser = subparsers.add_parser("lint", help="lint an explicit contract")
    _add_lint_arguments(lint_parser, demo_defaults=False)
    demo_parser = subparsers.add_parser("demo", help="run the invented local demo")
    _add_lint_arguments(demo_parser, demo_defaults=True)
    verify_parser = subparsers.add_parser(
        "verify", help="verify a saved report and its exact bound inputs"
    )
    verify_parser.add_argument("--report", required=True)
    verify_parser.add_argument("--contract", required=True)
    verify_parser.add_argument("--evidence", required=True)
    return parser


def _load_inputs(contract_path: str, evidence_path: str):
    contract, contract_bytes = load_json_file(contract_path, label="contract")
    evidence, evidence_bytes = load_json_file(evidence_path, label="evidence")
    return contract, contract_bytes, evidence, evidence_bytes


def _run_lint(args: argparse.Namespace) -> int:
    if args.output:
        if args.confirm_local_write != LOCAL_WRITE_CONFIRMATION:
            raise InputError(
                "--output requires the exact confirmation --confirm-local-write LOCAL_ONLY"
            )
    elif args.confirm_local_write is not None:
        raise InputError("--confirm-local-write is invalid without --output")

    contract, contract_bytes, evidence, evidence_bytes = _load_inputs(
        args.contract, args.evidence
    )
    report = build_report(
        contract,
        evidence,
        contract_bytes=contract_bytes,
        evidence_bytes=evidence_bytes,
    )
    output_bytes = pretty_json_bytes(report)
    if args.output:
        write_new_private_file(args.output, output_bytes)
        status = {
            "created": str(Path(args.output)),
            "mode": "0600",
            "report_sha256": report["report_digest"]["value"],
            "finding_count": report["summary"]["finding_count"],
        }
        sys.stdout.buffer.write(pretty_json_bytes(status))
    else:
        sys.stdout.buffer.write(output_bytes)
    return EXIT_OK if report["summary"]["all_supported"] else EXIT_FINDINGS


def _run_verify(args: argparse.Namespace) -> int:
    report, _report_bytes = load_json_file(args.report, label="report")
    contract, contract_bytes, evidence, evidence_bytes = _load_inputs(
        args.contract, args.evidence
    )
    verification = verify_report(
        report,
        contract,
        evidence,
        contract_bytes=contract_bytes,
        evidence_bytes=evidence_bytes,
    )
    sys.stdout.buffer.write(pretty_json_bytes(verification))
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.command in {"lint", "demo"}:
            return _run_lint(args)
        return _run_verify(args)
    except AuditMismatch as exc:
        print(f"AUDIT_MISMATCH: {exc}", file=sys.stderr)
        return EXIT_AUDIT_MISMATCH
    except InputError as exc:
        print(f"INVALID_INPUT: {exc}", file=sys.stderr)
        return EXIT_INVALID
    except LocalIOError as exc:
        print(f"LOCAL_IO_ERROR: {exc}", file=sys.stderr)
        return EXIT_IO
    except LinterError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_INVALID


if __name__ == "__main__":
    raise SystemExit(main())

