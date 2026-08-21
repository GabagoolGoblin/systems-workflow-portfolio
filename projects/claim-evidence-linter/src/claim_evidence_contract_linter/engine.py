"""Deterministic policy engine and hash-bound audit report construction."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .canonical import canonical_json_bytes, sha256_hex, with_report_digest
from .errors import AuditMismatch
from .validation import validate_contract, validate_cross_references, validate_evidence

ENGINE_VERSION = "1.0.0"
DECISION_MODEL = "deterministic-claim-contract-v1"
REPORT_SCHEMA_VERSION = "1.0"


def _term_present(text: str, term: str) -> bool:
    escaped = re.escape(term).replace(r"\ ", r"\s+")
    return re.search(rf"(?<!\w){escaped}(?!\w)", text.casefold()) is not None


def _effective_stance(claim: dict[str, Any], assertion: dict[str, Any]) -> str:
    if assertion["fact_id"] != claim["fact_id"]:
        return "irrelevant"
    return assertion["stance"]


def evaluate_claims(
    contract_value: Any,
    evidence_value: Any,
) -> list[dict[str, Any]]:
    """Validate inputs and return deterministic, ordered claim decisions."""

    contract = validate_contract(contract_value)
    evidence = validate_evidence(evidence_value)
    validate_cross_references(contract, evidence)

    sources = {source["source_id"]: source for source in evidence["sources"]}
    assertions = {
        source["source_id"]: {
            assertion["assertion_id"]: assertion
            for assertion in source["assertions"]
        }
        for source in evidence["sources"]
    }
    results: list[dict[str, Any]] = []
    for claim in contract["claims"]:
        evaluated_citations: list[dict[str, Any]] = []
        stance_sources: dict[str, set[str]] = {
            "supports": set(),
            "contradicts": set(),
            "qualifies": set(),
            "irrelevant": set(),
        }
        for citation in claim["citations"]:
            source = sources[citation["source_id"]]
            assertion = assertions[citation["source_id"]][citation["assertion_id"]]
            effective_stance = _effective_stance(claim, assertion)
            stance_sources[effective_stance].add(source["source_id"])
            source_content_digest = sha256_hex(source["content"].encode("utf-8"))
            binding = {
                "source_id": source["source_id"],
                "source_content_sha256": source_content_digest,
                "assertion": assertion,
                "citation": citation,
            }
            evaluated_citations.append(
                {
                    "source_id": source["source_id"],
                    "assertion_id": assertion["assertion_id"],
                    "start": citation["start"],
                    "end": citation["end"],
                    "quote": citation["quote"],
                    "declared_fact_id": assertion["fact_id"],
                    "claim_fact_match": assertion["fact_id"] == claim["fact_id"],
                    "declared_stance": assertion["stance"],
                    "effective_stance": effective_stance,
                    "source_content_sha256": source_content_digest,
                    "citation_binding_sha256": sha256_hex(canonical_json_bytes(binding)),
                }
            )

        support_count = len(stance_sources["supports"])
        contradiction_count = len(stance_sources["contradicts"])
        qualification_count = len(stance_sources["qualifies"])
        relevant_count = support_count + contradiction_count + qualification_count
        required_sources = contract["policy"]["minimum_distinct_sources"][
            claim["risk_tier"]
        ]
        absolute_terms = [
            term
            for term in contract["policy"]["absolute_terms"]
            if _term_present(claim["text"], term)
        ]

        reason_codes: list[str] = []
        if contradiction_count and not support_count:
            state = "UNSUPPORTED"
            reason_codes.append("DIRECT_CONTRADICTION")
        elif relevant_count == 0:
            state = "UNSUPPORTED"
            reason_codes.append("NO_RELEVANT_EVIDENCE")
        else:
            if support_count and contradiction_count:
                reason_codes.append("CONFLICTING_EVIDENCE")
            if qualification_count:
                reason_codes.append("QUALIFIED_EVIDENCE")
            if support_count < required_sources:
                reason_codes.append("INSUFFICIENT_INDEPENDENT_SUPPORT")
            if absolute_terms and claim["risk_tier"] != "high":
                reason_codes.append("ABSOLUTE_LANGUAGE_REQUIRES_HIGH_RISK")
            if reason_codes:
                state = "NEEDS_REVIEW"
            else:
                state = "SUPPORTED"
                reason_codes.append("SUFFICIENT_UNCONTESTED_SUPPORT")

        results.append(
            {
                "claim_id": claim["claim_id"],
                "text": claim["text"],
                "fact_id": claim["fact_id"],
                "risk_tier": claim["risk_tier"],
                "state": state,
                "reason_codes": reason_codes,
                "policy_observations": {
                    "required_distinct_supporting_sources": required_sources,
                    "distinct_supporting_sources": sorted(stance_sources["supports"]),
                    "distinct_contradicting_sources": sorted(
                        stance_sources["contradicts"]
                    ),
                    "distinct_qualifying_sources": sorted(stance_sources["qualifies"]),
                    "off_topic_sources": sorted(stance_sources["irrelevant"]),
                    "absolute_terms_found": absolute_terms,
                },
                "citations": evaluated_citations,
            }
        )
    return results


def build_report(
    contract_value: Any,
    evidence_value: Any,
    *,
    contract_bytes: bytes,
    evidence_bytes: bytes,
) -> dict[str, Any]:
    contract = validate_contract(contract_value)
    evidence = validate_evidence(evidence_value)
    validate_cross_references(contract, evidence)
    claim_results = evaluate_claims(contract, evidence)
    counts = Counter(result["state"] for result in claim_results)
    source_manifest = [
        {
            "source_id": source["source_id"],
            "content_sha256": sha256_hex(source["content"].encode("utf-8")),
            "source_object_sha256": sha256_hex(canonical_json_bytes(source)),
        }
        for source in evidence["sources"]
    ]
    report_without_digest = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_type": "claim_evidence_contract_lint",
        "engine": {
            "name": "claim-evidence-contract-linter",
            "version": ENGINE_VERSION,
            "decision_model": DECISION_MODEL,
        },
        "execution_guarantees": {
            "deterministic": True,
            "local_only": True,
            "network_access": False,
            "model_adjudication": False,
        },
        "contract_id": contract["contract_id"],
        "evidence_set_id": evidence["evidence_set_id"],
        "input_binding": {
            "algorithm": "sha256",
            "scope": "exact-input-file-bytes",
            "contract_sha256": sha256_hex(contract_bytes),
            "evidence_sha256": sha256_hex(evidence_bytes),
            "policy_canonical_sha256": sha256_hex(
                canonical_json_bytes(contract["policy"])
            ),
            "sources": source_manifest,
        },
        "summary": {
            "claim_count": len(claim_results),
            "supported": counts["SUPPORTED"],
            "unsupported": counts["UNSUPPORTED"],
            "needs_review": counts["NEEDS_REVIEW"],
            "finding_count": counts["UNSUPPORTED"] + counts["NEEDS_REVIEW"],
            "all_supported": counts["UNSUPPORTED"] == 0
            and counts["NEEDS_REVIEW"] == 0,
        },
        "claims": claim_results,
    }
    return with_report_digest(report_without_digest)


def verify_report(
    report_value: Any,
    contract_value: Any,
    evidence_value: Any,
    *,
    contract_bytes: bytes,
    evidence_bytes: bytes,
) -> dict[str, Any]:
    if type(report_value) is not dict:
        raise AuditMismatch("report must be a JSON object")
    digest = report_value.get("report_digest")
    if type(digest) is not dict:
        raise AuditMismatch("report_digest is missing or is not an object")
    if set(digest) != {"algorithm", "canonicalization", "value"}:
        raise AuditMismatch("report_digest has an invalid shape")
    if digest.get("algorithm") != "sha256":
        raise AuditMismatch("report_digest algorithm must be sha256")
    if digest.get("canonicalization") != "json-sort-keys-compact-utf8-v1":
        raise AuditMismatch("report_digest canonicalization is not supported")
    supplied_value = digest.get("value")
    if type(supplied_value) is not str or not re.fullmatch(r"[0-9a-f]{64}", supplied_value):
        raise AuditMismatch("report_digest value must be 64 lowercase hexadecimal characters")
    without_digest = dict(report_value)
    del without_digest["report_digest"]
    calculated_value = sha256_hex(canonical_json_bytes(without_digest))
    if calculated_value != supplied_value:
        raise AuditMismatch("report self-digest does not match its canonical content")

    expected = build_report(
        contract_value,
        evidence_value,
        contract_bytes=contract_bytes,
        evidence_bytes=evidence_bytes,
    )
    if report_value != expected:
        raise AuditMismatch(
            "report does not exactly match the deterministic result for these input bytes"
        )
    return {
        "verified": True,
        "report_sha256": supplied_value,
        "contract_sha256": expected["input_binding"]["contract_sha256"],
        "evidence_sha256": expected["input_binding"]["evidence_sha256"],
    }

