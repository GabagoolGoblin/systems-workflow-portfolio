"""In-memory demonstration of exact verification and two detected drift cases."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from claim_evidence_contract_linter.canonical import pretty_json_bytes
from claim_evidence_contract_linter.engine import build_report, verify_report
from claim_evidence_contract_linter.errors import AuditMismatch

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    contract_bytes = (PROJECT_ROOT / "demo" / "synthetic_contract.json").read_bytes()
    evidence_bytes = (PROJECT_ROOT / "demo" / "synthetic_evidence.json").read_bytes()
    contract = json.loads(contract_bytes)
    evidence = json.loads(evidence_bytes)
    report = build_report(
        contract,
        evidence,
        contract_bytes=contract_bytes,
        evidence_bytes=evidence_bytes,
    )
    baseline = verify_report(
        report,
        contract,
        evidence,
        contract_bytes=contract_bytes,
        evidence_bytes=evidence_bytes,
    )

    tampered_report = copy.deepcopy(report)
    tampered_report["summary"]["supported"] += 1
    report_tamper_detected = False
    try:
        verify_report(
            tampered_report,
            contract,
            evidence,
            contract_bytes=contract_bytes,
            evidence_bytes=evidence_bytes,
        )
    except AuditMismatch:
        report_tamper_detected = True

    input_drift_detected = False
    try:
        verify_report(
            report,
            contract,
            evidence,
            contract_bytes=contract_bytes + b" ",
            evidence_bytes=evidence_bytes,
        )
    except AuditMismatch:
        input_drift_detected = True

    result = {
        "baseline_verified": baseline["verified"],
        "report_tamper_detected": report_tamper_detected,
        "exact_input_byte_drift_detected": input_drift_detected,
        "network_used": False,
        "files_written": False,
    }
    print(pretty_json_bytes(result).decode("utf-8"), end="")
    return 0 if all((baseline["verified"], report_tamper_detected, input_drift_detected)) else 1


if __name__ == "__main__":
    raise SystemExit(main())

