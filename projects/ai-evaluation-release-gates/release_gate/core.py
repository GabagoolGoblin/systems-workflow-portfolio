"""Strict, offline evaluation and tamper-evident receipt construction.

The module reads only caller-supplied local JSON files. It opens no socket, loads
no credential, invokes no inference engine, mutates no model route, and grants no
production authority. Every bundled case and output is synthetic.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


MAX_FILE_BYTES = 1_000_000
MAX_JSON_DEPTH = 24
MAX_JSON_NODES = 20_000
ZERO_HASH = "0" * 64
WRITE_CONFIRMATION = "SYNTHETIC_RECEIPT_ONLY"

LAB_ID = "ai_workflow_evaluation_release_gate_lab"
DIMENSIONS = (
    "grounding",
    "instruction_adherence",
    "safe_escalation",
    "structured_output_fidelity",
)
ALLOWED_OUTCOMES = ("HOLD", "ROLLBACK", "PENDING")
ALLOWED_RATIONALES = {
    "better_grounding",
    "instruction_boundary_preserved",
    "safe_escalation_preserved",
    "handoff_contract_complete",
    "tie_no_material_difference",
}
SLICE_RATIONALE = {
    "grounding": "better_grounding",
    "instruction_adherence": "instruction_boundary_preserved",
    "safe_escalation": "safe_escalation_preserved",
    "structured_output_fidelity": "handoff_contract_complete",
}
CANDIDATE_ID = re.compile(r"^candidate_[a-z]+_v[1-9][0-9]*$")
CASE_ID = re.compile(r"^(?:DEV-[0-9]{3}|HOLD-[0-9]{3})$")


class ContractError(ValueError):
    """Raised when an input or receipt fails closed."""


@dataclass(frozen=True)
class LoadedJSON:
    value: Any
    sha256: str


@dataclass(frozen=True)
class EvaluationInputs:
    contract: dict[str, Any]
    casebook: dict[str, Any]
    adjudications: dict[str, Any] | None
    contract_sha256: str
    casebook_sha256: str
    adjudications_sha256: str | None


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ContractError(f"non-finite JSON number is forbidden: {value}")


def _count_nodes(value: Any, depth: int = 0) -> int:
    if depth > MAX_JSON_DEPTH:
        raise ContractError(f"JSON depth exceeds {MAX_JSON_DEPTH}")
    if isinstance(value, dict):
        return 1 + sum(_count_nodes(item, depth + 1) for item in value.values())
    if isinstance(value, list):
        return 1 + sum(_count_nodes(item, depth + 1) for item in value)
    return 1


def strict_loads(text: str, label: str) -> Any:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ContractError(f"{label}: invalid JSON: {exc}") from exc
    if _count_nodes(value) > MAX_JSON_NODES:
        raise ContractError(f"{label}: JSON node count exceeds {MAX_JSON_NODES}")
    return value


def load_json(path: Path, label: str) -> LoadedJSON:
    if path.is_symlink():
        raise ContractError(f"{label}: symlink input is forbidden")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ContractError(f"{label}: unable to read: {exc}") from exc
    if len(payload) > MAX_FILE_BYTES:
        raise ContractError(f"{label}: file exceeds {MAX_FILE_BYTES} bytes")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError(f"{label}: file is not UTF-8") from exc
    return LoadedJSON(strict_loads(text, label), sha256_bytes(payload))


def require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{path}: expected object")
    return value


def require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{path}: expected array")
    return value


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip() or any(ord(char) < 32 for char in value):
        raise ContractError(f"{path}: expected nonblank control-free string")
    return value


def require_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError(f"{path}: expected boolean")
    return value


def require_int(value: Any, path: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ContractError(f"{path}: expected integer in [{minimum}, {maximum}]")
    return value


def require_exact_keys(value: dict[str, Any], expected: Iterable[str], path: str) -> None:
    wanted = set(expected)
    actual = set(value)
    if actual != wanted:
        raise ContractError(
            f"{path}: exact keys required; missing={sorted(wanted - actual)} unknown={sorted(actual - wanted)}"
        )


def _require_unique_strings(value: Any, path: str) -> list[str]:
    items = require_list(value, path)
    result = [require_string(item, f"{path}[{index}]") for index, item in enumerate(items)]
    if not result or len(result) != len(set(result)):
        raise ContractError(f"{path}: expected nonempty unique strings")
    return result


def validate_contract(value: Any) -> dict[str, Any]:
    contract = require_object(value, "contract")
    require_exact_keys(
        contract,
        (
            "schema_version",
            "lab_id",
            "synthetic",
            "authority",
            "baseline_candidate_id",
            "challenger_candidate_id",
            "candidates",
            "dimensions",
            "partitions",
            "qualitative_rubric",
            "gate_policy",
        ),
        "contract",
    )
    if require_int(contract["schema_version"], "contract.schema_version", 1, 1) != 1:
        raise ContractError("contract.schema_version: only version 1 is supported")
    if require_string(contract["lab_id"], "contract.lab_id") != LAB_ID:
        raise ContractError("contract.lab_id: unexpected lab identifier")
    if require_bool(contract["synthetic"], "contract.synthetic") is not True:
        raise ContractError("contract.synthetic: must be true")
    if require_string(contract["authority"], "contract.authority") != "NO_PRODUCTION_AUTHORITY":
        raise ContractError("contract.authority: must deny production authority")

    candidates = require_list(contract["candidates"], "contract.candidates")
    if len(candidates) != 2:
        raise ContractError("contract.candidates: exactly two invented candidates required")
    candidate_ids: list[str] = []
    for index, candidate_value in enumerate(candidates):
        candidate = require_object(candidate_value, f"contract.candidates[{index}]")
        require_exact_keys(candidate, ("candidate_id", "display_name", "invented"), f"contract.candidates[{index}]")
        candidate_id = require_string(candidate["candidate_id"], f"contract.candidates[{index}].candidate_id")
        if not CANDIDATE_ID.fullmatch(candidate_id):
            raise ContractError(f"contract.candidates[{index}].candidate_id: invalid synthetic identifier")
        if require_bool(candidate["invented"], f"contract.candidates[{index}].invented") is not True:
            raise ContractError(f"contract.candidates[{index}].invented: must be true")
        require_string(candidate["display_name"], f"contract.candidates[{index}].display_name")
        candidate_ids.append(candidate_id)
    if len(set(candidate_ids)) != 2:
        raise ContractError("contract.candidates: duplicate candidate identifier")

    baseline = require_string(contract["baseline_candidate_id"], "contract.baseline_candidate_id")
    challenger = require_string(contract["challenger_candidate_id"], "contract.challenger_candidate_id")
    if baseline == challenger or {baseline, challenger} != set(candidate_ids):
        raise ContractError("contract candidate roles must bind the exact two candidate identifiers")
    if tuple(_require_unique_strings(contract["dimensions"], "contract.dimensions")) != DIMENSIONS:
        raise ContractError("contract.dimensions: exact ordered dimension vocabulary required")

    partitions = require_object(contract["partitions"], "contract.partitions")
    require_exact_keys(partitions, ("development_count", "holdout_count", "holdout_meaning"), "contract.partitions")
    require_int(partitions["development_count"], "contract.partitions.development_count", 8, 8)
    require_int(partitions["holdout_count"], "contract.partitions.holdout_count", 4, 4)
    if require_string(partitions["holdout_meaning"], "contract.partitions.holdout_meaning") != (
        "excluded_from_development_scoring_and_selection_then_hash_bound_until_explicit_local_reveal"
    ):
        raise ContractError("contract.partitions.holdout_meaning: exact non-confidential seal boundary required")

    rubric = require_object(contract["qualitative_rubric"], "contract.qualitative_rubric")
    require_exact_keys(rubric, ("minimum_score", "maximum_score", "anchors"), "contract.qualitative_rubric")
    require_int(rubric["minimum_score"], "contract.qualitative_rubric.minimum_score", 0, 0)
    require_int(rubric["maximum_score"], "contract.qualitative_rubric.maximum_score", 4, 4)
    anchors = require_object(rubric["anchors"], "contract.qualitative_rubric.anchors")
    require_exact_keys(anchors, ("0", "1", "2", "3", "4"), "contract.qualitative_rubric.anchors")
    for score in range(5):
        require_string(anchors[str(score)], f"contract.qualitative_rubric.anchors.{score}")

    gate = require_object(contract["gate_policy"], "contract.gate_policy")
    require_exact_keys(
        gate,
        (
            "exact_case_points",
            "maximum_case_regressions",
            "hard_veto_partition",
            "require_all_human_adjudications",
            "allowed_outcomes",
            "action_authorized",
        ),
        "contract.gate_policy",
    )
    require_int(gate["exact_case_points"], "contract.gate_policy.exact_case_points", 4, 4)
    require_int(gate["maximum_case_regressions"], "contract.gate_policy.maximum_case_regressions", 0, 4)
    if require_string(gate["hard_veto_partition"], "contract.gate_policy.hard_veto_partition") != "holdout":
        raise ContractError("contract.gate_policy.hard_veto_partition: holdout required")
    if require_bool(gate["require_all_human_adjudications"], "contract.gate_policy.require_all_human_adjudications") is not True:
        raise ContractError("contract.gate_policy.require_all_human_adjudications: must be true")
    if tuple(_require_unique_strings(gate["allowed_outcomes"], "contract.gate_policy.allowed_outcomes")) != ALLOWED_OUTCOMES:
        raise ContractError("contract.gate_policy.allowed_outcomes: exact fail-closed vocabulary required")
    if require_bool(gate["action_authorized"], "contract.gate_policy.action_authorized") is not False:
        raise ContractError("contract.gate_policy.action_authorized: must be false")
    return contract


def validate_casebook(value: Any, contract: dict[str, Any]) -> dict[str, Any]:
    casebook = require_object(value, "casebook")
    require_exact_keys(casebook, ("schema_version", "lab_id", "synthetic", "casebook_id", "cases"), "casebook")
    require_int(casebook["schema_version"], "casebook.schema_version", 1, 1)
    if require_string(casebook["lab_id"], "casebook.lab_id") != LAB_ID:
        raise ContractError("casebook.lab_id: mismatch")
    if require_bool(casebook["synthetic"], "casebook.synthetic") is not True:
        raise ContractError("casebook.synthetic: must be true")
    require_string(casebook["casebook_id"], "casebook.casebook_id")
    cases = require_list(casebook["cases"], "casebook.cases")
    if len(cases) != 12:
        raise ContractError("casebook.cases: exactly 12 cases required")

    candidate_ids = {candidate["candidate_id"] for candidate in contract["candidates"]}
    seen: set[str] = set()
    partition_counts = {"development": 0, "holdout": 0}
    slice_counts = {dimension: 0 for dimension in DIMENSIONS}
    human_count = 0
    for index, case_value in enumerate(cases):
        path = f"casebook.cases[{index}]"
        case = require_object(case_value, path)
        require_exact_keys(
            case,
            (
                "case_id",
                "partition",
                "sealed",
                "slice",
                "task_brief",
                "grader",
                "hard_veto",
                "failure_code",
                "responses",
            ),
            path,
        )
        case_id = require_string(case["case_id"], f"{path}.case_id")
        if not CASE_ID.fullmatch(case_id) or case_id in seen:
            raise ContractError(f"{path}.case_id: invalid or duplicate")
        seen.add(case_id)
        partition = require_string(case["partition"], f"{path}.partition")
        if partition not in partition_counts:
            raise ContractError(f"{path}.partition: expected development or holdout")
        if (partition == "development") != case_id.startswith("DEV-"):
            raise ContractError(f"{path}: identifier and partition disagree")
        sealed = require_bool(case["sealed"], f"{path}.sealed")
        if sealed != (partition == "holdout"):
            raise ContractError(f"{path}.sealed: holdout-only workflow seal required")
        partition_counts[partition] += 1
        dimension = require_string(case["slice"], f"{path}.slice")
        if dimension not in slice_counts:
            raise ContractError(f"{path}.slice: unknown dimension")
        slice_counts[dimension] += 1
        require_string(case["task_brief"], f"{path}.task_brief")
        require_string(case["failure_code"], f"{path}.failure_code")

        grader = require_object(case["grader"], f"{path}.grader")
        grader_type = require_string(grader.get("type"), f"{path}.grader.type")
        if grader_type == "token_contract":
            require_exact_keys(grader, ("type", "required_phrases", "forbidden_phrases"), f"{path}.grader")
            _require_unique_strings(grader["required_phrases"], f"{path}.grader.required_phrases")
            _require_unique_strings(grader["forbidden_phrases"], f"{path}.grader.forbidden_phrases")
        elif grader_type == "exact_json":
            require_exact_keys(grader, ("type", "expected"), f"{path}.grader")
            require_object(grader["expected"], f"{path}.grader.expected")
            canonical_bytes(grader["expected"])
        elif grader_type == "human_rubric":
            require_exact_keys(grader, ("type", "rubric_focus"), f"{path}.grader")
            require_string(grader["rubric_focus"], f"{path}.grader.rubric_focus")
            human_count += 1
        else:
            raise ContractError(f"{path}.grader.type: unknown grader")

        hard_veto = require_bool(case["hard_veto"], f"{path}.hard_veto")
        if hard_veto and partition != "holdout":
            raise ContractError(f"{path}.hard_veto: hard vetoes are holdout-only")
        if hard_veto and grader_type == "human_rubric":
            raise ContractError(f"{path}.hard_veto: must use an exact deterministic grader")

        responses = require_object(case["responses"], f"{path}.responses")
        require_exact_keys(responses, ("A", "B"), f"{path}.responses")
        response_candidates: set[str] = set()
        for label in ("A", "B"):
            response = require_object(responses[label], f"{path}.responses.{label}")
            require_exact_keys(response, ("candidate_id", "output"), f"{path}.responses.{label}")
            candidate_id = require_string(response["candidate_id"], f"{path}.responses.{label}.candidate_id")
            if candidate_id not in candidate_ids:
                raise ContractError(f"{path}.responses.{label}.candidate_id: undeclared candidate")
            response_candidates.add(candidate_id)
            require_string(response["output"], f"{path}.responses.{label}.output")
        if response_candidates != candidate_ids:
            raise ContractError(f"{path}.responses: must contain each candidate exactly once")

    if partition_counts != {"development": 8, "holdout": 4}:
        raise ContractError(f"casebook partitions mismatch: {partition_counts}")
    if any(count != 3 for count in slice_counts.values()):
        raise ContractError(f"casebook slice coverage mismatch: {slice_counts}")
    if human_count != 4:
        raise ContractError("casebook: exactly four qualitative human-rubric cases required")
    return casebook


def validate_adjudications(
    value: Any | None,
    contract: dict[str, Any],
    casebook: dict[str, Any],
) -> dict[str, Any] | None:
    if value is None:
        return None
    adjudications = require_object(value, "adjudications")
    require_exact_keys(adjudications, ("schema_version", "lab_id", "synthetic", "reviews"), "adjudications")
    require_int(adjudications["schema_version"], "adjudications.schema_version", 1, 1)
    if require_string(adjudications["lab_id"], "adjudications.lab_id") != LAB_ID:
        raise ContractError("adjudications.lab_id: mismatch")
    if require_bool(adjudications["synthetic"], "adjudications.synthetic") is not True:
        raise ContractError("adjudications.synthetic: must be true")

    qualitative = {
        case["case_id"]: case
        for case in casebook["cases"]
        if case["grader"]["type"] == "human_rubric"
    }
    reviews = require_list(adjudications["reviews"], "adjudications.reviews")
    seen: set[str] = set()
    for index, review_value in enumerate(reviews):
        path = f"adjudications.reviews[{index}]"
        review = require_object(review_value, path)
        require_exact_keys(review, ("case_id", "blind_preference", "rationale_code", "scores"), path)
        case_id = require_string(review["case_id"], f"{path}.case_id")
        if case_id not in qualitative or case_id in seen:
            raise ContractError(f"{path}.case_id: unknown, non-qualitative, or duplicate")
        seen.add(case_id)
        preference = require_string(review["blind_preference"], f"{path}.blind_preference")
        if preference not in {"A", "B", "tie"}:
            raise ContractError(f"{path}.blind_preference: expected A, B, or tie")
        rationale = require_string(review["rationale_code"], f"{path}.rationale_code")
        if rationale not in ALLOWED_RATIONALES:
            raise ContractError(f"{path}.rationale_code: unknown controlled reason")
        scores = require_object(review["scores"], f"{path}.scores")
        require_exact_keys(scores, ("A", "B"), f"{path}.scores")
        score_a = require_int(scores["A"], f"{path}.scores.A", 0, 4)
        score_b = require_int(scores["B"], f"{path}.scores.B", 0, 4)
        expected_preference = "tie" if score_a == score_b else ("A" if score_a > score_b else "B")
        if preference != expected_preference:
            raise ContractError(
                f"{path}.blind_preference: must match the ordering of blind-label scores"
            )
        expected_rationale = (
            "tie_no_material_difference"
            if preference == "tie"
            else SLICE_RATIONALE[qualitative[case_id]["slice"]]
        )
        if rationale != expected_rationale:
            raise ContractError(
                f"{path}.rationale_code: must match the case slice and tie state"
            )
    return adjudications


def load_inputs(contract_path: Path, casebook_path: Path, adjudications_path: Path | None = None) -> EvaluationInputs:
    loaded_contract = load_json(contract_path, "contract")
    contract = validate_contract(loaded_contract.value)
    loaded_casebook = load_json(casebook_path, "casebook")
    casebook = validate_casebook(loaded_casebook.value, contract)
    loaded_adjudications = load_json(adjudications_path, "adjudications") if adjudications_path else None
    adjudications = validate_adjudications(
        loaded_adjudications.value if loaded_adjudications else None,
        contract,
        casebook,
    )
    return EvaluationInputs(
        contract=contract,
        casebook=casebook,
        adjudications=adjudications,
        contract_sha256=loaded_contract.sha256,
        casebook_sha256=loaded_casebook.sha256,
        adjudications_sha256=loaded_adjudications.sha256 if loaded_adjudications else None,
    )


def grade_exact(case: dict[str, Any], output: str) -> bool:
    grader = case["grader"]
    if grader["type"] == "token_contract":
        folded = output.casefold()
        return all(phrase.casefold() in folded for phrase in grader["required_phrases"]) and not any(
            phrase.casefold() in folded for phrase in grader["forbidden_phrases"]
        )
    if grader["type"] == "exact_json":
        try:
            actual = strict_loads(output, f"{case['case_id']} response")
        except ContractError:
            return False
        return canonical_bytes(actual) == canonical_bytes(grader["expected"])
    raise ContractError(f"{case['case_id']}: human rubric has no deterministic grade")


def _audit_add(events: list[dict[str, Any]], event_type: str, details: dict[str, Any]) -> None:
    body = {
        "sequence": len(events) + 1,
        "event_type": event_type,
        "details": details,
        "previous_hash": events[-1]["event_hash"] if events else ZERO_HASH,
    }
    body["event_hash"] = sha256_bytes(canonical_bytes(body))
    events.append(body)


def verify_audit_chain(events: Any) -> bool:
    if not isinstance(events, list) or not events:
        return False
    previous = ZERO_HASH
    for expected_sequence, event in enumerate(events, start=1):
        if not isinstance(event, dict) or set(event) != {
            "sequence",
            "event_type",
            "details",
            "previous_hash",
            "event_hash",
        }:
            return False
        if event["sequence"] != expected_sequence or event["previous_hash"] != previous:
            return False
        body = {key: value for key, value in event.items() if key != "event_hash"}
        expected = sha256_bytes(canonical_bytes(body))
        if not hmac.compare_digest(str(event["event_hash"]), expected):
            return False
        previous = expected
    return True


def build_receipt(inputs: EvaluationInputs) -> dict[str, Any]:
    contract = inputs.contract
    casebook = inputs.casebook
    adjudications = inputs.adjudications
    reviews = {
        review["case_id"]: review
        for review in (adjudications["reviews"] if adjudications else [])
    }
    baseline = contract["baseline_candidate_id"]
    challenger = contract["challenger_candidate_id"]
    points = contract["gate_policy"]["exact_case_points"]
    candidate_totals = {baseline: 0, challenger: 0}
    slice_totals = {
        dimension: {baseline: 0, challenger: 0, "available_cases": 0, "total_cases": 0}
        for dimension in DIMENSIONS
    }
    case_results: list[dict[str, Any]] = []
    missing_human: list[str] = []
    regression_cases: list[str] = []
    hard_veto_failures: list[str] = []

    for case in casebook["cases"]:
        candidate_by_label = {
            label: response["candidate_id"]
            for label, response in case["responses"].items()
        }
        score_by_candidate: dict[str, int | None]
        pass_by_candidate: dict[str, bool | None]
        if case["grader"]["type"] == "human_rubric":
            review = reviews.get(case["case_id"])
            if review is None:
                score_by_candidate = {baseline: None, challenger: None}
                pass_by_candidate = {baseline: None, challenger: None}
                missing_human.append(case["case_id"])
            else:
                label_by_candidate = {
                    response["candidate_id"]: label
                    for label, response in case["responses"].items()
                }
                score_by_candidate = {
                    baseline: review["scores"][label_by_candidate[baseline]],
                    challenger: review["scores"][label_by_candidate[challenger]],
                }
                pass_by_candidate = {baseline: None, challenger: None}
        else:
            pass_by_candidate = {}
            score_by_candidate = {}
            for label, response in case["responses"].items():
                candidate_id = response["candidate_id"]
                passed = grade_exact(case, response["output"])
                pass_by_candidate[candidate_id] = passed
                score_by_candidate[candidate_id] = points if passed else 0

        complete = all(score_by_candidate[candidate] is not None for candidate in (baseline, challenger))
        slice_row = slice_totals[case["slice"]]
        slice_row["total_cases"] += 1
        if complete:
            slice_row["available_cases"] += 1
            for candidate_id in (baseline, challenger):
                score = int(score_by_candidate[candidate_id])
                candidate_totals[candidate_id] += score
                slice_row[candidate_id] += score
            if int(score_by_candidate[challenger]) < int(score_by_candidate[baseline]):
                regression_cases.append(case["case_id"])
        if (
            case["hard_veto"]
            and case["partition"] == contract["gate_policy"]["hard_veto_partition"]
            and pass_by_candidate[challenger] is False
        ):
            hard_veto_failures.append(case["case_id"])

        result = {
            "case_id": case["case_id"],
            "partition": case["partition"],
            "slice": case["slice"],
            "grader_type": case["grader"]["type"],
            "hard_veto": case["hard_veto"],
            "failure_code": case["failure_code"],
            "candidate_by_blind_label": candidate_by_label,
            "scores": score_by_candidate,
            "passes": pass_by_candidate,
            "complete": complete,
            "case_sha256": sha256_bytes(canonical_bytes(case)),
        }
        case_results.append(result)

    reason_codes: list[str]
    if missing_human:
        outcome = "PENDING"
        reason_codes = ["HUMAN_ADJUDICATION_INCOMPLETE"]
    elif (
        candidate_totals[challenger] < candidate_totals[baseline]
        or len(regression_cases) > contract["gate_policy"]["maximum_case_regressions"]
    ):
        outcome = "ROLLBACK"
        reason_codes = ["CHALLENGER_REGRESSION_LIMIT_EXCEEDED"]
    elif hard_veto_failures:
        outcome = "HOLD"
        reason_codes = ["HOLDOUT_HARD_VETO_FAILED"]
    else:
        outcome = "PENDING"
        reason_codes = ["REVIEW_COMPLETE_NO_PROMOTION_AUTHORITY"]

    if outcome not in ALLOWED_OUTCOMES:
        raise ContractError("internal error: disallowed outcome")

    holdout_cases = [case for case in casebook["cases"] if case["partition"] == "holdout"]
    events: list[dict[str, Any]] = []
    _audit_add(events, "MANIFEST_VALIDATED", {"development": 8, "holdout": 4, "synthetic": True})
    _audit_add(
        events,
        "EXACT_GRADERS_COMPLETED",
        {"exact_cases": 8, "qualitative_cases": 4, "inference_used": False},
    )
    _audit_add(
        events,
        "HUMAN_ADJUDICATION_STATE_RECORDED",
        {"completed": 4 - len(missing_human), "missing_case_ids": missing_human},
    )
    _audit_add(
        events,
        "RELEASE_GATE_DECISION_RECORDED",
        {"outcome": outcome, "reason_codes": reason_codes, "action_authorized": False},
    )

    body = {
        "schema_version": 1,
        "lab_id": LAB_ID,
        "receipt_id": "synthetic_release_gate_reference_v1",
        "boundary": {
            "personal_portfolio": True,
            "synthetic": True,
            "offline": True,
            "no_production_authority": True,
            "no_model_route_change": True,
        },
        "input_sha256": {
            "contract": inputs.contract_sha256,
            "casebook": inputs.casebook_sha256,
            "adjudications": inputs.adjudications_sha256,
        },
        "partition_binding": {
            "development_case_count": 8,
            "holdout_case_count": 4,
            "holdout_bundle_sha256": sha256_bytes(canonical_bytes(holdout_cases)),
            "seal_semantics": contract["partitions"]["holdout_meaning"],
            "cryptographic_confidentiality_claimed": False,
        },
        "candidate_roles": {
            "baseline": baseline,
            "challenger": challenger,
        },
        "outcome": outcome,
        "reason_codes": reason_codes,
        "action_authorized": False,
        "candidate_totals": candidate_totals,
        "slice_totals": slice_totals,
        "regression_case_ids": regression_cases,
        "hard_veto_failure_case_ids": hard_veto_failures,
        "missing_human_case_ids": missing_human,
        "case_results": case_results,
        "audit_chain": events,
    }
    receipt = dict(body)
    receipt["receipt_sha256"] = sha256_bytes(canonical_bytes(body))
    return receipt


def verify_receipt(receipt: Any, expected: dict[str, Any] | None = None) -> bool:
    if not isinstance(receipt, dict) or "receipt_sha256" not in receipt:
        return False
    body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    digest = sha256_bytes(canonical_bytes(body))
    if not hmac.compare_digest(str(receipt["receipt_sha256"]), digest):
        return False
    if receipt.get("outcome") not in ALLOWED_OUTCOMES:
        return False
    if receipt.get("action_authorized") is not False:
        return False
    if not verify_audit_chain(receipt.get("audit_chain")):
        return False
    if expected is not None and canonical_bytes(receipt) != canonical_bytes(expected):
        return False
    return True


def write_receipt(path: Path, receipt: dict[str, Any], confirmation: str | None) -> None:
    if confirmation != WRITE_CONFIRMATION:
        raise ContractError(f"output requires --confirm-local-write {WRITE_CONFIRMATION}")
    if path.is_symlink() or path.exists():
        raise ContractError("output path must be a new non-symlink file")
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise ContractError("output parent must be an existing non-symlink directory")
    payload = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise ContractError(f"unable to write receipt: {exc}") from exc
