"""High-confidence sensitive-value redaction for synthetic ticket text."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from .schema import Observation, Ticket


@dataclass(frozen=True)
class RedactionResult:
    text: str
    count: int
    kinds: tuple[str, ...]


@dataclass(frozen=True)
class RedactedTicket:
    ticket: Ticket
    count: int
    kinds: tuple[str, ...]


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<![0-9])(?:\+?1[ .-]?)?\(?[0-9]{3}\)?[ .-][0-9]{3}[ .-][0-9]{4}(?![0-9])")
IPV4_RE = re.compile(r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])")
SECRET_RE = re.compile(
    r"\b(api[_-]?key|password|token|secret)\s*[:=]\s*[^\s,;]+",
    re.IGNORECASE,
)
NAME_LABEL_RE = re.compile(
    r"\b(?:person_name|contact_name)\s*[:=]\s*[^,;\n]+",
    re.IGNORECASE,
)
PAYMENT_RE = re.compile(r"(?<![0-9])(?:[0-9][ -]?){13,19}(?![0-9])")


def redact_text(text: str) -> RedactionResult:
    """Redact high-confidence labeled or structured sensitive values."""
    replacements = (
        ("email", EMAIL_RE, "[REDACTED_EMAIL]"),
        ("phone", PHONE_RE, "[REDACTED_PHONE]"),
        ("network_address", IPV4_RE, "[REDACTED_NETWORK_ADDRESS]"),
        ("secret", SECRET_RE, "[REDACTED_SECRET]"),
        ("labeled_name", NAME_LABEL_RE, "[REDACTED_NAME]"),
        ("payment_number", PAYMENT_RE, "[REDACTED_NUMBER]"),
    )
    redacted = text
    count = 0
    kinds: list[str] = []
    for kind, pattern, replacement in replacements:
        redacted, matches = pattern.subn(replacement, redacted)
        if matches:
            count += matches
            kinds.extend([kind] * matches)
    return RedactionResult(text=redacted, count=count, kinds=tuple(sorted(set(kinds))))


def redact_ticket(ticket: Ticket) -> RedactedTicket:
    """Return a sanitized ticket without changing structural identifiers."""
    count = 0
    kinds: set[str] = set()

    def clean(text: str) -> str:
        nonlocal count
        result = redact_text(text)
        count += result.count
        kinds.update(result.kinds)
        return result.text

    observations = tuple(
        Observation(kind=item.kind, value=clean(item.value))
        for item in ticket.observations
    )
    sanitized = replace(
        ticket,
        subject=clean(ticket.subject),
        description=clean(ticket.description),
        observations=observations,
        attempted_steps=tuple(clean(item) for item in ticket.attempted_steps),
    )
    return RedactedTicket(ticket=sanitized, count=count, kinds=tuple(sorted(kinds)))

