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
from .events import CORRECTION_APPENDED, OBSERVATION_RECORDED, ORIGIN_OBSERVED, Envelope
from .reducer import ReducerProjector, Snapshot

# Genesis seed for a belief's view_version_hash lineage (empty string) — the value
# folded against for the first event that touches a belief. spec/NYX_V0_IMPLEMENTATION.md §1.
_GENESIS_VIEW_HASH = ""

# The value-setting event types (§8: "the value-recency guard applies to all
# value-setting handlers"). Both resolve a belief's current_value; they differ in
# the provenance they record, not in how the guard treats them.
_VALUE_SETTING = (OBSERVATION_RECORDED, CORRECTION_APPENDED)

_RESOLUTION_BASIS = {
    # A direct observation is a world-oracle class signal (Invariant 4 / architecture
    # §5), so it lands the belief at `verified` without violating No Silent Promotion
    # (Inv. 3) — the independent signal IS the observation. See decisions/0001.
    OBSERVATION_RECORDED: "direct observation (world-oracle class, Inv. 4)",
    CORRECTION_APPENDED: "correction supersedes prior value (Inv. 6 superseding event)",
}


def _instant(timestamp: str, field: str = "occurred_at") -> datetime:
    """Parse an ISO8601 timestamp to a UTC-aware datetime, for COMPARISON only.

    Also used for recorded_at/as_of cutoff comparisons (decisions/0010).

    Ordering of `occurred_at` is chronological, never lexical. Lexical order over ISO8601
    text is not chronological order once offsets vary: the same instant has several
    spellings (`Z` sorts after `+00:00`, though both mean UTC), and a non-UTC offset makes
    a later instant sort earlier (`09:00-05:00` is two hours AFTER `12:00Z`, but sorts
    before it). Comparing the raw strings corrupts the value-recency guard in BOTH
    directions — see decisions/0006.

    The stored string is NEVER rewritten. `occurred_at` sits inside the hashed envelope,
    so canonicalizing it at rest would change every `event_hash` and break
    `fold == replay-from-genesis` (§6). Normalization happens at the point of comparison
    and nowhere else.

    A NAIVE (offset-less) timestamp is refused rather than assumed to be UTC. Its instant
    is genuinely unknown, and silently picking one would reintroduce exactly the class of
    quiet wrong answer this function exists to remove. The real fix is canonicalizing
    timezone-bearing timestamps at the INGESTION boundary (immune Stage 1), so the system
    does not rely on compare-time normalization forever — logged as a follow-on gap in
    decisions/0006, not built here.
    """
    parsed = datetime.fromisoformat(timestamp)
    if parsed.tzinfo is None:
        raise ValueError(
            f"{field} {timestamp!r} has no timezone offset — its instant is "
            "ambiguous and will not be guessed. Timestamps must carry an offset (`Z` or "
            "`±HH:MM`). Boundary canonicalization is a follow-on gap; see decisions/0006."
        )
    return parsed.astimezone(timezone.utc)


class BackdatedCorrectionError(NotImplementedError):
    """A `correction_appended` whose occurred_at PREDATES the value it corrects.

    This is an INTERIM fail-loud stance, NOT decided semantics — see decisions/0005.
    The open question it defers:

      (A) A correction is *newer information*, governed by the §1 value-recency guard
          like any other value-setting event → a backdated one folds as provenance
          only and does NOT take the head.
      (B) A correction is an *authoritative override* — a deliberate "no, it was
          always X" — and takes the head regardless of its date.

    Both are defensible and the spec settles neither. Silently doing (A) — which is
    what the guard does if left alone — would read to the next person as a decision
    rather than an unexamined default, and it fails *quietly*: the correction is
    accepted, the head just doesn't move. That is the failure mode worth refusing.

    Subclasses NotImplementedError deliberately: this is the §7 gap protocol's
    "stub that fails loudly", not a validation error about bad user input. When the
    semantics are decided, grep `BackdatedCorrectionError` — every site that assumed
    the question was open is at the other end.
    """


def assert_not_backdated(
    prior_view: dict[str, Any] | None, event_type: str, occurred_at: str
) -> None:
    """Refuse a backdated correction. The single predicate, called from TWO places.

    Called by `fold` (so a replay is honest about a log that somehow contains one) and
    — crucially — by the write path BEFORE the append. Layer A is append-only and
    engine-enforced (Inv. 1): an appended event can never be removed. If this were
    only checked at fold time, the correction would already be durably in the log, and
    every subsequent full replay would re-fold it and raise. An unreplayable log is an
    unrecoverable one — replay IS the crash-recovery path (§6). So the rejection must
    happen before the commit point, not after it.
    """
    if event_type != CORRECTION_APPENDED or prior_view is None:
        return
    # Instant-based, never lexical (decisions/0006).
    if _instant(occurred_at) < _instant(prior_view["value_occurred_at"]):
        raise BackdatedCorrectionError(
            f"backdated correction: occurred_at {occurred_at!r} predates the value it "
            f"corrects ({prior_view['value_occurred_at']!r}) on belief "
            f"{prior_view['belief_id']!r}. Semantics UNDECIDED — see decisions/0005 "
            "(recency-governed vs. authoritative-override). Refusing rather than "
            "silently folding it as provenance-only."
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_for_origin(origin_type: str) -> str:
    """Resolve verification_state from the event's ORIGIN — never from its event type.

    A correction does not promote a belief by virtue of being a correction (Inv. 3:
    no silent promotion; only an independent world-oracle signal promotes). It
    resolves to whatever its own origin earns, exactly as an observation does.

    Only `observed` is mapped. `user_stated` in particular is NOT: architecture §2's
    user-stated split ("User asserted X" vs "X is true" — the user is a *source*, not
    ground truth, outside preference claims) means it cannot simply reuse this table,
    and no worked mapping exists yet. Fail loud rather than silently promote (§7 gap
    protocol, case 3 / case 4). See decisions/0004.
    """
    if origin_type != ORIGIN_OBSERVED:
        raise NotImplementedError(
            f"origin -> verification_state mapping for {origin_type!r} not decided — "
            "only `observed` is worked (decisions/0001). See spec/NYX_V0_IMPLEMENTATION.md §8 "
            "and architecture §2 (the user-stated split)."
        )
    return "verified"


def fold(
    prior_view: dict[str, Any] | None,
    envelope: Envelope,
    payload: dict[str, Any],
    as_of: str,
) -> dict[str, Any]:
    """Fold one event into a belief's materialized state (incremental delta-reducer).

    Recomputes `view_version_hash = SHA256(prior || event_hash)` and applies the
    value-recency guard (§1): fold ORDER is rowid, but a value-setting event whose
    occurred_at predates the current value updates provenance only — it does NOT
    supersede the newer value (the offline-reconnection seam).

    Handles the two value-setting types. Others (entity_merge_accepted, ...) are §8
    (open) and fail loud rather than silently mis-fold.

    The caller supplies the evaluation time (decisions/0010 §3b). This reducer
    never reads the clock; updated_at comes from the folded event's recorded_at.
    """
    if envelope.event_type not in _VALUE_SETTING:
        raise NotImplementedError(
            f"fold handler for {envelope.event_type!r} not implemented — "
            "see spec/NYX_V0_IMPLEMENTATION.md §8"
        )

    # Backdated corrections are refused, not quietly absorbed by the guard below
    # (decisions/0005 — interim fail-loud, semantics open). The write path checks this
    # BEFORE appending; this call is the replay-side backstop.
    assert_not_backdated(prior_view, envelope.event_type, envelope.occurred_at)

    prior_hash = _GENESIS_VIEW_HASH if prior_view is None else prior_view["view_version_hash"]
    supporting = [] if prior_view is None else list(prior_view["supporting_events"])
    opposing = [] if prior_view is None else list(prior_view["opposing_events"])
    superseding = [] if prior_view is None else list(prior_view["superseding_events"])
    new_view_hash = hashing._sha256_hex(prior_hash + envelope.event_hash)
    supporting.append(envelope.event_id)

    # Supersession is a property of the EVENT TYPE, not of what happened to be folded
    # first. A correction_appended is a superseding event (Inv. 6's class) whether or
    # not the value it supersedes has been folded yet — and it MUST be, or the fold
    # stops converging: on the correction-first ordering the correction meets
    # prior_view=None (nothing to supersede), and gating this on "a prior head exists"
    # would leave superseding_events empty in one order and populated in the other,
    # for the same two events. Order-independence of resolved state (§5 trace 2)
    # dies there. See decisions/0004.
    if envelope.event_type == CORRECTION_APPENDED:
        superseding.append(envelope.event_id)

    # Value-recency guard: an older-than-current value-setting event contributes
    # provenance but must not clobber the newer materialized value (§1/§4). This is
    # what makes the two fold orders converge — not any ordering of the fold itself.
    # The comparison is instant-based, never lexical (decisions/0006).
    if prior_view is not None and _instant(envelope.occurred_at) < _instant(
        prior_view["value_occurred_at"]
    ):
        view = dict(prior_view)
        view["supporting_events"] = supporting
        view["superseding_events"] = superseding
        view["view_version_hash"] = new_view_hash
        view["projected_as_of"] = as_of
        view["updated_at"] = envelope.recorded_at
        return view

    # This event sets the value. Note the belief head is NEVER parked in
    # verification_state='superseded': this row holds the LIVE corrected value, and a
    # one-row-per-attribute projection (§4) has no second row for the value that was
    # superseded. The superseded value is recorded as provenance (it stays in
    # supporting_events; the correction lands in superseding_events), never as the
    # head's state. Architecture line 104 (`any -> superseded`) reads as a belief-row
    # transition the §4 schema cannot express; two-file provenance makes that row the
    # bug. See decisions/0004.
    return {
        "belief_id": payload["belief_id"],
        "current_value": payload["value"],
        "value_occurred_at": envelope.occurred_at,
        "verification_state": _state_for_origin(envelope.origin_type),
        "verifiability": payload["verifiability"],
        "display_origin": envelope.origin_type,
        "supporting_events": supporting,
        "opposing_events": opposing,
        "superseding_events": superseding,
        "resolution_basis": _RESOLUTION_BASIS[envelope.event_type],
        "view_version_hash": new_view_hash,
        "projected_as_of": as_of,
        "updated_at": envelope.recorded_at,
    }


# Version-pinned implementations; the snapshot boundary is additive (ADR 0014).
PROJECTORS = {"0": fold, "1": ReducerProjector()}


def project(
    events: list[tuple[Envelope, dict]],
    as_of: str | None = None,
    projector_version: str = "0",
) -> dict[str, Any]:
    """Full replay: project(event_log, as_of, projector_version) from empty.

    The crash-recovery path AND the determinism oracle — a fresh full replay must
    produce, per belief, a view_version_hash identical to the incrementally-folded
    view (spec/NYX_V0_IMPLEMENTATION.md §6 acceptance bar). Folds in insertion
    (rowid) order; deterministic, versioned (Invariant 9). Returns belief_id -> view.

    ADR 0010: include recorded_at <= as_of, preserving log order, and pass the
    evaluation time to the selected fold. Omitted as_of samples the clock once.
    Before genesis the mapping is empty: no belief or update time exists.
    """
    if not isinstance(projector_version, str) or projector_version not in PROJECTORS:
        raise ValueError(f"Unsupported projector_version: {projector_version!r}")
    reducer = PROJECTORS[projector_version]
    if as_of is None:
        as_of = _now_iso()
    cutoff = _instant(as_of, "as_of")
    if isinstance(reducer, ReducerProjector):
        return project_snapshot(events, as_of, projector_version).beliefs()
    view: dict[str, Any] = {}
    position = 0
    previous_id = None
    for envelope, payload in events:
        if _instant(envelope.recorded_at, "recorded_at") > cutoff:
            continue
        if isinstance(reducer, ReducerProjector):
            snapshot = Snapshot(view, position, previous_id, projector_version)
            delta = reducer.reduce(snapshot, envelope, payload, as_of)
            view.update(delta.beliefs)
        else:
            # Refuse unsupported identity events before requiring belief_id.
            if projector_version == "0" and envelope.event_type not in _VALUE_SETTING:
                raise NotImplementedError(f"fold handler for {envelope.event_type!r} not implemented")
            belief_id = payload["belief_id"]
            view[belief_id] = reducer(view.get(belief_id), envelope, payload, as_of)
        position += 1
        previous_id = envelope.event_id
    return view


def project_snapshot(events, as_of: str, projector_version: str = "1") -> Snapshot:
    """Replay the complete identity-capable view, including mention-only prefixes."""
    projector = PROJECTORS.get(projector_version)
    if not isinstance(projector, ReducerProjector):
        raise ValueError("complete snapshot requires a registered snapshot projector")
    cutoff = _instant(as_of, "as_of")
    snapshot = Snapshot({}, projector_version=projector_version)
    for position, (envelope, payload) in enumerate(events, 1):
        if _instant(envelope.recorded_at, "recorded_at") > cutoff:
            continue
        delta = projector.reduce(snapshot, envelope, payload, as_of)
        snapshot = snapshot.apply(delta, position)
    return snapshot


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
