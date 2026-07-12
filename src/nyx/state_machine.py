"""Verification state machine — the enforcement of No Silent Promotion (Invariant 3).

spec/NYX_ARCHITECTURE.md §2 (two-dimensional state, transition contract) and
spec/NYX_V0_IMPLEMENTATION.md §1 (state-transition validator). The transition
table is not prose to interpret — it is a literal lookup guard. Promotion toward
`verified` requires a world oracle (Invariant 3/4); demotion may fire offline.
"""

from __future__ import annotations

from dataclasses import dataclass

# verification_state values — spec/NYX_ARCHITECTURE.md §2.
UNVERIFIED = "unverified"
VERIFIED = "verified"
QUESTIONED = "questioned"
QUARANTINED = "quarantined"
SUPERSEDED = "superseded"
REDACTED = "redacted"

# verifiability values — spec/NYX_ARCHITECTURE.md §2.
EXTERNALLY_CHECKABLE = "externally_checkable"
LOCALLY_CHECKABLE = "locally_checkable"
SUBJECTIVE = "subjective"
STRUCTURALLY_UNVERIFIABLE = "structurally_unverifiable"


@dataclass(frozen=True)
class TransitionRule:
    requires_world_oracle: bool
    offline_allowed: bool


# The transition contract from spec/NYX_ARCHITECTURE.md §2, keyed (from, to).
# Populate as a literal table in the walking skeleton — do not infer transitions
# at runtime. Left empty in the scaffold on purpose (no logic in commit 1).
STATE_TABLE: dict[tuple[str, str], TransitionRule] = {}


def transition(from_state: str, to_state: str, trigger_type: str, has_world_oracle: bool) -> bool:
    """Return True if the transition is permitted, else raise / reject.

    The entire enforcement mechanism for Invariant 3 is this lookup — not a model
    call: reject unknown transitions; reject promotion without a world oracle.
    spec/NYX_V0_IMPLEMENTATION.md §1. Implement alongside the walking skeleton.
    """
    raise NotImplementedError(
        "transition — implement the STATE_TABLE lookup guard; "
        "see spec/NYX_V0_IMPLEMENTATION.md §1, spec/NYX_ARCHITECTURE.md §2"
    )
