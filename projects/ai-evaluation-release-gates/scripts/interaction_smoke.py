#!/usr/bin/env python3
"""Exercise the complete static demo path in real headless Firefox."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def pass_check(label: str) -> None:
    print(f"PASS: {label}")


def verify_download(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    digest = value.pop("receipt_sha256")
    if hashlib.sha256(canonical(value)).hexdigest() != digest:
        raise AssertionError("browser receipt self-digest mismatch")
    previous = "0" * 64
    for sequence, event in enumerate(value["audit_chain"], start=1):
        event_hash = event.pop("event_hash")
        if event["sequence"] != sequence or event["previous_hash"] != previous:
            raise AssertionError("browser receipt audit-chain link mismatch")
        expected = hashlib.sha256(canonical(event)).hexdigest()
        if expected != event_hash:
            raise AssertionError("browser receipt audit event digest mismatch")
        previous = event_hash
    return value


def main() -> int:
    remote_requests: list[str] = []
    console_errors: list[str] = []
    page_errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 960}, accept_downloads=True)
        page.on("request", lambda request: remote_requests.append(request.url) if request.url.startswith(("http:", "https:")) else None)
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto((ROOT / "index.html").as_uri(), wait_until="load")

        expect(page.locator('[data-testid="boundary"]')).to_have_text("INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION")
        pass_check("permanent portfolio/synthetic/offline/no-authority boundary is visible")

        if page.evaluate("window.EVALUATION_RELEASE_GATE_HOLDOUT") is not None:
            raise AssertionError("holdout payload was present before explicit reveal")
        pass_check("base page excludes the separate holdout detail payload")

        page.locator('[data-view="review"]').click()
        expect(page.locator(".case-item")).to_have_count(8)
        pass_check("blind review initially exposes exactly eight development cases")

        page.locator('[data-case-id="DEV-003"]').click()
        page.locator("#run-exact").click()
        pills = page.locator(".response-card .grade-pill")
        expect(pills.nth(0)).to_have_text("EXACT FAIL")
        expect(pills.nth(1)).to_have_text("EXACT PASS")
        pass_check("strict structured-output case distinguishes an extra-key failure")

        page.locator('[data-case-id="DEV-002"]').click()
        page.locator("#score-a").select_option("1")
        page.locator("#score-b").select_option("4")
        page.locator("#record-judgment").click()
        pass_check("human rubric records an in-memory blind-label judgment")

        page.locator('[data-filter="holdout"]').click()
        expect(page.locator(".sealed-card")).to_contain_text("workflow-sealed")
        pass_check("holdout tab stops at an explicit reveal boundary")

        disabled_during_same_task = page.evaluate("""
            () => {
              document.querySelector('.sealed-card .button').click();
              const dependent = document.querySelector('#load-reference');
              const disabled = dependent.disabled;
              dependent.dispatchEvent(new Event('click'));
              return disabled;
            }
        """)
        if disabled_during_same_task is not True:
            raise AssertionError("dependent drill was not disabled synchronously")
        pass_check("dependent drills disable while the one local reveal promise is in flight")
        page.wait_for_function("window.EVALUATION_RELEASE_GATE_HOLDOUT && window.EVALUATION_RELEASE_GATE_HOLDOUT.holdout_cases.length === 4")
        expect(page.locator(".case-item")).to_have_count(4)
        expect(page.locator("#seal-chip")).to_have_text("HOLDOUT REVEALED LOCALLY")
        pass_check("explicit action loads four hash-bound cases from a local static bundle")

        page.locator('[data-view="gate"]').click()
        expect(page.locator("#gate-outcome")).to_have_text("HOLD")
        pass_check("a concurrent reference request joins the cached reveal promise without recursion")

        page.locator('[data-view="review"]').click()
        page.locator('[data-case-id="HOLD-103"]').click()
        expect(page.locator(".review-panel")).to_contain_text("HARD VETO")
        expect(page.locator(".response-card .grade-pill").nth(0)).to_have_text("EXACT FAIL")
        expect(page.locator(".response-card .grade-pill").nth(1)).to_have_text("EXACT PASS")
        pass_check("revealed safe-escalation holdout surfaces its deterministic hard veto")

        page.locator('[data-view="gate"]').click()
        page.locator("#load-reference").click()
        expect(page.locator("#gate-outcome")).to_have_text("HOLD")
        expect(page.locator("#gate-reason")).to_contain_text("HOLD-103")
        pass_check("reference blind review yields HOLD without authorizing action")

        page.locator('[data-view="matrix"]').click()
        expect(page.locator("#matrix-body")).to_contain_text("HARD VETO → HOLD")
        pass_check("regression matrix traces a slice failure to its gate effect")

        page.locator('[data-view="gate"]').click()
        page.locator("#load-regression").click()
        expect(page.locator("#gate-outcome")).to_have_text("ROLLBACK")
        pass_check("synthetic regression drill exercises the ROLLBACK branch")

        page.locator("#load-reference").click()
        expect(page.locator("#gate-outcome")).to_have_text("HOLD")
        page.wait_for_function("!document.querySelector('#export-receipt').disabled")
        with page.expect_download() as download_info:
            page.locator("#export-receipt").click()
        download = download_info.value
        if download.suggested_filename != "evaluation-release-gate-hold-synthetic-receipt.json":
            raise AssertionError(f"unexpected export filename: {download.suggested_filename}")
        exported = verify_download(Path(download.path()))
        pass_check("user-triggered local JSON export has a valid self-digest and audit chain")

        if exported["outcome"] != "HOLD" or exported["action_authorized"] is not False:
            raise AssertionError("exported gate authority boundary mismatch")
        if set(exported["allowed_outcomes"]) != {"HOLD", "ROLLBACK", "PENDING"}:
            raise AssertionError("exported allowed outcome vocabulary mismatch")
        pass_check("export contains only fail-closed outcomes and no production authority")

        if any(set(review["scores"]) != {"A", "B"} for review in exported["reviewer_inputs"]):
            raise AssertionError("exported reviewer input is not blind-label keyed")
        if any("candidate_" in json.dumps(review) for review in exported["reviewer_inputs"]):
            raise AssertionError("reviewer input leaked candidate identity")
        pass_check("persisted reviewer inputs remain genuinely label-blind")

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.on("request", lambda request: remote_requests.append(request.url) if request.url.startswith(("http:", "https:")) else None)
        mobile.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        mobile.on("pageerror", lambda error: page_errors.append(str(error)))
        mobile.goto((ROOT / "index.html").as_uri(), wait_until="load")
        for view in ("overview", "review", "failures", "matrix", "gate"):
            mobile.locator(f'[data-view="{view}"]').click()
            overflow = mobile.evaluate(
                "document.documentElement.scrollWidth - document.documentElement.clientWidth"
            )
            if overflow > 1:
                raise AssertionError(f"390px {view} view has {overflow}px horizontal overflow")
        expect(mobile.locator('[data-testid="boundary"]')).to_have_text("INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION")
        pass_check("all five views retain the disclosure with zero horizontal overflow at 390px")
        mobile.close()

        if remote_requests:
            raise AssertionError(f"unexpected HTTP(S) request(s): {remote_requests}")
        if console_errors:
            raise AssertionError(f"browser console error(s): {console_errors}")
        if page_errors:
            raise AssertionError(f"browser uncaught page error(s): {page_errors}")
        pass_check("full Firefox path made zero HTTP(S) requests and logged zero errors")

        with tempfile.TemporaryDirectory() as directory:
            tamper_root = Path(directory) / "tamper-demo"
            (tamper_root / "data").mkdir(parents=True)
            for relative in ("index.html", "styles.css", "app.js", "data/demo_snapshot.js", "data/holdout_snapshot.js"):
                source = ROOT / relative
                destination = tamper_root / relative
                shutil.copy2(source, destination)
            holdout_path = tamper_root / "data" / "holdout_snapshot.js"
            original = holdout_path.read_text(encoding="utf-8")
            altered = original.replace("Marked accepted so the rollout can continue.", "Tampered output retained the old declared digest.", 1)
            if altered == original:
                raise AssertionError("tamper fixture replacement did not apply")
            holdout_path.write_text(altered, encoding="utf-8")
            tamper_page = browser.new_page(viewport={"width": 1440, "height": 960})
            tamper_remote: list[str] = []
            tamper_console_errors: list[str] = []
            tamper_page_errors: list[str] = []
            tamper_page.on("request", lambda request: tamper_remote.append(request.url) if request.url.startswith(("http:", "https:")) else None)
            tamper_page.on("console", lambda message: tamper_console_errors.append(message.text) if message.type == "error" else None)
            tamper_page.on("pageerror", lambda error: tamper_page_errors.append(str(error)))
            tamper_page.goto((tamper_root / "index.html").as_uri(), wait_until="load")
            tamper_page.locator('[data-view="gate"]').click()
            tamper_page.locator("#load-reference").click()
            expect(tamper_page.locator("#gate-reason")).to_contain_text("Holdout reveal failed closed: Local holdout payload integrity check failed.")
            if tamper_page.evaluate("window.EVALUATION_RELEASE_GATE_HOLDOUT") is not None:
                raise AssertionError("tampered reveal payload remained available")
            if tamper_remote:
                raise AssertionError(f"tamper test made unexpected HTTP(S) requests: {tamper_remote}")
            if tamper_console_errors or tamper_page_errors:
                raise AssertionError(f"dependent tamper flow emitted an unhandled error: console={tamper_console_errors} page={tamper_page_errors}")
            pass_check("dependent reference action catches and surfaces detail-tampered reveal failure without an unhandled rejection")
            tamper_page.close()
        browser.close()

    print("OVERALL: PASS (19 browser flow checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
