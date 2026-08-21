#!/usr/bin/env python3
"""Verify local Markdown/HTML links and reject unapproved external link domains."""

from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)")


class References(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(str(values["id"]))
        for name in ("href", "src"):
            if values.get(name):
                self.values.append(str(values[name]))


def markdown_ids(text: str) -> set[str]:
    result: set[str] = set()
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if not match:
            continue
        value = re.sub(r"[^a-z0-9 _-]", "", match.group(1).casefold())
        result.add(re.sub(r"[ _]+", "-", value).strip("-"))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    policy = json.loads((root / "release-policy.json").read_text(encoding="utf-8"))
    allowed_domains = set(policy["allowed_external_link_domains"])
    excluded_prefixes = tuple(policy.get("link_scan_excluded_prefixes", []))
    errors: list[str] = []
    link_count = 0
    for source in sorted(root.rglob("*")):
        relative_source = source.relative_to(root)
        if relative_source.as_posix().startswith(excluded_prefixes):
            continue
        if relative_source.parts and relative_source.parts[0] == ".git":
            continue
        if not source.is_file() or source.is_symlink() or source.suffix.lower() not in {".md", ".html"}:
            continue
        text = source.read_text(encoding="utf-8")
        if source.suffix.lower() == ".html":
            parser_html = References()
            parser_html.feed(text)
            links = parser_html.values
        else:
            links = [match.group(1) for match in MARKDOWN_LINK.finditer(text)]
        for raw in links:
            link_count += 1
            if raw.startswith(("mailto:", "tel:", "javascript:", "data:")):
                errors.append(f"disallowed link scheme in {relative_source.as_posix()}: {raw}")
                continue
            parsed = urlparse(raw)
            if parsed.scheme in {"http", "https"}:
                if parsed.hostname not in allowed_domains:
                    errors.append(f"unapproved external domain in {relative_source.as_posix()}: {parsed.hostname}")
                continue
            if parsed.scheme:
                errors.append(f"unknown link scheme in {relative_source.as_posix()}: {raw}")
                continue
            decoded = unquote(parsed.path)
            if decoded.startswith("/"):
                errors.append(f"absolute repository link in {relative_source.as_posix()}: {raw}")
                continue
            target = source if not decoded else (source.parent / decoded).resolve(strict=False)
            try:
                target.relative_to(root)
            except ValueError:
                errors.append(f"escaping link in {relative_source.as_posix()}: {raw}")
                continue
            if not target.exists():
                errors.append(f"broken link in {relative_source.as_posix()}: {raw}")
                continue
            if parsed.fragment and target.is_file():
                try:
                    target_text = target.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    errors.append(f"fragment targets non-text file in {relative_source.as_posix()}: {raw}")
                    continue
                if target.suffix.lower() == ".html":
                    target_parser = References()
                    target_parser.feed(target_text)
                    anchors = target_parser.ids
                elif target.suffix.lower() == ".md":
                    anchors = markdown_ids(target_text)
                else:
                    anchors = set()
                if unquote(parsed.fragment).casefold() not in {anchor.casefold() for anchor in anchors}:
                    errors.append(f"missing fragment in {relative_source.as_posix()}: {raw}")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"PASS: {link_count} Markdown/HTML links resolve within the approved boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
