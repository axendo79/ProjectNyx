# ADR 0030: Sole Writer and Positional Event Assignment

Status: Accepted — maintainer acceptance 2026-09-23

Date: 2026-09-22

Implementation: Pending.

Supersedes: [ADR 0023 section 4](0023-stage-two-contract.md#4-retry-identity), only its undifferentiated submitted-contents retry rule, by defining semantic submissions separately from positional fields. Also supersedes [ADR 0010 section 1a](0010-projection-parameters.md#1a-append-enforces-recorded_at-monotonicity) and its backward-clock refusal acceptance case for ordinary writer timestamp assignment: the writer clamps within a 120-second skew threshold after checking the unadjusted clock, as specified in sections 4 and 5. Committed timestamps remain immutable and monotonically nondecreasing.

Related: [ADR 0014](0014-cross-belief-reducer-and-hash-lineage.md), [ADR 0019](0019-identity-bootstrap.md), [ADR 0020](0020-multi-user-authority-undecided.md), [ADR 0025](0025-incremental-result-commitment.md), [review and rulings](../design/2026-09-22-review-and-next-steps.md#rulings-2026-09-22).

## Context

Preparation currently binds the log predecessor and recording timestamp before
the append transaction. A competing append can invalidate an uncommitted pair;
retaining its earlier recording time can make every subsequent attempt refuse.
The ingestion module docstring tells callers to retain the complete Envelope /
Payload pair. ADR 0023 section 4 instead says retained recorded IDs and submitted
contents, without distinguishing the semantic submission from its log position.

The maintainer's R2 selects sole-writer ownership and the semantic/positional
split. The 2026-09-23 rulings select OS-level exclusion, a 120-second constant,
two clock samples with bounded clamping, synchronous structured refusal and
automatic recovery without a latch. The maintainer accepted these reviewed
rulings on 2026-09-23; implementation is a separate change.
Ownership of storage is not epistemic authority under
ADR 0020; it grants no ability to merge subjects, approve evidence or alter another
speaker's assertions.

## Decision

### 1. One owner, serialized submissions

One writer process owns all ordinary Layer A appends for a store. It holds an
OS-level lock on a lockfile beside the store, using msvcrt.locking on Windows
or fcntl on POSIX. A second writer open refuses before any store write.
Read-only opens neither acquire nor create the lockfile and are not blocked by
an active writer; exclusion governs writers only. The OS releases ownership
when the process dies; lockfile existence alone is neither
ownership nor a stale lock to bypass. Exclusion covers the owner's lifetime,
including restart and loss of the owner, without allowing two active owners.

Cross-process submission transport remains unbuilt and deferred; no current
consumer needs it. Other processes cannot independently prepare final append
positions or open the store for writing while the owner is active. This decision
requires exclusion, not a new queue, IPC service or submission transport.

The owner serializes requests and validates at the actual locked append prefix.
SQLite transaction exclusion remains a backstop. Existing derived-progress
requirements under ADR 0014 section 9 remain: unpublished accepted events must be
published before dependent new acceptance. Layer A append/freshness and derived
publication remain separate transactions, each atomic in its own scope. A
committed append survives a publication failure; recovery does not append it again.

Submission delivery is not a Layer A commit. A caller retains its semantic
submission until it learns the committed result and resubmits it after uncertain
delivery. This decision introduces no independently durable queue, no acknowledgment
before commit masquerading as success, and no exception to reconstructible
derived state.

### 2. Semantic and positional contents

The caller owns event_id, all payload IDs and associations, the complete payload,
occurred_at, source (including actor_id and the full source.config), source_class,
origin_type, event_type, schema_version and entity_refs. Source.config is semantic
source metadata, not a positional field. Semantic schema declarations remain
fixed; source metadata is not silently repaired.
Existing schema, taxonomy, identity, support and applicability validation remains
in force. Existing-subject association and unsupported stage-three events still
refuse.

The writer owns prev_event_hash and recorded_at. Ordinary callers no longer
supply recorded_at or a final predecessor hash. Under the append lock, after
retry lookup and validation, the writer reads the current tip, assigns the
positional fields under the clock contract below, and derives the envelope hash.
Payload commitments and the accepted idempotency formula remain unchanged.
Writer assignment is before first commitment, never mutation of a committed
envelope. Hashes are derived commitments, not another mutable caller identity.

No semantic ID is reminted to repair a lost race. A newly occupied
subject/property pair does not authorize redirecting a caller's conflicting
belief ID; ordinary acceptance still refuses under ADR 0022.

### 3. Retry identity and crash boundaries

For an uncommitted request, retry retains exactly the same semantic IDs and
contents. The writer re-derives both positional fields against the new append
position. The resulting event hash can differ from a previously prepared but
uncommitted attempt; no Layer A record is changed.

For a committed request, the writer verifies the semantic identity against the
stored record and returns the original committed Envelope / Payload pair,
including its original recorded_at, predecessor and hashes. It does not reassign
positions, resample a replacement recording time, remint an ID, or create another
candidate. A colliding event ID or idempotency key with different semantic
contents refuses. The comparison covers every caller-owned field from section 2:
event_id; the complete payload including every payload ID and association;
occurred_at; the complete source including actor_id and all source.config;
source_class; origin_type; event_type; schema_version; and entity_refs.

This complete comparison is required because the accepted idempotency formula
uses source actor_id, occurred_at and payload, not the complete source.config
or every other semantic field. An equal idempotency key is insufficient to prove
an equivalent retry. In particular, differing vocabulary or extractor metadata
under source.config, as required by [proposed ADR 0031](0031-source-report-claims.md),
must refuse as conflicting semantic reuse; it cannot silently return another
declaration's committed event. The formula itself remains unchanged.

A lost acknowledgment after commit therefore returns the committed pair on
retry. A failed observation after a committed mention uses the retained mention
and semantic observation request; the mention remains valid by itself. Existing
low-level exact-pair replay/integrity checks are not weakened to accept altered
committed pairs.

ADR 0023 section 4, as amended by this decision, defines “submitted contents” in
this writer contract as semantic contents for an uncommitted submission and
separately preserves the complete committed pair. At implementation, replace the
opening docstring in src/nyx/ingestion.py (“retain ... the complete Envelope /
Payload pair before submitting”) and submit's “exact retained pair” description with this
two-state contract. README's retained-pair preparation instructions must likewise
be reconciled. These are future documentation/code changes, not shipped behavior.

### 4. Write-time clock checks and bounded clamping

Use offset-bearing instants under the existing timestamp rules. A wall-clock
sample taken during preparation is insufficient: the owning writer samples its
clock at the locked write boundary and checks before any potential adjustment.

The permitted ahead-of-clock threshold is **120 seconds**, a named writer
constant, not runtime configuration. Changing it requires an ADR amendment.
Tests inject their own threshold through the clock/threshold seam; fixture
values do not supply a production default. Refusals show `threshold: 120 s`
for the production constant (and the injected duration with units in tests).

For each new ordinary append, under the append lock:

1. Take sample 1 of the writer clock. If
   `tip.recorded_at - sample_1 > 120 s`, halt before assignment or append.
   Exactly 120 seconds is within tolerance. Check the unadjusted sample; never
   clamp first and use the adjusted value to pass the skew check.
2. Assign `recorded_at = max(sample_1, tip.recorded_at)`, comparing instants.
   At genesis there is no predecessor, so assign sample 1. There is no increment.
   Equal timestamps remain legal and retain insertion/hash-chain ordering.
3. After assignment and before insertion, take sample 2, for validation only.
   Refuse if `recorded_at - sample_2 > 120 s`, including a clock step between
   samples. Sample 2 does not replace or advance the assigned timestamp. A
   failed candidate never becomes the next Layer A tip.

Recorded_at is never earlier than sample 1 or its predecessor's recorded_at.
During tolerated backward-clock skew it may be ahead of the writer's observed
wall clock by at most 120 seconds at these checks. This is no claim about true
recording time or civil time. Timestamp comparison follows the existing
offset-bearing instant rules; committed timestamps are never rewritten.
No Layer A refusal or alert event is introduced.

### 5. Halt, alert and recovery

A tip beyond the threshold blocks all new ordinary appends, including otherwise
valid submissions. The sole alert channel is a synchronous structured refusal
to the submitting caller: a typed error carrying a reason code, tip event_id,
tip recorded_at, the observed writer clock (sample 1 or sample 2, whichever check
failed), and the threshold with units. At genesis, if sample 2 fails, the tip
fields report the absence of a predecessor rather than inventing one. The CLI
and ingester must surface this refusal with a non-zero exit and all fields on
stderr when their write paths are implemented. This does not add a CLI writer
or implement the ingester. There is no durable alert store, diagnostic sink or
external monitoring channel. Do not report an uncommitted submission as
committed. Reads and retrieval of an already committed pair can still return
historical content; they must not append to clear the halt.

Delivery failure leaves the refusal in force and appends nothing. The halt
condition is re-derived from the log and clock on every attempt; if it persists,
a lost alert recurs on the next submission. Delivery is never an acknowledgment.

Recovery is automatic, with no latch. Each append attempt re-evaluates both
checks under the append lock. Appends resume when
`tip.recorded_at - sample_1 <= 120 s` and sample 2 validation passes. There is
no manual-release record, acknowledgment state or Nyx-side operator action.
The operator's lever is correcting the machine clock outside Nyx. Restart
re-reads the tip and rechecks; it confers no additional permission.

Recovery never rewrites or deletes Layer A, lowers the tip, fakes an earlier
timestamp or silently raises the threshold. A tip too far in the future to wait
out requires a separately authorized new-store procedure, which remains unbuilt,
unauthorized and out of scope. There is no in-place escape.

**Mechanism limit:** local skew checks cannot detect a machine whose wall clock
is already incorrect when the first bad timestamp is written. They can detect a
persisted tip ahead of a subsequently observed clock and stop further propagation.
They do not establish trustworthy UTC or correct an already committed timestamp.

### 6. Historical imports

A separate explicit historical-import path is unbuilt. It must not be simulated
by allowing recorded_at on the ordinary path or by temporarily disabling the skew
check. No API name, timestamp override, migration or backdating exception is
authorized. Its treatment of historical recording times, original commitments,
provenance and ordering requires a later contract consistent with append-only
history and explicit refusal of any incompatible monotonicity requirement.

## Ratification

Sections 1–5 incorporate the explicit maintainer rulings of 2026-09-23.
The maintainer accepted the reviewed contract on 2026-09-23. Acceptance does not
mark implementation complete. Under the commit protocol in AGENTS.md and
[ADR 0032](0032-explicit-stage-two-projector-selection.md#ratification), the agent
stages the authority change and stops for the maintainer's commit and confirmation.
The separate implementation change edits no decisions/ or spec/ files. After its
commit, the agent stages a separate one-line authority change marking this ADR's
Implementation complete and citing that commit, then stops for the maintainer's
commit. No commit hook may be bypassed.

## Accepted-ADR amendments

1. **ADR 0023 section 4:** the retry paragraphs now state the semantic /
   positional distinction in section 3 above: retain caller semantic IDs and
   contents; re-derive positions only when uncommitted; return and preserve the
   complete original committed pair otherwise. Preserve its no-reminting,
   no-matching, unchanged-idempotency-formula and committed-mention guarantees.
2. **ADR 0010 section 1a and its backward-clock acceptance case:** replace the
   ordinary writer's no-clamping refusal baseline with section 4's two-sample,
   120-second bounded assignment rule and section 5's automatic recovery and
   structured refusal. Preserve append-only committed timestamps, monotonicity,
   recording-time cutoffs and equal-timestamp ordering. Low-level integrity
   checks still refuse a pair whose recorded_at precedes the committed tip;
   they do not rewrite already prepared or committed envelopes.
3. No other accepted ADR needs amendment for the stated sole-writer and
   reportable-refusal contract. ADRs 0010 and 0023 carry partial-supersession
   navigation and distinguish their shipped implementation from this amendment's
   pending implementation. Both belong in the three-file authority change with
   this ADR; confirm them in `git status --short` and the acceptance diff.

## Acceptance cases

- A second writer open refuses before any store write while an owner holds the
  OS-level lock. Kill the owning writer in a subprocess, then verify that a new
  writer acquires the released lock and still runs the persisted-tip checks.
  Same-process close alone is insufficient. No cross-process submission transport
  is tested or built.
- While a writer holds the lock, a read-only open succeeds without acquiring or
  creating the lockfile. A read-only open against a store whose lockfile is
  absent also succeeds and leaves the lockfile absent.
- Retry before commit keeps semantic contents and re-derives positions. Retry
  after commit returns the byte-identical committed pair, even after later
  events append. Conflicting semantic reuse refuses, including an unchanged
  idempotency key with different source.config vocabulary/extractor metadata.
- Fail after mention commit, before observation commit, after append commit and
  during publication. Preserve accepted events and rebuildable atomic progress
  without duplicate candidates or acknowledgment-induced reminting.
- Ordinary callers supplying recorded_at refuse before mutation. No historical
  import escape hatch is inferred.
- With an injected clock and explicitly supplied test threshold, detect a tip
  beyond it before adjustment; refuse a new candidate beyond it, including a backward step
  between clock sampling and insertion. Refusal leaves Layer A unchanged.
- Within tolerance, assignment clamps to the later of sample 1 and predecessor
  time, without an increment. Exactly 120 seconds passes both threshold checks;
  120 seconds plus epsilon fails. Equal timestamps keep hash-chain ordering.
- Reopening cannot bypass an unsafe persisted tip. A structured refusal contains
  every required field and units; the CLI and ingester surface all fields on
  stderr with a non-zero exit when their write paths are implemented, as scoped
  in section 5. Failed delivery never appends. Recovery is automatic only when
  both checks pass, with no latch or manual-release record.
  Clock sample 2 validates without changing the assigned timestamp.
- A clock already wrong before the first append demonstrates the stated
  detection limit. A later corrected clock detects the ahead-of-clock tip.
- Replay uses committed contents and never samples a writer clock or reassigns
  positional fields. Existing projector semantics and hashes remain reproducible.
