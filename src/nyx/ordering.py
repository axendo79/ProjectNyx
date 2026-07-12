"""The internal ordering scalar — what the entity-link ceiling and Liver consume.

spec/NYX_V0_IMPLEMENTATION.md §1. The architecture (§2) defers the *user-facing*
synthesized confidence score (Invariant 2: never render fake-precise confidence),
but an *internal ordering scalar* is load-bearing NOW (entity-link ceiling §11,
Liver queue, corroboration gating). This module decides it so the arithmetic that
consumes it has a real, non-invented source.

At v0 claim_confidence is NOT a synthesized float — it is the STATE ORDINAL,
normalized. The only thing deferred is a *richer* synthesized score later (§3).
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
