"""Domain errors with stable CLI error codes."""

from __future__ import annotations


class MigrationError(Exception):
    code = "migration_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(MigrationError):
    code = "validation_error"


class IntegrityError(MigrationError):
    code = "integrity_error"


class StateConflictError(MigrationError):
    code = "state_conflict"
