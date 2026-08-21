"""Deterministic triage, duplicate, and human-approval rules."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any

from .schema import Ticket


APPROVAL_CONFIRMATION = "APPROVE_SYNTHETIC_OUTLINE"

CATEGORY_BY_WORKFLOW = {
    "menu_configuration": "configuration",
    "order_flow": "integration",
    "access": "identity_access",
    "reporting": "data_quality",
    "device_sync": "integration",
    "other": "needs_clarification",
}

OWNER_BY_CATEGORY = {
    "configuration": "application_support",
    "integration": "integration_support",
    "identity_access": "access_support",
    "data_quality": "reporting_support",
    "needs_clarification": "intake_review",
}

QUESTION_BY_HOLD = {
    "impact_not_confirmed": "What is the confirmed user and site impact?",
    "observations_missing": "What was directly observed, including any visible error?",
    "blocked_workflow_steps_missing": "What safe troubleshooting steps were already attempted?",
    "visible_error_detail_missing": "What exact error text was visible?",
    "multiple_site_scope_incomplete": "Which additional synthetic sites are affected?",
    "single_scope_conflicts_with_sites": "Is the impact limited to one site or spread across sites?",
    "workflow_needs_classification": "Which documented workflow is affected?",
    "access_signal_workflow_conflict": "Is this an access issue or a workflow issue?",
    "safety_signal_requires_review": "Has a designated human reviewer assessed the safety signal?",
    "duplicate_ticket_id": "Should this repeated ticket identifier be replaced or merged?",
    "possible_duplicate": "Does this report add evidence beyond the earlier matching intake?",
}


class ApprovalError(ValueError):
    """Raised when an outline has not passed the explicit approval boundary."""


@dataclass(frozen=True)
class ResponseOutline:
    acknowledged_facts: tuple[str, ...]
    evidence: tuple[dict[str, str], ...]
    attempted_steps: tuple[str, ...]
    open_questions: tuple[str, ...]
    next_action: str
    resolution_status: str = "not_verified"
    resolution_statement: str = "No resolution is claimed; investigation remains pending human review."

    def to_dict(self) -> dict[str, Any]:
        return {
            "acknowledged_facts": list(self.acknowledged_facts),
            "evidence": list(self.evidence),
            "attempted_steps": list(self.attempted_steps),
            "open_questions": list(self.open_questions),
            "next_action": self.next_action,
            "resolution_status": self.resolution_status,
            "resolution_statement": self.resolution_statement,
        }


@dataclass(frozen=True)
class TriageResult:
    ticket: Ticket
    severity: str
    category: str
    ownership: str
    completeness_holds: tuple[str, ...]
    ambiguity_holds: tuple[str, ...]
    duplicate_holds: tuple[str, ...]
    duplicate_of: str | None
    response_outline: ResponseOutline
    approval_state: str
    approved_reply: str | None = None

    @property
    def holds(self) -> tuple[str, ...]:
        return self.completeness_holds + self.ambiguity_holds + self.duplicate_holds

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticket": self.ticket.to_dict(),
            "triage": {
                "severity": self.severity,
                "category": self.category,
                "ownership": self.ownership,
                "completeness_holds": list(self.completeness_holds),
                "ambiguity_holds": list(self.ambiguity_holds),
                "duplicate_holds": list(self.duplicate_holds),
                "duplicate_of": self.duplicate_of,
            },
            "response_outline": self.response_outline.to_dict(),
            "approval": {
                "state": self.approval_state,
                "approved_reply": self.approved_reply,
            },
        }


class DuplicateIndex:
    """Batch-local exact-ID and normalized-subject duplicate index."""

    def __init__(self) -> None:
        self._ticket_ids: dict[str, str] = {}
        self._fingerprints: dict[tuple[tuple[str, ...], str, str], str] = {}

    @staticmethod
    def _normalized_subject(subject: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", subject.casefold()))

    def register(self, ticket: Ticket) -> tuple[str | None, str | None]:
        if ticket.ticket_id in self._ticket_ids:
            return self._ticket_ids[ticket.ticket_id], "duplicate_ticket_id"

        fingerprint = (
            tuple(sorted(ticket.site_codes)),
            ticket.affected_workflow,
            self._normalized_subject(ticket.subject),
        )
        duplicate_of = self._fingerprints.get(fingerprint)
        self._ticket_ids[ticket.ticket_id] = ticket.ticket_id
        if duplicate_of is not None:
            return duplicate_of, "possible_duplicate"
        self._fingerprints[fingerprint] = ticket.ticket_id
        return None, None


def severity_for(ticket: Ticket) -> str:
    signals = set(ticket.signals)
    if "safety_concern" in signals:
        return "critical"
    if ticket.impact == "multiple_sites" and "workflow_blocked" in signals:
        return "critical"
    if "workflow_blocked" in signals or ticket.impact == "multiple_sites":
        return "high"
    if signals.intersection(
        {"data_mismatch", "access_denied", "error_visible", "performance_degraded"}
    ):
        return "medium"
    return "low"


def completeness_holds_for(ticket: Ticket) -> tuple[str, ...]:
    holds: list[str] = []
    signals = set(ticket.signals)
    observation_kinds = {item.kind for item in ticket.observations}
    if ticket.impact == "unknown":
        holds.append("impact_not_confirmed")
    if not ticket.observations:
        holds.append("observations_missing")
    if "workflow_blocked" in signals and not ticket.attempted_steps:
        holds.append("blocked_workflow_steps_missing")
    if "error_visible" in signals and "error_text" not in observation_kinds:
        holds.append("visible_error_detail_missing")
    if ticket.impact == "multiple_sites" and len(ticket.site_codes) < 2:
        holds.append("multiple_site_scope_incomplete")
    return tuple(holds)


def ambiguity_holds_for(ticket: Ticket) -> tuple[str, ...]:
    holds: list[str] = []
    signals = set(ticket.signals)
    if ticket.impact in {"single_user", "single_site"} and len(ticket.site_codes) > 1:
        holds.append("single_scope_conflicts_with_sites")
    if ticket.affected_workflow == "other":
        holds.append("workflow_needs_classification")
    if "access_denied" in signals and ticket.affected_workflow != "access":
        holds.append("access_signal_workflow_conflict")
    if "safety_concern" in signals:
        holds.append("safety_signal_requires_review")
    return tuple(holds)


def build_response_outline(
    ticket: Ticket,
    ownership: str,
    holds: tuple[str, ...],
) -> ResponseOutline:
    site_summary = ", ".join(ticket.site_codes)
    facts = (
        f"Reported workflow: {ticket.affected_workflow}.",
        f"Reported impact: {ticket.impact}.",
        f"Synthetic sites in scope: {site_summary}.",
        f"Reported subject: {ticket.subject}.",
    )
    evidence = tuple(item.to_dict() for item in ticket.observations)
    questions = tuple(
        QUESTION_BY_HOLD.get(
            hold.split(":", 1)[0],
            "Can a human reviewer resolve the remaining intake hold?",
        )
        for hold in holds
    )
    return ResponseOutline(
        acknowledged_facts=facts,
        evidence=evidence,
        attempted_steps=ticket.attempted_steps,
        open_questions=questions,
        next_action=f"Route the evidence package to {ownership} for investigation.",
    )


def triage_ticket(ticket: Ticket, duplicate_index: DuplicateIndex) -> TriageResult:
    category = CATEGORY_BY_WORKFLOW[ticket.affected_workflow]
    ownership = OWNER_BY_CATEGORY[category]
    completeness = completeness_holds_for(ticket)
    ambiguity = ambiguity_holds_for(ticket)
    duplicate_of, duplicate_kind = duplicate_index.register(ticket)
    duplicate_holds = (
        (f"{duplicate_kind}:{duplicate_of}",)
        if duplicate_kind is not None and duplicate_of is not None
        else ()
    )
    holds = completeness + ambiguity + duplicate_holds
    outline = build_response_outline(ticket, ownership, holds)
    approval_state = "blocked_by_holds" if holds else "pending_human_approval"
    return TriageResult(
        ticket=ticket,
        severity=severity_for(ticket),
        category=category,
        ownership=ownership,
        completeness_holds=completeness,
        ambiguity_holds=ambiguity,
        duplicate_holds=duplicate_holds,
        duplicate_of=duplicate_of,
        response_outline=outline,
        approval_state=approval_state,
    )


def _render_approved_reply(result: TriageResult) -> str:
    facts = " ".join(result.response_outline.acknowledged_facts)
    next_action = result.response_outline.next_action
    return (
        f"Thank you for the synthetic report. {facts} "
        f"{next_action} No resolution has been verified; the case remains under review."
    )


def approve_triage(result: TriageResult, confirmation: str) -> TriageResult:
    if confirmation != APPROVAL_CONFIRMATION:
        raise ApprovalError("explicit synthetic-outline approval is required")
    if result.holds:
        raise ApprovalError("approval is blocked until every hold is resolved")
    if result.approval_state != "pending_human_approval":
        raise ApprovalError("result is not awaiting human approval")
    return replace(
        result,
        approval_state="approved_by_human",
        approved_reply=_render_approved_reply(result),
    )
