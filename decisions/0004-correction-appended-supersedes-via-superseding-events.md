# 0004 — `correction_appended` supersedes via a `superseding_events` column; the belief head is never marked `superseded`

- **Status:** Accepted — ratified by Josh, 2026-07-13; superseded in part by [ADR 0018](0018-correction-supersedes-candidates.md) for projector "1" correction payloads and supersession representation. The backdated-correction open gap is subject to [ADR 0005](0005-backdated-corrections-fail-loud-pending-semantics.md).
- **Date:** 2026-07-13
- **Scope:** `correction_appended` fold handler — `src/nyx/projection.py` `fold()`,
  `schema.sql` (`resolved_beliefs`), `src/nyx/storage.py`, `src/nyx/skeleton.py`
- **Relates to:** Invariants 1, 3, 5, 6 · Architecture §2 (state-transition contract,
  line 104) · V0 §1 (value-recency guard), §4 (schema), §5 (trace 2), §8 (line 287)

## Context

V0 §8 line 287 lists the `correction_appended` fold handler as still open: *"only
`observation_recorded` is worked above; `correction_appended`, `entity_merge_accepted`,
etc. need the same treatment. The value-recency guard (§1) applies to all value-setting
handlers."* V0 §1 line 44 is the entire mechanical statement of its semantics:
*"`correction_appended` supersedes."*

Writing the handler surfaced a three-way conflict about **where `superseded` is
recorded**:

1. **Architecture line 104** places `superseded` in the *state-transition contract*:
   `| any | superseded | correction event resolves prior event | depends on source |
   Yes (structural) |`. Read literally, a record's `verification_state` **becomes**
   `superseded`.
2. **V0 §4** makes `resolved_beliefs` **one row per attribute** (`belief_id` =
   `"entity:legion/property:ram"`), with a single `current_value` and a single
   `verification_state`. After a correction, that row holds the **live corrected
   value**. Setting its state to `superseded` would mark the live head as superseded
   and make `superseded` an absorbing state every corrected belief is stuck in forever.
3. **Invariant 6** names four event classes a belief exposes — supporting, opposing,
   **superseding**, gap — but the §4 DDL carries columns for only *supporting* and
   *opposing*. There is nowhere to record supersession. And Inv. 6 also states that
   verification *"adds to the set, never rewrites a member"*, which forbids the obvious
   workaround of retagging the superseded observation in place.

## Decision

**The belief head is never parked in `verification_state = 'superseded'`.** A
correction supersedes by *provenance*, not by putting the live head into a dead state:

- `current_value` / `value_occurred_at` become the correction's. The head stays **live**.
- The correction's `event_id` is recorded in a **new `superseding_events` column** on
  `resolved_beliefs` — the Inv. 6 class the §4 DDL omitted.
- The value it superseded **stays in `supporting_events`**, unmoved and unretagged
  (Inv. 6: never rewrite a member). The support set is append-only, like Layer A.
- `verification_state` is **origin-driven**, resolved by `_state_for_origin()` from the
  event's own origin type — never from the fact that it is a correction. A correction
  does not auto-promote (Inv. 3).
- `resolution_basis` records the supersession in words.

Per the two-file provenance rule (V0 is authoritative for schema/*how*; architecture for
*what/why*), **architecture line 104 is the bug**: it describes a belief-row transition
the §4 schema cannot express. It is not a second opinion to reconcile in prose.

## Rationale — including the correction-first convergence finding

Order-independence of resolved state comes from the **existing §1 value-recency guard**,
not from fold order. Fold order is rowid (§1, for hash determinism); the value a belief
resolves to keys on `occurred_at`. So:

- **Observation-first:** the observation sets the head; the correction (later
  `occurred_at`) supersedes it.
- **Correction-first:** the correction sets the head; the observation folds in *older*,
  hits the value-recency guard, and contributes provenance only. Same resolved value.

Walking the correction-first order by hand (V0 §5 trace 2, applied to corrections)
produced the finding that **drove the implementation**: on that order the correction
meets `prior_view = None` — *there is no head to supersede yet*. Had
`superseding_events` been populated only when a prior head existed, it would come out
empty in one order and populated in the other, **for the same two events**. The resolved
support set would then depend on arrival order, and order-independence dies.

Therefore: **`superseding_events` is populated by EVENT TYPE, not by whether a prior head
happened to be folded first.** A `correction_appended` *is* a superseding event (Inv. 6's
class) by its nature, regardless of arrival order. This is exactly the class of
composition/seam bug V0 §5 exists to catch, and it was caught by executing the trace
rather than reviewing it.

`view_version_hash` is **order-dependent by design** — it chains
`SHA256(prior || event_hash)` in rowid order (§1). Equality is asserted **fold-vs-replay
within an order** (the executable invariant), and deliberately **not across orders**;
making it order-invariant would require a hash redesign §1 rejects. Order-independence is
asserted on resolved **state** only.

Nothing here promotes anything. The correction is an ordinary append; it supersedes by
being a later event, never by editing one (Inv. 1, Inv. 5).

## Consequences

- `resolved_beliefs` gains `superseding_events TEXT NOT NULL`. This is an **addition to
  §4's DDL** — flagged as such in `schema.sql`, not a silent redesign.
- `observation_recorded` now also emits `superseding_events` (empty). The five §6
  skeleton tests remain green.
- `gap_events` remains the one Inv. 6 class with no column. Unbuilt — there is no
  `gap_recorded` handler yet. Not a decision, just an absence.
- Both value-setting types share one write path (`skeleton._record`): same validation,
  same hashing, same append. They differ only in the provenance the fold records.

## Open gaps this decision deliberately does NOT close

1. **Backdated corrections.** A correction whose `occurred_at` is *older* than the value
   it corrects currently folds through the value-recency guard as provenance only — it
   would **not** take the head. That is very likely wrong for a deliberate, authoritative
   correction, but the right semantics are undecided. **Do not infer the intended
   behaviour from what the code happens to do.** Not built, not tested.
2. **Origin → state mapping beyond `observed`.** `_state_for_origin()` maps `observed`
   only and raises `NotImplementedError` for anything else. `user_stated` in particular
   cannot simply reuse it: architecture §2's user-stated split ("User asserted X" vs "X is
   true" — the user is a *source*, not ground truth, outside preference claims) means a
   user-stated correction must earn its state differently. Fail loud, don't guess (§7 gap
   protocol).
3. **`idempotency_key` does not include `event_type`.** §1 defines it as
   `SHA256(source_id || occurred_at || canonicalize(payload))`. An observation and a
   correction with identical source, `occurred_at`, and payload would therefore collide
   into a single row. §1 is explicit, so this was **not** changed — recorded here as a
   latent edge, not a decision.
4. **Runtime is Python 3.14.2**, but `CLAUDE.md` says 3.11/3.12 ("the spec's earlier 3.14
   target was walked back"). The suite is green on 3.14, so nothing was acted on — but one
   of the two is stale and should be reconciled.

## Alternatives considered

- **Follow architecture line 104 literally — set the head's `verification_state` to
  `'superseded'`.** Rejected: the row holds the live corrected value while declaring
  itself superseded, and `superseded` becomes an absorbing state — a corrected belief
  could never read `verified`/`unverified` again.
- **Retag the superseded observation inside `supporting_events`.** Rejected on two counts:
  Inv. 6 forbids rewriting a member of the support set, and the §4 column is a JSON array
  of bare `event_id` strings with no per-member annotation slot to write into.
- **Restructure `resolved_beliefs` to one row per value** (so a prior-value row can hold
  `superseded` and the head is a separate row). Rejected: a real redesign of the core
  projection table, which CLAUDE.md's top rule forbids doing unilaterally. If line 104 is
  ever to be made literally true, *this* is the change it implies — and it is a spec
  change, not an implementation tweak.

---

*Decision-log format: one decision per file, `NNNN-kebab-title.md`, append-only in
spirit — supersede with a new file rather than rewriting a ratified one. Style per
`NYX_V0_IMPLEMENTATION.md` §8.*
