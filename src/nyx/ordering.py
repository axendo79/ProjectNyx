"""Unimplemented scalar/ceiling interfaces from the original v0 specification.

The constants below record the specified state ordinals; both functions still
raise NotImplementedError. Liver and corroboration consumers do not ship.
Stage-two constitutive-link handling lives in reducer.py under ADR 0021 and
does not call these stubs. Later link treatment still requires decisions.
"""

from __future__ import annotations

from typing import Sequence

from . import state_machine as sm

# State ordinal — spec/NYX_V0_IMPLEMENTATION.md §1. Countable, non-invented,
# fully specified by the state machine. Normalized to [0,1] as ordinal/3.
STATE_ORDINAL: dict[str, int] = {
    sm.QUARANTINED: 0,
    sm.QUESTIONED: 1,
    sm.UNVERIFIED: 2,
    sm.VERIFIED: 3,
}


def claim_scalar(verification_state: str) -> float:
    """v0 stand-in for claim_confidence: STATE_ORDINAL[state] / 3.0.

    No invented float — spec/NYX_V0_IMPLEMENTATION.md §1. Implement with the
    ceiling arithmetic below.
    """
    raise NotImplementedError(
        "claim_scalar — implement (STATE_ORDINAL/3.0); "
        "see spec/NYX_V0_IMPLEMENTATION.md §1"
    )


def effective_confidence(verification_state: str, entity_link_confidences: Sequence[float]) -> float:
    """Weakest-link ceiling: min(claim_scalar, min(link confidences in chain)).

    `min` is the epistemically safe PERMANENT choice, not a v0 placeholder
    (spec/NYX_V0_IMPLEMENTATION.md §1). entity_link_confidence is a real REAL in
    [0,1] from the resolver (§11). Implement when the ceiling is first consumed.
    """
    raise NotImplementedError(
        "effective_confidence — implement weakest-link min(); "
        "see spec/NYX_V0_IMPLEMENTATION.md §1, spec/NYX_ARCHITECTURE.md §11"
    )
