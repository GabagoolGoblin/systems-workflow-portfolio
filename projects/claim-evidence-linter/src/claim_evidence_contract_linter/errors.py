class LinterError(Exception):
    """Base class for expected, user-facing failures."""


class InputError(LinterError):
    """Input bytes, JSON, or schema failed closed validation."""


class AuditMismatch(LinterError):
    """A report digest or its bound inputs do not match."""


class LocalIOError(LinterError):
    """A local read or write could not be completed safely."""

