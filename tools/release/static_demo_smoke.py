#!/usr/bin/env python3
"""Run a bounded, write-free Firefox smoke check against one local static demo."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlparse


BOUNDARY = "INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION"
PRODUCT_BOUNDARY = (
    "INDEPENDENT PORTFOLIO DEMO · PUBLIC PRODUCT IDENTITY DATA · "
    "SYNTHETIC PRICING, OPERATOR INPUTS, AND WORKFLOW · "
    "NO AFFILIATION · NO PRODUCTION ACTION"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path)
    parser.add_argument("--allow-click-domain", action="append", default=[])
    args = parser.parse_args()
    html = args.html.resolve()
    if not html.is_file() or html.suffix.lower() != ".html":
        raise SystemExit(f"FAIL: local HTML file not found: {html}")
    expected_boundary = (
        PRODUCT_BOUNDARY
        if html.name == "index.html" and html.parent.name == "public-product-validation"
        else BOUNDARY
    )
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("FAIL: Playwright verification dependency is not installed")

    errors: list[str] = []
    checks = 0
    external_requests: list[str] = []
    console_errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=True)
        try:
            for width, height in ((1440, 960), (390, 844)):
                context = browser.new_context(viewport={"width": width, "height": height})
                page = context.new_page()
                page.on(
                    "request",
                    lambda request: external_requests.append(request.url)
                    if urlparse(request.url).scheme in {"http", "https"}
                    else None,
                )
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
                page.on("pageerror", lambda error: console_errors.append(str(error)))
                page.goto(html.as_uri(), wait_until="load")
                body = page.locator("body").inner_text().strip()
                checks += 1
                if len(body) < 80:
                    errors.append(f"{width}px: body is unexpectedly empty")
                checks += 1
                boundary = page.locator("[data-boundary]")
                if boundary.count() != 1 or boundary.inner_text().strip() != expected_boundary:
                    errors.append(f"{width}px: exact persistent boundary missing or altered")
                checks += 1
                overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                if overflow > 1:
                    errors.append(f"{width}px: horizontal overflow is {overflow}px")
                context.close()
        finally:
            browser.close()
    checks += 1
    if external_requests:
        errors.append(f"automatic HTTP(S) requests: {sorted(set(external_requests))}")
    checks += 1
    if console_errors:
        errors.append(f"console/page errors: {console_errors}")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"PASS: {checks} static-demo checks; disclosure, desktop/mobile layout, console, and automatic network")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
