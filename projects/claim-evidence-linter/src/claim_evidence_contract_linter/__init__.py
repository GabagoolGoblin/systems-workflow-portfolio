"""Deterministic claim-to-evidence contract linting."""

from .engine import ENGINE_VERSION, build_report, evaluate_claims

__all__ = ["ENGINE_VERSION", "build_report", "evaluate_claims"]
__version__ = ENGINE_VERSION

