# Nyx v0 Implementation Companion

**Purpose:** NYX_ARCHITECTURE.md is the Constitution — durable, and correctly refuses to invent epistemic coefficients (Invariant 2). This file is the opposite kind of document on purpose: **everything here is provisional, versioned, and expected to be replaced** once real usage data exists. Where the architecture says "rules, not formulas," this is where the *first* formula lives — labeled as a starting hypothesis, never presented as validated truth. Nothing in this file is a Constitution amendment.

**Document authority:** architecture is authoritative for *what/why*; this file is authoritative for *how* (schema, algorithms, defaults, tests). On conflict, the more specific mechanical statement wins and the other file is the bug. This file therefore *decides* mechanics the architecture only names — e.g. the internal ordering scalar (§1) that the architecture's confidence split (§2) defers the *user-facing* version of.

**The governing split:** *epistemic* formulas (decide what's true) stay deferred, genuinely, until there's data to calibrate against. *Operational* formulas (decide speed/order/alerting) are safe to set now, because being wrong costs performance, not integrity. Everything below is sorted into one of three bins: **deterministic** (no guessing possible — just an implementation), **operational v0** (a placeholder with a stated retune trigger), or **explicitly deferred** (with the reason it must stay that way).

---

## 1. Deterministic algorithms (no tuning — implement exactly)

**Event ID.** UUIDv7 (time-ordered UUID). No decision to make — any time-sortable unique ID satisfies §1; UUIDv7 is the standard choice.

**Idempotency key.** `SHA256(source_id || occurred_at || canonicalize(payload))`. Source-scoped duplicate guard per §1 — deterministic, no weighting.

**Event hash (tamper-evidence chain).**
```
event_hash = SHA256(canonical_json(event_minus_hash_fields) || prev_event_hash)
```
Canonical JSON = sorted keys, fixed float format, no whitespace variance — standard content-addressing practice, not invented here.

**Content-addressed dependency hash** (unifies the Liver's re-derivation check and the process trace's `hypothesis_id` matching, per §13's unification TBD — this closes that TBD):
```
dep_hash = SHA256(sorted([event_hash for event_id in dependency_set]))
```
Hashing the **event_hashes**, not just the event_ids, matters: it means the dependency hash also changes if an upstream event gets *superseded* (new event_hash chained on), not only if a dependency literally disappears. This is the single canonical hashing utility both the Liver (§3) and process trace (§7) should call.

**Delta-reducer fold.** Fold *order* is rowid (insertion) for hash determinism, but a value-setting event must not clobber a newer value just because it was *folded* later — the offline-reconnection seam (architecture §4/§5) appends old-`occurred_at` events at high rowid.
```
function fold(prior_view, new_event):
    # value-recency guard: a value-setting event older than the current value
    # updates provenance/support-set but does NOT supersede the newer value
    if new_event.sets_value and new_event.occurred_at < prior_view.value_occurred_at:
        updated_view = add_to_support_set(prior_view, new_event)   # provenance only
    else:
        updated_view = apply_event_to_belief(prior_view, new_event)  # per event_type
        if new_event.sets_value:
            updated_view.value_occurred_at = new_event.occurred_at
    updated_view.view_version_hash = SHA256(prior_view.view_version_hash || new_event.event_hash)
    updated_view.projected_as_of = now()
    return updated_view
```
`apply_event_to_belief` is event-type-specific (`observation_recorded` sets a value; `correction_appended` supersedes; `entity_merge_accepted` re-points affected mentions per the `as_of` rule in §4). Handlers are deterministic — no scoring. The `value_occurred_at` field is added to `resolved_beliefs` (§4) so the guard has state to compare against; without it, out-of-order reconnection events silently corrupt current values.

**Stale-projection check.** Reader compares the materialized `view_version_hash` lineage against `entity_event_index.latest_event_hash` for that belief's entity (the index is updated synchronously with the append, §4, so this check does not race). Mismatch → serve **stale-labeled**, do not block on a re-fold (architecture §8: a labeled stale read beats a stalled one for local single-user); match → serve as current.

**State-transition validator.** The table in §2 is not prose to interpret — implement it as a literal guard:
```
function transition(from_state, to_state, trigger_type, has_world_oracle):
    row = STATE_TABLE.lookup(from_state, to_state)
    if row is None: reject("no such transition")
    if row.requires_world_oracle and not has_world_oracle: reject("promotion requires world oracle — Inv. 3/4")
    return allow
```
This is the entire enforcement mechanism for No Silent Promotion (Invariant 3) — a lookup, not a model call.

**The internal ordering scalar (what the ceiling and Liver actually consume).** The architecture (§2) defers the *user-facing* confidence score but flags that an *internal ordering scalar* is load-bearing now. This file decides it, so the arithmetic below has a real source rather than a deferred value:

- `entity_link_confidence` — a real `REAL` in `[0,1]`, produced by the resolver, stored on `entity_links` (§4 schema). Exists at v0.
- `claim_confidence` for the ceiling is **not** a synthesized float at v0 — it is the **state ordinal**: `quarantined=0 < questioned=1 < unverified=2 < verified=3`, normalized to `[0,1]` as `ordinal/3`. This is countable, non-invented, and already fully specified by the state machine.
- The Liver queue's `low_conf_source` term (§2) is a **boolean** from source reliability, not this scalar — no synthesized number needed there either.

```
# v0: state ordinal stands in for claim_confidence; no invented float
claim_scalar = STATE_ORDINAL[verification_state] / 3.0
effective = min(claim_scalar, min(link.entity_link_confidence for link in chain))
```
Weakest-link `min` is the epistemically safe permanent choice. The only thing deferred is a *richer* synthesized `claim_confidence` later — the ordering scalar itself is decided and available, closing the "deferred in §3 but used in §1" contradiction the last review pass caught.

---

## 2. Operational v0 defaults (placeholders — retune trigger stated for each)

**Liver priority-queue score.** Not a truth formula — an *ordering* formula. Wrong weights mean the Liver audits things in a suboptimal sequence, not that it believes something false.
```
priority = w1*days_since_last_audit + w2*reference_count + w3*is_single_source + w4*is_low_confidence_source
```
v0 weights: `w1=1, w2=2, w3=3, w4=3` — arbitrary, roughly-equal starting point, sole purpose is establishing *an* order before real data exists.
**Retune when:** you have enough Liver history to check which flagged items actually turned out to matter (led to a real demotion/correction) vs. which were false alarms — reweight toward what predicted real problems.

**`idle_compute_budget` (§6).** v0: max 15% VRAM allocation for background Dream/Liver work while idle; max ~2,000 tokens/minute background spend; new background GPU submission halted within ~500ms–1s of a foreground request arriving (poll interval, not true interrupt — per §6's hardware caveat).
**Retune when:** running on real hardware (2080 Ti now, eventual 22GB card) — these numbers are guesses about your actual headroom, not measurements of it.

**Minimum sample floor (corroboration gate, §2/§4).** v0: **2** independent corroborating sources required for `unverified → verified` via corroboration. A direct world-oracle confirmation (human, for the relevant claim class) satisfies promotion on its own — it's already independent and authoritative by definition (Inv. 4), not subject to the count.
This is a discrete gate, not a continuous weight — lower-risk to set now than a scoring formula, and it's what "corroboration gates state" (§2) needs to actually run.
**Retune when:** you observe how often single-vs-double corroboration turned out reliable.

**Spleen alert thresholds (§3).** v0: contradiction-rate alert fires if unresolved contradictions exceed 2× the trailing 7-day average; immune false-positive halt fires if the false-positive rate exceeds 5% of intake in a rolling window.
**Retune when:** you have a baseline "normal" rate to compare against — these are meaningless until there's a trailing average to be a multiple *of*.

---

## 3. Explicitly deferred — and why a v0 number is *not* given here

**Confidence as a synthesized numeric score.** No placeholder formula is provided, deliberately — and it isn't needed to start coding. **v0 does not need a confidence score at all.** Everything actionable already exists without one: `verification_state` (the state machine, fully specified, §2) plus the **support set** (raw corroboration count, sources, opposing events, §2) gives every downstream component what it needs to act — the Liver prioritizes off structural factors (§1 above), the UI shows state-not-score by design (§8 already forbids rendering a decimal), and routing doesn't need a number either. A synthesized confidence score is a **ranking convenience for later**, not a blocker now. Ship v0 surfacing state + support set directly; add a real numeric score only once there's observed accuracy data to calibrate it against. Inventing one now would be the exact false-precision Invariant 2 forbids, for zero present benefit.

**Confidence decay curves.** Same reasoning — decay *category* (time-sensitive vs. timeless vs. unverifiable, already specified in §2) is enough to start; the decay *rate* stays deferred until there's data on how fast categories actually go stale in practice.

---

## 4. Schema (SQLite, WAL mode) — mechanical translation of already-decided fields

```sql
-- Layer A: Reality Layer. Append-only, ENGINE-enforced (Invariant 1).
-- ENVELOPE / PAYLOAD SPLIT (architecture Invariant 14): the hash chain covers
-- envelopes only, so a destroyed payload never breaks verification.
-- Envelope is PII-free by construction -- no free text, actor is an opaque id.
CREATE TABLE events (
    event_id        TEXT PRIMARY KEY,   -- UUIDv7
    idempotency_key TEXT NOT NULL,
    schema_version  TEXT NOT NULL,
    event_type      TEXT NOT NULL,      -- §1 taxonomy
    occurred_at     TEXT NOT NULL,      -- ISO8601, source time
    recorded_at     TEXT NOT NULL,      -- ISO8601, ingest time
    source          TEXT NOT NULL,      -- JSON: {actor_id (opaque), config}
    source_class    TEXT NOT NULL,      -- corroboration counts DISTINCT classes, not
                                        -- raw events -- collapses correlated ingestion
                                        -- (shared model context, re-entrant Dream
                                        -- synthesis, duplicate pasted origin)
    origin_type     TEXT NOT NULL,      -- observed|user_stated|verified_external|derived|personal
    payload_hash    TEXT NOT NULL,      -- content address of the payload row below
    entity_refs     TEXT,               -- JSON array, nullable (§11 soft links);
                                        -- resolves to canonical_entity_id post-merge
    prev_event_hash TEXT,
    event_hash      TEXT NOT NULL UNIQUE  -- covers envelope fields ONLY, not payload
);
CREATE UNIQUE INDEX idx_events_idempotency ON events(idempotency_key);

-- Payload: separately destroyable via key destruction (crypto-shredding).
-- Encrypted at write with a per-canonical-entity key from the keystore
-- (NOT per-mention -- a mention's key has no owner once entities merge/split).
-- A redacted payload is deleted here; the envelope row above is untouched,
-- so replay yields a typed REDACTED sentinel, never a broken chain.
CREATE TABLE payloads (
    payload_hash    TEXT PRIMARY KEY,
    event_id        TEXT NOT NULL REFERENCES events(event_id),
    canonical_entity_id TEXT,           -- key-binding target; nullable pre-resolution
    ciphertext      TEXT,               -- NULL after redaction (key destroyed)
    redacted        INTEGER NOT NULL DEFAULT 0
);

-- Append-only is a MECHANISM, not a convention (Invariant 1):
CREATE TRIGGER no_update_events BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'Layer A is append-only: updates forbidden'); END;
CREATE TRIGGER no_delete_events BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'Layer A is append-only: deletes forbidden'); END;

-- Resolved View: materialized, version-hashed projection (§1, decided: materialized-delta)
CREATE TABLE resolved_beliefs (
    belief_id           TEXT PRIMARY KEY,  -- e.g. "entity:legion/property:ram"
    current_value        TEXT,
    value_occurred_at     TEXT,            -- occurred_at of the event that set current_value;
                                           -- the fold's value-recency guard compares against this (§1)
    verification_state     TEXT NOT NULL,   -- §2 two-dimensional state
    verifiability            TEXT NOT NULL,
    display_origin            TEXT,
    supporting_events          TEXT NOT NULL, -- JSON array of event_id
    opposing_events             TEXT NOT NULL, -- JSON array of event_id
    resolution_basis              TEXT,
    view_version_hash              TEXT NOT NULL,  -- SHA256(prior_hash || latest folded event_hash)
    projected_as_of                 TEXT NOT NULL,  -- Invariant 9, explicit evaluation time
    updated_at                       TEXT NOT NULL
);

-- Stale-read detection: entity -> latest committed event touching it.
-- Updated SYNCHRONOUSLY in the same transaction as the events append (§1) —
-- the one exception to "append is the only sync step." Without this, stale
-- detection races the async projection and reads can be wrong-but-unlabeled.
CREATE TABLE entity_event_index (
    entity_id            TEXT PRIMARY KEY,
    latest_event_id       TEXT NOT NULL,
    latest_event_hash      TEXT NOT NULL,   -- reads compare view_version_hash lineage against this
    updated_at              TEXT NOT NULL
);

-- Process trace: SEPARATE store. Crash-durable (WAL + fsync) but MUTABLE —
-- explicitly NOT append-only. Grading updates a trace in place (ungraded ->
-- graded), so it cannot carry Layer A's immutability guarantee and has no
-- update-blocking trigger. (Corrects earlier "same guarantees as Layer A"
-- phrasing: immutability IS that guarantee; this table deliberately lacks it.)
CREATE TABLE process_traces (
    trace_id            TEXT PRIMARY KEY,
    hypothesis_id        TEXT NOT NULL,
    semantic_hash          TEXT NOT NULL,   -- unified content-addressing, §1 above
    model                    TEXT NOT NULL,
    evidence_available        TEXT,          -- JSON
    retrieved                   TEXT,          -- JSON
    failure_class                 TEXT,          -- missing_info|overlooked_info|wrong_model|NULL(ungraded)
    graded                          INTEGER NOT NULL DEFAULT 0,
    created_at                       TEXT NOT NULL
);
CREATE INDEX idx_traces_hypothesis ON process_traces(hypothesis_id, semantic_hash);

-- Record of absence (§5)
CREATE TABLE gaps (
    gap_id                    TEXT PRIMARY KEY,
    search_scope_signature     TEXT NOT NULL,
    methods_tried                 TEXT NOT NULL,  -- JSON array
    searched_at                    TEXT NOT NULL,
    verification_state              TEXT NOT NULL DEFAULT 'unverified',
    event_id                          TEXT NOT NULL  -- FK -> gap_recorded event
);

-- Identity v1 minimum (§11) — soft links only, no canonical graph yet
CREATE TABLE entity_links (
    mention_id               TEXT PRIMARY KEY,
    candidate_entity_id       TEXT NOT NULL,
    canonical_entity_id        TEXT,             -- nullable
    entity_link_confidence      REAL NOT NULL,
    link_basis                    TEXT,
    link_state                     TEXT NOT NULL,  -- proposed|accepted|rejected|split
    event_id                        TEXT           -- FK, set once decision becomes a Layer A event
);
```

---

## 5. Pre-coding gate: two worked traces (do this BEFORE writing component code)

Every bug found across eleven review passes was a *composition* or *seam* failure, not a component failure — because the whole council reviews artifacts and nobody executes them. The cheap fix is not a sixth reviewer; it is two traces pushed through the pipeline **by hand (or by the walking skeleton) before trusting any of this**:

1. **Hostile-input trace.** Take one crafted prompt-injection / malformed-write and walk it step by step through the §1 write path — immune stages, affect split, extraction, append-or-reject, index update. Confirm it either gets rejected-and-logged or lands as inert data, and that no stage silently "fixes" it into something that passes. This exercises the intake seam.
2. **Reconnection trace.** Simulate: append an `observation_recorded` value at T=now; then append a *second* value with `occurred_at` three weeks in the past (the offline-backlog case). Walk the fold. Confirm the older event updates the support set but the newer value survives (the §1 value-recency guard). This exercises the reconnection seam — the one that hid the out-of-order-fold bug from every reviewer.
3. **Redaction-demotion trace.** A belief at `verified` on three supporting events crosses its threshold; redact one. Walk the two-phase protocol (`redaction_requested` → key destroyed → sweep → `redaction_completed`). Confirm the belief lands at the correctly demoted state via incremental sweep, then confirm full replay-from-genesis under the current redaction set agrees. Exercises sweep/replay equivalence (architecture §4).
4. **Merge-pooling trace.** Two entities whose *pooled* events would cross a `verified` threshold that neither cleared alone. Walk the merge. Confirm the result is hold-plus-gated-proposal, never automatic promotion (Invariant 15).
5. **Crash-point trace.** Kill the process between each adjacent step of the redaction sequence — after `requested`, after key destruction, after the sweep, before `completed`. Confirm startup scan (`*_requested` with no matching `*_completed`) rolls forward correctly and idempotently from every kill point.

If any trace surfaces a gap, fix the spec before coding. These seams — intake, reconnection, redaction, merge, crash — are where the surviving bugs lived; running them on paper converts the last of the static-analysis blind spot into something caught pre-compile. Once code exists, promote all five into permanent property-based tests (generate event/redaction/merge sequences, assert fold ≡ replay, assert the support graph stays a DAG, assert no state transition promotes via reinterpretation) rather than one-time manual traces — a harness that runs forever beats a review that ran once.

## 6. Walking skeleton — Phase 1's actual acceptance bar

Not "build the immune system." One vertical slice, end to end, before anything gets built wide:

1. Submit one `observation_recorded` event (simplest origin type — no affect-split complexity yet).
2. Immune **Stage 1 only** (schema validation) — Stages 2–4 stubbed for the skeleton.
3. Append to `events` (idempotency key enforced, hash chain computed).
4. Delta-reducer folds it into `resolved_beliefs` (one row, `view_version_hash` computed).
5. Read it back; confirm a fresh full-replay fold produces an identical hash.

**Concrete acceptance test:**
```
GIVEN a fresh database
WHEN an observation_recorded event for "legion.ram = 64GB" is submitted
THEN events contains exactly 1 row with a valid event_hash
AND resolved_beliefs shows belief_id="entity:legion/property:ram", current_value="64GB",
    verification_state="verified", verifiability="externally_checkable"
AND replaying the full events log from empty produces an identical view_version_hash
AND resubmitting the exact same event (same idempotency_key) does not create a second row
AND attempting UPDATE on events raises an error (trigger enforcement, Invariant 1)
```
This is the real "done" bar for the first slice of Phase 1 (§12) — concrete and testable, not a component checklist.

---

## 7. Protocol: what Code does when it hits a gap

This document has three different kinds of "not fully specified," and they require three different behaviors. Code needs to know which one it's in, not infer it — the same distinction the architecture itself makes between "didn't look," "looked and found nothing," and "doesn't exist" (§5 of the architecture doc) applies here to the build process, not just to Nyx's own memory.

**1. Operational v0 defaults (§2, above) — SETTLED. Code against these directly.**
Do not ask, and do not silently "improve" a v0 number using your own judgment while implementing — if one looks wrong, flag it in the decision log rather than quietly changing it. Mark each with a comment citing its retune trigger, e.g.:
```python
LIVER_WEIGHTS = {"age": 1, "refs": 2, "single_source": 3, "low_conf_source": 3}
# v0 placeholder — retune once real audit history exists; see NYX_V0_IMPLEMENTATION.md §2
```

**2. Explicitly deferred (§3, above) — DO NOT invent a substitute.**
Use the stated fallback (state + support set stand in for a numeric confidence score; if a downstream step needs "a number," the fallback is corroboration *count*, not a synthesized score). Comment why nothing exists here, pointing at §3 — so a future reader, human or Code, doesn't mistake a deliberate absence for an oversight and quietly patch one in.

**3. Still open / unworked (§8, below) — STOP. Do not design a silent solution.**
Write a stub that fails loudly and points at the gap, rather than an implementation that will read as a real decision to the next person who opens the file:
```python
def wire_immune_stage_2(payload):
    raise NotImplementedError("Immune Stage 2 wiring undecided — see NYX_V0_IMPLEMENTATION.md §8")
```
Or ask directly. Either is fine. Guessing and moving on is not — that's exactly how a stub becomes load-bearing without anyone deciding it should be.

**4. Anything not listed in either document at all — highest-priority stop.**
Zero existing guidance means zero grounds to guess. This is the case with the least excuse for improvising, precisely because there's nothing here even attempting to cover it.

This extends the existing prompt-library norms (#6, #8, #9 — read the current committed file, never reconstruct from memory, one task at a time) with one more rule specific to these two spec files: know which of the four categories you're in *before* deciding whether to proceed or stop.

---

## 8. Still open (unlike §3, these just haven't been written yet — not deferred on principle)

- Delta-reducer per-event-type handlers (only `observation_recorded` is worked above; `correction_appended`, `entity_merge_accepted`, etc. need the same treatment). The value-recency guard (§1) applies to all value-setting handlers.
- Immune Stages 2–4 wiring (classifier invocation, STLM invocation path — subprocess vs. local server vs. embedded, per last session's "boundary decisions" gap). Stage 3 ships **static** (architecture §3) — no retraining loop until a threat corpus exists.
- Decision log (`decisions/0001-projection-model.md` style) — cheap to start, saves relitigating settled calls. Offer stands to stub this next.
- `meta_commentary` tagging (architecture Inv. 11): payload carries `meta_commentary: bool` + `meta_subtype` (`callback` | `self_reference`), assigned **at generation** before emit (so the ceiling can gate). Classification must be cheap and deterministic; ambiguous → default `self_reference` (under-counting inferred commentary is the failure to avoid, not over-counting). Tag is descriptive payload on the envelope, out of the confidence/ranking axis entirely. **Open:** the drift-metric sweep (rate of `self_reference` per window — align the window to whatever the emergence monitor already sweeps on, don't maintain two clocks) and the suppress-on-ceiling behavior. `callback` has no ceiling. The emergence monitor that owns this is itself unspecified (architecture §13) — until it exists, the tag can be *written and stored* but the ceiling has nothing to enforce it, so this ships as **tag-now, enforce-later**.
- Parameter-change event type (architecture §4 failure modes): a logged, outside-the-ledger event recording emotion/expression parameter changes (Spleen weighting, `self_reference` ceiling, pivot triggers), session-scoped by default, non-promoting like `meta_commentary`. Sandbox tuning is a **forked event log**, not a runtime flag — no `dev_mode` branch in live code.

*Resolved this pass (were contradictions, now decided): internal ordering scalar = state ordinal + link confidence (§1); reducer value-resolution keys on `occurred_at` (§1); `entity_event_index` synchronous with append (§4); process-trace mutable-not-immutable (§4); Stage 3 static-first (§3). All five were cross-file or seam bugs that survived eleven review passes.*

*Resolved in the erasure/merge pass: erasure mechanism decided (envelope/payload split, crypto-shredding, Invariant 14, §4 schema); the never-promote-on-reinterpretation rule generalized to Invariant 15 (redaction and merge both); correlated-corroboration overcalibration fixed via `source_class` (§2, §4); sweep/replay equivalence and the crash-between-key-destruction-and-completion gap added as failure modes (§4); crash-recovery is a startup scan for `*_requested` without `*_completed`, idempotent roll-forward. All found by forward-simulating the write path rather than reviewing it statically — the same review-vs-execution gap named in the council doc, now with a concrete instance of the fix (property-based testing, §12) rather than just the diagnosis.
