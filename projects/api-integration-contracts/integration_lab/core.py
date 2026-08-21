"""Strict, deterministic API and webhook contract simulation.

No function in this module opens a socket, sleeps, loads credentials, or calls an
external system. Every endpoint, tenant, key, payload, response, and event is a
synthetic fixture for a personal portfolio project.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable


MAX_FILE_BYTES = 1_000_000
MAX_JSON_DEPTH = 24
MAX_JSON_NODES = 10_000
ZERO_HASH = "0" * 64
SYNTHETIC_SECRET = "whsec_SYNTHETIC_PERSONAL_LAB_NOT_A_SECRET"
ACKNOWLEDGEMENT = "PERSONAL_PORTFOLIO_ONLY"

IDENTIFIER = re.compile(r"^[a-z]+(?:_[a-z0-9]+){2,5}$")
CORRELATION_ID = re.compile(r"^corr_[a-z0-9]{8}$")
IDEMPOTENCY_KEY = re.compile(r"^idem_[a-z0-9]{8}$")
SIGNATURE = re.compile(r"^v1=[0-9a-f]{64}$")
MONEY = re.compile(r"^(?:0|[1-9][0-9]{0,5})\.[0-9]{2}$")


class ContractError(ValueError):
    """Raised when the synthetic contract or fixture fails closed."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ContractError(f"non-finite JSON number is forbidden: {value}")


def _count_json(value: Any, *, depth: int = 0) -> int:
    if depth > MAX_JSON_DEPTH:
        raise ContractError("JSON nesting exceeds the lab limit")
    if isinstance(value, dict):
        return 1 + sum(_count_json(item, depth=depth + 1) for item in value.values())
    if isinstance(value, list):
        return 1 + sum(_count_json(item, depth=depth + 1) for item in value)
    return 1


def strict_loads(raw: str, label: str) -> Any:
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_no_duplicate_object,
            parse_constant=_reject_nonfinite,
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ContractError(f"{label}: invalid JSON: {exc}") from exc
    nodes = _count_json(value)
    if nodes > MAX_JSON_NODES:
        raise ContractError(f"{label}: JSON node count exceeds {MAX_JSON_NODES}")
    return value


def load_json_file(path: Path, label: str) -> tuple[Any, bytes]:
    if path.is_symlink():
        raise ContractError(f"{label}: symlink input is forbidden")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ContractError(f"{label}: unable to read file: {exc}") from exc
    if len(raw) > MAX_FILE_BYTES:
        raise ContractError(f"{label}: file exceeds {MAX_FILE_BYTES} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError(f"{label}: input is not UTF-8") from exc
    return strict_loads(text, label), raw


def require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{path}: expected object")
    return value


def require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{path}: expected array")
    return value


def require_string(value: Any, path: str, *, nonblank: bool = True) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{path}: expected string")
    if nonblank and (not value.strip() or any(ord(char) < 32 for char in value)):
        raise ContractError(f"{path}: expected nonblank control-free string")
    return value


def require_int(value: Any, path: str, *, minimum: int | None = None, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{path}: expected integer")
    if minimum is not None and value < minimum:
        raise ContractError(f"{path}: must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ContractError(f"{path}: must be at most {maximum}")
    return value


def require_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError(f"{path}: expected boolean")
    return value


def require_keys(value: dict[str, Any], required: Iterable[str], path: str) -> None:
    expected = set(required)
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ContractError(f"{path}: exact keys required; missing={missing}, unknown={unknown}")


def validate_contract(contract: Any) -> dict[str, Any]:
    obj = require_object(contract, "contract")
    require_keys(
        obj,
        (
            "schema_version",
            "lab_id",
            "synthetic",
            "synthetic_secret",
            "fixed_now_epoch",
            "replay_window_seconds",
            "retry_policy",
            "allowed_endpoint_paths",
            "webhook_contract",
        ),
        "contract",
    )
    if require_int(obj["schema_version"], "contract.schema_version") != 1:
        raise ContractError("contract.schema_version: only version 1 is supported")
    if require_string(obj["lab_id"], "contract.lab_id") != "api_integration_contract_lab":
        raise ContractError("contract.lab_id: unexpected lab identifier")
    if require_bool(obj["synthetic"], "contract.synthetic") is not True:
        raise ContractError("contract.synthetic: must be true")
    if require_string(obj["synthetic_secret"], "contract.synthetic_secret") != SYNTHETIC_SECRET:
        raise ContractError("contract.synthetic_secret: only the explicit public demo secret is accepted")
    require_int(obj["fixed_now_epoch"], "contract.fixed_now_epoch", minimum=1_700_000_000)
    require_int(obj["replay_window_seconds"], "contract.replay_window_seconds", minimum=30, maximum=900)

    retry = require_object(obj["retry_policy"], "contract.retry_policy")
    require_keys(retry, ("max_retries", "base_seconds", "cap_seconds"), "contract.retry_policy")
    require_int(retry["max_retries"], "contract.retry_policy.max_retries", minimum=1, maximum=5)
    base = require_int(retry["base_seconds"], "contract.retry_policy.base_seconds", minimum=1, maximum=30)
    cap = require_int(retry["cap_seconds"], "contract.retry_policy.cap_seconds", minimum=base, maximum=60)

    paths = require_list(obj["allowed_endpoint_paths"], "contract.allowed_endpoint_paths")
    if not paths or len(paths) != len(set(paths)):
        raise ContractError("contract.allowed_endpoint_paths: must be nonempty and unique")
    for index, path in enumerate(paths):
        text = require_string(path, f"contract.allowed_endpoint_paths[{index}]")
        if not re.fullmatch(r"/v1/synthetic/[a-z-]+", text):
            raise ContractError(f"contract.allowed_endpoint_paths[{index}]: unsafe synthetic path")

    webhook = require_object(obj["webhook_contract"], "contract.webhook_contract")
    require_keys(
        webhook,
        ("event_schema_version", "allowed_event_types", "required_data_fields"),
        "contract.webhook_contract",
    )
    if require_int(webhook["event_schema_version"], "contract.webhook_contract.event_schema_version") != 1:
        raise ContractError("contract.webhook_contract.event_schema_version: only version 1 is supported")
    event_types = require_list(webhook["allowed_event_types"], "contract.webhook_contract.allowed_event_types")
    if event_types != ["order.ready"]:
        raise ContractError("contract.webhook_contract.allowed_event_types: exact demo vocabulary required")
    data_fields = require_list(webhook["required_data_fields"], "contract.webhook_contract.required_data_fields")
    if data_fields != ["order_id", "status", "amount"]:
        raise ContractError("contract.webhook_contract.required_data_fields: exact demo schema required")
    return obj


def validate_run_fixture(run: Any) -> dict[str, Any]:
    obj = require_object(run, "run")
    require_keys(obj, ("schema_version", "synthetic", "deliveries", "exchange"), "run")
    if require_int(obj["schema_version"], "run.schema_version") != 1:
        raise ContractError("run.schema_version: only version 1 is supported")
    if require_bool(obj["synthetic"], "run.synthetic") is not True:
        raise ContractError("run.synthetic: must be true")
    deliveries = require_list(obj["deliveries"], "run.deliveries")
    if not 1 <= len(deliveries) <= 20:
        raise ContractError("run.deliveries: expected 1 through 20 synthetic deliveries")
    delivery_ids: set[str] = set()
    for index, delivery in enumerate(deliveries):
        item = require_object(delivery, f"run.deliveries[{index}]")
        require_keys(item, ("delivery_id", "headers", "raw_body", "expected_state"), f"run.deliveries[{index}]")
        delivery_id = require_string(item["delivery_id"], f"run.deliveries[{index}].delivery_id")
        if not re.fullmatch(r"delivery_demo_[0-9]{3}", delivery_id) or delivery_id in delivery_ids:
            raise ContractError(f"run.deliveries[{index}].delivery_id: invalid or duplicate")
        delivery_ids.add(delivery_id)
        require_object(item["headers"], f"run.deliveries[{index}].headers")
        raw = require_string(item["raw_body"], f"run.deliveries[{index}].raw_body")
        if len(raw.encode("utf-8")) > 32_000:
            raise ContractError(f"run.deliveries[{index}].raw_body: too large")
        state = require_string(item["expected_state"], f"run.deliveries[{index}].expected_state")
        if state not in {
            "ready_for_human",
            "suppressed_duplicate",
            "quarantined_signature",
            "quarantined_replay_window",
            "quarantined_schema_drift",
            "quarantined_header_contract",
        }:
            raise ContractError(f"run.deliveries[{index}].expected_state: unknown state")
    require_object(obj["exchange"], "run.exchange")
    return obj


def sign_webhook(secret: str, timestamp: str, raw_body: str) -> str:
    signed = f"{timestamp}.{raw_body}".encode("utf-8")
    return "v1=" + hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()


class AuditChain:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def add(self, event_type: str, subject_id: str, details: dict[str, Any]) -> None:
        body = {
            "seq": len(self.events) + 1,
            "event_type": event_type,
            "subject_id": subject_id,
            "details": details,
            "prev_hash": self.events[-1]["event_hash"] if self.events else ZERO_HASH,
        }
        body["event_hash"] = sha256_bytes(canonical_bytes(body))
        self.events.append(body)


def verify_audit_chain(events: Any) -> bool:
    if not isinstance(events, list) or not events:
        return False
    previous = ZERO_HASH
    for expected_seq, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            return False
        if set(event) != {"seq", "event_type", "subject_id", "details", "prev_hash", "event_hash"}:
            return False
        if event["seq"] != expected_seq or event["prev_hash"] != previous:
            return False
        body = {key: value for key, value in event.items() if key != "event_hash"}
        if not hmac.compare_digest(event["event_hash"], sha256_bytes(canonical_bytes(body))):
            return False
        previous = event["event_hash"]
    return True


def _header_contract(headers: dict[str, Any]) -> tuple[bool, list[str]]:
    expected = {"x-demo-signature", "x-demo-timestamp", "x-correlation-id", "idempotency-key"}
    if set(headers) != expected:
        return False, ["header_keys"]
    reasons: list[str] = []
    for key in expected:
        if not isinstance(headers[key], str):
            reasons.append(f"{key}_type")
    if reasons:
        return False, reasons
    if not SIGNATURE.fullmatch(headers["x-demo-signature"]):
        reasons.append("signature_shape")
    if not re.fullmatch(r"[0-9]{10}", headers["x-demo-timestamp"]):
        reasons.append("timestamp_shape")
    if not CORRELATION_ID.fullmatch(headers["x-correlation-id"]):
        reasons.append("correlation_id_shape")
    if not IDEMPOTENCY_KEY.fullmatch(headers["idempotency-key"]):
        reasons.append("idempotency_key_shape")
    return not reasons, reasons


def _payload_contract(payload: Any, contract: dict[str, Any]) -> tuple[str | None, list[str]]:
    if not isinstance(payload, dict):
        return "payload_invalid", ["payload_not_object"]
    top_keys = {"event_id", "event_type", "schema_version", "tenant_id", "data"}
    if set(payload) != top_keys:
        return "schema_drift", ["top_level_keys"]
    if payload.get("schema_version") != contract["webhook_contract"]["event_schema_version"]:
        return "schema_drift", ["schema_version"]
    if payload.get("event_type") not in contract["webhook_contract"]["allowed_event_types"]:
        return "schema_drift", ["event_type"]
    data = payload.get("data")
    expected_data = set(contract["webhook_contract"]["required_data_fields"])
    if not isinstance(data, dict) or set(data) != expected_data:
        return "schema_drift", ["data_fields"]

    reasons: list[str] = []
    if not isinstance(payload.get("event_id"), str) or not re.fullmatch(r"evt_demo_[0-9]{3}", payload["event_id"]):
        reasons.append("event_id")
    if not isinstance(payload.get("tenant_id"), str) or not re.fullmatch(r"tenant_demo_[0-9]{2}", payload["tenant_id"]):
        reasons.append("tenant_id")
    if not isinstance(data.get("order_id"), str) or not re.fullmatch(r"ord_demo_[0-9]{4}", data["order_id"]):
        reasons.append("order_id")
    if data.get("status") != "ready":
        reasons.append("status")
    if not isinstance(data.get("amount"), str) or not MONEY.fullmatch(data["amount"]):
        reasons.append("amount")
    return ("payload_invalid" if reasons else None), reasons


def evaluate_delivery(
    delivery: dict[str, Any],
    contract: dict[str, Any],
    seen_idempotency: set[str],
) -> dict[str, Any]:
    delivery_id = delivery["delivery_id"]
    headers = require_object(delivery["headers"], f"{delivery_id}.headers")
    raw_body = delivery["raw_body"]
    base: dict[str, Any] = {
        "delivery_id": delivery_id,
        "event_id": None,
        "correlation_id": headers.get("x-correlation-id") if isinstance(headers.get("x-correlation-id"), str) else None,
        "idempotency_key": headers.get("idempotency-key") if isinstance(headers.get("idempotency-key"), str) else None,
        "raw_body_sha256": sha256_bytes(raw_body.encode("utf-8")),
        "signature_valid": False,
        "timestamp_age_seconds": None,
        "state": "quarantined_header_contract",
        "reason_codes": [],
        "human_eligible": False,
    }
    headers_ok, header_reasons = _header_contract(headers)
    if not headers_ok:
        base["reason_codes"] = header_reasons
        return base

    signature = sign_webhook(contract["synthetic_secret"], headers["x-demo-timestamp"], raw_body)
    if not hmac.compare_digest(signature, headers["x-demo-signature"]):
        base["state"] = "quarantined_signature"
        base["reason_codes"] = ["hmac_mismatch"]
        return base
    base["signature_valid"] = True

    timestamp = int(headers["x-demo-timestamp"])
    age = contract["fixed_now_epoch"] - timestamp
    base["timestamp_age_seconds"] = age
    if age < 0 or age > contract["replay_window_seconds"]:
        base["state"] = "quarantined_replay_window"
        base["reason_codes"] = ["timestamp_in_future" if age < 0 else "timestamp_too_old"]
        return base

    idempotency_key = headers["idempotency-key"]
    if idempotency_key in seen_idempotency:
        base["state"] = "suppressed_duplicate"
        base["reason_codes"] = ["idempotency_key_seen"]
        return base

    try:
        payload = strict_loads(raw_body, f"{delivery_id}.raw_body")
    except ContractError:
        base["state"] = "quarantined_schema_drift"
        base["reason_codes"] = ["invalid_json"]
        return base
    if isinstance(payload, dict) and isinstance(payload.get("event_id"), str):
        base["event_id"] = payload["event_id"]
    category, payload_reasons = _payload_contract(payload, contract)
    if category is not None:
        # Both shape drift and value-contract violations are held at the same
        # visible schema boundary; reason codes retain the exact distinction.
        base["state"] = "quarantined_schema_drift"
        base["reason_codes"] = payload_reasons
        return base

    seen_idempotency.add(idempotency_key)
    base["state"] = "ready_for_human"
    base["human_eligible"] = True
    base["reason_codes"] = ["signature_timestamp_schema_valid"]
    return base


def _request_contract(exchange: dict[str, Any], contract: dict[str, Any]) -> None:
    require_keys(exchange, ("exchange_id", "method", "path", "headers", "body", "attempts", "expected_state"), "run.exchange")
    if not re.fullmatch(r"exchange_demo_[0-9]{3}", require_string(exchange["exchange_id"], "run.exchange.exchange_id")):
        raise ContractError("run.exchange.exchange_id: invalid")
    if exchange["method"] != "POST":
        raise ContractError("run.exchange.method: only POST is allowed in the fixture")
    if exchange["path"] not in contract["allowed_endpoint_paths"]:
        raise ContractError("run.exchange.path: path is not allowlisted")
    headers = require_object(exchange["headers"], "run.exchange.headers")
    require_keys(headers, ("content-type", "x-correlation-id", "idempotency-key"), "run.exchange.headers")
    if headers["content-type"] != "application/json":
        raise ContractError("run.exchange.headers.content-type: application/json required")
    if not isinstance(headers["x-correlation-id"], str) or not CORRELATION_ID.fullmatch(headers["x-correlation-id"]):
        raise ContractError("run.exchange.headers.x-correlation-id: invalid")
    if not isinstance(headers["idempotency-key"], str) or not IDEMPOTENCY_KEY.fullmatch(headers["idempotency-key"]):
        raise ContractError("run.exchange.headers.idempotency-key: invalid")
    body = require_object(exchange["body"], "run.exchange.body")
    require_keys(body, ("operation_id", "tenant_id", "resource_id", "desired_state"), "run.exchange.body")
    if not re.fullmatch(r"op_demo_[0-9]{4}", require_string(body["operation_id"], "run.exchange.body.operation_id")):
        raise ContractError("run.exchange.body.operation_id: invalid")
    if not re.fullmatch(r"tenant_demo_[0-9]{2}", require_string(body["tenant_id"], "run.exchange.body.tenant_id")):
        raise ContractError("run.exchange.body.tenant_id: invalid")
    if not re.fullmatch(r"res_demo_[0-9]{4}", require_string(body["resource_id"], "run.exchange.body.resource_id")):
        raise ContractError("run.exchange.body.resource_id: invalid")
    if body["desired_state"] != "active":
        raise ContractError("run.exchange.body.desired_state: exact demo value required")
    expected_state = require_string(exchange["expected_state"], "run.exchange.expected_state")
    if expected_state not in {
        "recovered_ready_for_human",
        "retry_scheduled",
        "exhausted_to_human",
        "failed_contract",
    }:
        raise ContractError("run.exchange.expected_state: unknown state")


def evaluate_exchange(exchange: dict[str, Any], contract: dict[str, Any], audit: AuditChain) -> dict[str, Any]:
    _request_contract(exchange, contract)
    attempts = require_list(exchange["attempts"], "run.exchange.attempts")
    if not attempts or len(attempts) > contract["retry_policy"]["max_retries"] + 1:
        raise ContractError("run.exchange.attempts: outside bounded attempt count")

    correlation = exchange["headers"]["x-correlation-id"]
    operation = exchange["body"]["operation_id"]
    schedule: list[int] = []
    state = "failed_contract"
    reason_codes: list[str] = []
    final_status: int | None = None
    attempt_views: list[dict[str, Any]] = []

    for expected_attempt, raw_attempt in enumerate(attempts, start=1):
        attempt = require_object(raw_attempt, f"run.exchange.attempts[{expected_attempt - 1}]")
        require_keys(attempt, ("attempt", "status", "headers", "body"), f"run.exchange.attempts[{expected_attempt - 1}]")
        if require_int(attempt["attempt"], f"run.exchange.attempts[{expected_attempt - 1}].attempt") != expected_attempt:
            raise ContractError("run.exchange.attempts: attempts must be consecutive from one")
        status = require_int(attempt["status"], f"run.exchange.attempts[{expected_attempt - 1}].status", minimum=100, maximum=599)
        headers = require_object(attempt["headers"], f"run.exchange.attempts[{expected_attempt - 1}].headers")
        body = require_object(attempt["body"], f"run.exchange.attempts[{expected_attempt - 1}].body")
        if headers.get("x-correlation-id") != correlation:
            if expected_attempt != len(attempts):
                raise ContractError("run.exchange.attempts: attempts after a terminal contract failure are forbidden")
            state = "failed_contract"
            reason_codes = ["correlation_echo_mismatch"]
            final_status = status
            attempt_views.append({"attempt": expected_attempt, "status": status, "outcome": "contract_failed"})
            audit.add("api_attempt_contract_failed", exchange["exchange_id"], {"attempt": expected_attempt, "reason": reason_codes[0]})
            break

        if status == 429:
            require_keys(headers, ("retry-after", "x-correlation-id"), f"run.exchange.attempts[{expected_attempt - 1}].headers")
            require_keys(body, ("error",), f"run.exchange.attempts[{expected_attempt - 1}].body")
            error = require_object(body["error"], f"run.exchange.attempts[{expected_attempt - 1}].body.error")
            require_keys(error, ("code", "message"), f"run.exchange.attempts[{expected_attempt - 1}].body.error")
            if error["code"] != "synthetic_rate_limited":
                raise ContractError("run.exchange.attempts: unexpected synthetic error code")
            require_string(error["message"], f"run.exchange.attempts[{expected_attempt - 1}].body.error.message")
            retry_after_text = headers["retry-after"]
            if not isinstance(retry_after_text, str) or not re.fullmatch(r"[0-9]{1,2}", retry_after_text):
                raise ContractError("run.exchange.attempts: invalid retry-after")
            retry_after = int(retry_after_text)
            if len(schedule) >= contract["retry_policy"]["max_retries"]:
                if expected_attempt != len(attempts):
                    raise ContractError("run.exchange.attempts: attempts after retry-budget exhaustion are forbidden")
                state = "exhausted_to_human"
                reason_codes = ["retry_budget_exhausted"]
                final_status = status
                attempt_views.append({"attempt": expected_attempt, "status": status, "outcome": "budget_exhausted"})
                audit.add("api_retry_budget_exhausted", exchange["exchange_id"], {"attempt": expected_attempt, "status": status})
                break
            policy_delay = min(
                contract["retry_policy"]["base_seconds"] * (2 ** len(schedule)),
                contract["retry_policy"]["cap_seconds"],
            )
            delay = min(max(policy_delay, retry_after), contract["retry_policy"]["cap_seconds"])
            schedule.append(delay)
            state = "retry_scheduled"
            reason_codes = ["synthetic_429"]
            final_status = status
            attempt_views.append({"attempt": expected_attempt, "status": status, "outcome": "virtual_retry_scheduled", "delay_seconds": delay})
            audit.add("api_virtual_retry_scheduled", exchange["exchange_id"], {"attempt": expected_attempt, "delay_seconds": delay, "status": status})
            continue

        if status == 202:
            require_keys(headers, ("x-correlation-id",), f"run.exchange.attempts[{expected_attempt - 1}].headers")
            require_keys(body, ("accepted", "operation_id", "state"), f"run.exchange.attempts[{expected_attempt - 1}].body")
            if body != {"accepted": True, "operation_id": operation, "state": "queued"}:
                if expected_attempt != len(attempts):
                    raise ContractError("run.exchange.attempts: attempts after a terminal contract failure are forbidden")
                state = "failed_contract"
                reason_codes = ["accepted_response_contract"]
                final_status = status
                attempt_views.append({"attempt": expected_attempt, "status": status, "outcome": "contract_failed"})
                audit.add("api_attempt_contract_failed", exchange["exchange_id"], {"attempt": expected_attempt, "reason": reason_codes[0]})
                break
            if expected_attempt != len(attempts):
                raise ContractError("run.exchange.attempts: terminal 202 must be the final supplied attempt")
            state = "recovered_ready_for_human"
            reason_codes = ["accepted_after_virtual_retry" if schedule else "accepted_first_attempt"]
            final_status = status
            attempt_views.append({"attempt": expected_attempt, "status": status, "outcome": "response_contract_passed"})
            audit.add("api_response_contract_passed", exchange["exchange_id"], {"attempt": expected_attempt, "status": status})
            break

        state = "failed_contract"
        if expected_attempt != len(attempts):
            raise ContractError("run.exchange.attempts: attempts after an unexpected terminal response are forbidden")
        reason_codes = ["unexpected_status"]
        final_status = status
        attempt_views.append({"attempt": expected_attempt, "status": status, "outcome": "contract_failed"})
        audit.add("api_attempt_contract_failed", exchange["exchange_id"], {"attempt": expected_attempt, "reason": reason_codes[0]})
        break

    result = {
        "exchange_id": exchange["exchange_id"],
        "method": exchange["method"],
        "path": exchange["path"],
        "correlation_id": correlation,
        "idempotency_key": exchange["headers"]["idempotency-key"],
        "request_body_sha256": sha256_bytes(canonical_bytes(exchange["body"])),
        "attempts": attempt_views,
        "retry_schedule_seconds": schedule,
        "virtual_delay_total_seconds": sum(schedule),
        "sleep_calls": 0,
        "network_calls": 0,
        "final_status": final_status,
        "state": state,
        "reason_codes": reason_codes,
        "human_eligible": state == "recovered_ready_for_human",
    }
    if result["state"] != exchange["expected_state"]:
        raise ContractError(
            f"run.exchange.expected_state: declared {exchange['expected_state']!r} but evaluated {result['state']!r}"
        )
    return result


def _receipt_digest_body(report: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in report.items() if key != "receipt_digest"}


def evaluate(
    contract_value: Any,
    run_value: Any,
    *,
    source_digests: dict[str, str] | None = None,
) -> dict[str, Any]:
    contract = validate_contract(deepcopy(contract_value))
    run = validate_run_fixture(deepcopy(run_value))
    if source_digests is None:
        source_digests = {
            "contract_sha256": sha256_bytes(canonical_bytes(contract)),
            "run_sha256": sha256_bytes(canonical_bytes(run)),
        }
    if set(source_digests) != {"contract_sha256", "run_sha256"}:
        raise ContractError("source_digests: exact digest keys required")

    audit = AuditChain()
    seen_idempotency: set[str] = set()
    deliveries: list[dict[str, Any]] = []
    for delivery in run["deliveries"]:
        result = evaluate_delivery(delivery, contract, seen_idempotency)
        if result["state"] != delivery["expected_state"]:
            raise ContractError(
                f"{delivery['delivery_id']}.expected_state: declared {delivery['expected_state']!r} "
                f"but evaluated {result['state']!r}"
            )
        deliveries.append(result)
        audit.add(
            "webhook_delivery_evaluated",
            result["delivery_id"],
            {
                "state": result["state"],
                "reason_codes": result["reason_codes"],
                "correlation_id": result["correlation_id"],
            },
        )

    exchange = evaluate_exchange(run["exchange"], contract, audit)
    promotion_material = {
        "candidate_id": run["exchange"]["body"]["operation_id"],
        "exchange_state": exchange["state"],
        "exchange_request_sha256": exchange["request_body_sha256"],
        "ready_delivery_ids": sorted(item["delivery_id"] for item in deliveries if item["human_eligible"]),
    }
    confirm_token = "review_" + sha256_bytes(canonical_bytes(promotion_material))[:16]
    promotion_gate = {
        "candidate_id": promotion_material["candidate_id"],
        "eligible": exchange["human_eligible"],
        "state": "awaiting_human" if exchange["human_eligible"] else "blocked",
        "confirm_token": confirm_token,
        "required_acknowledgement": ACKNOWLEDGEMENT,
        "acknowledged": False,
        "production_write": False,
    }
    audit.add(
        "promotion_gate_evaluated",
        promotion_gate["candidate_id"],
        {"eligible": promotion_gate["eligible"], "state": promotion_gate["state"]},
    )

    counts: dict[str, int] = {}
    for result in deliveries:
        counts[result["state"]] = counts.get(result["state"], 0) + 1
    report: dict[str, Any] = {
        "schema_version": 1,
        "lab_id": contract["lab_id"],
        "synthetic": True,
        "personal_project": True,
        "production_claim": False,
        "fixed_now_epoch": contract["fixed_now_epoch"],
        "source_digests": source_digests,
        "webhook_summary": {"total": len(deliveries), "states": dict(sorted(counts.items()))},
        "deliveries": deliveries,
        "exchange": exchange,
        "promotion_gate": promotion_gate,
        "audit": {"events": audit.events, "chain_head": audit.events[-1]["event_hash"]},
    }
    report["receipt_digest"] = sha256_bytes(canonical_bytes(_receipt_digest_body(report)))
    return report


def evaluate_files(contract_path: Path, run_path: Path) -> dict[str, Any]:
    contract, contract_raw = load_json_file(contract_path, "contract")
    run, run_raw = load_json_file(run_path, "run")
    return evaluate(
        contract,
        run,
        source_digests={
            "contract_sha256": sha256_bytes(contract_raw),
            "run_sha256": sha256_bytes(run_raw),
        },
    )


def verify_receipt(receipt: Any) -> bool:
    if not isinstance(receipt, dict) or not isinstance(receipt.get("receipt_digest"), str):
        return False
    if not hmac.compare_digest(receipt["receipt_digest"], sha256_bytes(canonical_bytes(_receipt_digest_body(receipt)))):
        return False
    audit = receipt.get("audit")
    if not isinstance(audit, dict) or set(audit) != {"events", "chain_head"}:
        return False
    if not verify_audit_chain(audit["events"]):
        return False
    return audit["chain_head"] == audit["events"][-1]["event_hash"]


def promote_simulated(report: dict[str, Any], confirm_token: str, acknowledgement: str) -> dict[str, Any]:
    if not verify_receipt(report):
        raise ContractError("promotion: base receipt failed verification")
    gate = report.get("promotion_gate")
    if not isinstance(gate, dict) or gate.get("eligible") is not True or gate.get("state") != "awaiting_human":
        raise ContractError("promotion: candidate is not eligible for human promotion")
    if not hmac.compare_digest(require_string(confirm_token, "promotion.confirm_token"), gate["confirm_token"]):
        raise ContractError("promotion: exact review token required")
    if acknowledgement != ACKNOWLEDGEMENT:
        raise ContractError("promotion: exact personal-project acknowledgement required")

    promoted = deepcopy(report)
    promoted["promotion_gate"]["state"] = "simulated_promoted"
    promoted["promotion_gate"]["acknowledged"] = True
    promoted["promotion_gate"]["production_write"] = False
    chain = AuditChain()
    chain.events = deepcopy(promoted["audit"]["events"])
    chain.add(
        "human_simulated_promotion_recorded",
        promoted["promotion_gate"]["candidate_id"],
        {"acknowledgement": ACKNOWLEDGEMENT, "production_write": False},
    )
    promoted["audit"] = {"events": chain.events, "chain_head": chain.events[-1]["event_hash"]}
    promoted["receipt_digest"] = sha256_bytes(canonical_bytes(_receipt_digest_body(promoted)))
    return promoted
