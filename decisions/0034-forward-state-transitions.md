# ADR 0034: Forward State Transitions Under Projector "3"

Status: Proposed

Date: 2026-10-05

Implementation: None

Supersedes on acceptance: [ADR 0023 section 5](0023-stage-two-contract.md#5-corrections-are-deferred-under-version-1), only under explicitly selected projector "3"; projectors "1" and "2" keep every refusal. [ADR 0024 section 1](0024-no-authoritative-head.md#1-no-authoritative-head-under-version-1), only to the extent that an explicit recorded transition ends a named candidate's live status under projector "3"; recency still selects nothing. [ADR 0031 section 8](0031-source-report-claims.md#8-exact-ratified-first-slice-contract), only its single-extractor admission, and only for report-correction evidence under section 6 below [DRAFT — maintainer to confirm].

Related: [ADR 0001](0001-observation-recorded-resolves-to-verified.md), [ADR 0003](0003-genesis-sentinels-and-hash-material-delimiters.md), [ADR 0005](0005-backdated-corrections-fail-loud-pending-semantics.md), [ADR 0006](0006-occurred-at-comparison-is-instant-based-not-lexical.md), [ADR 0010](0010-projection-parameters.md), [ADR 0011](0011-database-schema-versioning.md), [ADR 0014](0014-cross-belief-reducer-and-hash-lineage.md), [ADR 0015](0015-candidate-scoped-verification.md), [ADR 0018](0018-correction-supersedes-candidates.md), [ADR 0020](0020-multi-user-authority-undecided.md), [ADR 0022](0022-belief-container-uniqueness.md), [ADR 0025](0025-incremental-result-commitment.md), [ADR 0030](0030-sole-writer-and-positional-fields.md), [ADR 0032](0032-explicit-stage-two-projector-selection.md), proposed [ADR 0027](0027-stage-three-authority-and-acceptance.md), proposed [ADR 0028](0028-redaction-and-crypto-shredding.md), [supersession worksheet](../design/2026-10-04-supersession-worksheet.md), [valid-time worksheet](../design/2026-10-05-valid-time-worksheet.md).

## Context

Stage two accumulates disagreement by design. ADR 0024's consequences record that
a value reported yesterday and a different value today both remain candidates
indefinitely, because no accepted mechanism distinguishes an erroneous record, a
change, or a lapse. ADR 0018 decides correction semantics but ADR 0023 section 5
defers them under projector "1", and ADR 0025 keeps that refusal under "2".

The supersession worksheet (S1–S10) and the valid-time worksheet (V1–V10) separated
three questions that "newer" alone cannot answer: was the earlier record wrong;
did the state it described stop being Nyx's live state; and what applied in the
modelled world at an external time T. This ADR addresses the first two only.

The maintainer's 2026-10-05 rulings below are recorded as a **proposed contract**,
not acceptance. Mechanics not settled by those rulings are marked
[DRAFT — maintainer to confirm]. Status remains Proposed and implementation remains
None. Neither the rulings nor the draft choices authorize code.

## Maintainer rulings recorded 2026-10-05

- **R1. Projector.** Register explicitly selected projector "3". Projectors "0",
  "1" and "2" stay frozen: bytes, refusals, goldens and semantics. No fallback,
  default or automatic upgrade. Proposed ADRs 0027 and 0028 currently describe a
  stage-three projector "3"; they are renumbered when next revised. This ADR does
  not edit them.
- **R2. Three typed operations.** Projector "3" supports exactly three explicit
  forward state transitions on ClaimCandidates: **correction** (the recorded claim
  was wrong), **forward replacement** (the earlier claim was Nyx's live state until
  a later Layer-A position, and a fresh candidate is live from that position), and
  **expiry** (the earlier claim stops being live with no successor).
- **R3. Firewall.** Projector "3" establishes live, superseded, replaced and
  expired status by Layer-A order only. It establishes nothing about world-validity
  intervals, valid-from or valid-to dates, recency, or what applied at an external
  time T. Those questions belong to a separate valid-time contract.
- **R4. Naming.** Reads and APIs say "live" (or "unsuperseded" where only correction
  is meant). They never call a candidate "current"; belief lifecycle "current"
  under ADR 0022 is unrelated and unchanged.
- **R5. Targets and scope.** Every operation names a nonempty set of existing
  target candidate IDs, all within one exact claim scope (section 5). Correction
  and replacement record exactly one fresh replacement candidate. Eligibility is
  all-or-nothing: one invalid target refuses the whole event before append.
- **R6. Chains.** Only live candidates may be targeted. A request naming a target
  that is no longer live refuses clearly; it is never retargeted. Chains of
  separate events are allowed.
- **R7. Timestamps.** Corrections keep an event-time constraint: occurred_at must
  be at or after each target's recording-event occurred_at, compared as instants
  (ADR 0006); equal is allowed. Replacement and expiry give occurred_at no ordering
  authority; their effect is ordered solely by Layer-A position.
- **R8. Submission authority.** Under projector "3", any submission through the ADR
  0030 sole writer in the operator's deployment may submit an otherwise eligible
  transition. actor_id is recorded, not checked, and establishes no authority beyond
  this projector. This bounded single-operator rule resolves neither ADR 0020 nor
  proposed ADR 0027. Submission authority is not truth: each operation still
  satisfies its scope and evidence contract.
- **R9. Standing.** Replacement candidates earn their own standing from their own
  evidence. Nothing transfers from targets (ADR 0018). Target histories, support and
  verification records are retained. Any operation that would require an undecided
  dependent demotion or restoration under ADR 0015 section 5 refuses after an actual
  dependency check, not an assumption that none exist.
- **R10. Reads.** Return the complete live candidate set with provenance, standing
  and transition relations. No scalar winner. Retained non-live candidates stay
  readable by name together with the relation that ended their live status.
- **R11. Retries.** Keep the accepted idempotency formula and collision refusal
  (ADRs 0003 and 0030). Recognize an exact committed retry before testing target
  eligibility, so a committed transition's retry is not refused because its own
  targets are no longer live.
- **R12. Durability.** The recorded event is the sole authoritative record of each
  transition. Any relation index is derived, published atomically with progress,
  covered by lineage, and verified independently. The index is never the only copy.
- **R13. Evidence.** Two evidence classes for correction (section 6): report
  mis-extraction under a four-part rule, and same-scope correction with a recorded
  basis for ordinary claims. Evidence is recorded in the event. Replay never reruns
  extraction or consults external sources.
- **R14. Store transition.** Projector-"3" events are written first only to a
  working copy of an existing store. The original store and its backup bundle stay
  the projector-"2" reference until acceptance testing passes (section 10).

## Proposed contract

### 1. Version and dispatch

Projector "3" is registered alongside "0", "1" and "2" under ADR 0032's explicit
selection rules: every new selector parameter is named `projector_version` with no
default, and the AST guard covers new call sites. Projector "3" accepts every event
type and payload that projector "2" accepts, with identical results for them, plus
the three operations below. Version-"3" derived rows are isolated by
`projector_version`, as ADR 0025 isolates "2".

[DRAFT — maintainer to confirm] Version-"3" lineage uses the tag
`nyx-belief-lineage/3` and otherwise follows ADR 0025's committed representation,
extended to cover the fields in section 8.

### 2. Operations and recorded event types

Each operation is a semantically distinct recorded event type, never one generic
event whose meaning depends on an optional field. A reader distinguishes "the
record was wrong" from "the record was right and later changed" by event type alone.

| Operation | Event type | Fresh candidate | Effect on targets |
|---|---|---|---|
| Correction | existing `correction_appended` | exactly one | no longer live; relation `corrected_by` |
| Forward replacement | [DRAFT] new `candidate_replaced` | exactly one | no longer live from this position; relation `replaced_by` |
| Expiry | [DRAFT] new `candidate_expired` | none | no longer live from this position; relation `expired_at` |

ADR 0018 governs correction only. Replacement and expiry are new semantics decided
here; they do not reinterpret ADR 0018. Expiry records no fresh candidate, which is
consistent with ADR 0018 because expiry is not a correction. An empty value never
stands in for expiry.

### 3. Payloads

[DRAFT — maintainer to confirm] Correction and replacement payloads carry exactly
`{"claim": <one stage-two claim object>, "targets": [<candidate IDs>], "basis": <object>}`.
The claim object has exactly the stage-two claim fields (`mention_id`, `subject_id`,
`property_id`, `belief_id`, `claim_candidate_id`, `value`, `verifiability`) and is
validated exactly as an ordinary observation claim, including freshness of its
candidate ID. Expiry payloads carry exactly `{"belief_id": <ID>, "targets": [<candidate IDs>], "basis": <object>}`.

`targets` is a nonempty array of distinct nonempty strings, stored in canonical
sorted order; duplicates refuse. A fresh candidate ID never appears in its own
targets, so every relation points from a newer event to strictly earlier candidates
and no cycle can form. `basis` is defined in section 6 for corrections. For
replacement and expiry it is `{"kind": "stated", "statement": <nonempty string>}`
recording the submitted reason as data, with no effect on eligibility
[DRAFT — maintainer to confirm].

### 4. Eligibility, checked at the locked pre-event snapshot

After committed-retry recognition (section 9) and under the writer lock, for every
target:

- it exists as a ClaimCandidate in the selected projector-"3" snapshot;
- it is live (no prior correction, replacement or expiry relation);
- it belongs to the payload's belief, which is a current belief under ADR 0022;
- it satisfies the operation's exact-scope rule (section 5);
- for correction only, the R7 timestamp rule holds.

Any failure refuses the entire event before append with no change to event count,
tip, payloads or derived rows. Replay applies the same checks and refuses an invalid
recorded event, so a log can never fold differently from its append-time validation.

[DRAFT — maintainer to confirm] A correction whose occurred_at precedes a target's
raises `BackdatedCorrectionError`, retaining ADR 0005's named error and its
interim stance for corrections. ADR 0005 is therefore not superseded. Replacement
and expiry never raise it.

### 5. Exact claim scope

- **Ordinary claims.** Targets and any fresh candidate share one belief (one
  subject/property pair under ADR 0022). Distinct beliefs, subjects or properties
  refuse. Value equality, source lineage or similar text never establishes scope.
- **Report claims.** A correction targeting report-scoped candidates (ADR 0031)
  additionally requires every target and the fresh candidate to share repository,
  exact path, revision, blob, property and recorded source location. Two reports of
  different revisions are never in one correction scope; a later revision stating
  something else is another report.
- [DRAFT — maintainer to confirm] **Replacement and expiry refuse report-scoped
  targets.** A report about an immutable revision is not a state that lapses or is
  replaced; only correction applies to it.

### 6. Correction evidence

**Report mis-extraction.** All four must hold and be recorded in the correction
event's `source.config` and `basis`:

1. the same pinned repository, revision and blob as the target;
2. the same exact source location as the target;
3. an extractor identifier on the explicit admission list for correction evidence;
4. the fresh literal differs from the target's recorded literal.

A newer extractor version is not intrinsically more truthful; admission is the
trust decision. [DRAFT — maintainer to confirm] The admission list for correction
evidence starts empty. Admitting an extractor version (for example
`nyx.adr-literal/2`) is a separate maintainer ruling recording its identifier and
the defect it corrects. Until then report corrections refuse, because rerunning
`nyx.adr-literal/1` over the same bytes reproduces the target. Vocabulary meaning,
scope or value-shape changes remain vocabulary versions under ADR 0031 section 4.

**Ordinary claims.** The correction targets candidates in one belief (section 5)
and records `basis` as `{"kind": "stated_error", "statement": <nonempty string>}`.
The fresh candidate's standing comes from its own event under ADR 0001, never from
the basis text or the targets.

Replay validates only what Layer A records: identifiers, equality and difference of
recorded literals and locations, and admission-list membership as recorded in the
event and the accepted admission list. It never fetches blobs or reruns an
extractor. Reproducibility of a report correction is checked at admission and by an
independent verification script.

### 7. Reads

[DRAFT — maintainer to confirm] For a belief at an explicit cutoff and projector
"3":

- `live`: candidates with no transition relation at or before the cutoff;
- `retained`: every other candidate, each with its ending relation, the relation
  event ID and its log position;
- per-candidate provenance, standing and verification as under projector "2".

A cutoff before a transition returns the earlier live set unchanged; later events
never rewrite earlier answers (ADR 0010). Scalar belief requests keep ADR 0024
section 2's refusal whenever the belief holds more than one candidate, live or not.
This ADR adds no scalar or common-value read.

### 8. Derived relations, lineage and schema

The transition relation is a pure function of recorded events. [DRAFT — maintainer
to confirm] Projector "3" populates each target's existing `superseding_events`
candidate field with the transition event ID and adds a candidate field
`live_status` with values `live`, `corrected`, `replaced` or `expired`, both covered
by version-"3" lineage. A derived relation table, keyed by projector version, target
candidate and transition event, supports indexed reads. It is published in the same
transaction as progress and verified by full replay and by the standalone verifier.
A missing or corrupted relation row is a verification failure, never a silent
fallback to the candidate field or the reverse.

[DRAFT — maintainer to confirm] The relation table requires database schema version
5 under ADR 0011. Opening a version-4 store for projector "3" requires the explicit
migration of section 10; no automatic migration occurs.

### 9. Retries and idempotency

The existing formula and committed-retry comparison apply unchanged (ADRs 0003,
0023 section 4 as amended by 0030). An exact committed retry returns the original
envelope/payload pair before any eligibility check. Because event_type is outside
the idempotency key, two submissions of different operation types with equal actor,
occurred_at and payload collide and refuse as conflicting semantic contents. No
discriminator is added to evade that.

### 10. Event types, frozen readers and store transition

[DRAFT — maintainer to confirm] The two new event types join the shared Layer-A
event-type allowlist, so integrity validation accepts them in any store. Frozen
reducers "1" and "2" refuse them at reduction, as they refuse `correction_appended`.
Consequence: an `as_of` read under "2" whose cutoff precedes the first transition
event keeps working, and a read or replay reaching it refuses. Projector "0" keeps
its existing handling and refusals. The frozen-reader characterization tests
(Sol queue 11) supply the pre-change behavior that this compatibility statement
alters; it must be ratified knowingly.

Store transition, for any existing store:

1. hash and back up the original; it stays the projector-"2" reference;
2. copy it to a working store and migrate the copy to schema version 5;
3. prove projector-"3" full replay of the copied prefix equals projector-"2"
   results for every pre-existing event, and that existing IDs are not reminted;
4. only then append transition events to the working copy;
5. after acceptance (section 11) passes on the working copy, the maintainer names
   which store is authoritative. Two writable stores never continue in parallel.

## Acceptance cases

Start from ADR 0018's fixture: belief b-N holds c-A (64, verified), c-B (64,
questioned) and c-C (128).

- **Correction, one target:** a correction asserting 32 targets c-A. c-A is retained
  with `corrected`; c-B and c-C stay live; the fresh candidate is live with its own
  standing.
- **Correction, all targets:** targeting c-A, c-B and c-C leaves only the fresh
  candidate live; all three retain evidence and verification histories.
- **No targets / duplicate / foreign belief / one invalid of several:** each refuses
  before append; event count and tip unchanged; replay of a forged recorded event
  refuses.
- **Timestamp rule:** correction occurred_at equal to a target's is accepted;
  earlier refuses with `BackdatedCorrectionError`; timezone-equivalent spellings
  compare equal; a replacement with an earlier occurred_at is accepted.
- **Replacement:** "4100" then a replacement to "4200" targeting it: live set is
  {4200}; 4100 is retained with `replaced` and readable by name; a cutoff before the
  replacement returns {4100}.
- **Expiry:** expiring the only live candidate leaves an empty live set with the
  retained candidate and its `expired` relation; the scalar request still refuses.
- **Stale target:** after c-A is replaced, a correction or second replacement naming
  c-A refuses; nothing is retargeted.
- **Retry after later transitions:** replacement U1, then expiry of U1's fresh
  candidate; an identical retry of U1 returns U1's committed pair unchanged.
- **Cross-type collision:** a replacement and an expiry with equal actor,
  occurred_at and payload refuse as conflicting.
- **Report scope:** reports of revisions R1 and R2 cannot share a correction; a
  replacement or expiry naming a report candidate refuses; a report correction
  refuses while the admission list is empty, and succeeds under a test-only admitted
  extractor with all four evidence conditions, refusing when any one fails.
- **Dependency refusal:** a target with a recorded dependency requiring undecided
  demotion refuses; the check runs even when the answer is "none".
- **Durability:** a deleted or altered relation row or `live_status` field fails
  verification; crash after append and during publication recovers to equal
  results; incremental, materialized and replay results are equal at every prefix.
- **Frozen versions:** projector "0", "1" and "2" goldens and refusals are
  unchanged; an `as_of` read under "2" before the first transition works; one
  reaching it refuses.
- **Store transition:** working-copy prefix equality, unchanged identities, backup
  and restore of the working copy reproduce relations and live sets.

## Consequences

Nyx gains its first mechanism that changes which candidates are live without
choosing by recency. Disagreement that is not explicitly transitioned still
accumulates, as ADR 0024 intends. Questions about external validity time remain
open and are not answered by Layer-A order. The valid-time worksheet remains the
place for them.

Report corrections are specified but unavailable until an extractor is admitted.
Proposed ADRs 0027 and 0028 must be revised to a different projector number before
they can be ratified. ADR 0018's Implementation line changes only when this ADR's
implementation commit lands, through the usual A/B marker.

## Alternatives considered

- **Correction-only projector "3".** Architecturally valid, but it leaves lapse and
  replacement, the transitions that actually occur in ordinary state, without any
  mechanism. Rejected by the maintainer on 2026-10-05.
- **One generic supersession event with a kind field.** Rejected: intent would depend
  on an optional field and could be misread by any reader that ignores it.
- **Ordering replacement by occurred_at.** Rejected: it would reintroduce valid-time
  meaning through a timestamp whose meaning differs by event class.
- **Implicit closure of an earlier candidate by a later one.** Rejected: recency
  selection, excluded by ADR 0024.
