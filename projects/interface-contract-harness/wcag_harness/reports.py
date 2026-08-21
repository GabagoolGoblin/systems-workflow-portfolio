"""Stable JSON, Markdown, HTML, and hash-chain report emission."""

from __future__ import annotations

import html
import os
from pathlib import Path, PurePosixPath
from typing import Any

from .io_utils import (
    atomic_write,
    canonical_json_bytes,
    read_regular_file,
    reject_symlink_components,
    sha256,
    strict_json_loads,
)
from .model import ContractInputError

MAX_AUDIT_BYTES = 262_144
MAX_REPORT_BYTES = 2_000_000


def _markdown(report: dict[str, Any], report_json_sha256: str) -> bytes:
    summary = report["summary"]
    lines = [
        f"# Interface contract report: {report['suite']['id']}",
        "",
        f"**Result:** `{report['suite']['status'].upper()}`",
        "",
        report["scope_notice"],
        "",
        "## Summary",
        "",
        "| Cases | Matched | Regressed | Expected violations | Actual violations |",
        "|---:|---:|---:|---:|---:|",
        (
            f"| {summary['cases']} | {summary['cases_matched']} | "
            f"{summary['cases_regressed']} | {summary['expected_violations']} | "
            f"{summary['actual_violations']} |"
        ),
        "",
        f"Fixture bundle SHA-256: `{report['input_binding']['bundle_sha256']}`",
        "",
        f"JSON report SHA-256: `{report_json_sha256}`",
        "",
        "## Cases",
        "",
    ]
    for case in report["cases"]:
        icon = "PASS" if case["status"] == "matched" else "REGRESSION"
        lines.extend(
            [
                f"### {case['id']}: {icon}",
                "",
                f"Fixture: `{case['html']}`  ",
                f"Fixture SHA-256: `{case['fixture_sha256']}`",
                "",
            ]
        )
        if case["actual_violations"]:
            lines.extend(
                [
                    "| Rule | Node | Location | Message |",
                    "|---|---|---:|---|",
                ]
            )
            for item in case["actual_violations"]:
                message = item["message"].replace("|", "\\|")
                lines.append(
                    f"| `{item['rule_id']}` | `{item['node']}` | "
                    f"{item['line']}:{item['column']} | {message} |"
                )
            lines.append("")
        else:
            lines.extend(["No violations in the selected contract scope.", ""])
        if case["missing_expected"]:
            lines.extend(["Missing expected fingerprints:", ""])
            lines.extend(
                f"- `{item['rule_id']}` at `{item['node']}`"
                for item in case["missing_expected"]
            )
            lines.append("")
        if case["unexpected"]:
            lines.extend(["Unexpected fingerprints:", ""])
            lines.extend(
                f"- `{item['rule_id']}` at `{item['node']}`"
                for item in case["unexpected"]
            )
            lines.append("")
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _html(report: dict[str, Any], report_json_sha256: str) -> bytes:
    summary = report["summary"]
    status = report["suite"]["status"]
    case_cards: list[str] = []
    for case in report["cases"]:
        violations = "".join(
            "<li><code>{rule}</code><span>{node}</span><p>{message}</p></li>".format(
                rule=html.escape(item["rule_id"]),
                node=html.escape(item["node"]),
                message=html.escape(item["message"]),
            )
            for item in case["actual_violations"]
        ) or "<li class=\"empty\">No violations in selected scope.</li>"
        case_cards.append(
            """
            <article class="case {status}">
              <header><span class="pill">{badge}</span><h3>{case_id}</h3></header>
              <p class="fixture">{fixture}<br>{actual_count} observed · {expected_count} expected</p><ul>{violations}</ul>
            </article>
            """.format(
                status=html.escape(case["status"]),
                badge="expected match" if case["status"] == "matched" else "regression",
                case_id=html.escape(case["id"]),
                fixture=html.escape(case["html"]),
                actual_count=len(case["actual_violations"]),
                expected_count=len(case["expected_violations"]),
                violations=violations,
            )
        )
    rule_items = "".join(
        f"<li><code>{html.escape(rule['id'])}</code><span>{html.escape(rule['description'])}</span></li>"
        for rule in report["rules"]
    )
    document = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Interface contract report</title>
<style>
:root{{color-scheme:dark;--bg:#08111f;--panel:#101d30;--ink:#eef6ff;--muted:#9eb2ca;--cyan:#58e1d3;--rose:#ff7d9c;--line:#233751}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 15% 0,#153457 0,transparent 35%),var(--bg);color:var(--ink);font:16px/1.55 system-ui,sans-serif}}
main{{width:min(1120px,92vw);margin:auto;padding:64px 0 80px}}.eyebrow{{color:var(--cyan);font-weight:750;letter-spacing:.12em;text-transform:uppercase}}
.boundary{{margin:0 0 28px;padding:10px 14px;border:1px solid var(--line);border-radius:12px;color:var(--cyan);font:800 .72rem/1.45 ui-monospace,monospace;letter-spacing:.06em;text-transform:uppercase}}
h1{{font-size:clamp(2.4rem,6vw,5.8rem);line-height:.96;margin:.22em 0;max-width:900px}}.lede{{color:var(--muted);max-width:800px;font-size:1.12rem}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:36px 0}}.metric,.case,.scope{{border:1px solid var(--line);background:rgba(16,29,48,.86);border-radius:18px}}
.metric{{padding:20px}}.metric strong{{display:block;font-size:2rem}}.metric span,.fixture,.scope p{{color:var(--muted)}}
.status{{display:inline-flex;padding:8px 14px;border-radius:999px;background:{status_color};color:#06121c;font-weight:850;text-transform:uppercase}}
.section-title{{margin-top:40px}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;align-items:start}}.case{{padding:22px}}.case header{{display:flex;align-items:center;gap:12px;flex-wrap:wrap}}.case h3{{margin:0}}
.pill{{font-size:.72rem;font-weight:850;text-transform:uppercase;color:#06121c;background:var(--cyan);padding:4px 8px;border-radius:999px}}.regression .pill{{background:var(--rose)}}
ul{{list-style:none;padding:0}}.case li{{border-top:1px solid var(--line);padding:12px 0}}.case li span{{display:block;color:var(--muted);font:12px ui-monospace,monospace;overflow-wrap:anywhere}}.case li p{{margin:.3rem 0 0}}code{{color:var(--cyan)}}
.scope{{margin-top:24px;padding:24px}}.scope li{{display:grid;grid-template-columns:minmax(180px,.35fr) 1fr;gap:20px;padding:10px 0;border-top:1px solid var(--line)}}.hash{{overflow-wrap:anywhere;font:12px ui-monospace,monospace;color:var(--muted)}}
@media(max-width:900px){{.grid{{grid-template-columns:1fr 1fr}}}}@media(max-width:760px){{.metrics{{grid-template-columns:1fr 1fr}}.scope li{{grid-template-columns:1fr;gap:3px}}}}@media(max-width:560px){{.metrics,.grid{{grid-template-columns:1fr}}}}
</style></head><body><main>
<p class="boundary" role="note" data-boundary>INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION</p>
<p class="eyebrow">Synthetic QA evidence</p><h1>Interface contracts, made visible.</h1>
<p class="lede">{notice}</p><p class="status">suite {status}</p>
<p class="lede">A matched fixture may intentionally contain findings: observed fingerprints must exactly equal declared expectations.</p>
<section class="metrics" aria-label="Run summary">
<div class="metric"><strong>{cases}</strong><span>fixtures</span></div>
<div class="metric"><strong>{matched}</strong><span>matched</span></div>
<div class="metric"><strong>{regressed}</strong><span>regressed</span></div>
<div class="metric"><strong>{violations}</strong><span>observed findings</span></div></section>
<h2 class="section-title">Fixture evidence</h2>
<section class="grid" aria-label="Fixture results">{case_cards}</section>
<section class="scope"><h2>Bounded rule scope</h2><ul>{rule_items}</ul>
<p class="hash">Fixture bundle: {bundle}<br>JSON report: {report_hash}</p></section>
</main></body></html>
""".format(
        status_color="var(--cyan)" if status == "matched" else "var(--rose)",
        notice=html.escape(report["scope_notice"]),
        status=html.escape(status),
        cases=summary["cases"],
        matched=summary["cases_matched"],
        regressed=summary["cases_regressed"],
        violations=summary["actual_violations"],
        case_cards="".join(case_cards),
        rule_items=rule_items,
        bundle=html.escape(report["input_binding"]["bundle_sha256"]),
        report_hash=html.escape(report_json_sha256),
    )
    return document.encode("utf-8")


def _project_path(base: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(base.resolve())
    except ValueError as exc:
        raise ContractInputError(f"bound file is outside project base: {path}") from exc
    return relative.as_posix()


def write_report_bundle(
    report: dict[str, Any],
    bound_inputs: list[tuple[Path, bytes]],
    output_dir: Path,
    project_base: Path,
) -> dict[str, Any]:
    output_dir = output_dir.absolute()
    reject_symlink_components(output_dir, label="output path")
    output_dir = output_dir.resolve()
    project_base = project_base.resolve()
    try:
        output_dir.relative_to(project_base)
    except ValueError as exc:
        raise ContractInputError("output directory must be inside the project base") from exc
    if output_dir == project_base:
        raise ContractInputError("output directory must not be the project root")
    if output_dir.exists() and (not output_dir.is_dir() or output_dir.is_symlink()):
        raise ContractInputError("output path must be a non-symlink directory")
    output_dir.mkdir(parents=True, exist_ok=True)

    json_raw = canonical_json_bytes(report, pretty=True)
    json_sha = sha256(json_raw)
    markdown_raw = _markdown(report, json_sha)
    html_raw = _html(report, json_sha)
    outputs = {
        output_dir / "report.html": html_raw,
        output_dir / "report.json": json_raw,
        output_dir / "report.md": markdown_raw,
    }
    for path, raw in outputs.items():
        atomic_write(path, raw)

    base_relative = Path(os.path.relpath(project_base, output_dir)).as_posix()
    audit = {
        "algorithm": "sha256",
        "base_directory": base_relative,
        "files": sorted(
            [
                {
                    "path": _project_path(project_base, path),
                    "role": "input",
                    "sha256": sha256(raw),
                }
                for path, raw in bound_inputs
            ]
            + [
                {
                    "path": _project_path(project_base, path),
                    "role": "output",
                    "sha256": sha256(raw),
                }
                for path, raw in outputs.items()
            ],
            key=lambda item: (item["role"], item["path"]),
        ),
        "fixture_bundle_sha256": report["input_binding"]["bundle_sha256"],
        "report_json_sha256": json_sha,
        "schema_version": 1,
    }
    audit_raw = canonical_json_bytes(audit, pretty=True)
    audit_path = output_dir / "audit.json"
    atomic_write(audit_path, audit_raw)
    seal = f"{sha256(audit_raw)}  audit.json\n".encode("ascii")
    atomic_write(output_dir / "audit.sha256", seal)
    return audit


def _safe_audit_path(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ContractInputError("audit file path must be a normalized POSIX string")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ContractInputError(f"unsafe audit file path: {value!r}")
    return path


def _digest(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ContractInputError(f"{label} is not a SHA-256 digest")
    return value


def _keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ContractInputError(f"{label} contains missing or unknown keys")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ContractInputError(f"{label} must be a non-negative integer")
    return value


def _validate_bound_report(report: Any) -> list[str]:
    report = _keys(
        report,
        {
            "cases",
            "input_binding",
            "rules",
            "schema_version",
            "scope_notice",
            "suite",
            "summary",
            "tool",
        },
        "report",
    )
    if type(report["schema_version"]) is not int or report["schema_version"] != 1:
        raise ContractInputError("unsupported report schema")
    if not isinstance(report["scope_notice"], str) or not report["scope_notice"]:
        raise ContractInputError("report scope_notice must be a nonblank string")
    tool = _keys(report["tool"], {"name", "version"}, "report.tool")
    if tool["name"] != "interface-contract-harness" or not isinstance(
        tool["version"], str
    ):
        raise ContractInputError("report tool identity is invalid")
    suite = _keys(report["suite"], {"description", "id", "status"}, "report.suite")
    if (
        not isinstance(suite["description"], str)
        or not isinstance(suite["id"], str)
        or suite["status"] not in {"matched", "regression"}
    ):
        raise ContractInputError("report suite metadata is invalid")

    rules = report["rules"]
    if not isinstance(rules, list) or not rules:
        raise ContractInputError("report rules must be a non-empty array")
    enabled_rules: set[str] = set()
    for index, item in enumerate(rules):
        item = _keys(item, {"description", "id"}, f"report.rules[{index}]")
        if (
            not isinstance(item["id"], str)
            or not isinstance(item["description"], str)
            or not item["id"]
            or not item["description"]
            or item["id"] in enabled_rules
        ):
            raise ContractInputError(f"report.rules[{index}] is invalid")
        enabled_rules.add(item["id"])

    binding = _keys(
        report["input_binding"], {"bundle_sha256", "files"}, "report.input_binding"
    )
    bundle_digest = _digest(
        binding["bundle_sha256"], "report.input_binding.bundle_sha256"
    )
    if not isinstance(binding["files"], list) or not binding["files"]:
        raise ContractInputError("report input files must be a non-empty array")
    input_digests: list[str] = []
    input_by_path: dict[str, str] = {}
    normalized_input_entries: list[dict[str, str]] = []
    for index, item in enumerate(binding["files"]):
        item = _keys(item, {"path", "sha256"}, f"report.input files[{index}]")
        path = _safe_audit_path(item["path"]).as_posix()
        digest = _digest(item["sha256"], f"report.input files[{index}].sha256")
        if path in input_by_path:
            raise ContractInputError(f"duplicate report input path: {path}")
        input_by_path[path] = digest
        input_digests.append(digest)
        normalized_input_entries.append({"path": path, "sha256": digest})
    if "manifest.json" not in input_by_path:
        raise ContractInputError("report input binding does not contain manifest.json")
    if sha256(canonical_json_bytes(normalized_input_entries)) != bundle_digest:
        raise ContractInputError("report fixture bundle digest is internally inconsistent")

    cases = report["cases"]
    if not isinstance(cases, list) or not cases:
        raise ContractInputError("report cases must be a non-empty array")
    case_ids: set[str] = set()
    counted_actual = 0
    counted_expected = 0
    counted_matched = 0
    fingerprint_keys = {"node", "rule_id"}
    for case_index, case in enumerate(cases):
        case = _keys(
            case,
            {
                "actual_violations",
                "expected_violations",
                "fixture_sha256",
                "html",
                "id",
                "missing_expected",
                "status",
                "unexpected",
            },
            f"report.cases[{case_index}]",
        )
        if (
            not isinstance(case["id"], str)
            or not case["id"]
            or case["id"] in case_ids
            or not isinstance(case["html"], str)
            or case["status"] not in {"matched", "regression"}
        ):
            raise ContractInputError(f"report.cases[{case_index}] metadata is invalid")
        case_ids.add(case["id"])
        fixture_digest = _digest(
            case["fixture_sha256"], f"report.cases[{case_index}].fixture_sha256"
        )
        if input_by_path.get(case["html"]) != fixture_digest:
            raise ContractInputError(
                f"report.cases[{case_index}] fixture binding is inconsistent"
            )
        for array_name in (
            "actual_violations",
            "expected_violations",
            "missing_expected",
            "unexpected",
        ):
            if not isinstance(case[array_name], list):
                raise ContractInputError(
                    f"report.cases[{case_index}].{array_name} must be an array"
                )
        actual_pairs: set[tuple[str, str]] = set()
        for finding_index, finding in enumerate(case["actual_violations"]):
            finding = _keys(
                finding,
                {"column", "line", "message", "node", "rule_id", "severity"},
                f"report.cases[{case_index}].actual_violations[{finding_index}]",
            )
            if (
                finding["rule_id"] not in enabled_rules
                or not isinstance(finding["node"], str)
                or not isinstance(finding["message"], str)
                or finding["severity"] != "error"
            ):
                raise ContractInputError("report actual violation is invalid")
            _nonnegative_int(finding["line"], "report violation line")
            _nonnegative_int(finding["column"], "report violation column")
            pair = (finding["rule_id"], finding["node"])
            if pair in actual_pairs:
                raise ContractInputError("report contains duplicate actual fingerprints")
            actual_pairs.add(pair)
        fingerprint_sets: dict[str, set[tuple[str, str]]] = {}
        for array_name in ("expected_violations", "missing_expected", "unexpected"):
            pairs: set[tuple[str, str]] = set()
            for finding_index, finding in enumerate(case[array_name]):
                finding = _keys(
                    finding,
                    fingerprint_keys,
                    f"report.cases[{case_index}].{array_name}[{finding_index}]",
                )
                if finding["rule_id"] not in enabled_rules or not isinstance(
                    finding["node"], str
                ):
                    raise ContractInputError("report fingerprint is invalid")
                pair = (finding["rule_id"], finding["node"])
                if pair in pairs:
                    raise ContractInputError("report contains duplicate fingerprints")
                pairs.add(pair)
            fingerprint_sets[array_name] = pairs
        if fingerprint_sets["missing_expected"] != (
            fingerprint_sets["expected_violations"] - actual_pairs
        ) or fingerprint_sets["unexpected"] != (
            actual_pairs - fingerprint_sets["expected_violations"]
        ):
            raise ContractInputError(
                f"report.cases[{case_index}] comparison sets are inconsistent"
            )
        missing_present = bool(case["missing_expected"] or case["unexpected"])
        expected_status = "regression" if missing_present else "matched"
        if case["status"] != expected_status:
            raise ContractInputError(f"report.cases[{case_index}] status is inconsistent")
        counted_actual += len(case["actual_violations"])
        counted_expected += len(case["expected_violations"])
        counted_matched += int(case["status"] == "matched")

    summary = _keys(
        report["summary"],
        {
            "actual_violations",
            "cases",
            "cases_matched",
            "cases_regressed",
            "expected_violations",
        },
        "report.summary",
    )
    for key, value in summary.items():
        _nonnegative_int(value, f"report.summary.{key}")
    expected_summary = {
        "actual_violations": counted_actual,
        "cases": len(cases),
        "cases_matched": counted_matched,
        "cases_regressed": len(cases) - counted_matched,
        "expected_violations": counted_expected,
    }
    if summary != expected_summary:
        raise ContractInputError("report summary is inconsistent")
    expected_suite_status = "matched" if counted_matched == len(cases) else "regression"
    if suite["status"] != expected_suite_status:
        raise ContractInputError("report suite status is inconsistent")
    return input_digests


def verify_report_bundle(audit_path: Path, seal_path: Path) -> dict[str, int | str]:
    audit_path = audit_path.absolute()
    seal_path = seal_path.absolute()
    if audit_path.is_symlink() or seal_path.is_symlink():
        raise ContractInputError("audit and seal must not be symlinks")
    if audit_path.name != "audit.json" or seal_path.name != "audit.sha256":
        raise ContractInputError("audit and seal must use their canonical filenames")
    audit_raw = read_regular_file(audit_path, max_bytes=MAX_AUDIT_BYTES)
    seal_raw = read_regular_file(seal_path, max_bytes=256)
    expected_seal = f"{sha256(audit_raw)}  audit.json\n".encode("ascii")
    if seal_raw != expected_seal:
        raise ContractInputError("audit seal does not match audit.json")
    audit = strict_json_loads(audit_raw, label="audit")
    if not isinstance(audit, dict):
        raise ContractInputError("audit root must be an object")
    expected_keys = {
        "algorithm",
        "base_directory",
        "files",
        "fixture_bundle_sha256",
        "report_json_sha256",
        "schema_version",
    }
    if set(audit) != expected_keys:
        raise ContractInputError("audit contains missing or unknown keys")
    if type(audit["schema_version"]) is not int or audit["schema_version"] != 1 or audit["algorithm"] != "sha256":
        raise ContractInputError("unsupported audit schema or algorithm")
    for digest_field in ("fixture_bundle_sha256", "report_json_sha256"):
        digest_value = audit[digest_field]
        if (
            not isinstance(digest_value, str)
            or len(digest_value) != 64
            or any(character not in "0123456789abcdef" for character in digest_value)
        ):
            raise ContractInputError(f"audit {digest_field} is not a SHA-256 digest")
    if not isinstance(audit["base_directory"], str) or "\\" in audit["base_directory"]:
        raise ContractInputError("audit base_directory must be a relative POSIX string")
    base_parts = PurePosixPath(audit["base_directory"])
    if base_parts.is_absolute() or not base_parts.parts or any(
        part != ".." for part in base_parts.parts
    ):
        raise ContractInputError("audit base_directory must ascend only to its project root")
    base_candidate = audit_path.parent / audit["base_directory"]
    reject_symlink_components(base_candidate, label="audit base path")
    base = base_candidate.resolve()
    if not base.is_dir() or base == Path(base.anchor):
        raise ContractInputError("audit base_directory is not a bounded directory")
    files = audit["files"]
    if not isinstance(files, list) or not files:
        raise ContractInputError("audit files must be a non-empty array")
    seen: set[str] = set()
    output_names: set[str] = set()
    report_json_found = False
    report_input_digests: list[str] | None = None
    audit_input_digests: list[str] = []
    input_count = 0
    output_count = 0
    for index, item in enumerate(files):
        if not isinstance(item, dict) or set(item) != {"path", "role", "sha256"}:
            raise ContractInputError(f"audit files[{index}] is invalid")
        relative = _safe_audit_path(item["path"])
        if item["role"] not in {"input", "output"}:
            raise ContractInputError(f"audit files[{index}] has an unknown role")
        digest = item["sha256"]
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ContractInputError(f"audit files[{index}] has an invalid digest")
        text_path = relative.as_posix()
        if text_path in seen:
            raise ContractInputError(f"audit contains duplicate path: {text_path}")
        seen.add(text_path)
        lexical_candidate = base / Path(*relative.parts)
        if lexical_candidate.is_symlink():
            raise ContractInputError(f"audit target must not be a symlink: {text_path}")
        candidate = lexical_candidate.resolve()
        try:
            candidate.relative_to(base)
        except ValueError as exc:
            raise ContractInputError(f"audit path escapes base: {text_path}") from exc
        raw = read_regular_file(candidate, max_bytes=MAX_REPORT_BYTES)
        if sha256(raw) != digest:
            raise ContractInputError(f"digest mismatch: {text_path}")
        input_count += int(item["role"] == "input")
        if item["role"] == "input":
            audit_input_digests.append(digest)
        output_count += int(item["role"] == "output")
        if item["role"] == "output":
            if candidate.parent != audit_path.parent.resolve():
                raise ContractInputError("report outputs must be beside audit.json")
            output_names.add(candidate.name)
        if item["role"] == "output" and candidate.name == "report.json":
            if sha256(raw) != audit["report_json_sha256"]:
                raise ContractInputError("report_json_sha256 binding mismatch")
            report = strict_json_loads(raw, label="report.json")
            report_input_digests = _validate_bound_report(report)
            if (
                not isinstance(report, dict)
                or report.get("input_binding", {}).get("bundle_sha256")
                != audit["fixture_bundle_sha256"]
            ):
                raise ContractInputError("fixture bundle binding mismatch")
            report_json_found = True
    if not report_json_found:
        raise ContractInputError("audit does not bind an output report.json")
    if report_input_digests is None or sorted(report_input_digests) != sorted(
        audit_input_digests
    ):
        raise ContractInputError("audit inputs do not match report input bindings")
    if output_names != {"report.html", "report.json", "report.md"}:
        raise ContractInputError("audit does not bind the exact report output set")
    return {
        "audit_sha256": sha256(audit_raw),
        "files_verified": len(files),
        "inputs_verified": input_count,
        "outputs_verified": output_count,
        "status": "verified",
    }
