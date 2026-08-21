#!/usr/bin/env python3
"""Exercise meaningful demo transitions in headless Firefox."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def report(label: str) -> None:
    print(f"PASS: {label}")


def assert_active_tab_visible(page) -> None:
    geometry = page.locator(".primary-nav").evaluate(
        """nav => {
            const active = nav.querySelector('[data-view].active');
            const navBox = nav.getBoundingClientRect();
            const activeBox = active.getBoundingClientRect();
            return {
                activeLeft: activeBox.left,
                activeRight: activeBox.right,
                navLeft: navBox.left,
                navRight: navBox.right,
                viewportWidth: window.innerWidth,
                pageOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
            };
        }"""
    )
    visible_left = max(0, geometry["navLeft"])
    visible_right = min(geometry["viewportWidth"], geometry["navRight"])
    if geometry["activeLeft"] < visible_left - 1 or geometry["activeRight"] > visible_right + 1:
        raise AssertionError(f"active navigation tab is clipped: {geometry}")
    if geometry["pageOverflow"] > 1:
        raise AssertionError(f"mobile page overflowed horizontally: {geometry}")


def main() -> int:
    remote_requests: list[str] = []
    console_errors: list[str] = []
    url = f"{(ROOT / 'index.html').as_uri()}?view=overview&scenario=baseline#page-top"

    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 960}, accept_downloads=True)
        page.on("request", lambda request: remote_requests.append(request.url) if request.url.startswith(("http:", "https:")) else None)
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.goto(url, wait_until="load")

        expect(page.locator(".disclosure")).to_contain_text("INDEPENDENT PORTFOLIO DEMO")
        expect(page.locator(".disclosure")).to_contain_text("SYNTHETIC DATA")
        report("permanent disclosure is screenshot-visible")

        page.locator('[data-view="discovery"]').click()
        page.locator('[data-toggle-decision="DS-02"]').click()
        expect(page.locator('[data-toggle-decision="DS-02"]')).to_have_text("Confirmed")
        page.locator("[data-discovery-note]").fill("Synthetic owner will review the corrected roster before UAT.")
        page.locator("[data-save-note]").click()
        report("discovery decision and escaped transient note are recorded")

        page.locator('[data-view="readiness"]').click()
        page.locator('[data-readiness-id="RD-02"]').click()
        expect(page.locator(".detail-card")).to_contain_text("In progress")
        page.locator('[data-advance-readiness="RD-02"]').click()
        expect(page.locator(".detail-card")).to_contain_text("Review-ready")
        page.locator('[data-advance-readiness="RD-02"]').click()
        expect(page.locator(".detail-card")).to_contain_text("Ready")
        report("readiness stops at review-ready before a separate reviewer action")

        page.locator('[data-view="exceptions"]').click()
        action = page.locator('[data-advance-exception="EX-17"]')
        action.click()
        expect(page.locator(".detail-card")).to_contain_text("In progress")
        page.locator('[data-advance-exception="EX-17"]').click()
        expect(page.locator(".detail-card")).to_contain_text("Review-ready")
        page.locator('[data-advance-exception="EX-17"]').click()
        expect(page.locator(".detail-card")).to_contain_text("Accepted")
        expect(page.locator(".uat-case").filter(has_text="UAT-04")).to_contain_text("Pass")
        report("exception reproduction advances only through explicit human review")

        page.locator("#scenario-select").select_option("review-ready")
        page.locator('[data-view="exceptions"]').click()
        page.locator('[data-advance-exception="EX-17"]').click()
        page.locator('[data-view="enablement"]').click()
        page.locator('[data-ack-handoff="HO-03"]').click()
        handoff_card = page.locator("section.card").filter(has_text="Customer-owner handoffs")
        expect(handoff_card.locator(".card-head .tag")).to_have_text("4/4 acknowledged")
        report("named receiving-owner handoff becomes explicit")

        page.locator('[data-view="acceptance"]').click()
        page.locator("[data-run-checks]").click()
        expect(page.locator("[data-acceptance-score]")).to_have_text("8/9")
        expect(page.locator('[data-check-id="acceptance"]')).to_contain_text("Needs action")
        report("all prerequisite gates still stop before human go-live acceptance")

        accept_button = page.locator("[data-record-acceptance]")
        expect(accept_button).to_be_enabled()
        accept_button.click()
        expect(page.locator("[data-acceptance-score]")).to_have_text("9/9")
        expect(page.locator(".acceptance-hero")).to_contain_text("Synthetic acceptance recorded")
        report("named synthetic acceptance produces a scoped nine-of-nine state")

        page.locator("[data-show-audit]").click()
        expect(page.locator(".event-list")).to_contain_text("Synthetic go-live acceptance recorded")
        expect(page.locator(".event-list")).to_contain_text("HO-03 handoff acknowledged")
        report("audit trail retains handoff, checks, and acceptance events")

        with page.expect_download() as download_info:
            page.locator("[data-export-audit]").click()
        download = download_info.value
        if download.suggested_filename != "synthetic-first-value-launch-audit.json":
            raise AssertionError(f"unexpected download name: {download.suggested_filename}")
        report("local JSON export requires and responds to a user click")

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.on("request", lambda request: remote_requests.append(request.url) if request.url.startswith(("http:", "https:")) else None)
        mobile.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        mobile.goto(url.replace("view=overview", "view=exceptions"), wait_until="load")
        expect(mobile.locator('[data-view="exceptions"]')).to_have_attribute("aria-current", "page")
        assert_active_tab_visible(mobile)
        mobile.keyboard.press("6")
        expect(mobile.locator('[data-view="acceptance"]')).to_have_attribute("aria-current", "page")
        assert_active_tab_visible(mobile)
        mobile.close()
        report("active mobile tab intersects the navigation viewport on load and view change with zero page overflow")

        if remote_requests:
            raise AssertionError(f"unexpected remote request(s): {remote_requests}")
        if console_errors:
            raise AssertionError(f"browser console error(s): {console_errors}")
        report("complete browser path made zero HTTP(S) requests and logged no errors")
        browser.close()

    print("OVERALL: PASS (11 browser flow checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
