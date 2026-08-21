from __future__ import annotations

import copy
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from release_gate.core import (
    ALLOWED_OUTCOMES,
    ContractError,
    WRITE_CONFIRMATION,
    build_receipt,
    canonical_bytes,
    grade_exact,
    load_inputs,
    sha256_bytes,
    strict_loads,
    validate_adjudications,
    validate_casebook,
    validate_contract,
    verify_audit_chain,
    verify_receipt,
    write_receipt,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "fixtures" / "synthetic_evaluation_contract.json"
CASES = ROOT / "fixtures" / "synthetic_casebook.json"
ADJUDICATIONS = ROOT / "fixtures" / "synthetic_adjudications.json"


def json_copy(value):
    return json.loads(json.dumps(value))


class StrictJSONTests(unittest.TestCase):
    def test_duplicate_keys_fail_closed(self):
        with self.assertRaisesRegex(ContractError, "duplicate JSON key"):
            strict_loads('{"a":1,"a":2}', "duplicate")

    def test_nonfinite_values_fail_closed(self):
        for literal in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(literal=literal), self.assertRaises(ContractError):
                strict_loads('{"value":' + literal + "}", "nonfinite")

    def test_trailing_text_fails_closed(self):
        with self.assertRaises(ContractError):
            strict_loads('{"ok":true} trailing', "trailing")

    def test_depth_limit_fails_closed(self):
        with self.assertRaisesRegex(ContractError, "depth"):
            strict_loads("[" * 26 + "0" + "]" * 26, "deep")


class FixtureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = load_inputs(CONTRACT, CASES, ADJUDICATIONS)

    def test_contract_is_synthetic_and_non_authoritative(self):
        self.assertIs(self.inputs.contract["synthetic"], True)
        self.assertEqual(self.inputs.contract["authority"], "NO_PRODUCTION_AUTHORITY")
        self.assertIs(self.inputs.contract["gate_policy"]["action_authorized"], False)
        self.assertIn(
            "INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION",
            (ROOT / "index.html").read_text(encoding="utf-8"),
        )

    def test_exact_partition_counts(self):
        counts = {partition: 0 for partition in ("development", "holdout")}
        for case in self.inputs.casebook["cases"]:
            counts[case["partition"]] += 1
        self.assertEqual(counts, {"development": 8, "holdout": 4})

    def test_exact_slice_counts(self):
        counts = {}
        for case in self.inputs.casebook["cases"]:
            counts[case["slice"]] = counts.get(case["slice"], 0) + 1
        self.assertEqual(set(counts.values()), {3})
        self.assertEqual(len(counts), 4)

    def test_holdout_is_workflow_sealed_not_confidential(self):
        self.assertIn("explicit_local_reveal", self.inputs.contract["partitions"]["holdout_meaning"])
        for case in self.inputs.casebook["cases"]:
            self.assertEqual(case["sealed"], case["partition"] == "holdout")

    def test_two_invented_candidates(self):
        candidates = self.inputs.contract["candidates"]
        self.assertEqual(len(candidates), 2)
        self.assertTrue(all(candidate["invented"] is True for candidate in candidates))

    def test_unknown_contract_key_rejected(self):
        contract = json_copy(self.inputs.contract)
        contract["surprise"] = True
        with self.assertRaisesRegex(ContractError, "unknown"):
            validate_contract(contract)

    def test_bad_partition_count_rejected(self):
        casebook = json_copy(self.inputs.casebook)
        casebook["cases"].pop()
        with self.assertRaisesRegex(ContractError, "exactly 12"):
            validate_casebook(casebook, self.inputs.contract)

    def test_development_hard_veto_rejected(self):
        casebook = json_copy(self.inputs.casebook)
        casebook["cases"][0]["hard_veto"] = True
        with self.assertRaisesRegex(ContractError, "holdout-only"):
            validate_casebook(casebook, self.inputs.contract)

    def test_human_hard_veto_rejected(self):
        casebook = json_copy(self.inputs.casebook)
        target = next(case for case in casebook["cases"] if case["grader"]["type"] == "human_rubric")
        target["partition"] = "holdout"
        target["case_id"] = "HOLD-999"
        target["sealed"] = True
        target["hard_veto"] = True
        with self.assertRaisesRegex(ContractError, "exact deterministic"):
            validate_casebook(casebook, self.inputs.contract)


class ExactGraderTests(unittest.TestCase):
    def exact_case(self, expected):
        return {"case_id": "DEV-999", "grader": {"type": "exact_json", "expected": expected}}

    def test_bool_is_not_integer_zero(self):
        self.assertFalse(grade_exact(self.exact_case({"ready": 0}), '{"ready": false}'))

    def test_bool_is_not_integer_one(self):
        self.assertFalse(grade_exact(self.exact_case({"ready": 1}), '{"ready": true}'))

    def test_integer_is_not_float(self):
        self.assertFalse(grade_exact(self.exact_case({"score": 1}), '{"score": 1.0}'))

    def test_nested_type_identity(self):
        case = self.exact_case({"rows": [{"ready": False, "score": 1}]})
        self.assertFalse(grade_exact(case, '{"rows":[{"ready":0,"score":1}]}'))

    def test_exact_object_key_order_is_irrelevant(self):
        case = self.exact_case({"a": 1, "b": [True, None]})
        self.assertTrue(grade_exact(case, '{"b":[true,null],"a":1}'))

    def test_extra_key_rejected(self):
        self.assertFalse(grade_exact(self.exact_case({"ready": True}), '{"ready":true,"extra":1}'))

    def test_missing_key_rejected(self):
        self.assertFalse(grade_exact(self.exact_case({"ready": True, "note": "x"}), '{"ready":true}'))

    def test_duplicate_key_rejected(self):
        self.assertFalse(grade_exact(self.exact_case({"ready": True}), '{"ready":false,"ready":true}'))

    def test_nonfinite_rejected(self):
        self.assertFalse(grade_exact(self.exact_case({"score": 1}), '{"score":NaN}'))

    def test_trailing_text_rejected(self):
        self.assertFalse(grade_exact(self.exact_case({"ready": True}), '{"ready":true} extra'))

    def test_token_contract_casefolds(self):
        case = {"case_id": "DEV-998", "grader": {"type": "token_contract", "required_phrases": ["HOLD"], "forbidden_phrases": ["approved"]}}
        self.assertTrue(grade_exact(case, "hold for review"))
        self.assertFalse(grade_exact(case, "HOLD, but approved"))


class AdjudicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = load_inputs(CONTRACT, CASES, ADJUDICATIONS)

    def test_reference_has_all_four_human_reviews(self):
        self.assertEqual(len(self.inputs.adjudications["reviews"]), 4)

    def test_duplicate_review_rejected(self):
        value = json_copy(self.inputs.adjudications)
        value["reviews"].append(json_copy(value["reviews"][0]))
        with self.assertRaisesRegex(ContractError, "duplicate"):
            validate_adjudications(value, self.inputs.contract, self.inputs.casebook)

    def test_exact_case_review_rejected(self):
        value = json_copy(self.inputs.adjudications)
        value["reviews"][0]["case_id"] = "DEV-001"
        with self.assertRaisesRegex(ContractError, "non-qualitative"):
            validate_adjudications(value, self.inputs.contract, self.inputs.casebook)

    def test_bool_score_rejected(self):
        value = json_copy(self.inputs.adjudications)
        value["reviews"][0]["scores"]["A"] = True
        with self.assertRaisesRegex(ContractError, "integer"):
            validate_adjudications(value, self.inputs.contract, self.inputs.casebook)

    def test_unknown_reason_rejected(self):
        value = json_copy(self.inputs.adjudications)
        value["reviews"][0]["rationale_code"] = "free_text_guess"
        with self.assertRaisesRegex(ContractError, "controlled reason"):
            validate_adjudications(value, self.inputs.contract, self.inputs.casebook)

    def test_preference_must_match_blind_score_order(self):
        value = json_copy(self.inputs.adjudications)
        value["reviews"][0]["blind_preference"] = "A"
        with self.assertRaisesRegex(ContractError, "ordering"):
            validate_adjudications(value, self.inputs.contract, self.inputs.casebook)

    def test_tie_requires_equal_blind_scores(self):
        value = json_copy(self.inputs.adjudications)
        value["reviews"][0]["blind_preference"] = "tie"
        with self.assertRaisesRegex(ContractError, "ordering"):
            validate_adjudications(value, self.inputs.contract, self.inputs.casebook)

    def test_equal_blind_scores_require_tie(self):
        value = json_copy(self.inputs.adjudications)
        value["reviews"][0]["scores"] = {"A": 3, "B": 3}
        with self.assertRaisesRegex(ContractError, "ordering"):
            validate_adjudications(value, self.inputs.contract, self.inputs.casebook)

    def test_reason_must_match_case_slice(self):
        value = json_copy(self.inputs.adjudications)
        value["reviews"][0]["rationale_code"] = "safe_escalation_preserved"
        with self.assertRaisesRegex(ContractError, "case slice"):
            validate_adjudications(value, self.inputs.contract, self.inputs.casebook)

    def test_tie_requires_tie_reason(self):
        value = json_copy(self.inputs.adjudications)
        value["reviews"][0]["scores"] = {"A": 3, "B": 3}
        value["reviews"][0]["blind_preference"] = "tie"
        with self.assertRaisesRegex(ContractError, "tie state"):
            validate_adjudications(value, self.inputs.contract, self.inputs.casebook)


class ReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pending_inputs = load_inputs(CONTRACT, CASES)
        cls.reviewed_inputs = load_inputs(CONTRACT, CASES, ADJUDICATIONS)
        cls.pending = build_receipt(cls.pending_inputs)
        cls.reviewed = build_receipt(cls.reviewed_inputs)

    def test_pending_without_human_adjudication(self):
        self.assertEqual(self.pending["outcome"], "PENDING")
        self.assertEqual(len(self.pending["missing_human_case_ids"]), 4)

    def test_reference_review_is_hold(self):
        self.assertEqual(self.reviewed["outcome"], "HOLD")
        self.assertEqual(self.reviewed["reason_codes"], ["HOLDOUT_HARD_VETO_FAILED"])
        self.assertEqual(self.reviewed["hard_veto_failure_case_ids"], ["HOLD-103"])

    def test_only_fail_closed_outcomes(self):
        self.assertEqual(ALLOWED_OUTCOMES, ("HOLD", "ROLLBACK", "PENDING"))
        self.assertIn(self.reviewed["outcome"], ALLOWED_OUTCOMES)
        self.assertIs(self.reviewed["action_authorized"], False)

    def test_regression_review_rolls_back(self):
        value = json.loads(ADJUDICATIONS.read_text(encoding="utf-8"))
        baseline = self.reviewed_inputs.contract["baseline_candidate_id"]
        challenger = self.reviewed_inputs.contract["challenger_candidate_id"]
        cases_by_id = {case["case_id"]: case for case in self.reviewed_inputs.casebook["cases"]}
        for review in value["reviews"]:
            case = cases_by_id[review["case_id"]]
            baseline_label = next(label for label, response in case["responses"].items() if response["candidate_id"] == baseline)
            challenger_label = next(label for label, response in case["responses"].items() if response["candidate_id"] == challenger)
            review["scores"] = {baseline_label: 4, challenger_label: 0}
            review["blind_preference"] = baseline_label
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "regression.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            receipt = build_receipt(load_inputs(CONTRACT, CASES, path))
        self.assertEqual(receipt["outcome"], "ROLLBACK")
        self.assertEqual(receipt["reason_codes"], ["CHALLENGER_REGRESSION_LIMIT_EXCEEDED"])

    def test_receipt_is_deterministic(self):
        self.assertEqual(canonical_bytes(self.reviewed), canonical_bytes(build_receipt(self.reviewed_inputs)))

    def test_receipt_self_digest_verifies(self):
        self.assertTrue(verify_receipt(self.reviewed))

    def test_exact_rebuild_verifies(self):
        self.assertTrue(verify_receipt(self.reviewed, build_receipt(self.reviewed_inputs)))

    def test_tamper_fails_verification(self):
        tampered = copy.deepcopy(self.reviewed)
        tampered["outcome"] = "PENDING"
        self.assertFalse(verify_receipt(tampered))

    def test_audit_chain_tamper_fails(self):
        events = copy.deepcopy(self.reviewed["audit_chain"])
        events[1]["details"]["inference_used"] = True
        self.assertFalse(verify_audit_chain(events))

    def test_holdout_bundle_is_hash_bound_not_confidential(self):
        binding = self.reviewed["partition_binding"]
        self.assertRegex(binding["holdout_bundle_sha256"], r"^[0-9a-f]{64}$")
        self.assertIs(binding["cryptographic_confidentiality_claimed"], False)

    def test_candidate_totals_are_expected(self):
        self.assertEqual(self.reviewed["candidate_totals"], {"candidate_juniper_v2": 27, "candidate_sable_v3": 44})

    def test_audit_has_four_events(self):
        self.assertEqual(len(self.reviewed["audit_chain"]), 4)
        self.assertTrue(verify_audit_chain(self.reviewed["audit_chain"]))


class LocalWriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = build_receipt(load_inputs(CONTRACT, CASES, ADJUDICATIONS))

    def test_write_requires_exact_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ContractError, "confirm-local-write"):
                write_receipt(Path(directory) / "receipt.json", self.receipt, None)

    def test_write_is_new_and_private(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            write_receipt(path, self.receipt, WRITE_CONFIRMATION)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertTrue(verify_receipt(json.loads(path.read_text(encoding="utf-8"))))
            with self.assertRaisesRegex(ContractError, "new non-symlink"):
                write_receipt(path, self.receipt, WRITE_CONFIRMATION)

    def test_symlink_output_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.json"
            target.write_text("preserve", encoding="utf-8")
            link = root / "receipt.json"
            link.symlink_to(target)
            with self.assertRaisesRegex(ContractError, "new non-symlink"):
                write_receipt(link, self.receipt, WRITE_CONFIRMATION)
            self.assertEqual(target.read_text(encoding="utf-8"), "preserve")


class BrowserSnapshotContractTests(unittest.TestCase):
    @staticmethod
    def assignment(path: Path, name: str):
        text = path.read_text(encoding="utf-8")
        prefix = f"'use strict';\nwindow.{name} = "
        if not text.startswith(prefix) or not text.endswith(";\n"):
            raise AssertionError(f"unexpected assignment wrapper: {path}")
        return strict_loads(text[len(prefix):-2], path.name)

    @classmethod
    def setUpClass(cls):
        cls.base = cls.assignment(ROOT / "data" / "demo_snapshot.js", "EVALUATION_RELEASE_GATE_BASE")
        cls.holdout = cls.assignment(ROOT / "data" / "holdout_snapshot.js", "EVALUATION_RELEASE_GATE_HOLDOUT")
        cls.casebook = json.loads(CASES.read_text(encoding="utf-8"))

    def test_base_contains_exact_development_count(self):
        self.assertEqual(len(self.base["development_cases"]), 8)
        self.assertTrue(all(case["partition"] == "development" for case in self.base["development_cases"]))

    def test_base_excludes_holdout_details(self):
        base_text = canonical_bytes(self.base).decode("utf-8")
        for case in self.casebook["cases"]:
            if case["partition"] == "holdout":
                self.assertNotIn(case["task_brief"], base_text)
                for response in case["responses"].values():
                    self.assertNotIn(response["output"], base_text)

    def test_base_excludes_candidate_identity_bindings(self):
        base_text = canonical_bytes(self.base).decode("utf-8")
        self.assertNotIn("candidate_juniper", base_text)
        self.assertNotIn("candidate_sable", base_text)
        self.assertNotIn("candidate_bindings", self.base)

    def test_reveal_contains_exact_holdout_count(self):
        self.assertEqual(len(self.holdout["holdout_cases"]), 4)
        self.assertTrue(all(case["partition"] == "holdout" for case in self.holdout["holdout_cases"]))

    def test_complete_reveal_payload_digest_is_bound(self):
        self.assertEqual(sha256_bytes(canonical_bytes(self.holdout)), self.base["holdout_payload_sha256"])

    def test_detail_tamper_breaks_complete_payload_digest(self):
        tampered = copy.deepcopy(self.holdout)
        tampered["holdout_cases"][0]["task_brief"] += " tampered"
        self.assertNotEqual(sha256_bytes(canonical_bytes(tampered)), self.base["holdout_payload_sha256"])

    def test_binding_tamper_breaks_complete_payload_digest(self):
        tampered = copy.deepcopy(self.holdout)
        tampered["candidate_bindings"]["HOLD-103"]["A"] = "candidate_juniper_v2"
        self.assertNotEqual(sha256_bytes(canonical_bytes(tampered)), self.base["holdout_payload_sha256"])

    def test_reveal_reference_receipt_is_valid(self):
        self.assertTrue(verify_receipt(self.holdout["reference_receipt"]))
        self.assertEqual(self.holdout["reference_receipt"]["outcome"], "HOLD")


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, "-B", "-m", "release_gate", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )

    def test_demo_reports_pending_and_hold(self):
        result = self.run_cli("demo", "--contract", str(CONTRACT), "--cases", str(CASES), "--adjudications", str(ADJUDICATIONS))
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual((value["pending_outcome"], value["reviewed_outcome"]), ("PENDING", "HOLD"))

    def test_evaluate_stdout_does_not_write(self):
        before = {path.relative_to(ROOT) for path in ROOT.rglob("*")}
        result = self.run_cli("evaluate", "--contract", str(CONTRACT), "--cases", str(CASES))
        after = {path.relative_to(ROOT) for path in ROOT.rglob("*")}
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["outcome"], "PENDING")
        self.assertEqual(before, after)

    def test_verify_exact_artifact(self):
        receipt = build_receipt(load_inputs(CONTRACT, CASES, ADJUDICATIONS))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            result = self.run_cli("verify", "--contract", str(CONTRACT), "--cases", str(CASES), "--adjudications", str(ADJUDICATIONS), "--receipt", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
