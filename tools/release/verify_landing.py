#!/usr/bin/env python3
"""Verify the all-12 landing plus product and HITL paths in real Firefox."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]

PUBLIC_COUNT_TEXT = {
    "README.md": (
        "The repository declares 378 deterministic tests and 79 separately counted project browser checks. "
        "`make verify` confirms these counts against the exact tree.",
    ),
    "docs/PROJECT_INDEX.md": (
        "Counts above describe this repository. Exact exported-tree evidence is produced by release verification; "
        "deterministic tests remain separate from browser checks.",
    ),
    "index.html": (
        'aria-label="Verification scope"',
        "<div><dt>378</dt><dd>deterministic tests</dd></div>",
        "<div><dt>79</dt><dd>browser checks</dd></div>",
    ),
}
STALE_PUBLIC_COUNT_WORDING = (
    "frozen source verification scope",
    "frozen-source baseline",
    "frozen source baseline",
)
GLOBAL_BOUNDARY = (
    "INDEPENDENT PORTFOLIO DEMOS · SYNTHETIC WORKFLOWS · "
    "ATTRIBUTED PUBLIC PRODUCT IDENTITY · NO AFFILIATION · NO PRODUCTION ACTION"
)
PRODUCT_BOUNDARY = (
    "INDEPENDENT PORTFOLIO DEMO · PUBLIC PRODUCT IDENTITY DATA · "
    "SYNTHETIC PRICING, OPERATOR INPUTS, AND WORKFLOW · "
    "NO AFFILIATION · NO PRODUCTION ACTION"
)
ASSEMBLED_REPOSITORY_TEXT = {
    "README.md": (
        "The restrictive root `LICENSE` governs owner-created material",
        "third-party material keeps its own separate terms",
    ),
    "CHANGELOG.md": (
        "Applied the restrictive root license and public Git identity",
    ),
    "NOTICE.md": ("The root `LICENSE` governs owner-created material.",),
    "projects/catalog-lifecycle/README.md": (
        "Owner-created files are governed only by the repository root `LICENSE`.",
    ),
    "projects/catalog-lifecycle/PROVENANCE.md": (
        "The root `LICENSE` governs owner-created material.",
    ),
    "projects/support-triage-workbench/README.md": (
        "owner-created material is governed by the common root `LICENSE`",
    ),
    "projects/support-triage-workbench/PROVENANCE.md": (
        "its provenance is recorded in `release-decisions.json`",
    ),
    "projects/human-in-the-loop-control/README.md": (
        "the clean-room provenance is recorded in `release-decisions.json`",
    ),
    "projects/human-in-the-loop-control/PROVENANCE.md": (
        "its clean-room provenance is recorded in `release-decisions.json`",
    ),
    "projects/public-product-validation/README.md": (
        "Owner-created code and documentation are governed by the root `LICENSE`.",
    ),
    "projects/public-product-validation/PROVENANCE.md": (
        "its provenance is recorded in `release-decisions.json`",
        "The third-party data paths remain under their stated ODbL/DbCL terms.",
    ),
    "projects/implementation-readiness/README.md": (
        "Owner-created material is governed by the root `LICENSE`",
    ),
    "projects/implementation-readiness/PROVENANCE.md": (
        "its provenance is recorded in `release-decisions.json`",
    ),
    "projects/customer-launch-readiness/README.md": (
        "Owner-created material is governed by the common root `LICENSE`",
    ),
    "projects/customer-launch-readiness/PROVENANCE.md": (
        "its provenance is recorded in `release-decisions.json`",
    ),
}
STALE_PREBUILD_TEXT = (
    "This override packet supplies neither the owner-controlled root license",
    "Kept owner-controlled licensing, Git identity",
    "when supplied through an approved release decision",
    "This override packet supplies no root license",
    "only after the owner installs an approved license",
    "Public inclusion remains blocked until",
    "public inclusion remains blocked until",
    "becomes releasable only",
    "license selected before release",
)


def verify_public_count_wording() -> None:
    """Bind counts to the repository without banning legitimate frozen-data prose."""
    for relative, required in PUBLIC_COUNT_TEXT.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for phrase in required:
            if text.count(phrase) != 1:
                raise AssertionError(f"public count wording missing or duplicated in {relative}: {phrase!r}")
        lowered = text.lower()
        for stale in STALE_PUBLIC_COUNT_WORDING:
            if stale in lowered:
                raise AssertionError(f"stale public count wording remains in {relative}: {stale!r}")


def verify_assembled_repository_wording() -> None:
    """Reject construction-phase license/provenance claims on the exact public surfaces."""
    for relative, required in ASSEMBLED_REPOSITORY_TEXT.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for phrase in required:
            if text.count(phrase) != 1:
                raise AssertionError(
                    f"assembled-repository wording missing or duplicated in {relative}: {phrase!r}"
                )
        for phrase in STALE_PREBUILD_TEXT:
            if phrase in text:
                raise AssertionError(f"stale pre-build wording remains in {relative}: {phrase!r}")


def main() -> int:
    verify_public_count_wording()
    verify_assembled_repository_wording()
    try:
        from playwright.sync_api import expect, sync_playwright
    except ImportError:
        raise SystemExit("FAIL: Playwright verification dependency is not installed")

    errors: list[str] = []
    checks = 0
    requests: list[str] = []
    console_errors: list[str] = []

    def listen(page: object) -> None:
        page.on(
            "request",
            lambda request: requests.append(request.url)
            if urlparse(request.url).scheme in {"http", "https"}
            else None,
        )
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on("pageerror", lambda error: console_errors.append(str(error)))

    def check(condition: bool, message: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            errors.append(message)

    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=True)
        try:
            landing = browser.new_page(viewport={"width": 1440, "height": 960})
            listen(landing)
            landing.goto((ROOT / "index.html").as_uri(), wait_until="load")
            landing.wait_for_function("document.body.dataset.renderState === 'ready'")
            expect(landing.locator("[data-boundary]")).to_have_text(GLOBAL_BOUNDARY)
            check(
                landing.locator("[data-boundary]").count() == 1
                and "SYNTHETIC WORKFLOWS" in landing.locator("[data-boundary]").inner_text()
                and "ATTRIBUTED PUBLIC PRODUCT IDENTITY" in landing.locator("[data-boundary]").inner_text()
                and "NO AFFILIATION" in landing.locator("[data-boundary]").inner_text(),
                "permanent landing disclosure missing",
            )
            check(
                landing.locator("a.eyebrow").inner_text().strip()
                == "SYSTEMS IMPLEMENTATION PORTFOLIO",
                "landing identity-neutral portfolio label drifted",
            )
            check(landing.locator("article[data-project-id]").count() == 12, "landing does not render twelve projects")
            evidence_strip = landing.locator(".evidence-strip")
            check(
                evidence_strip.get_attribute("aria-label") == "Verification scope"
                and evidence_strip.locator("dt").all_inner_texts() == ["12", "378", "79", "0"]
                and evidence_strip.locator("dd").all_inner_texts() == [
                    "curated projects", "deterministic tests", "browser checks", "runtime services"
                ],
                "landing evidence strip does not bind 378/79 to the repository",
            )
            landing.wait_for_function("[...document.images].every(image => image.complete && image.naturalWidth > 0)")
            check(landing.locator("article[data-project-id] img").count() == 7, "landing does not render seven reviewed previews")
            cards = landing.locator("article[data-project-id]").all()
            ids = [card.get_attribute("data-project-id") for card in cards]
            check(
                ids[:3] == ["api-integration-contracts", "public-product-validation", "human-in-the-loop-control"],
                f"featured order drifted: {ids[:3]}",
            )
            for name, expected_count in (("integration", 1), ("governance", 2), ("catalog", 4), ("quality", 1), ("operations", 4)):
                landing.locator(f'button[data-filter="{name}"]').click()
                check(landing.locator("article[data-project-id]").count() == expected_count, f"{name} filter count is not {expected_count}")
            landing.locator('button[data-filter="all"]').click()
            check(landing.locator("article[data-project-id]").count() == 12, "all filter did not restore twelve cards")
            hrefs = landing.locator("a").evaluate_all("nodes => nodes.map(node => node.getAttribute('href'))")
            check(not any((href or "").startswith(("http://", "https://")) for href in hrefs), "landing contains a remote route")

            mobile = browser.new_page(viewport={"width": 390, "height": 844})
            listen(mobile)
            mobile.goto((ROOT / "index.html").as_uri(), wait_until="load")
            mobile.wait_for_function("document.body.dataset.renderState === 'ready'")
            check(mobile.locator("article[data-project-id]").count() == 12, "mobile landing does not render twelve projects")
            check(mobile.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1, "390px landing overflows horizontally")

            product = browser.new_page(viewport={"width": 1440, "height": 960})
            listen(product)
            product.goto(f"{(ROOT / 'projects/public-product-validation/index.html').as_uri()}?view=intake", wait_until="load")
            expect(product.locator("[data-boundary]")).to_have_text(PRODUCT_BOUNDARY)
            for phrase in (
                "INDEPENDENT PORTFOLIO DEMO",
                "PUBLIC PRODUCT IDENTITY DATA",
                "SYNTHETIC PRICING, OPERATOR INPUTS, AND WORKFLOW",
                "NO AFFILIATION",
                "NO PRODUCTION ACTION",
            ):
                expect(product.locator(".truth-ribbon")).to_contain_text(phrase)
                expect(product.locator("#public-boundary-title").locator("xpath=..")).to_contain_text(phrase)
            check("SYNTHETIC DATA" not in product.locator("body").inner_text(), "product boundary falsely labels public identity records as synthetic")
            expect(product.locator(".license-note")).to_contain_text("every price and operation is synthetic")
            expect(product.locator(".license-note")).to_contain_text("No live writes")
            product.locator('[data-action="parse-input"]').click()
            expect(product.locator("tbody [data-record-id]")).to_have_count(9)
            expect(product.locator("table")).to_contain_text("Synthetic price (not sourced from Open Food Facts)")
            product.locator('[data-filter="conflict"]').click()
            expect(product.locator("tbody [data-record-id]")).to_have_count(2)
            product.locator("tbody [data-record-id]").first.click()
            product.locator('[data-action="review-selected"]').click()
            expect(product.locator('input[name="decision"][value="stage"]')).to_be_disabled()
            product.locator('[data-review-id="DEMO-SUB-01"]').click()
            stage = product.locator('input[name="decision"][value="stage"]')
            expect(stage).to_be_enabled()
            stage.check()
            product.locator("#decision-ack").check()
            product.locator("#record-decision").click()
            expect(product.locator(".decision-receipt")).to_contain_text("External writes: 0")
            product.locator('[data-view="evidence"]').click()
            expect(product.locator("#main-content")).to_contain_text("ODbL")
            expect(product.locator(".hash-box")).to_contain_text("2bd27bdbb6b89e323ec1083dd01f0962f6c73a8df1da0a172a2c7e3bb0f1c9fb")
            checks += 12

            hitl = browser.new_page(viewport={"width": 1440, "height": 960})
            listen(hitl)
            hitl.goto((ROOT / "projects/human-in-the-loop-control/preview/index.html").as_uri(), wait_until="load")
            expect(hitl.locator(".boundary")).to_contain_text("NO PRODUCTION ACTION")
            expect(hitl.locator("#rows tr")).to_have_count(5)
            expect(hitl.locator('[data-action="approve"]')).to_be_disabled()
            hitl.locator('[data-action="resolve"]').click()
            expect(hitl.locator("#metric-held")).to_have_text("2")
            duplicate_row = hitl.locator('[data-request-id="LAB-REQ-005"]')
            expect(duplicate_row).to_contain_text("Held: duplicate barcode submission")
            expect(duplicate_row).to_contain_text("HELD")
            hitl.locator('[data-action="validate"]').click()
            expect(hitl.locator("#metric-held")).to_have_text("1")
            hitl.locator('[data-action="stage"]').click()
            hitl.locator("#mismatch").check()
            hitl.locator('[data-action="verify"]').click()
            expect(hitl.locator("#metric-gate-detail")).to_have_text("reread mismatch")
            expect(hitl.locator('[data-action="approve"]')).to_be_disabled()
            hitl.locator('[data-action="reset"]').click()
            for action in ("resolve", "validate", "stage", "verify"):
                hitl.locator(f'[data-action="{action}"]').click()
            expect(hitl.locator("#metric-gate")).to_have_text("HUMAN")
            expect(hitl.locator('[data-action="approve"]')).to_be_enabled()
            hitl.locator('[data-action="approve"]').click()
            expect(hitl.locator("#metric-gate")).to_have_text("APPROVED")
            expect(duplicate_row).to_contain_text("Held: duplicate barcode submission")
            expect(duplicate_row).to_contain_text("HELD")
            expect(hitl.locator("#audit")).to_contain_text("only in-memory demo state changed")
            checks += 15

            for label, path in {
                "implementation-readiness": ROOT / "projects/implementation-readiness/index.html",
                "customer-launch-readiness": ROOT / "projects/customer-launch-readiness/index.html",
                "public-product-validation": ROOT / "projects/public-product-validation/index.html",
                "human-in-the-loop-control": ROOT / "projects/human-in-the-loop-control/preview/index.html",
            }.items():
                mobile.goto(path.as_uri(), wait_until="load")
                width = mobile.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                check(width <= 1, f"390px {label} overflow is {width}px")
        finally:
            browser.close()

    check(not requests, f"automatic HTTP(S) requests: {sorted(set(requests))}")
    check(not console_errors, f"console/page errors: {console_errors}")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"PASS: {checks} all-12 landing/product/HITL checks; seven previews, mobile layout, zero network/errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
