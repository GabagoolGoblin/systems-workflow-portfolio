#!/usr/bin/env python3
"""Exercise the complete local workflow in a real browser with Playwright."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def report(label: str) -> None:
    print(f"PASS: {label}")


def main() -> int:
    remote_requests: list[str] = []
    url = f"{(ROOT / 'index.html').as_uri()}?view=overview#page-top"

    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 960}, accept_downloads=True)
        page.on(
            "request",
            lambda request: remote_requests.append(request.url)
            if request.url.startswith(("http:", "https:"))
            else None,
        )
        page.goto(url, wait_until="load")

        expect(page.locator(".disclosure")).to_contain_text("INDEPENDENT PORTFOLIO DEMO")
        report("permanent disclosure is visible")

        page.locator('[data-view="gaps"]').click()
        page.locator('[data-gap-id="GAP-07"]').click()
        expect(page.locator(".detail-card")).to_contain_text("Review period is not declared")
        report("gap can be selected and inspected")

        page.locator('[data-go-action="ACT-204"]').click()
        action = page.locator('[data-advance-action="ACT-204"]')
        expect(action).to_have_text("Start simulated work")
        action.click()
        expect(page.locator('[data-advance-action="ACT-204"]')).to_have_text("Mark review-ready")
        report("queued action advances to in progress")

        page.locator('[data-advance-action="ACT-204"]').click()
        expect(page.locator('[data-advance-action="ACT-204"]')).to_be_disabled()
        report("action completion stops at review-ready")

        page.locator('[data-view="acceptance"]').click()
        page.locator("[data-run-checks]").click()
        expect(page.locator(".result-score")).to_contain_text("6")
        gap_check = page.locator(".check-item").filter(has_text="No unresolved blocker or high gap")
        expect(gap_check).to_contain_text("GAP-07 is review-ready, not accepted")
        report("acceptance run stops at six of seven before human acknowledgment")

        acknowledgment = page.locator("[data-acknowledge]")
        expect(acknowledgment).to_be_enabled()
        acknowledgment.click()
        expect(page.locator(".result-score")).to_contain_text("7")
        expect(gap_check).to_contain_text("GAP-07 reviewer-accepted in this demo")
        report("reviewer acknowledgment produces the scoped seven-of-seven state")

        page.locator('[data-view="evidence"]').click()
        page.locator('[data-evidence-id="EV-102"]').click()
        expect(page.locator(".detail-card")).to_contain_text("Accepted")
        expect(page.locator(".detail-card")).to_contain_text("prior qualification was resolved")
        report("evidence status stays synchronized with the reviewer decision")

        page.locator('[data-view="audit"]').click()
        expect(page.locator(".event-list")).to_contain_text("IR-01 reviewer acknowledgment recorded")
        expect(page.locator(".event-list")).to_contain_text("ACT-204 marked complete")
        report("audit trail retains action and reviewer events")

        with page.expect_download() as download_info:
            page.locator("[data-export-audit]").click()
        download = download_info.value
        if download.suggested_filename != "synthetic-readiness-audit.json":
            raise AssertionError(f"unexpected download name: {download.suggested_filename}")
        report("local synthetic JSON export downloads after a user click")

        if remote_requests:
            raise AssertionError(f"unexpected remote request(s): {remote_requests}")
        report("complete interaction path made zero HTTP(S) requests")
        browser.close()

    print("OVERALL: PASS (10 browser interaction checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
