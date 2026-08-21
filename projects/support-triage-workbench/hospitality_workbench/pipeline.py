"""Offline processing pipeline for synthetic tickets."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from .audit import AuditLog
from .redaction import redact_ticket
from .schema import Ticket
from .triage import (
    APPROVAL_CONFIRMATION,
    ApprovalError,
    DuplicateIndex,
    approve_triage,
    triage_ticket,
)


OUTPUT_SCHEMA = "synthetic-support-output-v1"


def process_tickets(
    tickets: Iterable[Ticket],
    *,
    audit_log: AuditLog | None = None,
    approve_eligible: bool = False,
) -> dict[str, Any]:
    """Redact, triage, optionally approve, and serialize an offline batch."""
    ticket_list = tuple(tickets)
    duplicate_index = DuplicateIndex()
    processed: list[dict[str, Any]] = []
    severities: Counter[str] = Counter()
    approval_states: Counter[str] = Counter()

    for ticket in ticket_list:
        if audit_log is not None:
            audit_log.append(
                "ticket_received",
                ticket.ticket_id,
                {"schema_version": ticket.schema_version},
            )

        redacted = redact_ticket(ticket)
        if audit_log is not None and redacted.count:
            audit_log.append(
                "redaction_applied",
                ticket.ticket_id,
                {"count": redacted.count, "kinds": list(redacted.kinds)},
            )

        result = triage_ticket(redacted.ticket, duplicate_index)
        if audit_log is not None:
            audit_log.append(
                "triage_completed",
                ticket.ticket_id,
                {
                    "severity": result.severity,
                    "category": result.category,
                    "ownership": result.ownership,
                    "hold_count": len(result.holds),
                    "duplicate": result.duplicate_of is not None,
                },
            )

        if approve_eligible:
            try:
                result = approve_triage(result, APPROVAL_CONFIRMATION)
            except ApprovalError:
                if audit_log is not None:
                    audit_log.append(
                        "approval_blocked",
                        ticket.ticket_id,
                        {"hold_count": len(result.holds)},
                    )
            else:
                if audit_log is not None:
                    audit_log.append(
                        "approval_granted",
                        ticket.ticket_id,
                        {"approved_reply_present": True},
                    )
        elif audit_log is not None:
            event_type = "approval_blocked" if result.holds else "approval_pending"
            audit_log.append(
                event_type,
                ticket.ticket_id,
                {"hold_count": len(result.holds)},
            )

        severities[result.severity] += 1
        approval_states[result.approval_state] += 1
        item = result.to_dict()
        item["redaction"] = {"count": redacted.count, "kinds": list(redacted.kinds)}
        processed.append(item)

    return {
        "schema_version": OUTPUT_SCHEMA,
        "synthetic_only": True,
        "offline_only": True,
        "summary": {
            "ticket_count": len(processed),
            "severity_counts": dict(sorted(severities.items())),
            "approval_counts": dict(sorted(approval_states.items())),
        },
        "results": processed,
    }

