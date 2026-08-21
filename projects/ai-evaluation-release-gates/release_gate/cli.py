"""Command-line interface for the synthetic release-gate evaluator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import ContractError, build_receipt, load_inputs, load_json, verify_receipt, write_receipt


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Offline synthetic AI workflow evaluation release gate")
    subparsers = value.add_subparsers(dest="command", required=True)

    evaluate = subparsers.add_parser("evaluate", help="build a deterministic receipt")
    evaluate.add_argument("--contract", type=Path, required=True)
    evaluate.add_argument("--cases", type=Path, required=True)
    evaluate.add_argument("--adjudications", type=Path)
    evaluate.add_argument("--output", type=Path)
    evaluate.add_argument("--confirm-local-write")

    verify = subparsers.add_parser("verify", help="verify and exactly rebuild a receipt")
    verify.add_argument("--contract", type=Path, required=True)
    verify.add_argument("--cases", type=Path, required=True)
    verify.add_argument("--adjudications", type=Path)
    verify.add_argument("--receipt", type=Path, required=True)

    demo = subparsers.add_parser("demo", help="show pending and adjudicated outcomes without writing")
    demo.add_argument("--contract", type=Path, required=True)
    demo.add_argument("--cases", type=Path, required=True)
    demo.add_argument("--adjudications", type=Path, required=True)
    return value


def emit(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "evaluate":
            inputs = load_inputs(args.contract, args.cases, args.adjudications)
            receipt = build_receipt(inputs)
            if args.output:
                write_receipt(args.output, receipt, args.confirm_local_write)
                emit({"status": "WRITTEN_LOCAL_ONLY", "output": str(args.output), "outcome": receipt["outcome"], "receipt_sha256": receipt["receipt_sha256"]})
            else:
                emit(receipt)
            return 0

        if args.command == "verify":
            loaded_receipt = load_json(args.receipt, "receipt").value
            expected = build_receipt(load_inputs(args.contract, args.cases, args.adjudications))
            passed = verify_receipt(loaded_receipt, expected)
            emit({"status": "PASS" if passed else "FAIL", "exact_rebuild": passed, "action_authorized": False})
            return 0 if passed else 3

        pending = build_receipt(load_inputs(args.contract, args.cases))
        reviewed = build_receipt(load_inputs(args.contract, args.cases, args.adjudications))
        emit(
            {
                "lab": "PERSONAL PORTFOLIO / SYNTHETIC / OFFLINE / NO PRODUCTION AUTHORITY",
                "development_cases": 8,
                "holdout_cases": 4,
                "pending_outcome": pending["outcome"],
                "reviewed_outcome": reviewed["outcome"],
                "reviewed_reason_codes": reviewed["reason_codes"],
                "allowed_outcomes": list(("HOLD", "ROLLBACK", "PENDING")),
                "action_authorized": False,
            }
        )
        return 0
    except ContractError as exc:
        emit({"status": "ERROR", "error": str(exc), "action_authorized": False})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
