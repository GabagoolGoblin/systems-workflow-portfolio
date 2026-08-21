#!/usr/bin/env python3
"""Fail-closed static security, privacy, provenance, and boundary scan."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATHS = (
    ROOT / "index.html",
    ROOT / "styles.css",
    ROOT / "app.js",
    ROOT / "data" / "demo_snapshot.js",
    ROOT / "data" / "holdout_snapshot.js",
)


def result(label: str, passed: bool, detail: str) -> bool:
    print(f"{'PASS' if passed else 'FAIL'}: {label}: {detail}")
    return passed


def main() -> int:
    runtime = "\n".join(path.read_text(encoding="utf-8") for path in RUNTIME_PATHS)
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "app.js").read_text(encoding="utf-8")
    base_text = (ROOT / "data" / "demo_snapshot.js").read_text(encoding="utf-8")
    holdout_text = (ROOT / "data" / "holdout_snapshot.js").read_text(encoding="utf-8")
    casebook = json.loads((ROOT / "fixtures" / "synthetic_casebook.json").read_text(encoding="utf-8"))
    adjudications = json.loads((ROOT / "fixtures" / "synthetic_adjudications.json").read_text(encoding="utf-8"))
    checks: list[bool] = []

    forbidden_runtime = {
        "HTTP(S) URL": r"https?://",
        "fetch": r"\bfetch\s*\(",
        "XMLHttpRequest": r"\bXMLHttpRequest\b",
        "WebSocket": r"\bWebSocket\b",
        "EventSource": r"\bEventSource\b",
        "sendBeacon": r"\bsendBeacon\b",
        "iframe": r"<iframe\b",
        "form submission": r"<form\b",
        "localStorage": r"\blocalStorage\b",
        "sessionStorage": r"\bsessionStorage\b",
        "indexedDB": r"\bindexedDB\b",
        "service worker": r"\bserviceWorker\b",
        "cookie access": r"document\.cookie",
        "innerHTML sink": r"\.innerHTML\b",
        "outerHTML sink": r"\.outerHTML\b",
        "insertAdjacentHTML sink": r"\binsertAdjacentHTML\b",
        "document.write sink": r"document\.write\s*\(",
        "dynamic code evaluation": r"\beval\s*\(|\bnew\s+Function\s*\(",
        "web worker": r"\bnew\s+Worker\s*\(",
    }
    for label, pattern in forbidden_runtime.items():
        checks.append(result(f"runtime has no {label}", re.search(pattern, runtime, re.IGNORECASE) is None, pattern))

    provider_names = (
        "Open" + "AI", "Anthro" + "pic", "Clau" + "de", "Gem" + "ini",
        "Gr" + "ok", "Lla" + "ma", "Mis" + "tral",
    )
    checks.append(result("runtime names no inference provider", not any(name.casefold() in runtime.casefold() for name in provider_names), "invented candidate labels only"))

    boundary = "INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION"
    checks.append(result("permanent top boundary is exact", boundary in html, boundary))
    checks.append(result("footer repeats portfolio boundary", "ALL NAMES, CASES, OUTPUTS, SCORES, AND PROGRAM DATA ARE INVENTED" in html, "invented-data footer"))
    checks.append(result("CSP blocks connections", "connect-src 'none'" in html, "connect-src 'none'"))
    checks.append(result("CSP blocks forms", "form-action 'none'" in html, "form-action 'none'"))
    checks.append(result("CSP blocks objects", "object-src 'none'" in html, "object-src 'none'"))
    checks.append(result("browser export is click-bound", "addEventListener('click', exportReceipt)" in app, "explicit user event"))
    checks.append(result("browser export uses a local Blob", "new Blob" in app and "URL.createObjectURL" in app, "local download only"))
    checks.append(result("runtime declares no inference", '"inference":false' in base_text, "static precomputed outputs"))
    checks.append(result("runtime declares no persistence", '"persistence":false' in base_text, "in-memory state"))
    checks.append(result("runtime declares no production action", '"production_action":false' in base_text, "display-only gate"))

    development = [case for case in casebook["cases"] if case["partition"] == "development"]
    holdout = [case for case in casebook["cases"] if case["partition"] == "holdout"]
    checks.append(result("casebook has exactly 8 development cases", len(development) == 8, str(len(development))))
    checks.append(result("casebook has exactly 4 holdout cases", len(holdout) == 4, str(len(holdout))))
    checks.append(result("base snapshot excludes holdout task briefs", all(case["task_brief"] not in base_text for case in holdout), "details absent until reveal"))
    checks.append(result("base snapshot excludes holdout outputs", all(response["output"] not in base_text for case in holdout for response in case["responses"].values()), "outputs absent until reveal"))
    checks.append(result("base snapshot excludes candidate bindings", "candidate_bindings" not in base_text and "candidate_juniper" not in base_text and "candidate_sable" not in base_text, "blind before reveal"))
    checks.append(result("separate reveal bundle contains four details", sum(case["task_brief"] in holdout_text for case in holdout) == 4, "local static reveal"))
    checks.append(result("seal disclaims confidentiality", '"cryptographic_confidentiality_claimed":false' in base_text, "workflow boundary only"))
    checks.append(result("HTML does not preload holdout bundle", "holdout_snapshot.js" not in html, "dynamic local reveal only"))
    checks.append(result("review scores use blind labels only", all(set(review["scores"]) == {"A", "B"} for review in adjudications["reviews"]), "A/B keyed reviewer input"))
    checks.append(result("allowed outcomes are fail-closed", all(token in runtime for token in ("HOLD", "ROLLBACK", "PENDING")) and "PROMOTE" not in runtime, "no promote outcome"))

    transients = [path for path in ROOT.rglob("*") if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}]
    checks.append(result("no Python cache artifacts", not transients, str(len(transients))))
    checks.append(result("no nested Git metadata", not (ROOT / ".git").exists(), "single repository root only"))
    license_files = [path for path in ROOT.iterdir() if path.is_file() and path.name.casefold().startswith(("license", "copying"))]
    checks.append(result("no conflicting project-local license", not license_files, "license scope is repository-root only"))

    scan_exclusions = {Path(__file__).resolve()}
    project_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in ROOT.rglob("*")
        if path.is_file() and path not in scan_exclusions and path.suffix.lower() != ".png"
    )
    retired_collision_name = "signal" + "room"
    checks.append(result(
        "retired colliding demo name is absent",
        retired_collision_name not in project_text.casefold(),
        "capability-first generic naming only",
    ))
    secrets = {
        "private key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "bearer token": r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}",
        "GitHub token": r"gh[pousr]_[A-Za-z0-9]{20,}",
        "AWS access key": r"AKIA[0-9A-Z]{16}",
        "generic assigned secret": r"(?i)(?:api[_-]?key|secret[_-]?key|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}",
    }
    for label, pattern in secrets.items():
        checks.append(result(f"project has no {label}", re.search(pattern, project_text) is None, pattern))

    passed = all(checks)
    print(f"OVERALL: {'PASS' if passed else 'FAIL'} ({sum(checks)}/{len(checks)} checks)")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
