from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from integration_lab.core import (
    ACKNOWLEDGEMENT,
    ContractError,
    SYNTHETIC_SECRET,
    evaluate,
    evaluate_delivery,
    evaluate_exchange,
    evaluate_files,
    load_json_file,
    promote_simulated,
    sign_webhook,
    strict_loads,
    validate_contract,
    validate_run_fixture,
    verify_audit_chain,
    verify_receipt,
    AuditChain,
)
from tests.support import CONTRACT_PATH, RUN_PATH, fixtures, rate_limited_attempt


class StrictJsonAndContractTests(unittest.TestCase):
    def test_reference_contract_and_run_validate(self) -> None:
        contract, run = fixtures()
        self.assertEqual("api_integration_contract_lab", validate_contract(contract)["lab_id"])
        self.assertEqual(7, len(validate_run_fixture(run)["deliveries"]))

    def test_duplicate_json_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(ContractError, "duplicate JSON key"):
            strict_loads('{"synthetic":true,"synthetic":true}', "duplicate")

    def test_nonfinite_json_is_rejected(self) -> None:
        with self.assertRaisesRegex(ContractError, "non-finite"):
            strict_loads('{"value":NaN}', "nonfinite")

    def test_excessive_json_depth_is_rejected(self) -> None:
        raw = "[" * 26 + "0" + "]" * 26
        with self.assertRaisesRegex(ContractError, "nesting"):
            strict_loads(raw, "deep")

    def test_unknown_contract_key_fails_closed(self) -> None:
        contract, _ = fixtures()
        contract["unexpected"] = True
        with self.assertRaisesRegex(ContractError, "exact keys"):
            validate_contract(contract)

    def test_false_synthetic_declaration_is_rejected(self) -> None:
        contract, run = fixtures()
        contract["synthetic"] = False
        with self.assertRaisesRegex(ContractError, "must be true"):
            validate_contract(contract)
        run["synthetic"] = False
        with self.assertRaisesRegex(ContractError, "must be true"):
            validate_run_fixture(run)

    def test_only_explicit_public_demo_secret_is_accepted(self) -> None:
        contract, _ = fixtures()
        self.assertEqual(SYNTHETIC_SECRET, contract["synthetic_secret"])
        contract["synthetic_secret"] = "real-looking-secret"
        with self.assertRaisesRegex(ContractError, "explicit public demo secret"):
            validate_contract(contract)

    def test_symlink_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="api-lab-symlink-") as temp_dir:
            root = Path(temp_dir)
            target = root / "target.json"
            target.write_text("{}", encoding="utf-8")
            link = root / "link.json"
            link.symlink_to(target)
            with self.assertRaisesRegex(ContractError, "symlink"):
                load_json_file(link, "link")


class WebhookContractTests(unittest.TestCase):
    def test_reference_deliveries_reach_every_declared_state(self) -> None:
        report = evaluate_files(CONTRACT_PATH, RUN_PATH)
        states = [item["state"] for item in report["deliveries"]]
        self.assertEqual(
            [
                "ready_for_human",
                "suppressed_duplicate",
                "quarantined_signature",
                "quarantined_replay_window",
                "quarantined_schema_drift",
                "quarantined_header_contract",
                "ready_for_human",
            ],
            states,
        )

    def test_hmac_binds_timestamp_and_exact_raw_bytes(self) -> None:
        contract, run = fixtures()
        original = run["deliveries"][0]
        self.assertEqual(
            original["headers"]["x-demo-signature"],
            sign_webhook(SYNTHETIC_SECRET, original["headers"]["x-demo-timestamp"], original["raw_body"]),
        )
        changed = deepcopy(original)
        changed["raw_body"] += " "
        result = evaluate_delivery(changed, contract, set())
        self.assertEqual("quarantined_signature", result["state"])
        self.assertFalse(result["signature_valid"])

    def test_invalid_signature_fails_before_payload_promotion(self) -> None:
        contract, run = fixtures()
        result = evaluate_delivery(run["deliveries"][2], contract, set())
        self.assertEqual(["hmac_mismatch"], result["reason_codes"])
        self.assertFalse(result["human_eligible"])

    def test_stale_and_future_timestamps_are_quarantined(self) -> None:
        contract, run = fixtures()
        stale = evaluate_delivery(run["deliveries"][3], contract, set())
        self.assertEqual("timestamp_too_old", stale["reason_codes"][0])

        future = deepcopy(run["deliveries"][0])
        future["headers"]["x-demo-timestamp"] = str(contract["fixed_now_epoch"] + 1)
        future["headers"]["x-demo-signature"] = sign_webhook(
            SYNTHETIC_SECRET, future["headers"]["x-demo-timestamp"], future["raw_body"]
        )
        result = evaluate_delivery(future, contract, set())
        self.assertEqual("quarantined_replay_window", result["state"])
        self.assertEqual(["timestamp_in_future"], result["reason_codes"])

    def test_duplicate_suppression_uses_prior_accepted_key(self) -> None:
        contract, run = fixtures()
        seen: set[str] = set()
        first = evaluate_delivery(run["deliveries"][0], contract, seen)
        second = evaluate_delivery(run["deliveries"][1], contract, seen)
        self.assertEqual("ready_for_human", first["state"])
        self.assertEqual("suppressed_duplicate", second["state"])
        self.assertEqual(["idempotency_key_seen"], second["reason_codes"])

    def test_failed_signature_does_not_poison_idempotency_scope(self) -> None:
        contract, run = fixtures()
        bad = deepcopy(run["deliveries"][0])
        bad["headers"]["x-demo-signature"] = "v1=" + "0" * 64
        seen: set[str] = set()
        self.assertEqual("quarantined_signature", evaluate_delivery(bad, contract, seen)["state"])
        self.assertEqual("ready_for_human", evaluate_delivery(run["deliveries"][0], contract, seen)["state"])

    def test_unknown_data_field_is_schema_drift(self) -> None:
        contract, run = fixtures()
        result = evaluate_delivery(run["deliveries"][4], contract, set())
        self.assertEqual("quarantined_schema_drift", result["state"])
        self.assertEqual(["data_fields"], result["reason_codes"])

    def test_bad_correlation_id_is_header_quarantine(self) -> None:
        contract, run = fixtures()
        result = evaluate_delivery(run["deliveries"][5], contract, set())
        self.assertEqual("quarantined_header_contract", result["state"])
        self.assertEqual(["correlation_id_shape"], result["reason_codes"])

    def test_delivery_expected_state_mismatch_fails_closed(self) -> None:
        contract, run = fixtures()
        run["deliveries"][0]["expected_state"] = "quarantined_signature"
        with self.assertRaisesRegex(ContractError, "expected_state"):
            evaluate(contract, run)


class ExchangeContractTests(unittest.TestCase):
    def test_reference_exchange_builds_virtual_2_4_schedule_and_recovers(self) -> None:
        report = evaluate_files(CONTRACT_PATH, RUN_PATH)
        exchange = report["exchange"]
        self.assertEqual([2, 4], exchange["retry_schedule_seconds"])
        self.assertEqual(6, exchange["virtual_delay_total_seconds"])
        self.assertEqual(202, exchange["final_status"])
        self.assertEqual("recovered_ready_for_human", exchange["state"])

    def test_exchange_performs_no_network_or_sleep(self) -> None:
        exchange = evaluate_files(CONTRACT_PATH, RUN_PATH)["exchange"]
        self.assertEqual(0, exchange["network_calls"])
        self.assertEqual(0, exchange["sleep_calls"])

    def test_trailing_attempt_after_terminal_202_is_rejected(self) -> None:
        contract, run = fixtures()
        extra = rate_limited_attempt(4, run["exchange"]["headers"]["x-correlation-id"])
        run["exchange"]["attempts"].append(extra)
        with self.assertRaisesRegex(ContractError, "terminal 202 must be the final"):
            evaluate(contract, run)

    def test_exchange_expected_state_mismatch_fails_closed(self) -> None:
        contract, run = fixtures()
        run["exchange"]["expected_state"] = "failed_contract"
        with self.assertRaisesRegex(ContractError, "expected_state"):
            evaluate(contract, run)

    def test_correlation_echo_mismatch_is_contract_failure(self) -> None:
        contract, run = fixtures()
        run["exchange"]["attempts"] = [deepcopy(run["exchange"]["attempts"][2])]
        run["exchange"]["attempts"][0]["attempt"] = 1
        run["exchange"]["attempts"][0]["headers"]["x-correlation-id"] = "corr_deadbeef"
        run["exchange"]["expected_state"] = "failed_contract"
        audit = AuditChain()
        result = evaluate_exchange(run["exchange"], contract, audit)
        self.assertEqual("failed_contract", result["state"])
        self.assertEqual(["correlation_echo_mismatch"], result["reason_codes"])

    def test_retry_budget_exhaustion_routes_to_human(self) -> None:
        contract, run = fixtures()
        correlation = run["exchange"]["headers"]["x-correlation-id"]
        run["exchange"]["attempts"] = [
            rate_limited_attempt(1, correlation, "2"),
            rate_limited_attempt(2, correlation, "3"),
            rate_limited_attempt(3, correlation, "8"),
            rate_limited_attempt(4, correlation, "8"),
        ]
        run["exchange"]["expected_state"] = "exhausted_to_human"
        result = evaluate_exchange(run["exchange"], contract, AuditChain())
        self.assertEqual("exhausted_to_human", result["state"])
        self.assertEqual([2, 4, 8], result["retry_schedule_seconds"])
        self.assertFalse(result["human_eligible"])

    def test_nonallowlisted_path_is_rejected(self) -> None:
        contract, run = fixtures()
        run["exchange"]["path"] = "/v1/production/resources"
        with self.assertRaisesRegex(ContractError, "not allowlisted"):
            evaluate(contract, run)

    def test_accepted_response_schema_drift_fails_contract(self) -> None:
        contract, run = fixtures()
        run["exchange"]["attempts"] = [deepcopy(run["exchange"]["attempts"][2])]
        run["exchange"]["attempts"][0]["attempt"] = 1
        run["exchange"]["attempts"][0]["body"]["state"] = "done"
        run["exchange"]["expected_state"] = "failed_contract"
        result = evaluate_exchange(run["exchange"], contract, AuditChain())
        self.assertEqual("failed_contract", result["state"])
        self.assertEqual(["accepted_response_contract"], result["reason_codes"])


class ReceiptAndPromotionTests(unittest.TestCase):
    def test_report_is_deterministic_and_verifies(self) -> None:
        first = evaluate_files(CONTRACT_PATH, RUN_PATH)
        second = evaluate_files(CONTRACT_PATH, RUN_PATH)
        self.assertEqual(first, second)
        self.assertTrue(verify_receipt(first))
        self.assertTrue(verify_audit_chain(first["audit"]["events"]))

    def test_audit_event_tamper_is_detected(self) -> None:
        receipt = evaluate_files(CONTRACT_PATH, RUN_PATH)
        receipt["audit"]["events"][0]["details"]["state"] = "forged"
        self.assertFalse(verify_receipt(receipt))

    def test_receipt_digest_tamper_is_detected(self) -> None:
        receipt = evaluate_files(CONTRACT_PATH, RUN_PATH)
        receipt["receipt_digest"] = "0" * 64
        self.assertFalse(verify_receipt(receipt))

    def test_wrong_promotion_token_is_rejected(self) -> None:
        receipt = evaluate_files(CONTRACT_PATH, RUN_PATH)
        with self.assertRaisesRegex(ContractError, "exact review token"):
            promote_simulated(receipt, "review_wrong00000000", ACKNOWLEDGEMENT)

    def test_wrong_personal_project_acknowledgement_is_rejected(self) -> None:
        receipt = evaluate_files(CONTRACT_PATH, RUN_PATH)
        with self.assertRaisesRegex(ContractError, "personal-project acknowledgement"):
            promote_simulated(receipt, receipt["promotion_gate"]["confirm_token"], "PRODUCTION_APPROVED")

    def test_exact_human_gate_adds_verified_simulated_event_without_mutating_base(self) -> None:
        base = evaluate_files(CONTRACT_PATH, RUN_PATH)
        original = deepcopy(base)
        promoted = promote_simulated(base, base["promotion_gate"]["confirm_token"], ACKNOWLEDGEMENT)
        self.assertEqual(original, base)
        self.assertEqual("simulated_promoted", promoted["promotion_gate"]["state"])
        self.assertFalse(promoted["promotion_gate"]["production_write"])
        self.assertEqual(len(base["audit"]["events"]) + 1, len(promoted["audit"]["events"]))
        self.assertTrue(verify_receipt(promoted))

    def test_exact_input_byte_drift_changes_source_and_receipt_digests(self) -> None:
        baseline = evaluate_files(CONTRACT_PATH, RUN_PATH)
        with tempfile.TemporaryDirectory(prefix="api-lab-byte-drift-") as temp_dir:
            contract_copy = Path(temp_dir) / "contract.json"
            contract_copy.write_bytes(CONTRACT_PATH.read_bytes() + b"\n")
            drifted = evaluate_files(contract_copy, RUN_PATH)
        self.assertNotEqual(baseline["source_digests"]["contract_sha256"], drifted["source_digests"]["contract_sha256"])
        self.assertNotEqual(baseline["receipt_digest"], drifted["receipt_digest"])


if __name__ == "__main__":
    unittest.main()
