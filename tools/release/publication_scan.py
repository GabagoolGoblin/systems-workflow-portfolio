#!/usr/bin/env python3
"""Fail closed on private material, unsafe paths, placeholders, and release drift."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath


TEXT_SUFFIXES = {
    "",
    ".css",
    ".csv",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
PLACEHOLDER = re.compile(
    "(?i)(?:"
    + "OWNER" + "_CONTACT|OWNER" + "_GITHUB_HANDLE|CHOOSE[_ -]?" + "LICENSE|"
    + "T" + "BD|TO" + "[- ]?DO|example\\.(?:com|org|net))"
)
SHA256_RE = re.compile(r"[0-9a-f]{64}")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
GITHUB_HANDLE_RE = re.compile(
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?"
)

DECISION_KEYS = {
    "schema", "decision_status", "repository_visibility",
    "repository_topology", "repository_name", "repository_topology_approved",
    "license_spdx", "license_scope", "license_approved",
    "owner_provenance_approved", "public_git_identity_approved",
    "public_git_identity", "codeowners_approved", "reporting_channels_approved",
    "private_reporting_channels", "hero_assets_approved", "hero_assets",
    "ci_dependencies_approved", "ci_review", "all12_artifact_review", "projects",
    "clean_history_clone_gate_required", "clean_history_clone_receipt_sha256",
    "clean_history_clone_receipt_approved", "company_context_approved",
    "open_food_facts_distribution_approved",
    "product_capture_contact_metadata_approved", "restrictive_projects_resolved",
    "hitl_asset_provenance_approved", "remote_creation_approved", "push_approved",
    "release_approved", "pages_approved", "publication_approved",
}
IDENTITY_KEYS = {"author_name", "author_email", "github_handle", "approved"}
REPORTING_CHANNEL_KEYS = {"security", "conduct"}
PROJECT_DECISION_KEYS = {"include", "provenance_approved", "provenance_sha256"}
HERO_DECISION_KEYS = {"sha256", "approved", "native_visual_review_approved"}
CI_REVIEW_KEYS = {
    "workflow_sha256", "requirements_ci_lock_sha256", "action_pins", "approved",
}
ALL12_ARTIFACT_REVIEW_KEYS = {"artifacts", "approved"}
ALL12_ARTIFACT_PATHS = {
    "projects/public-product-validation/DATA_LICENSE.md",
    "projects/public-product-validation/data/DATA_REDACTION_RECEIPT.json",
    "projects/public-product-validation/data/open_food_facts_snapshot.json",
    "third_party/licenses/DbCL-1.0.txt",
    "third_party/licenses/ODbL-1.0.txt",
}
PROJECT_RELEASE_DIRS = {
    "ai-release-gate": "ai-evaluation-release-gates",
    "api-contracts": "api-integration-contracts",
    "claim-linter": "claim-evidence-linter",
    "hitl-controls": "human-in-the-loop-control",
    "launch-lab": "customer-launch-readiness",
    "lifecycle": "catalog-lifecycle",
    "migration-validator": "catalog-migration-validator",
    "price-controls": "bulk-price-control",
    "product-validation": "public-product-validation",
    "readiness": "implementation-readiness",
    "support-workbench": "support-triage-workbench",
    "wcag-harness": "interface-contract-harness",
}
WAVE1_PROJECT_IDS = {
    "ai-release-gate", "api-contracts", "claim-linter", "lifecycle",
    "migration-validator", "price-controls", "wcag-harness",
}
ALL12_PROJECT_IDS = set(PROJECT_RELEASE_DIRS)
HERO_BY_PROJECT = {
    "ai-release-gate": "assets/project-previews/ai-evaluation-release-gates.png",
    "api-contracts": "assets/project-previews/api-integration-contracts.png",
    "launch-lab": "assets/project-previews/customer-launch-readiness.png",
    "lifecycle": "assets/project-previews/catalog-lifecycle.png",
    "product-validation": "assets/project-previews/public-product-validation.png",
    "readiness": "assets/project-previews/implementation-readiness.png",
    "wcag-harness": "assets/project-previews/interface-contract-harness.png",
}
EXPECTED_ACTION_PINS = {
    "actions/checkout@v6": "d23441a48e516b6c34aea4fa41551a30e30af803",
    "actions/setup-python@v6": "ece7cb06caefa5fff74198d8649806c4678c61a1",
}
OWNER_GATE_PATHS = {"LICENSE", "release-decisions.json"}
EXPECTED_CONTENT_SCAN_EXCLUSIONS = {
    "wave1": {
        "projects/ai-evaluation-release-gates/scripts/security_privacy_scan.py",
        "projects/api-integration-contracts/scripts/security_privacy_scan.py",
        "projects/claim-evidence-linter/tools/audit_project.py",
        "release-policy.json", "tools/release/publication_scan.py",
    },
    "all12": {
        "projects/ai-evaluation-release-gates/scripts/security_privacy_scan.py",
        "projects/api-integration-contracts/scripts/security_privacy_scan.py",
        "projects/claim-evidence-linter/tools/audit_project.py",
        "projects/customer-launch-readiness/scripts/security_privacy_scan.py",
        "projects/implementation-readiness/scripts/security_privacy_scan.py",
        "projects/support-triage-workbench/tools/publication_scan.py",
        "release-policy.json", "tools/release/publication_scan.py",
    },
}
BUILTIN_FORBIDDEN = {
    "absolute home path": re.compile(
        r"(?:/home/[A-Za-z0-9._-]+/|/Users/[A-Za-z0-9._-]+/|"
        r"[A-Za-z]:\\Users\\[^\\\s]+\\)", re.IGNORECASE,
    ),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "permissive license grant": re.compile(
        re.escape("Permis" + "sion is hereby " + "gran" + "ted"), re.IGNORECASE
    ),
}
POLICY_KEYS = {
    "schema", "mode", "selected_projects", "decision_project_ids",
    "owner_gate_paths", "required_paths", "required_project_files",
    "forbidden_path_parts", "forbidden_file_names", "max_regular_file_bytes",
    "forbidden_content_regex", "content_scan_exclusions", "runtime_extensions",
    "allowed_external_link_domains", "link_scan_excluded_prefixes",
    "manifest_excludes",
}


def iter_paths(root: Path):
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        relative_current = current_path.relative_to(root)
        if relative_current == Path("."):
            directories[:] = [name for name in directories if name != ".git"]
        for name in sorted(directories):
            yield current_path / name
        for name in sorted(files):
            yield current_path / name


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load_json(path: Path) -> object:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result

    return json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates
    )


def safe_relative(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and bool(path.parts)
        and all(part not in {"", ".", ".."} for part in path.parts)
        and path.as_posix() == value
    )


def expected_project_ids(mode: object) -> set[str]:
    return WAVE1_PROJECT_IDS if mode == "wave1" else ALL12_PROJECT_IDS


def effective_codeowners(path: Path, github_handle: str) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return False
    active = []
    for source_line in lines:
        line = source_line.split("#", 1)[0].strip()
        if not line:
            continue
        fields = line.split()
        expected_owner = f"@{github_handle}".casefold()
        if len(fields) < 2 or any(
            owner.casefold() != expected_owner for owner in fields[1:]
        ):
            return False
        active.append(fields)
    return bool(active)


def effective_license(path: Path, license_spdx: object) -> bool:
    if not path.is_file() or path.is_symlink() or path.stat().st_size < 200:
        return False
    try:
        value = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    if license_spdx != "NOASSERTION":
        return False
    normalized = " ".join(value.split())
    required = (
        "All rights reserved",
        "No additional license or reuse permission is granted",
        "GitHub's Terms of Service",
        "including AI/ML training as provided there",
        "viewing, displaying, reproducing, and forking",
        "does not prohibit or narrow those platform rights",
        "applicable law",
        "third-party material",
        "THIRD_PARTY_NOTICES.md",
    )
    permissive_grant = "Permis" + "sion is hereby " + "gran" + "ted"
    return all(marker in normalized for marker in required) and permissive_grant not in normalized


def validate_identity_and_channels(
    data: dict[str, object], root: Path, approved_emails: set[str]
) -> list[str]:
    errors: list[str] = []
    identity = data.get("public_git_identity")
    github_handle: str | None = None
    if not isinstance(identity, dict):
        errors.append("public_git_identity is missing")
    else:
        if set(identity) != IDENTITY_KEYS:
            errors.append("public_git_identity contains missing or unknown keys")
        author_name = identity.get("author_name")
        author_email = identity.get("author_email")
        handle = identity.get("github_handle")
        if (
            not isinstance(author_name, str) or not author_name.strip()
            or author_name != author_name.strip()
            or any(ord(character) < 32 for character in author_name)
        ):
            errors.append("public Git author name is invalid")
        if (
            not isinstance(author_email, str)
            or not EMAIL_RE.fullmatch(author_email)
        ):
            errors.append("public Git author email is invalid")
        else:
            approved_emails.add(author_email.casefold())
        if (
            not isinstance(handle, str) or not GITHUB_HANDLE_RE.fullmatch(handle)
        ):
            errors.append("GitHub handle is invalid")
        else:
            github_handle = handle
        if identity.get("approved") is not True:
            errors.append("public Git identity object is not approved")
    if github_handle is None or not effective_codeowners(
        root / ".github" / "CODEOWNERS", github_handle
    ):
        errors.append("CODEOWNERS does not bind only the approved GitHub handle")

    channels = data.get("private_reporting_channels")
    if not isinstance(channels, dict):
        errors.append("private_reporting_channels is missing")
    else:
        if set(channels) != REPORTING_CHANNEL_KEYS:
            errors.append("private_reporting_channels contains missing or unknown keys")
        for key in sorted(REPORTING_CHANNEL_KEYS):
            value = channels.get(key)
            if (
                not isinstance(value, str) or not value.strip()
                or value != value.strip() or PLACEHOLDER.search(value)
            ):
                errors.append(f"private reporting channel is invalid: {key}")
    return errors


def validate_project_and_hero_bindings(
    data: dict[str, object], root: Path, mode: object
) -> list[str]:
    errors: list[str] = []
    expected_ids = expected_project_ids(mode)
    projects = data.get("projects")
    if not isinstance(projects, dict):
        errors.append("projects decision map is missing")
    else:
        if set(projects) != expected_ids:
            errors.append("projects decision map is not the exact selected set")
        for project_id in sorted(expected_ids):
            item = projects.get(project_id)
            if not isinstance(item, dict):
                errors.append(f"project decision is missing: {project_id}")
                continue
            if set(item) != PROJECT_DECISION_KEYS:
                errors.append(
                    f"project decision contains missing or unknown keys: {project_id}"
                )
            if item.get("include") is not True:
                errors.append(f"project is not owner-approved for inclusion: {project_id}")
            if item.get("provenance_approved") is not True:
                errors.append(f"project provenance is not owner-approved: {project_id}")
            source = root / "projects" / PROJECT_RELEASE_DIRS[project_id] / "PROVENANCE.md"
            digest = item.get("provenance_sha256")
            if (
                not isinstance(digest, str) or not SHA256_RE.fullmatch(digest)
                or not source.is_file() or source.is_symlink() or sha256(source) != digest
            ):
                errors.append(
                    "project provenance digest is not bound to supplied bytes: "
                    f"{project_id}"
                )

    expected_heroes = {
        HERO_BY_PROJECT[project_id]
        for project_id in expected_ids if project_id in HERO_BY_PROJECT
    }
    heroes = data.get("hero_assets")
    if not isinstance(heroes, dict) or set(heroes) != expected_heroes:
        errors.append("hero_assets decision map is not the exact selected hero set")
    else:
        for relative in sorted(expected_heroes):
            item = heroes.get(relative)
            source = root / relative
            if not isinstance(item, dict):
                errors.append(f"hero decision is missing: {relative}")
                continue
            if set(item) != HERO_DECISION_KEYS:
                errors.append(f"hero decision contains missing or unknown keys: {relative}")
            digest = item.get("sha256")
            if (
                not isinstance(digest, str) or not SHA256_RE.fullmatch(digest)
                or not source.is_file() or source.is_symlink() or sha256(source) != digest
            ):
                errors.append(f"hero digest is not bound to supplied bytes: {relative}")
            if (
                item.get("approved") is not True
                or item.get("native_visual_review_approved") is not True
            ):
                errors.append(f"hero lacks owner/native visual approval: {relative}")
    return errors


def workflow_action_pins(path: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    try:
        value = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return {}, [f"cannot read CI workflow: {exc}"]
    raw_uses = re.findall(r"(?m)^\s*(?:-\s+)?uses:\s*(\S+)", value)
    pins: dict[str, str] = {}
    pattern = re.compile(
        r"(?m)^\s*(?:-\s+)?uses:\s*"
        r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([0-9a-f]{40})"
        r"\s+#\s*(v[0-9]+)\s*$"
    )
    matches = list(pattern.finditer(value))
    if len(matches) != len(raw_uses):
        errors.append("CI workflow contains an unpinned or unreviewed action use")
    for item in matches:
        key = f"{item.group(1)}@{item.group(3)}"
        digest = item.group(2)
        if key in pins and pins[key] != digest:
            errors.append(f"CI workflow action has conflicting pins: {key}")
        pins[key] = digest
    if pins != EXPECTED_ACTION_PINS:
        errors.append("CI workflow action pins are not the exact reviewed set")
    return pins, errors


def validate_ci_and_artifact_bindings(
    data: dict[str, object], root: Path, mode: object
) -> list[str]:
    errors: list[str] = []
    workflow = root / ".github" / "workflows" / "verify.yml"
    lock = root / "requirements-ci.lock"
    observed_pins, pin_errors = workflow_action_pins(workflow)
    errors.extend(pin_errors)
    review = data.get("ci_review")
    if not isinstance(review, dict):
        errors.append("ci_review is missing")
    else:
        if set(review) != CI_REVIEW_KEYS:
            errors.append("ci_review contains missing or unknown keys")
        for key, source in (
            ("workflow_sha256", workflow),
            ("requirements_ci_lock_sha256", lock),
        ):
            digest = review.get(key)
            if (
                not isinstance(digest, str) or not SHA256_RE.fullmatch(digest)
                or not source.is_file() or source.is_symlink() or sha256(source) != digest
            ):
                errors.append(f"CI review digest is not bound to supplied bytes: {key}")
        if review.get("action_pins") != EXPECTED_ACTION_PINS:
            errors.append("CI action pins are not the exact reviewed set")
        if observed_pins != EXPECTED_ACTION_PINS:
            errors.append("CI action pins are not bound to the supplied workflow")
        if review.get("approved") is not True:
            errors.append("CI review object is not approved")

    artifact_review = data.get("all12_artifact_review")
    if not isinstance(artifact_review, dict):
        errors.append("all12_artifact_review is missing")
        return errors
    if set(artifact_review) != ALL12_ARTIFACT_REVIEW_KEYS:
        errors.append("all12_artifact_review contains missing or unknown keys")
        return errors
    expected = ALL12_ARTIFACT_PATHS if mode == "all12" else set()
    artifacts = artifact_review.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != expected:
        errors.append("all12 artifact digest map is not the exact mode-specific set")
    else:
        for relative in sorted(expected):
            source = root / relative
            digest = artifacts.get(relative)
            if (
                not isinstance(digest, str) or not SHA256_RE.fullmatch(digest)
                or not source.is_file() or source.is_symlink() or sha256(source) != digest
            ):
                errors.append(
                    f"all12 artifact digest is not bound to supplied bytes: {relative}"
                )
    if artifact_review.get("approved") is not (mode == "all12"):
        errors.append("all12_artifact_review approval does not match the release mode")
    return errors


def validate_decisions(
    path: Path,
    root: Path,
    mode: object,
    approved_emails: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    approved_emails = approved_emails if approved_emails is not None else set()
    try:
        data = load_json(path)
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        return [f"invalid release decisions: {exc}"]
    if not isinstance(data, dict):
        return ["release decisions root must be an object"]
    if set(data) != DECISION_KEYS:
        errors.append("release decisions contain missing or unknown top-level keys")
    if data.get("schema") != "portfolio-release-decisions/v2":
        errors.append("release decisions use the wrong schema")
    if data.get("decision_status") != "APPROVED_FOR_CANDIDATE_BUILD":
        errors.append("decision_status is not APPROVED_FOR_CANDIDATE_BUILD")
    visibility = data.get("repository_visibility")
    license_spdx = data.get("license_spdx")
    if visibility != "public":
        errors.append("selected repository_visibility must be public")
    if license_spdx != "NOASSERTION":
        errors.append("selected restrictive public release license_spdx must be NOASSERTION")
    if data.get("license_scope") != (
        "owner_created_material_all_rights_reserved_no_additional_license_"
        "beyond_github_terms_or_applicable_law_third_party_rights_unchanged"
    ):
        errors.append(
            "license_scope does not bind the restrictive owner posture, limited "
            "GitHub/platform-law exception, and unchanged third-party rights"
        )
    if data.get("repository_topology") != "curated_monorepo":
        errors.append("repository_topology must be curated_monorepo")
    if data.get("repository_name") != "systems-workflow-portfolio":
        errors.append("repository_name must match the reviewed topology")
    for key in (
        "repository_topology_approved", "license_approved",
        "owner_provenance_approved", "public_git_identity_approved",
        "codeowners_approved", "reporting_channels_approved",
        "hero_assets_approved", "ci_dependencies_approved",
    ):
        if data.get(key) is not True:
            errors.append(f"owner decision not approved: {key}")
    if not effective_license(root / "LICENSE", license_spdx):
        errors.append("root LICENSE is not effective for the approved license_spdx")
    errors.extend(validate_identity_and_channels(data, root, approved_emails))
    identity = data.get("public_git_identity")
    expected_email = identity.get("author_email") if isinstance(identity, dict) else None
    observed_emails = [
        item.casefold() for item in EMAIL_RE.findall(path.read_text(encoding="utf-8"))
    ]
    if (
        not isinstance(expected_email, str)
        or observed_emails != [expected_email.casefold()]
    ):
        errors.append("release decisions contain an unbound or repeated email address")
    errors.extend(validate_project_and_hero_bindings(data, root, mode))
    errors.extend(validate_ci_and_artifact_bindings(data, root, mode))

    if data.get("clean_history_clone_gate_required") is not True:
        errors.append("clean-history clone gate is not required")
    if data.get("clean_history_clone_receipt_sha256") is not None:
        errors.append("pre-build clean-history clone receipt must be null")
    if data.get("clean_history_clone_receipt_approved") is not False:
        errors.append("pre-build clean-history clone receipt approval must be false")
    for key in (
        "remote_creation_approved", "push_approved", "release_approved",
        "pages_approved", "publication_approved",
    ):
        if data.get(key) is not False:
            errors.append(f"candidate build must not authorize: {key}")
    for key in (
        "company_context_approved", "open_food_facts_distribution_approved",
        "product_capture_contact_metadata_approved", "restrictive_projects_resolved",
        "hitl_asset_provenance_approved",
    ):
        if data.get(key) is not (mode == "all12"):
            errors.append(f"{key} approval does not match the release mode")
    return errors


def validate_policy(data: object) -> tuple[dict[str, object], list[str]]:
    if not isinstance(data, dict):
        return {}, ["release policy root must be an object"]
    errors: list[str] = []
    if set(data) != POLICY_KEYS:
        errors.append("release policy contains missing or unknown top-level keys")
    if data.get("schema") != "systems-workflow-portfolio-release-policy/v1":
        errors.append("wrong release policy schema")
    mode = data.get("mode")
    if mode not in {"wave1", "all12"}:
        errors.append("release policy mode must be wave1 or all12")
        mode = "wave1"

    def string_set(key: str, *, paths: bool = False) -> set[str]:
        value = data.get(key)
        if (
            not isinstance(value, list)
            or not all(isinstance(item, str) for item in value)
            or len(value) != len(set(value))
        ):
            errors.append(f"release policy {key} must be a duplicate-free string list")
            return set()
        if paths and any(not safe_relative(item) for item in value):
            errors.append(f"release policy {key} contains an unsafe path")
        return set(value)

    expected_ids = expected_project_ids(mode)
    if string_set("decision_project_ids") != expected_ids:
        errors.append("release policy decision project set is not the exact mode set")
    if string_set("selected_projects") != {
        PROJECT_RELEASE_DIRS[item] for item in expected_ids
    }:
        errors.append("release policy selected project set is not the exact mode set")
    if string_set("owner_gate_paths", paths=True) != OWNER_GATE_PATHS:
        errors.append("release policy owner gate paths are not the exact reviewed set")
    for key in (
        "required_paths", "required_project_files", "content_scan_exclusions",
        "manifest_excludes",
    ):
        string_set(key, paths=True)
    for key in (
        "forbidden_path_parts", "forbidden_file_names", "runtime_extensions",
        "allowed_external_link_domains", "link_scan_excluded_prefixes",
    ):
        string_set(key)
    exclusions = data.get("content_scan_exclusions")
    if isinstance(exclusions, list) and set(exclusions) != EXPECTED_CONTENT_SCAN_EXCLUSIONS[mode]:
        errors.append("release policy content scan exclusions are not the exact reviewed set")
    max_bytes = data.get("max_regular_file_bytes")
    if (
        not isinstance(max_bytes, int) or isinstance(max_bytes, bool)
        or not 0 < max_bytes <= 10 * 1024 * 1024
    ):
        errors.append("release policy max_regular_file_bytes is invalid")
    patterns = data.get("forbidden_content_regex")
    if not isinstance(patterns, dict) or not all(
        isinstance(label, str) and isinstance(pattern, str)
        for label, pattern in patterns.items()
    ):
        errors.append("release policy forbidden_content_regex must be a string map")
    else:
        for label, pattern in patterns.items():
            try:
                re.compile(pattern)
            except re.error as exc:
                errors.append(f"invalid forbidden-content regex {label!r}: {exc}")
    return data, errors


def scan_release(
    root: Path, policy_path: Path, allow_owner_gates: bool
) -> list[str]:
    try:
        policy_value = load_json(policy_path)
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        return [f"invalid release policy: {exc}"]
    policy, errors = validate_policy(policy_value)
    if not policy or errors:
        return sorted(set(errors))
    owner_gates = set(policy["owner_gate_paths"])
    for raw in policy["required_paths"]:
        if allow_owner_gates and raw in OWNER_GATE_PATHS:
            path = root / raw
            if (path.exists() or path.is_symlink()) and (
                not path.is_file() or path.is_symlink()
            ):
                errors.append(f"owner gate path is not a regular file: {raw}")
            continue
        path = root / raw
        if not path.is_file() or path.is_symlink():
            errors.append(f"required regular file missing: {raw}")
    for project in policy["selected_projects"]:
        for name in policy["required_project_files"]:
            raw = f"projects/{project}/{name}"
            if not (root / raw).is_file():
                errors.append(f"required project document missing: {raw}")

    approved_identity_emails: set[str] = set()
    license_path = root / "LICENSE"
    decisions_path = root / "release-decisions.json"
    gate_present = {
        "LICENSE": license_path.exists() or license_path.is_symlink(),
        "release-decisions.json": decisions_path.exists() or decisions_path.is_symlink(),
    }
    validate_owner_gates = not allow_owner_gates or any(gate_present.values())
    if validate_owner_gates:
        for raw, present in sorted(gate_present.items()):
            if not present:
                errors.append(f"partially resolved owner gate is missing: {raw}")
        if decisions_path.is_file() and not decisions_path.is_symlink():
            errors.extend(
                validate_decisions(
                    decisions_path, root, policy.get("mode"), approved_identity_emails
                )
            )

    forbidden_parts = set(policy["forbidden_path_parts"])
    forbidden_names = set(policy["forbidden_file_names"])
    max_bytes = int(policy["max_regular_file_bytes"])
    exclusions = set(policy["content_scan_exclusions"])
    patterns = {label: re.compile(pattern) for label, pattern in policy["forbidden_content_regex"].items()}
    runtime_suffixes = set(policy["runtime_extensions"])
    seen_folded: dict[str, str] = {}
    for path in iter_paths(root):
        relative = path.relative_to(root)
        raw = relative.as_posix()
        if path.is_symlink():
            errors.append(f"symlink forbidden: {raw}")
            continue
        if forbidden_parts.intersection(relative.parts):
            errors.append(f"forbidden path component: {raw}")
        if path.name in forbidden_names or path.suffix in {".pyc", ".pyo"}:
            errors.append(f"forbidden file: {raw}")
        prior = seen_folded.setdefault(raw.casefold(), raw)
        if prior != raw:
            errors.append(f"case-fold path collision: {prior} / {raw}")
        if not path.is_file():
            continue
        if path.stat().st_size > max_bytes:
            errors.append(f"file exceeds {max_bytes} bytes: {raw}")
        if path.suffix == ".json":
            try:
                load_json(path)
            except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"invalid JSON: {raw}: {exc}")
        # Exact owner gates retain path/symlink/size/JSON checks in deferred mode.
        # Only generic text matching is skipped; adjacent or renamed paths do not match.
        if allow_owner_gates and raw in owner_gates and raw in OWNER_GATE_PATHS:
            try:
                owner_gate_text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                errors.append(f"declared text is not UTF-8: {raw}")
                continue
            for label, pattern in BUILTIN_FORBIDDEN.items():
                if pattern.search(owner_gate_text):
                    errors.append(f"{label} marker in: {raw}")
            continue
        if raw in exclusions or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            value = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"declared text is not UTF-8: {raw}")
            continue
        if PLACEHOLDER.search(value):
            errors.append(f"placeholder marker in: {raw}")
        for label, pattern in BUILTIN_FORBIDDEN.items():
            if pattern.search(value):
                errors.append(f"{label} marker in: {raw}")
        for match in EMAIL_RE.finditer(value):
            if not (
                raw == "release-decisions.json"
                and match.group(0).casefold() in approved_identity_emails
            ):
                errors.append(f"email address marker in: {raw}")
        for label, pattern in patterns.items():
            if label in BUILTIN_FORBIDDEN or label == "email address":
                continue
            if pattern.search(value):
                errors.append(f"{label} marker in: {raw}")
        if path.suffix.lower() in runtime_suffixes and re.search(r"https?://", value, re.IGNORECASE):
            errors.append(f"automatic-network-capable URL in runtime text: {raw}")

    if (root / ".github" / "workflows" / "pages.yml").exists() or (root / ".github" / "workflows" / "release.yml").exists():
        errors.append("deployment/release workflow present before separate authorization")
    return sorted(set(errors))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def synthetic_license() -> str:
    return """All rights reserved.

Copyright (c) 2099 Synthetic Owner

No additional license or reuse permission is granted for owner-created material
beyond the limited rights required by GitHub's Terms of Service for platform
functionality while this repository is public, permission expressly granted in
writing by the copyright holder, and applicable law.

GitHub's Terms of Service may grant GitHub, its affiliates, and public users
limited rights for hosting, service operation and improvement (including AI/ML
training as provided there), viewing, displaying, reproducing, and forking
public content. This notice does not prohibit or narrow those platform rights.

This notice does not alter the terms of any third-party material identified in
THIRD_PARTY_NOTICES.md. The material is provided without warranty to the
maximum extent permitted by applicable law.
"""


def build_self_test_fixture(root: Path, policy: dict[str, object]) -> dict[str, object]:
    mode = policy["mode"]
    selected_ids = expected_project_ids(mode)
    (root / ".github" / "CODEOWNERS").write_text(
        "* @synthetic-owner\n", encoding="utf-8"
    )
    (root / "LICENSE").write_text(synthetic_license(), encoding="utf-8")
    for raw in policy["required_paths"]:
        path = root / raw
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".json":
            write_json(path, {})
        else:
            path.write_text("# Synthetic self-test scaffold.\n", encoding="utf-8")

    projects: dict[str, object] = {}
    for project_id in sorted(selected_ids):
        source = root / "projects" / PROJECT_RELEASE_DIRS[project_id] / "PROVENANCE.md"
        projects[project_id] = {
            "include": True,
            "provenance_approved": True,
            "provenance_sha256": sha256(source),
        }
    heroes: dict[str, object] = {}
    for relative in sorted(
        HERO_BY_PROJECT[item] for item in selected_ids if item in HERO_BY_PROJECT
    ):
        source = root / relative
        heroes[relative] = {
            "sha256": sha256(source),
            "approved": True,
            "native_visual_review_approved": True,
        }
    artifacts: dict[str, str] = {}
    if mode == "all12":
        artifacts = {relative: sha256(root / relative) for relative in ALL12_ARTIFACT_PATHS}
    workflow = root / ".github" / "workflows" / "verify.yml"
    lock = root / "requirements-ci.lock"
    all12 = mode == "all12"
    decisions: dict[str, object] = {
        "schema": "portfolio-release-decisions/v2",
        "decision_status": "APPROVED_FOR_CANDIDATE_BUILD",
        "repository_visibility": "public",
        "repository_topology": "curated_monorepo",
        "repository_name": "systems-workflow-portfolio",
        "repository_topology_approved": True,
        "license_spdx": "NOASSERTION",
        "license_scope": (
            "owner_created_material_all_rights_reserved_no_additional_license_"
            "beyond_github_terms_or_applicable_law_third_party_rights_unchanged"
        ),
        "license_approved": True,
        "owner_provenance_approved": True,
        "public_git_identity_approved": True,
        "public_git_identity": {
            "author_name": "Synthetic Owner",
            "author_email": "Synthetic-Owner@Portfolio.Invalid",
            "github_handle": "Synthetic-Owner",
            "approved": True,
        },
        "codeowners_approved": True,
        "reporting_channels_approved": True,
        "private_reporting_channels": {
            "security": "GitHub private vulnerability reporting",
            "conduct": "Private maintainer conduct escalation",
        },
        "hero_assets_approved": True,
        "hero_assets": heroes,
        "ci_dependencies_approved": True,
        "ci_review": {
            "workflow_sha256": sha256(workflow),
            "requirements_ci_lock_sha256": sha256(lock),
            "action_pins": EXPECTED_ACTION_PINS,
            "approved": True,
        },
        "all12_artifact_review": {"artifacts": artifacts, "approved": all12},
        "projects": projects,
        "clean_history_clone_gate_required": True,
        "clean_history_clone_receipt_sha256": None,
        "clean_history_clone_receipt_approved": False,
        "company_context_approved": all12,
        "open_food_facts_distribution_approved": all12,
        "product_capture_contact_metadata_approved": all12,
        "restrictive_projects_resolved": all12,
        "hitl_asset_provenance_approved": all12,
        "remote_creation_approved": False,
        "push_approved": False,
        "release_approved": False,
        "pages_approved": False,
        "publication_approved": False,
    }
    write_json(root / "release-decisions.json", decisions)
    return decisions


def run_self_tests(policy_path: Path, source_root: Path) -> int:
    policy_value = load_json(policy_path)
    policy, policy_errors = validate_policy(policy_value)
    if policy_errors:
        raise ValueError(f"self-test policy is invalid: {policy_errors}")
    negative_count = 0
    with tempfile.TemporaryDirectory(prefix="publication-scan-self-test-") as directory:
        root = Path(directory) / "fixture"
        shutil.copytree(
            source_root,
            root,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "*.pyo"),
        )
        baseline = build_self_test_fixture(root, policy)
        decision_path = root / "release-decisions.json"
        for deferred in (False, True):
            findings = scan_release(root, root / "release-policy.json", deferred)
            if findings:
                raise ValueError(
                    "valid synthetic .invalid decision fixture was rejected: "
                    f"deferred={deferred}: {findings}"
                )
        preserved_identity = load_json(decision_path)["public_git_identity"]  # type: ignore[index]
        if preserved_identity != baseline["public_git_identity"]:  # type: ignore[index]
            raise ValueError("case-preserved identity bytes were rewritten during validation")

        cases: list[tuple[str, dict[str, object]]] = []

        def change(label: str, path: tuple[str, ...], value: object) -> None:
            candidate = copy.deepcopy(baseline)
            target = candidate
            for key in path[:-1]:
                target = target[key]  # type: ignore[index]
            target[path[-1]] = value  # type: ignore[index]
            cases.append((label, candidate))

        change("wrong schema", ("schema",), "portfolio-release-decisions/v1")
        change("wrong status", ("decision_status",), "OWNER_APPROVED")
        change("approval false", ("license_approved",), False)
        change("wrong visibility", ("repository_visibility",), "private")
        change("permissive license A", ("license_spdx",), "M" + "IT")
        change("permissive license B", ("license_spdx",), "Apa" + "che-2.0")
        change(
            "wrong restrictive scope",
            ("license_scope",),
            "owner_created_material_excluding_third_party_data_and_marks",
        )
        change(
            "identity email invalid", ("public_git_identity", "author_email"),
            "not-an-email",
        )
        change(
            "identity handle invalid", ("public_git_identity", "github_handle"),
            "Synthetic_Owner",
        )
        change("premature push", ("push_approved",), True)
        change(
            "premature clone receipt", ("clean_history_clone_receipt_approved",), True
        )
        first_project = sorted(baseline["projects"])[0]  # type: ignore[arg-type]
        change(
            "provenance digest drift",
            ("projects", first_project, "provenance_sha256"), "0" * 64,
        )
        first_hero = sorted(baseline["hero_assets"])[0]  # type: ignore[arg-type]
        change("hero digest drift", ("hero_assets", first_hero, "sha256"), "0" * 64)
        change("CI digest drift", ("ci_review", "workflow_sha256"), "0" * 64)
        change(
            "unbound decision email",
            ("private_reporting_channels", "conduct"),
            "Contact intruder@portfolio.invalid",
        )
        missing_project = copy.deepcopy(baseline)
        missing_project["projects"].pop(first_project)  # type: ignore[union-attr]
        cases.append(("missing project", missing_project))
        unknown = copy.deepcopy(baseline)
        unknown["unknown"] = False
        cases.append(("unknown top-level key", unknown))
        for label, candidate in cases:
            write_json(decision_path, candidate)
            if not validate_decisions(decision_path, root, policy["mode"]):
                raise ValueError(f"negative decision control was accepted: {label}")
            negative_count += 1
        write_json(decision_path, baseline)

        duplicate = decision_path.read_text(encoding="utf-8").replace(
            "{\n", '{\n  "schema": "portfolio-release-decisions/v2",\n', 1
        )
        decision_path.write_text(duplicate, encoding="utf-8")
        if not any(
            "duplicate JSON key" in item
            for item in validate_decisions(decision_path, root, policy["mode"])
        ):
            raise ValueError("duplicate decision JSON key was accepted")
        negative_count += 1
        write_json(decision_path, baseline)

        codeowners = root / ".github" / "CODEOWNERS"
        codeowners.write_text("* @synthetic-owner @other-owner\n", encoding="utf-8")
        if not validate_decisions(decision_path, root, policy["mode"]):
            raise ValueError("non-owner CODEOWNERS rule was accepted")
        negative_count += 1
        codeowners.write_text("* @synthetic-owner\n", encoding="utf-8")

        license_path = root / "LICENSE"
        license_path.write_text("All rights reserved.\n" * 20, encoding="utf-8")
        if not validate_decisions(decision_path, root, policy["mode"]):
            raise ValueError("license bytes inconsistent with SPDX were accepted")
        negative_count += 1
        license_path.write_text(synthetic_license(), encoding="utf-8")

        permissive = synthetic_license().replace(
            "No additional license or reuse permission is granted",
            "Permis" + "sion is hereby " + "gran" + "ted",
        )
        license_path.write_text(permissive, encoding="utf-8")
        findings = scan_release(root, root / "release-policy.json", True)
        if not any("permissive license grant marker in: LICENSE" in item for item in findings):
            raise ValueError("permissive license grant bytes escaped content scanning")
        negative_count += 1
        license_path.write_text(synthetic_license(), encoding="utf-8")

        near_miss = root / "near-miss" / "release-decisions.json"
        write_json(near_miss, {"email": "intruder@portfolio.invalid"})
        findings = scan_release(root, root / "release-policy.json", True)
        if not any("email address marker in: near-miss/" in item for item in findings):
            raise ValueError("near-miss owner-gate path bypassed email scanning")
        negative_count += 1
        shutil.rmtree(near_miss.parent)

        note = root / "non-owner.txt"
        note.write_text("contact intruder@portfolio.invalid\n", encoding="utf-8")
        findings = scan_release(root, root / "release-policy.json", True)
        if not any("email address marker in: non-owner.txt" in item for item in findings):
            raise ValueError("non-owner email was accepted")
        negative_count += 1
        note.unlink()

        branding = root / "non-owner-branding.txt"
        branding_controls = (
            "Com" + "pass",
            "Com" + "pass A" + "I",
            "Com" + "pass Gr" + "oup",
            "E" + "MC",
            "Secure" + "frame",
            "Tex" + "ture",
            "Pro" + "ton",
            "LAN" + "-LLM",
            "Work" + "station",
            "Co" + "dex",
            "Open" + "AI",
            "Anthro" + "pic",
            "Clau" + "de",
            "Op" + "us",
            "Fa" + "ble",
            "Gr" + "ok",
            "Qw" + "en",
            "Lla" + "ma",
            "Gem" + "ini",
            "Mis" + "tral",
        )
        for value in branding_controls:
            branding.write_text(f"directed branding: {value}\n", encoding="utf-8")
            findings = scan_release(root, root / "release-policy.json", True)
            if not any(
                "private client or model branding marker in: non-owner-branding.txt"
                in item for item in findings
            ):
                raise ValueError("private client/model branding negative control escaped")
            negative_count += 1
        branding.write_text("private identity: " + "sw" + "ra" + "th" + "\n", encoding="utf-8")
        findings = scan_release(root, root / "release-policy.json", True)
        if not any(
            "private identity or contact marker in: non-owner-branding.txt" in item
            for item in findings
        ):
            raise ValueError("private identity negative control escaped")
        negative_count += 1
        branding.unlink()

        secret = root / "secret.txt"
        secret.write_text("ghp_" + "A" * 24 + "\n", encoding="utf-8")
        findings = scan_release(root, root / "release-policy.json", True)
        if not any("GitHub token marker in: secret.txt" in item for item in findings):
            raise ValueError("high-confidence secret was accepted")
        negative_count += 1
        secret.unlink()

        owner_secret = copy.deepcopy(baseline)
        owner_secret["private_reporting_channels"]["security"] = (  # type: ignore[index]
            "ghp_" + "B" * 24
        )
        write_json(decision_path, owner_secret)
        findings = scan_release(root, root / "release-policy.json", True)
        if not any(
            "GitHub token marker in: release-decisions.json" in item
            for item in findings
        ):
            raise ValueError("exact owner gate bypassed high-confidence secret scanning")
        negative_count += 1
        write_json(decision_path, baseline)

        retired = copy.deepcopy(baseline)
        retired["private_reporting_channels"]["conduct"] = (  # type: ignore[index]
            "Private " + "signal" + "room"
        )
        write_json(decision_path, retired)
        findings = scan_release(root, root / "release-policy.json", False)
        if not any(
            "retired colliding demo name marker in: release-decisions.json" in item
            for item in findings
        ):
            raise ValueError("resolved decision received an all-content exemption")
        negative_count += 1
        write_json(decision_path, baseline)

        small_policy = copy.deepcopy(policy)
        small_policy["max_regular_file_bytes"] = decision_path.stat().st_size - 1
        write_json(root / "release-policy.json", small_policy)
        findings = scan_release(root, root / "release-policy.json", True)
        if not any("file exceeds" in item and item.endswith("release-decisions.json") for item in findings):
            raise ValueError("exact owner gate bypassed size scanning")
        negative_count += 1
        write_json(root / "release-policy.json", policy)

        decision_path.write_text("{ invalid JSON\n", encoding="utf-8")
        findings = scan_release(root, root / "release-policy.json", True)
        if not any("invalid JSON: release-decisions.json" in item for item in findings):
            raise ValueError("invalid owner-gate JSON bypassed structural scanning")
        negative_count += 1
        write_json(decision_path, baseline)

        license_path.unlink()
        license_path.symlink_to("release-decisions.json")
        findings = scan_release(root, root / "release-policy.json", True)
        if not any("symlink forbidden: LICENSE" in item for item in findings):
            raise ValueError("owner-gate symlink bypassed path scanning")
        negative_count += 1
    return negative_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--allow-owner-gates", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    policy_path = args.policy.resolve()
    if args.self_test:
        try:
            count = run_self_tests(policy_path, root)
        except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
            print(f"FAIL: publication scanner self-test: {exc}")
            return 1
        print(f"PASS: publication scanner self-test ({count} negative controls)")
    errors = scan_release(root, policy_path, args.allow_owner_gates)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    mode = "owner gates deferred" if args.allow_owner_gates else "owner gates resolved"
    print(
        f"PASS: publication scan ({mode}); v2 decisions, paths, content, JSON, "
        "assets, and runtime network boundary verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
