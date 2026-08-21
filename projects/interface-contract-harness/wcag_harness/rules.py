"""Explicit, deterministic accessibility-oriented interface contracts."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from .model import Document, Element, Violation

Rule = Callable[[Document], Iterable[Violation]]
LANGUAGE_TAG = re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")
HEADING_LEVEL = {f"h{level}": level for level in range(1, 7)}
ASCII_WHITESPACE = re.compile(r"[\t\n\f\r ]")


def _violation(rule_id: str, element: Element, message: str) -> Violation:
    return Violation(rule_id, element.path(), message, element.line, element.column)


def _normalized(value: str | None) -> str:
    return " ".join((value or "").split())


def _id_index(document: Document) -> dict[str, Element]:
    return {
        value: element
        for element in document.elements()
        if (value := element.attrs.get("id")) is not None
        and value != ""
        and not ASCII_WHITESPACE.search(value)
    }


def _ancestor(element: Element, tag: str) -> Element | None:
    parent = element.parent
    while parent is not None:
        if parent.tag == tag:
            return parent
        parent = parent.parent
    return None


def _accessible_name(
    element: Element, document: Document, *, include_labels: bool = False
) -> str:
    direct = _normalized(element.attrs.get("aria-label"))
    if direct:
        return direct
    references = _normalized(element.attrs.get("aria-labelledby")).split()
    if references:
        index = _id_index(document)
        referenced_text = " ".join(
            index[item].text_content() for item in references if item in index
        )
        if _normalized(referenced_text):
            return _normalized(referenced_text)
    if include_labels:
        element_id = _normalized(element.attrs.get("id"))
        if element_id:
            for candidate in document.elements():
                if (
                    candidate.tag == "label"
                    and _normalized(candidate.attrs.get("for")) == element_id
                    and candidate.text_content()
                ):
                    return candidate.text_content()
        wrapping_label = _ancestor(element, "label")
        if wrapping_label is not None and wrapping_label.text_content():
            return wrapping_label.text_content()
    if element.tag == "input":
        kind = _normalized(element.attrs.get("type")).lower() or "text"
        if kind in {"button", "submit", "reset"}:
            value = _normalized(element.attrs.get("value"))
            if value:
                return value
        if kind == "image":
            alt = _normalized(element.attrs.get("alt"))
            if alt:
                return alt
    if element.tag in {"button", "a"} or _normalized(
        element.attrs.get("role")
    ).lower() in {
        "button",
        "link",
    }:
        if element.text_content():
            return element.text_content()
    return _normalized(element.attrs.get("title"))


def document_language(document: Document) -> Iterable[Violation]:
    value = _normalized(document.root.attrs.get("lang"))
    if not value:
        yield _violation(
            "document-language", document.root, "<html> must declare a lang value"
        )
    elif not LANGUAGE_TAG.fullmatch(value):
        yield _violation(
            "document-language",
            document.root,
            "lang must match the harness's bounded language-tag syntax",
        )


def unique_id(document: Document) -> Iterable[Violation]:
    seen: set[str] = set()
    for element in document.elements():
        if "id" not in element.attrs:
            continue
        value = element.attrs.get("id") or ""
        if not value or ASCII_WHITESPACE.search(value):
            yield _violation(
                "unique-id",
                element,
                "id must be non-empty and contain no ASCII whitespace",
            )
        elif value in seen:
            yield _violation("unique-id", element, f"duplicate id {value!r}")
        else:
            seen.add(value)


def image_alternative(document: Document) -> Iterable[Violation]:
    for element in document.elements():
        if element.tag == "img" and "alt" not in element.attrs:
            yield _violation(
                "image-alternative",
                element,
                "img must declare alt; alt=\"\" is accepted for declared decoration",
            )


def interactive_name(document: Document) -> Iterable[Violation]:
    for element in document.elements():
        is_link = element.tag == "a" and "href" in element.attrs
        is_button = element.tag == "button"
        has_role = _normalized(element.attrs.get("role")).lower() in {"button", "link"}
        if (is_link or is_button or has_role) and not _accessible_name(element, document):
            yield _violation(
                "interactive-name", element, "interactive element has no accessible name"
            )


def form_control_name(document: Document) -> Iterable[Violation]:
    for element in document.elements():
        if element.tag not in {"input", "select", "textarea"}:
            continue
        kind = _normalized(element.attrs.get("type")).lower() or "text"
        if element.tag == "input" and kind == "hidden":
            continue
        if not _accessible_name(element, document, include_labels=True):
            yield _violation(
                "form-control-name", element, "form control has no accessible name"
            )


def aria_reference_integrity(document: Document) -> Iterable[Violation]:
    index = _id_index(document)
    for element in document.elements():
        problems: list[str] = []
        for attribute in ("aria-labelledby", "aria-describedby"):
            if attribute not in element.attrs:
                continue
            references = _normalized(element.attrs.get(attribute)).split()
            missing = [item for item in references if item not in index]
            if not references:
                problems.append(f"{attribute} must contain at least one id reference")
            elif missing:
                joined = ", ".join(missing)
                problems.append(f"{attribute} references missing ids: {joined}")
        if problems:
            yield _violation(
                "aria-reference-integrity", element, "; ".join(problems)
            )


def heading_order(document: Document) -> Iterable[Violation]:
    previous: int | None = None
    for element in document.elements():
        if element.tag not in HEADING_LEVEL:
            continue
        level = HEADING_LEVEL[element.tag]
        if previous is not None and level > previous + 1:
            yield _violation(
                "heading-order",
                element,
                f"heading level jumps from h{previous} to h{level}",
            )
        previous = level


def explicit_button_type(document: Document) -> Iterable[Violation]:
    accepted = {"button", "reset", "submit"}
    for element in document.elements():
        if element.tag != "button":
            continue
        value = _normalized(element.attrs.get("type")).lower()
        if value not in accepted:
            yield _violation(
                "explicit-button-type",
                element,
                "button type must be explicitly button, reset, or submit",
            )


def table_header_contract(document: Document) -> Iterable[Violation]:
    accepted_scope = {"col", "colgroup", "row", "rowgroup"}
    for table in (item for item in document.elements() if item.tag == "table"):
        descendants = [
            item for item in table.descendants() if _ancestor(item, "table") is table
        ]
        if any(item.tag == "td" for item in descendants) and not any(
            item.tag == "th" for item in descendants
        ):
            yield _violation(
                "table-header-contract",
                table,
                "data table contains td cells but no th cells",
            )
        for header in (item for item in descendants if item.tag == "th"):
            scope = _normalized(header.attrs.get("scope")).lower()
            if scope not in accepted_scope:
                yield _violation(
                    "table-header-contract",
                    header,
                    "th scope must be row, col, rowgroup, or colgroup",
                )


RULES: dict[str, Rule] = {
    "aria-reference-integrity": aria_reference_integrity,
    "document-language": document_language,
    "explicit-button-type": explicit_button_type,
    "form-control-name": form_control_name,
    "heading-order": heading_order,
    "image-alternative": image_alternative,
    "interactive-name": interactive_name,
    "table-header-contract": table_header_contract,
    "unique-id": unique_id,
}

RULE_DESCRIPTIONS: dict[str, str] = {
    "aria-reference-integrity": "aria-labelledby/describedby tokens resolve to fixture ids.",
    "document-language": "The html root declares a bounded, syntactically valid lang tag.",
    "explicit-button-type": "Native buttons declare button, submit, or reset explicitly.",
    "form-control-name": "Non-hidden input, select, and textarea controls have a computed name.",
    "heading-order": "After the first heading, levels do not increase by more than one.",
    "image-alternative": "Every img declares alt; empty alt is accepted as intentional decoration.",
    "interactive-name": "Links, buttons, and button/link roles have a computed name.",
    "table-header-contract": "Data tables include headers and every th declares a supported scope.",
    "unique-id": "Declared ids are non-empty and unique within the fixture.",
}


def run_rules(document: Document, selected: list[str]) -> list[Violation]:
    violations: list[Violation] = []
    order = {rule_id: index for index, rule_id in enumerate(selected)}
    for rule_id in selected:
        violations.extend(RULES[rule_id](document))
    return sorted(
        violations,
        key=lambda item: (order[item.rule_id], item.node, item.line, item.column, item.message),
    )
