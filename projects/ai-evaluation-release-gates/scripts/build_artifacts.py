#!/usr/bin/env python3
"""Build deterministic browser snapshots and reference receipts from strict fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from release_gate.core import build_receipt, canonical_bytes, grade_exact, load_inputs, sha256_bytes


CONTRACT = ROOT / "fixtures" / "synthetic_evaluation_contract.json"
CASEBOOK = ROOT / "fixtures" / "synthetic_casebook.json"
ADJUDICATIONS = ROOT / "fixtures" / "synthetic_adjudications.json"


def public_case(case: dict) -> dict:
    grader = case["grader"]
    if grader["type"] == "human_rubric":
        public_grader = {"type": "human_rubric", "rubric_focus": grader["rubric_focus"]}
        auto_grades = {"A": None, "B": None}
    else:
        public_grader = grader
        auto_grades = {
            label: grade_exact(case, response["output"])
            for label, response in case["responses"].items()
        }
    return {
        "case_id": case["case_id"],
        "partition": case["partition"],
        "sealed": case["sealed"],
        "slice": case["slice"],
        "task_brief": case["task_brief"],
        "grader": public_grader,
        "hard_veto": case["hard_veto"],
        "failure_code": case["failure_code"],
        "responses": {
            label: {"output": response["output"]}
            for label, response in case["responses"].items()
        },
        "automatic_pass": auto_grades,
        "case_sha256": sha256_bytes(canonical_bytes(case)),
    }


def javascript_assignment(name: str, value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"'use strict';\nwindow.{name} = {payload};\n"


def main() -> None:
    complete = load_inputs(CONTRACT, CASEBOOK, ADJUDICATIONS)
    pending = load_inputs(CONTRACT, CASEBOOK)
    contract = complete.contract
    cases = complete.casebook["cases"]
    development = [case for case in cases if case["partition"] == "development"]
    holdout = [case for case in cases if case["partition"] == "holdout"]
    holdout_bundle_sha = sha256_bytes(canonical_bytes(holdout))
    bindings = {
        case["case_id"]: {
            label: response["candidate_id"]
            for label, response in case["responses"].items()
        }
        for case in cases
    }
    holdout_payload = {
        "schema_version": 1,
        "holdout_cases": [public_case(case) for case in holdout],
        "holdout_bundle_sha256": holdout_bundle_sha,
        "candidate_bindings": bindings,
        "candidate_roles": {
            "baseline": contract["baseline_candidate_id"],
            "challenger": contract["challenger_candidate_id"],
        },
        "candidate_display_names": {
            candidate["candidate_id"]: candidate["display_name"]
            for candidate in contract["candidates"]
        },
        "reference_adjudications": complete.adjudications["reviews"],
        "reference_receipt": build_receipt(complete),
    }
    holdout_payload_sha = sha256_bytes(canonical_bytes(holdout_payload))

    base = {
        "schema_version": 1,
        "boundary": "PERSONAL PORTFOLIO / SYNTHETIC / OFFLINE / NO PRODUCTION AUTHORITY",
        "runtime": {"network": False, "inference": False, "persistence": False, "production_action": False},
        "dimensions": contract["dimensions"],
        "rubric": contract["qualitative_rubric"],
        "gate_policy": contract["gate_policy"],
        "development_cases": [public_case(case) for case in development],
        "holdout_manifest": [
            {
                "case_id": case["case_id"],
                "slice": case["slice"],
                "hard_veto": case["hard_veto"],
                "case_sha256": sha256_bytes(canonical_bytes(case)),
            }
            for case in holdout
        ],
        "holdout_bundle_sha256": holdout_bundle_sha,
        "holdout_payload_sha256": holdout_payload_sha,
        "holdout_semantics": contract["partitions"]["holdout_meaning"],
        "cryptographic_confidentiality_claimed": False,
        "input_sha256": {
            "contract": complete.contract_sha256,
            "casebook": complete.casebook_sha256,
            "adjudications": complete.adjudications_sha256,
        },
        "pending_summary": {
            "outcome": build_receipt(pending)["outcome"],
            "reason_codes": build_receipt(pending)["reason_codes"],
            "missing_human_case_ids": build_receipt(pending)["missing_human_case_ids"],
            "action_authorized": False,
        },
        "controlled_rationale_codes": [
            "better_grounding",
            "instruction_boundary_preserved",
            "safe_escalation_preserved",
            "handoff_contract_complete",
            "tie_no_material_difference",
        ],
    }
    (ROOT / "data" / "demo_snapshot.js").write_text(
        javascript_assignment("EVALUATION_RELEASE_GATE_BASE", base), encoding="utf-8", newline="\n"
    )
    (ROOT / "data" / "holdout_snapshot.js").write_text(
        javascript_assignment("EVALUATION_RELEASE_GATE_HOLDOUT", holdout_payload), encoding="utf-8", newline="\n"
    )
    receipt_path = ROOT / "artifacts" / "reference_hold_receipt.json"
    receipt_path.write_text(
        json.dumps(build_receipt(complete), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "development_cases_in_base": len(development),
        "holdout_cases_in_reveal_bundle": len(holdout),
        "holdout_bundle_sha256": holdout_bundle_sha,
        "holdout_payload_sha256": holdout_payload_sha,
        "reference_outcome": build_receipt(complete)["outcome"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
