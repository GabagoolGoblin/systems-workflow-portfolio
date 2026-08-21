"""Small immutable-ish data model used by the parser and rule engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator


class ContractInputError(ValueError):
    """Raised when an input falls outside the harness's explicit safe contract."""


@dataclass
class Element:
    tag: str
    attrs: dict[str, str | None]
    line: int
    column: int
    parent: Element | None = field(default=None, repr=False)
    content: list[str | Element] = field(default_factory=list, repr=False)

    def children(self) -> Iterator[Element]:
        for item in self.content:
            if isinstance(item, Element):
                yield item

    def descendants(self) -> Iterator[Element]:
        for child in self.children():
            yield child
            yield from child.descendants()

    def text_content(self) -> str:
        pieces: list[str] = []
        for item in self.content:
            pieces.append(item if isinstance(item, str) else item.text_content())
        return " ".join("".join(pieces).split())

    def path(self) -> str:
        parts: list[str] = []
        current: Element | None = self
        while current is not None:
            index = 1
            if current.parent is not None:
                for sibling in current.parent.children():
                    if sibling is current:
                        break
                    if sibling.tag == current.tag:
                        index += 1
            parts.append(f"{current.tag}[{index}]")
            current = current.parent
        return "/".join(reversed(parts))


@dataclass(frozen=True, order=True)
class Violation:
    rule_id: str
    node: str
    message: str
    line: int
    column: int
    severity: str = "error"

    def fingerprint(self) -> dict[str, str]:
        return {"node": self.node, "rule_id": self.rule_id}

    def as_dict(self) -> dict[str, int | str]:
        return {
            "column": self.column,
            "line": self.line,
            "message": self.message,
            "node": self.node,
            "rule_id": self.rule_id,
            "severity": self.severity,
        }


@dataclass
class Document:
    root: Element
    doctype_seen: bool

    def elements(self) -> Iterator[Element]:
        yield self.root
        yield from self.root.descendants()
