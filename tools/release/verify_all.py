#!/usr/bin/env python3
"""Run the complete all-12 verification matrix without mutating tracked bytes."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PYTHON = [sys.executable, "-E", "-B"]
PYTHON_PROJECT_PATH = [sys.executable, "-B"]


def tree_snapshot() -> dict[str, tuple[str, int, int, str]]:
    """Bind every release-tree entry except repository metadata."""
    snapshot: dict[str, tuple[str, int, int, str]] = {}
    for path in sorted(ROOT.rglob("*"), key=lambda item: item.relative_to(ROOT).as_posix()):
        relative = path.relative_to(ROOT)
        if relative.parts and relative.parts[0] == ".git":
            continue
        key = relative.as_posix()
        metadata = path.lstat()
        mode = metadata.st_mode & 0o777
        if path.is_symlink():
            snapshot[key] = ("symlink", mode, metadata.st_size, os.readlink(path))
        elif path.is_dir():
            snapshot[key] = ("directory", mode, 0, "")
        elif path.is_file():
            value = hashlib.sha256()
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    value.update(block)
            snapshot[key] = ("file", mode, metadata.st_size, value.hexdigest())
        else:
            snapshot[key] = ("special", mode, metadata.st_size, "")
    return snapshot


def immutable_tree(before: dict[str, tuple[str, int, int, str]]) -> tuple[str, bool, str]:
    after = tree_snapshot()
    changed = [path for path in sorted(set(before) | set(after)) if before.get(path) != after.get(path)]
    return "immutable-tree", not changed, f"changed={changed}"


def sanitized_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("PYTHON")
    }
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONUTF8"] = "1"
    if extra:
        environment.update(extra)
    return environment


def command(
    label: str,
    argv: list[str],
    cwd: Path = ROOT,
    contains: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> tuple[str, bool, str]:
    environment = sanitized_environment(extra_env)
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return label, False, f"execution error: {error}"
    combined = result.stdout + result.stderr
    passed = result.returncode == 0 and (contains is None or contains in combined)
    detail = f"exit={result.returncode}"
    if contains is not None:
        detail += f" expected={contains!r} observed={contains in combined}"
    if not passed:
        detail += f"\n{combined[-5000:]}"
    return label, passed, detail


def no_transients() -> tuple[str, bool, str]:
    found = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if relative.parts and relative.parts[0] == ".git":
            continue
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            found.append(relative.as_posix())
    return "clean-tree", not found, f"transients={found}"


def hitl_gui_smoke() -> tuple[str, bool, str]:
    project = ROOT / "projects" / "human-in-the-loop-control"
    tracked_log = project / "demos" / "hitl-desktop" / "last_run_log.txt"
    with tempfile.TemporaryDirectory(prefix="hitl-release-smoke-") as directory:
        log_path = Path(directory) / "hitl-smoke.log"
        gui_prefix = ["xvfb-run", "-a"] if shutil.which("xvfb-run") else []
        if not gui_prefix and not os.environ.get("DISPLAY"):
            return "hitl-native-smoke", False, "neither xvfb-run nor a graphical DISPLAY is available"
        result = command(
            "hitl-native-smoke",
            [
                *gui_prefix,
                *PYTHON,
                "demos/hitl-desktop/smoke_test.py",
                "--log-path",
                str(log_path),
            ],
            project,
            "OVERALL PASS",
        )
        if not result[1]:
            return result
        if not log_path.is_file() or "HITL GUI SMOKE: PASS" not in log_path.read_text(encoding="utf-8"):
            return result[0], False, "explicit external smoke summary was not written"
        if tracked_log.exists():
            return result[0], False, "GUI smoke wrote the forbidden tracked-tree log"
    return result[0], True, "explicit temporary log verified; tracked-tree writes=0"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", action="store_true")
    parser.add_argument("--allow-owner-gates", action="store_true")
    args = parser.parse_args()
    before = tree_snapshot()

    scans = [
        str(ROOT / "tools" / "release" / "publication_scan.py"),
        "--self-test",
        "--policy",
        str(ROOT / "release-policy.json"),
    ]
    if args.allow_owner_gates:
        scans.append("--allow-owner-gates")
    scans.append(str(ROOT))

    jobs: list[tuple[str, list[str], Path, str | None]] = [
        ("inventory", PYTHON + [str(ROOT / "tools/release/verify_inventory.py"), "--check", str(ROOT / "release-inventory.json")], ROOT, "PASS:"),
        ("publication-scan", PYTHON + scans, ROOT, "PASS:"),
        ("links", PYTHON + [str(ROOT / "tools/release/verify_links.py"), "--root", str(ROOT)], ROOT, "PASS:"),
        ("manifest", PYTHON + [str(ROOT / "tools/release/verify_manifest.py"), str(ROOT / "RELEASE_MANIFEST.sha256")], ROOT, "PASS:"),
        ("lifecycle-unit", PYTHON + ["-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], ROOT / "projects/catalog-lifecycle", "Ran 12 tests"),
        ("interface-unit", PYTHON + ["-m", "unittest", "discover", "-s", "tests", "-v"], ROOT / "projects/interface-contract-harness", "Ran 41 tests"),
        ("claim-unit", PYTHON_PROJECT_PATH + ["-m", "unittest", "discover", "-s", "tests", "-v"], ROOT / "projects/claim-evidence-linter", "Ran 52 tests"),
        ("price-unit", PYTHON + ["-m", "unittest", "discover", "-s", "tests", "-v"], ROOT / "projects/bulk-price-control", "Ran 43 tests"),
        ("migration-unit", PYTHON + ["-m", "unittest", "discover", "-s", "tests", "-v"], ROOT / "projects/catalog-migration-validator", "Ran 40 tests"),
        ("api-unit", PYTHON + ["-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], ROOT / "projects/api-integration-contracts", "Ran 48 tests"),
        ("ai-unit", PYTHON + ["-m", "unittest", "discover", "-s", "tests", "-v"], ROOT / "projects/ai-evaluation-release-gates", "Ran 60 tests"),
        ("readiness-unit", PYTHON + ["-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], ROOT / "projects/implementation-readiness", "Ran 13 tests"),
        ("product-unit", PYTHON + ["-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], ROOT / "projects/public-product-validation", "Ran 19 tests"),
        ("support-unit", PYTHON + ["-m", "unittest", "discover", "-s", "tests", "-v"], ROOT / "projects/support-triage-workbench", "Ran 21 tests"),
        ("hitl-unit", PYTHON + ["-m", "unittest", "discover", "-s", "demos/hitl-desktop", "-p", "test_*.py", "-v"], ROOT / "projects/human-in-the-loop-control", "Ran 15 tests"),
        ("launch-unit", PYTHON + ["-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], ROOT / "projects/customer-launch-readiness", "Ran 14 tests"),
        ("claim-scan", PYTHON + ["tools/audit_project.py"], ROOT / "projects/claim-evidence-linter", "PASS:"),
        ("api-scan", PYTHON + ["scripts/security_privacy_scan.py"], ROOT / "projects/api-integration-contracts", "OVERALL: PASS"),
        ("ai-scan", PYTHON + ["scripts/security_privacy_scan.py"], ROOT / "projects/ai-evaluation-release-gates", "OVERALL: PASS"),
        ("readiness-scan", PYTHON + ["scripts/security_privacy_scan.py"], ROOT / "projects/implementation-readiness", "OVERALL: PASS"),
        ("launch-scan", PYTHON + ["scripts/security_privacy_scan.py"], ROOT / "projects/customer-launch-readiness", "OVERALL: PASS"),
        ("support-scan", PYTHON + ["tools/publication_scan.py"], ROOT / "projects/support-triage-workbench", '"ok": true'),
        ("root-generated", PYTHON + ["tools/release/verify_generated.py", "--root", "."], ROOT, "PASS:"),
        ("interface-generated", PYTHON + ["tools/release/verify_generated.py", "--project", "projects/interface-contract-harness"], ROOT, "PASS:"),
        ("api-generated", PYTHON + ["tools/release/verify_generated.py", "--project", "projects/api-integration-contracts"], ROOT, "PASS:"),
        ("ai-generated", PYTHON + ["tools/release/verify_generated.py", "--project", "projects/ai-evaluation-release-gates"], ROOT, "PASS:"),
        ("product-generated", PYTHON + ["tools/release/verify_generated.py", "--project", "projects/public-product-validation"], ROOT, "PASS:"),
    ]
    if args.browser:
        jobs.extend(
            [
                ("landing-browser", PYTHON + ["tools/release/verify_landing.py"], ROOT, "PASS:"),
                ("lifecycle-browser", PYTHON + ["tools/release/static_demo_smoke.py", "projects/catalog-lifecycle/index.html"], ROOT, "PASS:"),
                ("interface-demo-browser", PYTHON + ["tools/release/static_demo_smoke.py", "projects/interface-contract-harness/demo/index.html"], ROOT, "PASS:"),
                ("interface-report-browser", PYTHON + ["tools/release/static_demo_smoke.py", "projects/interface-contract-harness/build/report.html"], ROOT, "PASS:"),
                ("product-static-browser", PYTHON + ["tools/release/static_demo_smoke.py", "projects/public-product-validation/index.html", "--allow-click-domain", "world.openfoodfacts.org", "--allow-click-domain", "openfoodfacts.github.io", "--allow-click-domain", "opendatacommons.org"], ROOT, "PASS:"),
                ("api-browser", PYTHON + ["scripts/browser_verify.py"], ROOT / "projects/api-integration-contracts", "OVERALL: PASS"),
                ("ai-browser", PYTHON + ["scripts/interaction_smoke.py"], ROOT / "projects/ai-evaluation-release-gates", "OVERALL: PASS"),
                ("readiness-browser", PYTHON + ["scripts/interaction_smoke.py"], ROOT / "projects/implementation-readiness", "OVERALL: PASS"),
                ("launch-browser", PYTHON + ["scripts/interaction_smoke.py"], ROOT / "projects/customer-launch-readiness", "OVERALL: PASS"),
            ]
        )

    results = [
        command(
            label,
            argv,
            cwd,
            expected,
            {"PYTHONPATH": "src"} if label == "claim-unit" else None,
        )
        for label, argv, cwd, expected in jobs
    ]
    if args.browser:
        results.append(hitl_gui_smoke())
    results.extend(
        [
            command("inventory-post", PYTHON + [str(ROOT / "tools/release/verify_inventory.py"), "--check", str(ROOT / "release-inventory.json")], ROOT, "PASS:"),
            command("manifest-post", PYTHON + [str(ROOT / "tools/release/verify_manifest.py"), str(ROOT / "RELEASE_MANIFEST.sha256")], ROOT, "PASS:"),
            no_transients(),
            immutable_tree(before),
        ]
    )
    for label, passed, detail in results:
        print(f"{'PASS' if passed else 'FAIL'}: {label}: {detail}")
    passed = all(item[1] for item in results)
    print(f"OVERALL: {'PASS' if passed else 'FAIL'} ({sum(item[1] for item in results)}/{len(results)} checks)")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
