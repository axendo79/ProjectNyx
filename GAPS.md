# Known gaps

Findings and their **open, deferred, or resolved** status, checked against the code.
Refusal behavior is stated per finding; a logged gap does not imply that every
affected path already fails before append.

This file is the register. Where a gap carries enough reasoning that it must not be
relitigated, it has an ADR in `decisions/` and this file points at it.

> **Before entity-merge work, read [ADR 0013](decisions/0013-cross-belief-identity-semantics.md),
> then [ADR 0014](decisions/0014-cross-belief-reducer-and-hash-lineage.md) as amended by
> [ADR 0015](decisions/0015-candidate-scoped-verification.md), with current stage limits in
> [ADR 0023](decisions/0023-stage-two-contract.md).**
> ADR 0014 supersedes the recorded blocker in [ADR 0008](decisions/0008-fold-signature-cannot-express-cross-belief-events.md).
> The reducer seam is implemented for stage two; merge/split handlers remain unimplemented.

---

## Cross-belief reducer — seam implemented; merge/split handlers pending

### The legacy `fold` signature cannot express a cross-belief event — resolved for projector "1"
**→ [ADR 0008](decisions/0008-fold-signature-cannot-express-cross-belief-events.md)** ·
Recorded blocker resolved by [ADR 0014](decisions/0014-cross-belief-reducer-and-hash-lineage.md)
(accepted 2026-09-08); stage-two seam implemented · `src/nyx/reducer.py`, `src/nyx/projection.py`

Projector "0" retains `fold(prior_view, envelope, payload, as_of) -> dict` and its
single-belief lineage. For projector "1", `project` dispatches to the snapshot
reducer in `src/nyx/reducer.py`, which returns one complete event delta. Mention
events need no belief, and one observation can affect multiple beliefs. The
public `project` return shape remains a belief mapping.

The superseding reducer and lineage contract is [ADR 0014](decisions/0014-cross-belief-reducer-and-hash-lineage.md).
Its stage-two seam, structured lineage, derived progress, atomic publication,
and recovery ship in `src/nyx/reducer.py` and `src/nyx/storage.py`, with coverage in
`tests/test_reducer_boundary.py`. Version "0" remains isolated.

ADR 0008 retains the historical finding and warning against ad hoc workarounds.
The former differing-state merge refusal is superseded by
[ADR 0015](decisions/0015-candidate-scoped-verification.md).
For the current unimplemented merge/split stage, see [ADR 0023](decisions/0023-stage-two-contract.md).

---

## Correctness gaps

### Redaction breaks the write path and replay
`src/nyx/storage.py` · Invariant 14 · unbuilt, **will fail loudly if reached**

A redacted payload has `ciphertext = NULL` (key destroyed). Two sites assume it is present:

- `safe_append_event` extracts the entity key with `json.loads(payload.ciphertext)["belief_id"]`
  → `TypeError` on `None`.
- `read_all_events` yields a `None` payload for a redacted row, which `project` then
  subscripts → `TypeError`.

So the moment redaction exists, **replay of a log containing a redacted event dies** — and
replay is the crash-recovery path *and* the determinism oracle (§6). The spec's own answer
is that replay must yield a **typed REDACTED sentinel** rather than a broken chain
(`schema.sql`, V0 §4); that sentinel does not exist yet. Redaction is unbuilt, so this is
unreachable today.

### `project()` event dispatch — resolved for supported stages
`src/nyx/projection.py` · **RESOLVED**

Version "0" rejects unsupported event types before requiring `payload["belief_id"]`.
Version "1" dispatches to the complete snapshot reducer and supports mention
events and explicitly scoped observations. Unsupported event types still refuse;
their implementation limits are governed by [ADR 0023](decisions/0023-stage-two-contract.md).

### `as_of` / `projector_version` — resolved
**RESOLVED ([ADR 0010](decisions/0010-projection-parameters.md), commit `101007b`):** `project()` now
bounds `recorded_at` inclusively and selects a versioned fold from a registry;
unsupported versions raise. `fold()` receives an explicit evaluation time for
`projected_as_of`, and `updated_at` comes from the last included event's `recorded_at`.
Regression tests compare complete serialized views across incremental fold and replay at a shared evaluation time, and cover a single-belief live write. They do not establish whole-view equality for live materialized beliefs updated at different times; ADR 0012 defines and implements a separate explicit whole-view evaluation operation, described below.

---

### Whole-view equality across live materialized beliefs and replay
**RESOLVED ([ADR 0012](decisions/0012-whole-view-equality.md)):**
`storage.evaluate_whole_view(conn, as_of, projector_version="0")` reconstructs
from the log at an explicit shared evaluation time and selected projector version.
It leaves raw materialized rows and Layer A unchanged. Ordinary `read_belief()`
continues to read materialized state without replay.

All seven ADR acceptance cases are covered in `tests/test_whole_view_equality.py`,
including complete-field comparisons, historical cutoffs, and a controlled
time-dependent projector. Different timestamps on raw live materialized rows
remain expected; those rows are not automatically a shared-time snapshot.
ADR 0008's event-shape blocker is resolved by ADR 0014 and the stage-two seam is
implemented. The superseding verification boundary is in
[ADR 0015](decisions/0015-candidate-scoped-verification.md); remaining stage limits
are in [ADR 0023](decisions/0023-stage-two-contract.md).

---

## Schema / operational gaps

### Database schema versioning — resolved
**RESOLVED ([ADR 0011](decisions/0011-database-schema-versioning.md)):** `init_db()`
validates metadata on every new connection. Ordinary opens never create or stamp
metadata. Explicit `create=True` initializes only an empty database, with schema
and metadata in one transaction; non-empty creation requests refuse. Missing,
zero, unsupported, or malformed metadata refuses without repair or migration.
The ADR acceptance tests cover refusal without mutation and rollback on failure.
Automatic migrations remain outside scope; incompatible databases are rejected.

### Timestamp canonicalization belongs at the ingestion boundary
`src/nyx/immune.py` · follow-on from
[ADR 0006](decisions/0006-occurred-at-comparison-is-instant-based-not-lexical.md)

Stored timestamp strings are not canonicalized on ingestion. In projector "0",
immune Stage 1 accepts a naive (offset-less) `occurred_at`. `_instant()` refuses
it only when a comparison is reached; a first value can bypass that comparison
and materialize successfully. Later comparison can fail after an observation has
already appended. See `immune.stage1_schema_validate`, `projection.fold`, and
`projection.assert_not_backdated`.

Projector "1" validates timezone-bearing timestamps through `reducer.reduce`
before append and again during replay, without rewriting the recorded strings.
The remaining legacy boundary gap must not be mistaken for guaranteed refusal.

---

## Undecided semantics (fail loud, on purpose)

### Backdated corrections
**→ [ADR 0005](decisions/0005-backdated-corrections-fail-loud-pending-semantics.md)** ·
raises `BackdatedCorrectionError`

A correction whose `occurred_at` predates the value it corrects is **refused**, pending a
decision: is a correction *newer information* (recency-governed → folds as provenance only)
or an *authoritative override* (takes the head regardless of date)? Settling it means
settling whether `occurred_at` on a correction is **event** time or **validity** time. The
raise is greppable so the decision, when made, finds every site that assumed it was open.

### Origin → verification_state beyond `observed`
**→ [ADR 0004](decisions/0004-correction-appended-supersedes-via-superseding-events.md)** ·
`_state_for_origin` raises `NotImplementedError`

Only `observed` is mapped (ADR 0001). `user_stated` cannot reuse it: architecture §2's
user-stated split ("User asserted X" vs "X is true" — the user is a *source*, not ground
truth, outside preference claims) means it must earn its state differently.

### Candidate corrections and target eligibility
**Deferred:** [ADR 0018](decisions/0018-correction-supersedes-candidates.md) governs
candidate supersession; [ADR 0023 §5](decisions/0023-stage-two-contract.md#5-corrections-are-deferred-under-version-1)
governs the current stage boundary. Candidate-target eligibility is incomplete.
Version "1" refuses corrections before append and on replay, including explicit-target
submissions. Version "0" retains its implemented correction path and existing refusals.

### Existing-subject association and multi-user authority
**Blocked:** admissible association bases remain unratified under
[ADR 0019 §4](decisions/0019-identity-bootstrap.md#4-association-with-an-existing-subject-requires-an-admissible-basis).
Authority assumptions remain undecided under [ADR 0020](decisions/0020-multi-user-authority-undecided.md),
including a single operator handling different speakers' assertions. Stage two
refuses existing-subject associations at append and replay. Attribution and
constitutive bootstrap do not supply the missing authority decision.

### Mention correction
**Undecided:** [ADR 0019 §1](decisions/0019-identity-bootstrap.md#1-mention-recording-is-a-separate-event)
and [ADR 0021](decisions/0021-bootstrap-link-treatment.md) leave mention-correction
mechanics open. No handler ships; candidate-correction semantics do not fill this gap.

### Support attachment to an existing ClaimCandidate
**Out of scope pending decisions:** [ADR 0023 §2](decisions/0023-stage-two-contract.md#2-ordinary-observations-create-fresh-claimcandidates).
Claim continuity, targeting/applicability, verification effects, dependency history,
correction scope, and retry treatment are not supplied for support attachment.
Distinct observations reusing a candidate ID refuse at append and replay.

### Retention, coalescing, and temporal resolution
**Undecided:** retention/coalescing remains open under [ADR 0023](decisions/0023-stage-two-contract.md).
The lineage-scaling probe is reported in `README.md`; it authorizes no reduction
in lineage coverage. Temporal applicability and disagreement resolution remain
open under [ADR 0024](decisions/0024-no-authoritative-head.md). No aging-out,
latest-value selection, or value-based candidate compaction ships for version "1".

The repeated serialization and rebuilding of accumulated collections is
**resolved for projector "2"** by
[ADR 0025](decisions/0025-incremental-result-commitment.md). Canonical incremental
trees preserve all candidates, dependencies, and provenance paths; this settles
representation, not retention or coalescing. Version "1" remains frozen. Full
content reads still enumerate collections, and immutable historical tree nodes
are retained. Migration, collection reclamation, and checkpoints do not ship.

### Usage recording
**Boundary resolved; recording mechanics undecided:**
[ADR 0026](decisions/0026-usage-is-not-evidence.md) excludes Dream references,
retrieval exposures, and activation records from evidence and belief lineage.
It binds the non-authoritative activation direction in `design/`. Recording
location, durable authority, ordering, retention, recovery, configuration, and
usage replay remain unspecified. No usage recorder ships; submitting a usage
event to the world-evidence reducer refuses at append and replay.

### Additional scalar belief reads
**Deferred:** [ADR 0024 §2](decisions/0024-no-authoritative-head.md#2-scalar-belief-requests-and-named-candidate-reads).
Common-value reads for multiple agreeing candidates are undecided. The code also
supplies no single-candidate scalar belief contract; `scalar_belief_value` refuses
multiple candidates and otherwise raises `NotImplementedError`. Named-candidate
value reads are implemented.

### Later link treatment and support-dependent verification transitions
**Blocked where unspecified:** non-constitutive link treatment is governed by
[ADR 0021 §3](decisions/0021-bootstrap-link-treatment.md#3-confidence-ceiling-computation);
the current reducer refuses it. Unspecified support-dependent demotion/restoration
transitions remain subject to [ADR 0015 §5](decisions/0015-candidate-scoped-verification.md#5-restrictions-follow-actual-dependencies).
The implemented candidate records and constitutive links do not supply those decisions.

---

## Noted, not acted on

- **`idempotency_key` omits `event_type`.** V0 §1 defines it as
  `SHA256(source_id || occurred_at || canonicalize(payload))`. An observation and a
  correction with identical source, time, and payload would collide into one row. §1 is
  explicit, so this was not changed — recorded as a latent edge. ([ADR 0004](decisions/0004-correction-appended-supersedes-via-superseding-events.md))
- ~~**Python version.** Runtime is **3.14.2**; `CLAUDE.md` says 3.11/3.12 ("the spec's earlier
  3.14 target was walked back"). Suite is green on 3.14. One of the two is stale.~~ **RESOLVED
  ([ADR 0009](decisions/0009-python-314-re-adopted-as-target.md)):** 3.14 re-adopted as the
  target. The architecture §402 downgrade P0 was never enforced, 3.14 is the only interpreter
  installed, and the suite is green on it. `CLAUDE.md` and §402 updated to match.
- **`gap_events` has no column.** Invariant 6 names four event classes a belief exposes
  (supporting, opposing, superseding, gap); `resolved_beliefs` now carries three. No
  `gap_recorded` handler exists yet, so this is an absence, not a decision.
- ~~**V0 §4's DDL is wrong about the `payloads` primary key.** Corrected in `schema.sql` per
  [ADR 0007](decisions/0007-payloads-keyed-by-event-id-not-payload-hash.md); the spec file
  itself still needs fixing.~~ **RESOLVED:** §4's DDL now matches `schema.sql`
  (`event_id` PRIMARY KEY, `payload_hash` NOT NULL + corroboration index), with an inline
  note pointing at ADR 0007.
