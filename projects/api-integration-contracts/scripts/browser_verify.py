#!/usr/bin/env python3
"""Exercise the complete offline lab flow in Playwright Firefox."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def passed(label: str) -> None:
    print(f"PASS: {label}")


def main() -> int:
    remote_requests: list[str] = []
    console_errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 960}, reduced_motion="reduce")
        page.on("request", lambda request: remote_requests.append(request.url) if request.url.startswith(("http:", "https:")) else None)
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)

        page.goto(f"{(ROOT / 'index.html').as_uri()}?view=gate&scenario=promoted", wait_until="load")
        expect(page.locator("[data-boundary]")).to_have_text(
            "INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION"
        )
        passed("exact persistent portfolio boundary is visible")

        expect(page.locator("[data-promote]")).to_be_disabled()
        expect(page.locator("main")).not_to_contain_text("Simulated promotion recorded")
        passed("URL query cannot prefill or bypass the human gate")

        page.locator('[data-view="exchange"]').click()
        expect(page.locator(".attempt-card")).to_have_count(3)
        expect(page.locator(".retry-strip")).to_contain_text("2s / 4s")
        expect(page.locator("main")).to_contain_text("no socket opens")
        passed("429 fixtures render the exact 2s/4s virtual recovery and zero-live-call boundary")

        page.locator('[data-view="inbox"]').click()
        expect(page.locator(".event-row")).to_have_count(7)
        page.locator('[data-inbox-filter="duplicate"]').click()
        expect(page.locator(".event-row")).to_have_count(1)
        expect(page.locator("main")).to_contain_text("idempotency key seen")
        passed("inbox exposes deterministic duplicate suppression")

        page.locator('[data-inbox-filter="quarantine"]').click()
        expect(page.locator(".event-row")).to_have_count(4)
        page.locator("[data-inbox-search]").fill("corr_04de56fa")
        expect(page.locator(".event-row")).to_have_count(1)
        expect(page.locator("main")).to_contain_text("data fields")
        passed("inbox filter/search isolates the schema-drift evidence")

        page.locator('[data-view="quarantine"]').click()
        page.locator('[data-quarantine-id="delivery_demo_003"]').click()
        expect(page.locator("main")).to_contain_text("never bypass HMAC")
        expect(page.locator("main")).to_contain_text("hmac_mismatch")
        passed("quarantine preserves distinct failure reason and bounded recovery")

        page.locator('[data-view="gate"]').click()
        token = page.locator(".gate-control code").inner_text()
        expect(page.locator("[data-promote]")).to_be_disabled()
        page.locator("[data-gate-token]").fill(token)
        expect(page.locator("[data-promote]")).to_be_disabled()
        page.locator("[data-gate-ack]").check()
        expect(page.locator("[data-promote]")).to_be_enabled()
        passed("exact token plus explicit personal-project acknowledgement are both required")

        page.locator("[data-promote]").click()
        expect(page.locator("main")).to_contain_text("Simulated promotion recorded")
        expect(page.locator("main")).to_contain_text("production_write=false")
        passed("human action records only a browser-memory simulated promotion")

        page.locator('[data-view="audit"]').click()
        expect(page.locator("main")).to_contain_text("Browser promotion is intentionally not inserted into the base hash chain")
        expect(page.locator(".audit-list li")).to_have_count(7)
        expect(page.locator("footer")).to_contain_text("base receipt preserved")
        passed("audit view keeps the verified base chain distinct from browser state")

        page.locator("#reset-demo").click()
        expect(page).to_have_title("Contract map — Contract Lab")
        expect(page.locator("footer")).to_contain_text("Base receipt · 11 hash-linked events")
        passed("reset clears transient promotion state and returns to the contract map")

        mobile = browser.new_page(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
        mobile.on("request", lambda request: remote_requests.append(request.url) if request.url.startswith(("http:", "https:")) else None)
        mobile.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        mobile.goto((ROOT / "index.html").as_uri(), wait_until="load")
        overflow = mobile.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
        if overflow:
            raise AssertionError("390px layout has horizontal overflow")
        passed("390px responsive layout has no horizontal overflow")
        mobile.close()

        if remote_requests:
            raise AssertionError(f"unexpected HTTP(S) request(s): {remote_requests}")
        if console_errors:
            raise AssertionError(f"browser console error(s): {console_errors}")
        passed("complete browser flow made zero HTTP(S) requests and logged no errors")
        browser.close()

    print("OVERALL: PASS (12 browser flow checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
