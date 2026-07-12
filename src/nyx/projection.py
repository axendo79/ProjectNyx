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

from datetime import datetime, timezone
from typing import Any

from . import hashing
from .events import OBSERVATION_RECORDED, Envelope

# Genesis seed for a belief's view_version_hash lineage (empty string) — the value
# folded against for the first event that touches a belief. spec/NYX_V0_IMPLEMENTATION.md §1.
_GENESIS_VIEW_HASH = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fold(prior_view: dict[str, Any] | None, envelope: Envelope, payload: dict[str, Any]) -> dict[str, Any]:
    """Fold one event into a belief's materialized state (incremental delta-reducer).

    Recomputes `view_version_hash = SHA256(prior || event_hash)` and applies the
    value-recency guard (§1): fold ORDER is rowid, but a value-setting event whose
    occurred_at predates the current value updates provenance only — it does NOT
    supersede the newer value (the offline-reconnection seam).

    Only `observation_recorded` is handled — the one event type on §6's seam. Other
    handlers (correction_appended, entity_merge_accepted, ...) are §8 (open) and
    fail loud rather than silently mis-fold.
    """
    if envelope.event_type != OBSERVATION_RECORDED:
        raise NotImplementedError(
            f"fold handler for {envelope.event_type!r} not implemented — "
            "see spec/NYX_V0_IMPLEMENTATION.md §8"
        )

    now = _now_iso()
    prior_hash = _GENESIS_VIEW_HASH if prior_view is None else prior_view["view_version_hash"]
    supporting = [] if prior_view is None else list(prior_view["supporting_events"])
    opposing = [] if prior_view is None else list(prior_view["opposing_events"])
    new_view_hash = hashing._sha256_hex(prior_hash + envelope.event_hash)
    supporting.append(envelope.event_id)

    # Value-recency guard: an older-than-current value-setting event contributes
    # provenance but must not clobber the newer materialized value (§1/§4).
    if prior_view is not None and envelope.occurred_at < prior_view["value_occurred_at"]:
        view = dict(prior_view)
        view["supporting_events"] = supporting
        view["view_version_hash"] = new_view_hash
        view["projected_as_of"] = now
        view["updated_at"] = now
        return view

    # observation_recorded sets the value. A direct observation is a world-oracle
    # class signal (Invariant 4 / architecture §5: "world oracle ... direct
    # observation ..."), so it lands the belief at `verified` without violating No
    # Silent Promotion (Inv. 3) — the independent signal is the observation itself.
    return {
        "belief_id": payload["belief_id"],
        "current_value": payload["value"],
        "value_occurred_at": envelope.occurred_at,
        "verification_state": "verified",
        "verifiability": payload["verifiability"],
        "display_origin": envelope.origin_type,
        "supporting_events": supporting,
        "opposing_events": opposing,
        "resolution_basis": "direct observation (world-oracle class, Inv. 4)",
        "view_version_hash": new_view_hash,
        "projected_as_of": now,
        "updated_at": now,
    }


def project(events: list[tuple[Envelope, dict]], as_of: str, projector_version: str) -> dict[str, Any]:
    """Full replay: project(event_log, as_of, projector_version) from empty.

    The crash-recovery path AND the determinism oracle — a fresh full replay must
    produce, per belief, a view_version_hash identical to the incrementally-folded
    view (spec/NYX_V0_IMPLEMENTATION.md §6 acceptance bar). Folds in insertion
    (rowid) order; deterministic, versioned (Invariant 9). Returns belief_id -> view.
    """
    view: dict[str, Any] = {}
    for envelope, payload in events:
        belief_id = payload["belief_id"]
        view[belief_id] = fold(view.get(belief_id), envelope, payload)
    return view


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
