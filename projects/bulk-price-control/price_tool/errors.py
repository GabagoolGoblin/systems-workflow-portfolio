"""Domain errors with stable machine-readable codes."""

from __future__ import annotations


class PriceToolError(Exception):
    """A controlled failure that should be shown without a traceback."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ValidationError(PriceToolError):
    """Input failed a deterministic validation rule."""

    def __init__(self, message: str) -> None:
        super().__init__("validation_error", message)


class IntegrityError(PriceToolError):
    """A staged or audited artifact failed an integrity check."""

    def __init__(self, message: str) -> None:
        super().__init__("integrity_error", message)


class StateConflictError(PriceToolError):
    """Current state no longer matches the state that was staged."""

    def __init__(self, message: str) -> None:
        super().__init__("state_conflict", message)

