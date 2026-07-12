"""Resolved View — materialized deterministic projection of Layer A.

spec/NYX_ARCHITECTURE.md §1 (materialized-delta, decided) and Invariant 9
(projection determinism). spec/NYX_V0_IMPLEMENTATION.md §1 (fold algorithm),
§4 (resolved_beliefs schema).

Two derivation paths that MUST agree (executable invariant, spec §12):
  incremental `fold` folded event-by-event  ≡  `project` (full replay from genesis)
under the current redaction/merge set. Full replay is the crash-recovery path and
the test oracle; the incremental fold is the hot path.

Value-recency guard (§1/§4): fold ORDER is rowid (insertion) for hash determinism,
but the VALUE a belief resolves to keys on `occurred_at`. A late-arriving event
whose occurred_at predates the current value updates provenance/support-set but
does NOT supersede the newer value — the offline-reconnection seam.
"""

from __future__ import annotations

from typing import Any, Mapping

from .events import Envelope


def fold(prior_view: Mapping[str, Any], new_event: Envelope) -> dict[str, Any]:
    """Fold one event into the materialized belief state (incremental delta-reducer).

    Applies the value-recency guard and recomputes
    `view_version_hash = SHA256(prior.view_version_hash || new_event.event_hash)`.
    `apply_event_to_belief` is event-type-specific; the walking skeleton needs only
    `observation_recorded` (sets a value). spec/NYX_V0_IMPLEMENTATION.md §1, §6.
    Other handlers (correction_appended, entity_merge_accepted, ...) are §8 (open).
    """
    raise NotImplementedError(
        "fold — implement in walking skeleton (observation_recorded handler only); "
        "see spec/NYX_V0_IMPLEMENTATION.md §1, §6"
    )


def project(events: list[Envelope], as_of: str, projector_version: str) -> dict[str, Any]:
    """Full replay: project(event_log, as_of, projector_version) from empty.

    The crash-recovery path AND the determinism oracle — a fresh full replay must
    produce a view_version_hash identical to the incrementally-folded view
    (spec/NYX_V0_IMPLEMENTATION.md §6 acceptance bar). Deterministic, time-aware,
    versioned (Invariant 9). Implement in the walking skeleton.
    """
    raise NotImplementedError(
        "project (full replay) — implement in walking skeleton; "
        "see spec/NYX_V0_IMPLEMENTATION.md §6, spec/NYX_ARCHITECTURE.md §1"
    )


def is_stale(view_version_hash_lineage: str, latest_event_hash: str) -> bool:
    """Stale-projection check: compare the materialized view_version_hash lineage
    against entity_event_index.latest_event_hash for the belief's entity. Mismatch
    → serve stale-labeled (never block on a re-fold). The synchronous index (§4)
    is what makes this not race. spec/NYX_V0_IMPLEMENTATION.md §1.
    """
    raise NotImplementedError(
        "is_stale — implement with the read path; "
        "see spec/NYX_V0_IMPLEMENTATION.md §1, spec/NYX_ARCHITECTURE.md §8"
    )
