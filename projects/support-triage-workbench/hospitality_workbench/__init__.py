"""Offline synthetic support-intake workbench."""

from .pipeline import process_tickets
from .schema import Ticket, load_synthetic_batch, parse_synthetic_batch

__all__ = [
    "Ticket",
    "load_synthetic_batch",
    "parse_synthetic_batch",
    "process_tickets",
]

