"""A strict, non-rendering HTML parser for bounded synthetic fixtures."""

from __future__ import annotations

import re
from html.parser import HTMLParser

from .model import ContractInputError, Document, Element

MAX_HTML_BYTES = 131_072
MAX_ELEMENTS = 4_096
MAX_DEPTH = 128
MAX_ATTRIBUTES = 64
MAX_ATTRIBUTE_VALUE = 8_192

# Explicit HTML vocabulary. Unknown elements are rejected so new platform surface
# cannot silently bypass a contract. This is a fixture parser, not a browser.
KNOWN_ELEMENTS = frozenset(
    "a abbr address area article aside audio b base bdi bdo blockquote body br "
    "button canvas caption cite code col colgroup data datalist dd del details dfn "
    "dialog div dl dt em embed fieldset figcaption figure footer form h1 h2 h3 h4 "
    "h5 h6 head header hgroup hr html i iframe img input ins kbd label legend li "
    "link main map mark menu meta meter nav noscript object ol optgroup option output "
    "p param picture pre progress q rp rt ruby s samp script search section select slot small "
    "source span strong style sub summary sup table tbody td template textarea tfoot "
    "th thead time title tr track u ul var video wbr".split()
)
VOID_ELEMENTS = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)
ATTRIBUTE_NAME = re.compile(r"^[a-z_:][a-z0-9_.:-]*$")


class _StrictHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[Element] = []
        self.root: Element | None = None
        self.doctype_seen = False
        self.element_count = 0
        self._closed_root = False

    def _fail(self, message: str) -> None:
        line, column = self.getpos()
        raise ContractInputError(f"HTML parse error at {line}:{column}: {message}")

    def handle_decl(self, decl: str) -> None:
        if decl.strip().lower() != "doctype html":
            self._fail("only <!doctype html> is accepted")
        if self.doctype_seen or self.root is not None:
            self._fail("doctype must occur once before the root element")
        self.doctype_seen = True

    def unknown_decl(self, data: str) -> None:
        self._fail("unknown declaration")

    def handle_pi(self, data: str) -> None:
        self._fail("processing instructions are not accepted")

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self._open(tag, attrs, self_closing=False)

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag.lower() not in VOID_ELEMENTS:
            self._fail("only void elements may use self-closing syntax")
        self._open(tag, attrs, self_closing=True)

    def _open(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
        *,
        self_closing: bool,
    ) -> None:
        tag = tag.lower()
        if tag not in KNOWN_ELEMENTS:
            self._fail(f"unknown element <{tag}>")
        if self._closed_root:
            self._fail("content is not allowed after </html>")
        if len(attrs) > MAX_ATTRIBUTES:
            self._fail(f"<{tag}> exceeds the {MAX_ATTRIBUTES}-attribute limit")
        normalized: dict[str, str | None] = {}
        for raw_name, value in attrs:
            name = raw_name.lower()
            if not ATTRIBUTE_NAME.fullmatch(name):
                self._fail(f"invalid attribute name {raw_name!r}")
            if name in normalized:
                self._fail(f"duplicate attribute {name!r} on <{tag}>")
            if value is not None and len(value) > MAX_ATTRIBUTE_VALUE:
                self._fail(f"attribute {name!r} exceeds the value limit")
            normalized[name] = value

        line, column = self.getpos()
        parent = self.stack[-1] if self.stack else None
        if parent is None:
            if self.root is not None:
                self._fail("exactly one root element is required")
            if tag != "html":
                self._fail("the root element must be <html>")
        elif tag == "html":
            self._fail("nested <html> is not accepted")

        element = Element(tag, normalized, line, column, parent)
        self.element_count += 1
        if self.element_count > MAX_ELEMENTS:
            self._fail(f"document exceeds the {MAX_ELEMENTS}-element limit")
        if parent is None:
            self.root = element
        else:
            parent.content.append(element)

        if tag not in VOID_ELEMENTS and not self_closing:
            self.stack.append(element)
            if len(self.stack) > MAX_DEPTH:
                self._fail(f"document exceeds the {MAX_DEPTH}-element depth limit")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in VOID_ELEMENTS:
            self._fail(f"void element </{tag}> must not have an end tag")
        if not self.stack:
            self._fail(f"unexpected closing tag </{tag}>")
        expected = self.stack[-1].tag
        if tag != expected:
            self._fail(f"mismatched closing tag </{tag}>; expected </{expected}>")
        self.stack.pop()
        if tag == "html":
            self._closed_root = True

    def handle_data(self, data: str) -> None:
        if not self.stack:
            if data.strip():
                if self._closed_root:
                    self._fail("content is not allowed after </html>")
                self._fail("text is not allowed outside the root element")
            return
        self.stack[-1].content.append(data)

    def close_document(self) -> Document:
        super().close()
        if self.root is None:
            raise ContractInputError("HTML parse error: missing <html> root")
        if not self.doctype_seen:
            raise ContractInputError("HTML parse error: missing <!doctype html>")
        if self.stack:
            tags = ", ".join(f"<{item.tag}>" for item in self.stack)
            raise ContractInputError(f"HTML parse error: unclosed elements: {tags}")
        if not self._closed_root:
            raise ContractInputError("HTML parse error: missing </html>")
        return Document(self.root, self.doctype_seen)


def parse_html(raw: bytes) -> Document:
    """Parse one complete fixture without executing, fetching, or rendering it."""

    if len(raw) > MAX_HTML_BYTES:
        raise ContractInputError(
            f"HTML input exceeds the {MAX_HTML_BYTES}-byte fixture limit"
        )
    if b"\x00" in raw:
        raise ContractInputError("HTML input contains a NUL byte")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ContractInputError("HTML input must be valid UTF-8") from exc
    parser = _StrictHTMLParser()
    try:
        parser.feed(text)
        return parser.close_document()
    except ContractInputError:
        raise
    except Exception as exc:  # HTMLParser failures are normalized and fail closed.
        raise ContractInputError(f"HTML parser rejected the fixture: {exc}") from exc
