"""Verification vocabulary and an unimplemented general transition interface.

The state table is empty and transition() raises NotImplementedError. Current
observed-origin handling is enforced in projection.py and the stage-two reducers.
General transitions remain subject to the specifications and superseding ADRs;
these declarations do not establish implemented promotion or demotion behavior.
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
# Still unimplemented; populate only where accepted decisions settle transitions.
STATE_TABLE: dict[tuple[str, str], TransitionRule] = {}


def transition(from_state: str, to_state: str, trigger_type: str, has_world_oracle: bool) -> bool:
    """Return True if the transition is permitted, else raise / reject.

    Reserved lookup-guard interface from spec/NYX_V0_IMPLEMENTATION.md §1.
    No general transition enforcement is implemented in this function.
    """
    raise NotImplementedError(
        "transition — implement the STATE_TABLE lookup guard; "
        "see spec/NYX_V0_IMPLEMENTATION.md §1, spec/NYX_ARCHITECTURE.md §2"
    )
