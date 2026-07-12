"""Identifier generation.

spec/NYX_V0_IMPLEMENTATION.md §1 — Event ID: UUIDv7 (time-ordered UUID). Any
time-sortable unique id satisfies the ordering requirement of §1; UUIDv7 is the
standard choice.
"""

from __future__ import annotations


def new_event_id() -> str:
    """Return a fresh time-ordered event id (UUIDv7 string).

    Deterministic algorithm — spec/NYX_V0_IMPLEMENTATION.md §1. Implement in the
    walking skeleton (commit 2).
    """
    raise NotImplementedError(
        "new_event_id (UUIDv7) — implement in walking skeleton; "
        "see spec/NYX_V0_IMPLEMENTATION.md §1"
    )
