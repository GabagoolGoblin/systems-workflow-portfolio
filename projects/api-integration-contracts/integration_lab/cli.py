"""Command-line entry point for the synthetic integration contract lab."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import ACKNOWLEDGEMENT, ContractError, evaluate_files, promote_simulated, strict_loads, verify_receipt


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("demo", "evaluate"):
        command = commands.add_parser(name)
        command.add_argument("--contract", type=Path, default=Path("fixtures/synthetic_contract.json"))
        command.add_argument("--run", type=Path, default=Path("fixtures/synthetic_run.json"))
    verify = commands.add_parser("verify")
    verify.add_argument("receipt", type=Path)
    promote = commands.add_parser("promote")
    promote.add_argument("--contract", type=Path, default=Path("fixtures/synthetic_contract.json"))
    promote.add_argument("--run", type=Path, default=Path("fixtures/synthetic_run.json"))
    promote.add_argument("--confirm-token", required=True)
    promote.add_argument("--acknowledge", required=True, help=f"exact value required: {ACKNOWLEDGEMENT}")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command in {"demo", "evaluate"}:
            report = evaluate_files(args.contract, args.run)
            emit(report)
            if args.command == "evaluate" and report["webhook_summary"]["states"].get("ready_for_human", 0) == 0:
                return 1
            return 0
        if args.command == "verify":
            if args.receipt.is_symlink():
                raise ContractError("verify: symlink receipt is forbidden")
            raw = args.receipt.read_text(encoding="utf-8")
            receipt = strict_loads(raw, "receipt")
            if not verify_receipt(receipt):
                raise ContractError("verify: receipt digest or audit chain mismatch")
            emit({"ok": True, "receipt_digest": receipt["receipt_digest"], "audit_events": len(receipt["audit"]["events"])})
            return 0
        if args.command == "promote":
            report = evaluate_files(args.contract, args.run)
            emit(promote_simulated(report, args.confirm_token, args.acknowledge))
            return 0
    except (ContractError, OSError, UnicodeError) as exc:
        emit({"ok": False, "error": str(exc)})
        return 2
    raise AssertionError("unreachable command")

