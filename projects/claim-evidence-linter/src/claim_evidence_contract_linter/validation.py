"""Strict, fail-closed schema and cross-reference validation."""

from __future__ import annotations

import re
from typing import Any

from .errors import InputError

SCHEMA_VERSION = "1.0"
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
RISK_TIERS = ("low", "medium", "high")
STANCES = ("supports", "contradicts", "qualifies", "irrelevant")


def _fail(path: str, message: str) -> None:
    raise InputError(f"{path}: {message}")


def _dict(value: Any, path: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(path, "must be an object")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if type(value) is not list:
        _fail(path, "must be an array")
    return value


def _string(
    value: Any,
    path: str,
    *,
    minimum: int = 1,
    maximum: int,
) -> str:
    if type(value) is not str:
        _fail(path, "must be a string")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        _fail(path, "must contain valid Unicode scalar values (no lone surrogates)")
    if not minimum <= len(value) <= maximum:
        _fail(path, f"length must be between {minimum} and {maximum} code points")
    return value


def _integer(value: Any, path: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int:
        _fail(path, "must be an integer (booleans are not accepted)")
    if not minimum <= value <= maximum:
        _fail(path, f"must be between {minimum} and {maximum}")
    return value


def _identifier(value: Any, path: str) -> str:
    result = _string(value, path, maximum=64)
    if not IDENTIFIER.fullmatch(result):
        _fail(path, "must match ^[a-z][a-z0-9_-]{0,63}$")
    return result


def _exact_keys(value: dict[str, Any], path: str, required: set[str]) -> None:
    actual = set(value)
    missing = sorted(required - actual)
    unknown = sorted(actual - required)
    if missing:
        _fail(path, f"missing keys: {', '.join(missing)}")
    if unknown:
        _fail(path, f"unknown keys: {', '.join(unknown)}")


def _unique_ids(items: list[dict[str, Any]], key: str, path: str) -> None:
    seen: set[str] = set()
    for index, item in enumerate(items):
        value = item[key]
        if value in seen:
            _fail(f"{path}[{index}].{key}", f"duplicate identifier: {value}")
        seen.add(value)


def validate_contract(value: Any) -> dict[str, Any]:
    contract = _dict(value, "contract")
    _exact_keys(
        contract,
        "contract",
        {"schema_version", "contract_id", "policy", "claims"},
    )
    if contract["schema_version"] != SCHEMA_VERSION:
        _fail("contract.schema_version", f"must equal {SCHEMA_VERSION!r}")
    _identifier(contract["contract_id"], "contract.contract_id")

    policy = _dict(contract["policy"], "contract.policy")
    _exact_keys(
        policy,
        "contract.policy",
        {"minimum_distinct_sources", "absolute_terms"},
    )
    minimums = _dict(
        policy["minimum_distinct_sources"],
        "contract.policy.minimum_distinct_sources",
    )
    _exact_keys(
        minimums,
        "contract.policy.minimum_distinct_sources",
        set(RISK_TIERS),
    )
    for tier in RISK_TIERS:
        _integer(
            minimums[tier],
            f"contract.policy.minimum_distinct_sources.{tier}",
            minimum=1,
            maximum=10,
        )

    terms = _list(policy["absolute_terms"], "contract.policy.absolute_terms")
    if len(terms) > 50:
        _fail("contract.policy.absolute_terms", "must contain at most 50 terms")
    seen_terms: set[str] = set()
    for index, term_value in enumerate(terms):
        term = _string(
            term_value,
            f"contract.policy.absolute_terms[{index}]",
            maximum=80,
        )
        if term != term.casefold() or term != term.strip():
            _fail(
                f"contract.policy.absolute_terms[{index}]",
                "must be trimmed and case-folded",
            )
        if term in seen_terms:
            _fail(
                f"contract.policy.absolute_terms[{index}]",
                f"duplicate term: {term!r}",
            )
        seen_terms.add(term)

    claims = _list(contract["claims"], "contract.claims")
    if not 1 <= len(claims) <= 500:
        _fail("contract.claims", "must contain between 1 and 500 claims")
    checked_claims: list[dict[str, Any]] = []
    for index, claim_value in enumerate(claims):
        path = f"contract.claims[{index}]"
        claim = _dict(claim_value, path)
        _exact_keys(
            claim,
            path,
            {"claim_id", "text", "fact_id", "risk_tier", "citations"},
        )
        _identifier(claim["claim_id"], f"{path}.claim_id")
        _string(claim["text"], f"{path}.text", maximum=500)
        _identifier(claim["fact_id"], f"{path}.fact_id")
        if claim["risk_tier"] not in RISK_TIERS:
            _fail(f"{path}.risk_tier", f"must be one of {', '.join(RISK_TIERS)}")
        citations = _list(claim["citations"], f"{path}.citations")
        if len(citations) > 20:
            _fail(f"{path}.citations", "must contain at most 20 citations")
        seen_citations: set[tuple[str, str]] = set()
        for citation_index, citation_value in enumerate(citations):
            citation_path = f"{path}.citations[{citation_index}]"
            citation = _dict(citation_value, citation_path)
            _exact_keys(
                citation,
                citation_path,
                {"source_id", "assertion_id", "start", "end", "quote"},
            )
            source_id = _identifier(citation["source_id"], f"{citation_path}.source_id")
            assertion_id = _identifier(
                citation["assertion_id"], f"{citation_path}.assertion_id"
            )
            _integer(citation["start"], f"{citation_path}.start", minimum=0, maximum=1_000_000)
            _integer(citation["end"], f"{citation_path}.end", minimum=1, maximum=1_000_000)
            if citation["end"] <= citation["start"]:
                _fail(f"{citation_path}.end", "must be greater than start")
            _string(citation["quote"], f"{citation_path}.quote", maximum=10_000)
            citation_key = (source_id, assertion_id)
            if citation_key in seen_citations:
                _fail(citation_path, "duplicate source/assertion citation")
            seen_citations.add(citation_key)
        checked_claims.append(claim)
    _unique_ids(checked_claims, "claim_id", "contract.claims")
    return contract


def validate_evidence(value: Any) -> dict[str, Any]:
    evidence = _dict(value, "evidence")
    _exact_keys(
        evidence,
        "evidence",
        {"schema_version", "evidence_set_id", "sources"},
    )
    if evidence["schema_version"] != SCHEMA_VERSION:
        _fail("evidence.schema_version", f"must equal {SCHEMA_VERSION!r}")
    _identifier(evidence["evidence_set_id"], "evidence.evidence_set_id")
    sources = _list(evidence["sources"], "evidence.sources")
    if not 1 <= len(sources) <= 500:
        _fail("evidence.sources", "must contain between 1 and 500 sources")
    checked_sources: list[dict[str, Any]] = []
    for index, source_value in enumerate(sources):
        path = f"evidence.sources[{index}]"
        source = _dict(source_value, path)
        _exact_keys(source, path, {"source_id", "title", "content", "assertions"})
        _identifier(source["source_id"], f"{path}.source_id")
        _string(source["title"], f"{path}.title", maximum=200)
        content = _string(source["content"], f"{path}.content", maximum=100_000)
        assertions = _list(source["assertions"], f"{path}.assertions")
        if not 1 <= len(assertions) <= 500:
            _fail(f"{path}.assertions", "must contain between 1 and 500 assertions")
        checked_assertions: list[dict[str, Any]] = []
        for assertion_index, assertion_value in enumerate(assertions):
            assertion_path = f"{path}.assertions[{assertion_index}]"
            assertion = _dict(assertion_value, assertion_path)
            _exact_keys(
                assertion,
                assertion_path,
                {"assertion_id", "fact_id", "stance", "start", "end", "quote"},
            )
            _identifier(assertion["assertion_id"], f"{assertion_path}.assertion_id")
            _identifier(assertion["fact_id"], f"{assertion_path}.fact_id")
            if assertion["stance"] not in STANCES:
                _fail(
                    f"{assertion_path}.stance",
                    f"must be one of {', '.join(STANCES)}",
                )
            start = _integer(
                assertion["start"],
                f"{assertion_path}.start",
                minimum=0,
                maximum=100_000,
            )
            end = _integer(
                assertion["end"],
                f"{assertion_path}.end",
                minimum=1,
                maximum=100_000,
            )
            if end <= start:
                _fail(f"{assertion_path}.end", "must be greater than start")
            if end > len(content):
                _fail(
                    f"{assertion_path}.end",
                    f"exceeds source content length {len(content)}",
                )
            quote = _string(
                assertion["quote"],
                f"{assertion_path}.quote",
                maximum=10_000,
            )
            if content[start:end] != quote:
                _fail(
                    assertion_path,
                    "quote does not exactly match content[start:end] using "
                    "Unicode code-point offsets",
                )
            checked_assertions.append(assertion)
        _unique_ids(checked_assertions, "assertion_id", f"{path}.assertions")
        checked_sources.append(source)
    _unique_ids(checked_sources, "source_id", "evidence.sources")
    return evidence


def validate_cross_references(
    contract: dict[str, Any], evidence: dict[str, Any]
) -> None:
    sources = {source["source_id"]: source for source in evidence["sources"]}
    assertions = {
        source["source_id"]: {
            assertion["assertion_id"]: assertion
            for assertion in source["assertions"]
        }
        for source in evidence["sources"]
    }
    for claim_index, claim in enumerate(contract["claims"]):
        for citation_index, citation in enumerate(claim["citations"]):
            path = f"contract.claims[{claim_index}].citations[{citation_index}]"
            source_id = citation["source_id"]
            assertion_id = citation["assertion_id"]
            if source_id not in sources:
                _fail(f"{path}.source_id", f"unknown source: {source_id}")
            if assertion_id not in assertions[source_id]:
                _fail(
                    f"{path}.assertion_id",
                    f"unknown assertion {assertion_id!r} in source {source_id!r}",
                )
            assertion = assertions[source_id][assertion_id]
            for key in ("start", "end", "quote"):
                if citation[key] != assertion[key]:
                    _fail(
                        f"{path}.{key}",
                        f"must exactly match referenced assertion {key}",
                    )
