"""Manifest validation and deterministic suite execution."""

from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath
from typing import Any

from . import __version__
from .io_utils import canonical_json_bytes, read_regular_file, sha256, strict_json_loads
from .model import ContractInputError
from .parser import MAX_HTML_BYTES, parse_html
from .rules import RULES, RULE_DESCRIPTIONS, run_rules

MAX_MANIFEST_BYTES = 262_144
MAX_CASES = 100
MAX_VIOLATIONS_PER_CASE = 1_000
MAX_VIOLATIONS_PER_SUITE = 2_000
IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
NODE_PATH = re.compile(r"^html\[1\](?:/[a-z0-9]+\[[1-9][0-9]*\])*$")


def _exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        details: list[str] = []
        if missing:
            details.append(f"missing={missing}")
        if unknown:
            details.append(f"unknown={unknown}")
        raise ContractInputError(f"{label} keys are invalid ({'; '.join(details)})")


def _text(value: Any, label: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ContractInputError(
            f"{label} must be a non-blank string of at most {maximum} characters"
        )
    return value


def _safe_relative_html(value: Any, label: str) -> str:
    text = _text(value, label, maximum=240)
    candidate = PurePosixPath(text)
    if (
        candidate.is_absolute()
        or any(part in {"", ".", ".."} for part in candidate.parts)
        or candidate.suffix.lower() != ".html"
        or "\\" in text
    ):
        raise ContractInputError(f"{label} must be a normalized relative .html path")
    return candidate.as_posix()


def load_manifest(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = read_regular_file(path, max_bytes=MAX_MANIFEST_BYTES)
    manifest = strict_json_loads(raw, label="manifest")
    if not isinstance(manifest, dict):
        raise ContractInputError("manifest root must be an object")
    _exact_keys(
        manifest,
        {"cases", "description", "rules", "schema_version", "suite_id"},
        "manifest",
    )
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ContractInputError("manifest schema_version must be integer 1")
    suite_id = _text(manifest["suite_id"], "suite_id", maximum=80)
    if not IDENTIFIER.fullmatch(suite_id):
        raise ContractInputError("suite_id must be lowercase kebab-case")
    _text(manifest["description"], "description", maximum=500)

    rules = manifest["rules"]
    if not isinstance(rules, list) or not rules or not all(
        isinstance(item, str) for item in rules
    ):
        raise ContractInputError("rules must be a non-empty string array")
    if len(set(rules)) != len(rules):
        raise ContractInputError("rules must not contain duplicates")
    unknown_rules = sorted(set(rules) - set(RULES))
    if unknown_rules:
        raise ContractInputError(f"unknown rule ids: {unknown_rules}")

    cases = manifest["cases"]
    if (
        not isinstance(cases, list)
        or not cases
        or len(cases) > MAX_CASES
        or not all(isinstance(item, dict) for item in cases)
    ):
        raise ContractInputError(f"cases must contain 1..{MAX_CASES} objects")
    case_ids: set[str] = set()
    case_paths: set[str] = set()
    for index, case in enumerate(cases):
        label = f"cases[{index}]"
        _exact_keys(case, {"expected_violations", "html", "id"}, label)
        case_id = _text(case["id"], f"{label}.id", maximum=80)
        if not IDENTIFIER.fullmatch(case_id):
            raise ContractInputError(f"{label}.id must be lowercase kebab-case")
        if case_id in case_ids:
            raise ContractInputError(f"duplicate case id: {case_id}")
        case_ids.add(case_id)
        html_path = _safe_relative_html(case["html"], f"{label}.html")
        if html_path in case_paths:
            raise ContractInputError(f"duplicate fixture path: {html_path}")
        case_paths.add(html_path)
        expected = case["expected_violations"]
        if not isinstance(expected, list) or not all(
            isinstance(item, dict) for item in expected
        ):
            raise ContractInputError(f"{label}.expected_violations must be an array")
        fingerprints: set[tuple[str, str]] = set()
        for violation_index, violation in enumerate(expected):
            violation_label = f"{label}.expected_violations[{violation_index}]"
            _exact_keys(violation, {"node", "rule_id"}, violation_label)
            rule_id = _text(
                violation["rule_id"], f"{violation_label}.rule_id", maximum=80
            )
            node = _text(violation["node"], f"{violation_label}.node", maximum=500)
            if rule_id not in rules:
                raise ContractInputError(
                    f"{violation_label}.rule_id is not enabled by this manifest"
                )
            if not NODE_PATH.fullmatch(node):
                raise ContractInputError(f"{violation_label}.node is not a stable node path")
            fingerprint = (rule_id, node)
            if fingerprint in fingerprints:
                raise ContractInputError(f"duplicate expected violation: {fingerprint}")
            fingerprints.add(fingerprint)
    return manifest, raw


def _fixture_path(manifest_path: Path, relative: str) -> Path:
    fixture_root = manifest_path.parent.resolve()
    candidate = fixture_root / relative
    if candidate.is_symlink():
        raise ContractInputError(f"fixture must not be a symlink: {relative}")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(fixture_root)
    except ValueError as exc:
        raise ContractInputError(f"fixture escapes manifest directory: {relative}") from exc
    return candidate


def execute_suite(manifest_path: Path) -> tuple[dict[str, Any], list[tuple[Path, bytes]]]:
    """Validate all inputs, then return a deterministic report and bound input bytes."""

    manifest_path = manifest_path.absolute()
    if manifest_path.is_symlink():
        raise ContractInputError("manifest must not be a symlink")
    manifest, manifest_raw = load_manifest(manifest_path)
    selected_rules: list[str] = manifest["rules"]
    bound_inputs: list[tuple[Path, bytes]] = [(manifest_path, manifest_raw)]
    prepared: list[tuple[dict[str, Any], Path, bytes]] = []
    for case in manifest["cases"]:
        path = _fixture_path(manifest_path, case["html"])
        raw = read_regular_file(path, max_bytes=MAX_HTML_BYTES)
        prepared.append((case, path, raw))
        bound_inputs.append((path, raw))

    input_entries = [
        {"path": "manifest.json", "sha256": sha256(manifest_raw)}
    ] + [
        {"path": case["html"], "sha256": sha256(raw)}
        for case, _path, raw in prepared
    ]
    bundle_sha256 = sha256(canonical_json_bytes(input_entries))

    case_reports: list[dict[str, Any]] = []
    actual_total = 0
    expected_total = 0
    matched_total = 0
    for case, _path, raw in prepared:
        document = parse_html(raw)
        actual_violations = run_rules(document, selected_rules)
        if len(actual_violations) > MAX_VIOLATIONS_PER_CASE:
            raise ContractInputError(
                f"case {case['id']} exceeds the {MAX_VIOLATIONS_PER_CASE}-violation limit"
            )
        actual = [item.fingerprint() for item in actual_violations]
        expected = sorted(
            case["expected_violations"], key=lambda item: (item["rule_id"], item["node"])
        )
        actual_fingerprints = sorted(
            actual, key=lambda item: (item["rule_id"], item["node"])
        )
        actual_pairs = [
            (item["rule_id"], item["node"]) for item in actual_fingerprints
        ]
        if len(actual_pairs) != len(set(actual_pairs)):
            raise ContractInputError(
                f"rule engine emitted duplicate fingerprints for case {case['id']}"
            )
        expected_keys = {(item["rule_id"], item["node"]) for item in expected}
        actual_keys = {(item["rule_id"], item["node"]) for item in actual_fingerprints}
        missing = [
            item
            for item in expected
            if (item["rule_id"], item["node"]) not in actual_keys
        ]
        unexpected = [
            item
            for item in actual_fingerprints
            if (item["rule_id"], item["node"]) not in expected_keys
        ]
        matched = not missing and not unexpected
        actual_total += len(actual_fingerprints)
        if actual_total > MAX_VIOLATIONS_PER_SUITE:
            raise ContractInputError(
                f"suite exceeds the {MAX_VIOLATIONS_PER_SUITE}-violation limit"
            )
        expected_total += len(expected)
        matched_total += int(matched)
        case_reports.append(
            {
                "actual_violations": [item.as_dict() for item in actual_violations],
                "expected_violations": expected,
                "fixture_sha256": sha256(raw),
                "html": case["html"],
                "id": case["id"],
                "missing_expected": missing,
                "status": "matched" if matched else "regression",
                "unexpected": unexpected,
            }
        )

    case_count = len(case_reports)
    report: dict[str, Any] = {
        "cases": case_reports,
        "input_binding": {
            "bundle_sha256": bundle_sha256,
            "files": input_entries,
        },
        "rules": [
            {"description": RULE_DESCRIPTIONS[rule_id], "id": rule_id}
            for rule_id in selected_rules
        ],
        "schema_version": 1,
        "scope_notice": (
            "Deterministic fixture contracts only; not full WCAG conformance, "
            "legal certification, browser testing, or assistive-technology certification."
        ),
        "suite": {
            "description": manifest["description"],
            "id": manifest["suite_id"],
            "status": "matched" if matched_total == case_count else "regression",
        },
        "summary": {
            "actual_violations": actual_total,
            "cases": case_count,
            "cases_matched": matched_total,
            "cases_regressed": case_count - matched_total,
            "expected_violations": expected_total,
        },
        "tool": {"name": "interface-contract-harness", "version": __version__},
    }
    return report, bound_inputs


def common_project_base(manifest_path: Path, output_dir: Path) -> Path:
    manifest_path = manifest_path.resolve()
    output_dir = output_dir.resolve()
    base = Path(os.path.commonpath([manifest_path.parent, output_dir])).resolve()
    if base == Path(base.anchor):
        raise ContractInputError("manifest and output must share a bounded project directory")
    return base
