from __future__ import annotations

import copy
import json
import unittest

from claim_evidence_contract_linter.canonical import canonical_json_bytes, sha256_hex
from claim_evidence_contract_linter.engine import build_report, evaluate_claims, verify_report
from claim_evidence_contract_linter.errors import AuditMismatch, InputError

from support import fixture_values, mutable_fixtures


class DecisionTests(unittest.TestCase):
    def test_demo_exercises_all_three_states(self):
        contract, _cb, evidence, _eb = fixture_values()
        results = evaluate_claims(contract, evidence)
        states = {result["claim_id"]: result["state"] for result in results}
        self.assertEqual(
            states,
            {
                "claim-escalation-rate": "SUPPORTED",
                "claim-zero-errors": "UNSUPPORTED",
                "claim-production-ready": "NEEDS_REVIEW",
                "claim-citation-integrity": "SUPPORTED",
            },
        )

    def test_demo_reason_codes_are_explicit(self):
        contract, _cb, evidence, _eb = fixture_values()
        results = {item["claim_id"]: item for item in evaluate_claims(contract, evidence)}
        self.assertEqual(
            results["claim-zero-errors"]["reason_codes"], ["DIRECT_CONTRADICTION"]
        )
        self.assertEqual(
            results["claim-production-ready"]["reason_codes"],
            [
                "QUALIFIED_EVIDENCE",
                "INSUFFICIENT_INDEPENDENT_SUPPORT",
                "ABSOLUTE_LANGUAGE_REQUIRES_HIGH_RISK",
            ],
        )

    def test_wrong_fact_qualifier_is_off_topic_not_a_review_trigger(self):
        contract, _cb, evidence, _eb = mutable_fixtures()
        claim = contract["claims"][2]
        claim["fact_id"] = "different-fact"
        result = evaluate_claims(contract, evidence)[2]
        self.assertEqual(result["state"], "UNSUPPORTED")
        self.assertEqual(result["reason_codes"], ["NO_RELEVANT_EVIDENCE"])
        self.assertEqual(result["policy_observations"]["distinct_qualifying_sources"], [])

    def test_conflicting_support_and_contradiction_needs_review(self):
        contract, _cb, evidence, _eb = mutable_fixtures()
        contradictory = evidence["sources"][0]["assertions"][1]
        contradictory["fact_id"] = "escalation-rate-97"
        contract["claims"][0]["citations"].append(
            {
                "source_id": "run-a",
                "assertion_id": "assert-errors-remain",
                "start": 97,
                "end": 126,
                "quote": "Two false negatives remained.",
            }
        )
        result = evaluate_claims(contract, evidence)[0]
        self.assertEqual(result["state"], "NEEDS_REVIEW")
        self.assertIn("CONFLICTING_EVIDENCE", result["reason_codes"])

    def test_high_risk_claim_with_one_support_needs_review(self):
        contract, _cb, evidence, _eb = mutable_fixtures()
        contract["claims"][0]["citations"].pop()
        result = evaluate_claims(contract, evidence)[0]
        self.assertEqual(result["state"], "NEEDS_REVIEW")
        self.assertEqual(result["policy_observations"]["distinct_supporting_sources"], ["run-a"])

    def test_no_citations_is_unsupported(self):
        contract, _cb, evidence, _eb = mutable_fixtures()
        contract["claims"][3]["citations"] = []
        result = evaluate_claims(contract, evidence)[3]
        self.assertEqual(result["state"], "UNSUPPORTED")
        self.assertEqual(result["reason_codes"], ["NO_RELEVANT_EVIDENCE"])

    def test_absolute_term_is_boundary_aware(self):
        contract, _cb, evidence, _eb = mutable_fixtures()
        claim = contract["claims"][3]
        claim["text"] = "The synthetic queue was zeroed after the cited check."
        result = evaluate_claims(contract, evidence)[3]
        self.assertEqual(result["state"], "SUPPORTED")
        self.assertEqual(result["policy_observations"]["absolute_terms_found"], [])

    def test_absolute_phrase_accepts_multiple_spaces(self):
        contract, _cb, evidence, _eb = mutable_fixtures()
        contract["claims"][3]["text"] = "The result is fully   compliant."
        result = evaluate_claims(contract, evidence)[3]
        self.assertEqual(result["state"], "NEEDS_REVIEW")
        self.assertEqual(
            result["policy_observations"]["absolute_terms_found"], ["fully compliant"]
        )

    def test_unicode_spans_use_code_points(self):
        contract = {
            "schema_version": "1.0",
            "contract_id": "unicode-contract",
            "policy": {
                "minimum_distinct_sources": {"low": 1, "medium": 1, "high": 2},
                "absolute_terms": [],
            },
            "claims": [
                {
                    "claim_id": "unicode-claim",
                    "text": "The invented préflight passed.",
                    "fact_id": "preflight-passed",
                    "risk_tier": "low",
                    "citations": [
                        {
                            "source_id": "unicode-source",
                            "assertion_id": "unicode-assertion",
                            "start": 0,
                            "end": 19,
                            "quote": "Préflight ✓ passed.",
                        }
                    ],
                }
            ],
        }
        evidence = {
            "schema_version": "1.0",
            "evidence_set_id": "unicode-evidence",
            "sources": [
                {
                    "source_id": "unicode-source",
                    "title": "Invented Unicode check",
                    "content": "Préflight ✓ passed.",
                    "assertions": [
                        {
                            "assertion_id": "unicode-assertion",
                            "fact_id": "preflight-passed",
                            "stance": "supports",
                            "start": 0,
                            "end": 19,
                            "quote": "Préflight ✓ passed.",
                        }
                    ],
                }
            ],
        }
        self.assertEqual(evaluate_claims(contract, evidence)[0]["state"], "SUPPORTED")


class AuditReportTests(unittest.TestCase):
    def _report(self):
        contract, contract_bytes, evidence, evidence_bytes = fixture_values()
        return (
            build_report(
                contract,
                evidence,
                contract_bytes=contract_bytes,
                evidence_bytes=evidence_bytes,
            ),
            contract,
            contract_bytes,
            evidence,
            evidence_bytes,
        )

    def test_report_is_deterministic(self):
        first = self._report()[0]
        second = self._report()[0]
        self.assertEqual(first, second)

    def test_report_self_digest_is_correct(self):
        report = self._report()[0]
        supplied = report["report_digest"]["value"]
        body = dict(report)
        del body["report_digest"]
        self.assertEqual(supplied, sha256_hex(canonical_json_bytes(body)))

    def test_report_binds_exact_input_bytes(self):
        report, contract, contract_bytes, evidence, evidence_bytes = self._report()
        altered_bytes = contract_bytes + b" "
        altered = build_report(
            contract,
            evidence,
            contract_bytes=altered_bytes,
            evidence_bytes=evidence_bytes,
        )
        self.assertNotEqual(
            report["input_binding"]["contract_sha256"],
            altered["input_binding"]["contract_sha256"],
        )
        self.assertNotEqual(
            report["report_digest"]["value"], altered["report_digest"]["value"]
        )

    def test_verify_accepts_exact_report_and_inputs(self):
        report, contract, contract_bytes, evidence, evidence_bytes = self._report()
        result = verify_report(
            report,
            contract,
            evidence,
            contract_bytes=contract_bytes,
            evidence_bytes=evidence_bytes,
        )
        self.assertTrue(result["verified"])

    def test_verify_rejects_self_digest_tamper(self):
        report, contract, contract_bytes, evidence, evidence_bytes = self._report()
        report["summary"]["supported"] = 99
        with self.assertRaisesRegex(AuditMismatch, "self-digest"):
            verify_report(
                report,
                contract,
                evidence,
                contract_bytes=contract_bytes,
                evidence_bytes=evidence_bytes,
            )

    def test_verify_rejects_rehashed_forgery_by_full_recomputation(self):
        report, contract, contract_bytes, evidence, evidence_bytes = self._report()
        report["summary"]["supported"] = 99
        body = dict(report)
        del body["report_digest"]
        report["report_digest"]["value"] = sha256_hex(canonical_json_bytes(body))
        with self.assertRaisesRegex(AuditMismatch, "does not exactly match"):
            verify_report(
                report,
                contract,
                evidence,
                contract_bytes=contract_bytes,
                evidence_bytes=evidence_bytes,
            )

    def test_verify_rejects_semantically_same_but_byte_changed_input(self):
        report, contract, contract_bytes, evidence, evidence_bytes = self._report()
        with self.assertRaisesRegex(AuditMismatch, "does not exactly match"):
            verify_report(
                report,
                contract,
                evidence,
                contract_bytes=contract_bytes + b" ",
                evidence_bytes=evidence_bytes,
            )

    def test_citation_digest_changes_when_source_content_changes(self):
        report, contract, contract_bytes, evidence, evidence_bytes = self._report()
        first_digest = report["claims"][0]["citations"][0]["citation_binding_sha256"]
        changed = copy.deepcopy(evidence)
        changed["sources"][0]["content"] += " Invented appendix."
        changed_bytes = json.dumps(changed).encode("utf-8")
        changed_report = build_report(
            contract,
            changed,
            contract_bytes=contract_bytes,
            evidence_bytes=changed_bytes,
        )
        changed_digest = changed_report["claims"][0]["citations"][0][
            "citation_binding_sha256"
        ]
        self.assertNotEqual(first_digest, changed_digest)

    def test_bad_exact_citation_fails_closed(self):
        contract, contract_bytes, evidence, evidence_bytes = mutable_fixtures()
        contract["claims"][0]["citations"][0]["quote"] += " "
        with self.assertRaisesRegex(InputError, "must exactly match"):
            build_report(
                contract,
                evidence,
                contract_bytes=contract_bytes,
                evidence_bytes=evidence_bytes,
            )


if __name__ == "__main__":
    unittest.main()
