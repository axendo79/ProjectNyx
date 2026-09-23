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

Proposed stage-three draft: [ADR 0027](decisions/0027-stage-three-authority-and-acceptance.md).

---

## Correctness gaps

### Redaction breaks the write path and replay
`src/nyx/storage.py` · Invariant 14 · unbuilt, **will fail loudly if reached**

Redaction and crypto-shredding are not implemented. Stored redacted rows explicitly
raise `NotImplementedError` through `integrity.decode_payload`; missing rows or
unmarked NULL content raise `IntegrityError`. Replay still cannot reconstruct a
redacted history. The specified typed REDACTED sentinel does not exist yet.
Integrity validation closes silent payload loss, not the redaction semantics gap.

Proposed redaction draft: [ADR 0028](decisions/0028-redaction-and-crypto-shredding.md).

### Read/replay integrity and append parity — resolved
**RESOLVED:** `src/nyx/integrity.py`, `storage.py`, `projection.py`, `reducer.py`,
`committed.py`, and `skeleton.py`; regression coverage in `tests/test_event_integrity.py`.
All versions verify payload content against the envelope's payload hash, stored
envelope hashes, predecessor associations, and existing envelope schema/taxonomy.
Full log reads and rebuilds refuse missing payload rows instead of dropping events
through an inner join. Pending publication checks the applied anchor and each
event it reads, without scanning the entire already-published prefix.

Legacy append now rejects invalid hashes/links and conflicting reused IDs or keys.
Only identical retained event/payload pairs are retries; the raw legacy writer
retrieves its original pair. No hash formula or accepted event semantics changed.

### Typed identity freshness and `is_stale` — resolved for stage two
**RESOLVED:** `storage.read_identity_status` and its typed wrappers disclose
record presence, applied progress, and append freshness for versions "1"/"2".
Existing typed record readers warn on stale results, including unpublished `None`.
Unknown-subject absence conservatively uses the log tip. `projection.is_stale`
uses positions under ADR 0014. Legacy raw belief reads retain their original shape;
these fixes do not add a general retrieval subsystem.

### Version-2 snapshot read parity — resolved
**RESOLVED:** `committed.Snapshot.events()` returns the canonical event list and
`current_belief()` returns the complete belief, matching version "1". Internal
`current_header()` preserves indexed incremental writes. Both public contracts and
detachment are tested in `tests/test_event_integrity.py`; existing incremental-write
guards remain in `tests/test_incremental_commitment.py`.

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

### Stage-two projector defaults — E2, resolved by ADR 0032
**Resolved:** [ADR 0032](decisions/0032-explicit-stage-two-projector-selection.md)
requires explicit stage-two projector selection and narrowly amends ADR 0025
section 1. Omission refuses before work; existing callers explicitly retain
their previous selection. An AST guard covers all Python under src/ and scripts/,
including private helpers, constant defaults, generated dataclass parameters
and future functions. Enumerated aliases are checked for existence and their
required/default-"0" contracts; parser options are matched exactly. Unrelated
parameter names are outside the guard; review checks for hidden selectors.
The explicit legacy default-"0" allowlist remains unchanged. This closes accidental selection,
not projector "1"'s measured whole-store ingestion cost.

### Writer concurrency and positional retries — E3/O1, pending ADR 0030
**Open / decision-blocked:** preparation binds `prev_event_hash` and
`recorded_at` before append. A competing append can invalidate an uncommitted
retained pair; a retained earlier timestamp then refuses under ADR 0010.
The [review, E3/O1 and R2](design/2026-09-22-review-and-next-steps.md) calls for
one writer and a semantic/positional submission split. Proposed ADR 0030 must
clarify ADR 0023 section 4, committed versus uncommitted retries, skew checks,
halt/alert/recovery and a separate unbuilt historical-import path. No writer
ownership mechanism or clock-skew recovery ships. ADR 0010's no-clamping refusal
remains the baseline; equal recording timestamps are allowed.

### External source-report scope — O2, pending ADR 0031
**Open / decision-blocked:** every supported observed-origin ClaimCandidate is
verified under ADR 0001. The writer does not enforce that external-content
claims describe what an artifact stated instead of asserting its contents as
world truth. `source_class` alone provides no such boundary.
The [review, O2 and R3](design/2026-09-22-review-and-next-steps.md) selects
report-scoped claims as the immediate direction and a separate origin mapping
as the target. Proposed ADR 0031 must define ingestion-only vocabulary
enforcement and immutable per-event vocabulary identity/version/hash. Property
IDs remain exact opaque strings under ADR 0023; no registry or replay-time
vocabulary check is introduced. None of this enforcement ships in Step 0.

### Listing and search surface — O3, unbuilt
**Open:** typed ID lookups and explicit replay are available, but no public
subject/mention/property/belief listing or search API ships. The
[review, O3 and section 4.3](design/2026-09-22-review-and-next-steps.md) describes
a future derived index. R5 permits mention text for public corpora only as an
inventoried copy rebuildable from Layer A; it does not implement the index or
decide its schema, query API or publication mechanics.

### Whole-store growth — O4, measurement available; retention deferred
**Measured concern / deferred retention:** the
[review, O4](design/2026-09-22-review-and-next-steps.md) supplies reviewer evidence
of 21,381 retained nodes, about 6.8 MB node content and a 12 MB database at
600 events. Those are supplied measurements, not a universal bytes-per-event
bound. The [whole-store probe](scripts/probe_store_scaling.py) measures ingestion,
verification, retained-node content and checkpointed database bytes separately
with one mention and five observations per subject. Its normal scales are
300/600/1200/2400 events; projector "1" can be capped or skipped. Full runs are
manual; only tiny smoke coverage is in pytest. ADR 0025 still retains historical
nodes. No garbage collection, growth threshold or retention policy is selected.
The [Step 0 measurements](design/2026-09-22-store-scaling.json), made on
Python 3.14.2 / Windows 11, retain 17,538 nodes at 600 events and 86,559 at 2,400;
the latter store is 48,660,480 bytes (20,275.20 bytes/event). These fixed fixture
IDs differ from the review's, so node counts are not asserted to match it.
The verifier's repeated publication-prefix copy is fixed and deterministically
tested, but total version-2 verification still scales superlinearly in this run
(14.84/48.10 seconds at 1,200/2,400 events). Other verifier work remains unchanged;
the copy-count regression is not a claim of linear end-to-end verification.

### Corpus restriction — R4, policy in force; erasure unbuilt
**Public-corpus policy:** public corpus only until the erasure requirements
(Gate 3 of proposed ADR 0027 together with proposed ADR 0028 9 and 11) are
accepted, implemented and passed. This is the maintainer's
[2026-09-22 ruling](design/2026-09-22-review-and-next-steps.md#rulings-2026-09-22),
not a claim that those Proposed ADRs are ratified or their gates passed.
ADR 0002's plaintext storage remains in force. The restriction does not provide
encryption, deletion, private-data migration or a source-classification checker.

### Rename identity — scoped subjects retained
**Boundary recorded; ingester unbuilt:** under ADR 0019's scoped bootstrap and
ADR 0023's stage limits, a renamed file remains a separate subject. Git's
rename/similarity result is only a report-scoped claim; it supplies no accepted
identity association or merge authority. ADR numbers are metadata/searchable
text, never identity. The [review's rename ruling](design/2026-09-22-review-and-next-steps.md#rulings-2026-09-22)
requires the `902467a` R092 rename from `0009-projection-parameters.md` to
`0010-projection-parameters.md` as a future regression fixture in proposed ADR
0031. No rename handler or file-history ingester is implemented here.

### Standalone replay verifier — implemented for shipped contracts

[scripts/verify_store.py](scripts/verify_store.py), covered by
[tests/test_verify_store.py](tests/test_verify_store.py), independently checks
envelope/payload commitments, genesis and predecessor links, recording-time
monotonicity and materialized event coverage. It reconstructs legacy and
stage-two contents from the log without normal read/projector validation.
For projector "2", it rebuilds roots from leaves and checks retained headers
against independently reconstructed lineage under
[ADR 0025](decisions/0025-incremental-result-commitment.md).
Full-log accounting reports events beyond validated stored publication progress
as pending without failing verification. Missing applied events and projected
references absent from the log fail coverage; unknown progress is not inferred
from timestamps or hashes. Evaluation-only time and unavailable
version-specific checks remain explicitly unchecked. This does not implement
redaction, merge/split or other deferred semantics. Architecture section 13's
unbuilt-verifier wording predates this implementation; the protected spec has
not been edited in this pass.

### Duplicate-key payload text is accepted outside canonical writer preparation
**Open hardening / decision-blocked:** `src/nyx/integrity.py`, `storage.py`;
original-text authentication and cross-decoder interpretation are not established
by the current canonical-content commitment. No accepted-contract violation is
demonstrated by this finding, so it is not classified as a correctness fix.

The [B2 findings](design/0027-b2-private-value-codec-ruling-brief.md#2-complete-call-site-inventory-and-external-payload-reachability)
record successful synthetic duplicate-key payload appends under projectors
"0", "1" and "2", with the submitted text retained unchanged and last-wins
decoded content returned on read. All **31 `json.loads` call sites** across
`src/nyx/` and `scripts/verify_store.py` omit `object_pairs_hook` (and the three
numeric parsing hooks); duplicate object keys therefore collapse last-wins under
the shared default decoder. The verifier's log checks accepted the same samples.

**Hash distinction:** `{"value":1,"value":2}` and `{"value":2}` have different
raw UTF-8 SHA-256 digests, respectively
`ef07538311c29ebdde0960d157b1222ff7f39622c0367ff23305a592d997dbda` and
`49c987621f206f09e5fbe23b516b55a36f838cb14867961f1d84a554d3a35b6b`.
Both decode to the same object and produce the **same Nyx canonical payload
hash**, the second digest above. They do not produce different accepted
`payload_hash` values. `events.py:114–115` hashes canonical object content;
`integrity.py:90,93,101,105–106` checks the supplied commitments against that
decoded/canonical content. Submitting a raw-text digest that differs from the
recomputed canonical digest would fail that check. This is parser information
loss, not a hash collision.

**Contract assessment:** [architecture Invariant 14](spec/NYX_ARCHITECTURE.md)
states:

> The constitutional guarantee is that nothing is *silently* rewritten. Envelopes retain event identity, order and payload/hash-chain commitments; payload content is stored separately.

The envelope-only `event_hash` scope does not mean payload content is unbound:
the envelope includes `payload_hash`. It does mean that the outer hash does not
independently authenticate the original payload text. [ADR 0002, Decision and
Rationale](decisions/0002-payload-stored-plaintext-in-v0.md#decision) governs
`build_event`'s canonical plaintext output and describes the envelope-only chain;
it does not define strict decoding of independently supplied payload text.
[ADR 0007, Context](decisions/0007-payloads-keyed-by-event-id-not-payload-hash.md#context)
records the canonical-content formula:

> `payload_hash = SHA256(canonical_json({belief_id, value, verifiability}))`

[ADR 0014 §5](decisions/0014-cross-belief-reducer-and-hash-lineage.md#5-lineage-covers-ancestry-and-result)
requires:

> Referenced observation and
> identity-event dependencies are identified by event ID and event hash so their
> recorded contents are covered as well as their names.

Its [§6](decisions/0014-cross-belief-reducer-and-hash-lineage.md#6-canonical-serialization)
also states:

> Lineage uses the shared canonical JSON discipline in src/nyx/hashing.py: sorted
> object keys, compact separators, preserved Unicode strings, and UTF-8 bytes for
> hashing.

ADR 0014 does not separately redefine `payload_hash` as a hash of raw input text
or specify duplicate-key rejection. [ADR 0025 §§1/3](decisions/0025-incremental-result-commitment.md#decision)
preserves Layer A hashes and complete logical dependency contents. The probes
retain the original Layer A text and replay the same decoded object; they do not
show an append-only rewrite or divergent replay under the shipped interpreter.
The stressed boundary is what "recorded contents" authenticates across parsers:
strict original-text identity is outside the demonstrated canonical-content
guarantee. This is an open hardening/interpretation boundary, not evidence that
the existing envelope or lineage hash formula was implemented incorrectly.

**Reachability:** the Python append API accepts caller-supplied
`Payload.ciphertext` text; it does not require provenance from Nyx's encoder.
`storage.py:289,310,397,413–415` and `ingestion.py:56–64` expose this path.
The demonstrated caller changed text before its first ordinary append, without
direct SQL writes or changes to validation code. An external producer can thus
supply such text through an application using these APIs; this is not restricted
to a hostile writer editing the database. No remote/untrusted import endpoint
was demonstrated, and the shipped CLI is read-only. Exact retained-pair retries
and canonical stored Merkle-node checks remain separate rejection boundaries.

**Classification rationale:** the register separates implemented correctness
failures from open semantics and explicitly versioned contract changes. The
evidence establishes permissive input and a commitment-scope limitation; changing
that acceptance boundary requires a ruling. The ruling questions remain in the
[B2 brief, questions 4/8](design/0027-b2-private-value-codec-ruling-brief.md#additive-ruling-questions-and-overlap-with-questions-17).
This entry supplies no fix or default.

### Cross-language canonicalization and verifier independence remain unproven
**Open / decision-blocked:** the proposed private-codec and conformance contract
is incomplete; the existing Python hashing implementation remains in force.

`src/nyx/hashing.py:30` uses Python float formatting and omits `allow_nan=False`.
The [B2 cross-language findings](design/0027-b2-private-value-codec-ruling-brief.md#3-float-bytes-hashes-and-the-limit-of-verifier-independence)
record different Python/Node bytes and SHA-256 digests for `1e-6`
(`1e-06` / `0.000001`), `1.2345678901234567e20` and negative zero (`-0.0` / `0`).
Bare `NaN`/`Infinity` output is outside RFC 8259's JSON number grammar; Node's
strict JSON decoder rejects it. [RFC 8259 §6](https://www.rfc-editor.org/rfc/rfc8259).
This demonstrates a failure of cross-language **default** interchange, not that
another language is incapable of reproducing Python-compatible bytes. Current
evidence verifies the recorded Python runtime; cross-Python-version stability is
also unverified.

[ADR 0014 §§5–6](decisions/0014-cross-belief-reducer-and-hash-lineage.md#5-lineage-covers-ancestry-and-result)
and [ADR 0025 §§2–6](decisions/0025-incremental-result-commitment.md#2-canonical-authenticated-map)
bind complete logical content through the shared canonical serializer. Formatting
differences can propagate through payload commitments, Merkle roots and lineage.
No independent cross-language value/number and parser contract is supplied by
those accepted decisions. This is a portability/assurance gap, not a demonstrated
failure to reproduce the accepted frozen fixtures on the recorded runtime.

`scripts/verify_store.py:2–7` discloses shared hashing/Merkle primitives; its digest
at line 45 calls the same serializer and its payload parser at line 112 uses the
same default decoder. Its independent record reconstruction therefore does not
independently validate canonicalization or detect a shared parser interpretation.
Its recomputation claim remains valid within that stated scope; a passing result
is not cross-language conformance or independent cryptographic review.
Proposed [ADR 0027 Gate 2](decisions/0027-stage-three-authority-and-acceptance.md#gate-2-independent-protocol-review)
requires independent protocol findings, and
[Gate 3](decisions/0027-stage-three-authority-and-acceptance.md#gate-3-implementation-and-operational-assurance)
requires implementation evidence including frozen-vector conformance and parser
strictness. The present verifier alone establishes neither gate.

**Observed corpus:** the two existing seed stores contain 9 and 11 committed
events and no floats in the inspected stored JSON or SQL cells; the retained
`tests/fixtures/version0_ordinary.json` is also float-free. Python test fixtures
do contain floats: `test_reducer_boundary.py:297–305` canonicalizes snapshot value
`1.25`, and lines 196–210 prepare float-bearing invalid submissions. This supports
absence in the inspected persisted corpus, not a universal "no float ever
committed" claim. Float exclusion would not change those seed values, but is not
a no-op across the existing encoder/replay domain and helper fixtures.

**Classification rationale:** closing the cross-language private codec and its
evidence requires unresolved B2 rulings under the Proposed contract, rather than
an already specified correctness fix. Questions 1–3/6–7/9–11 and the measurement
limits remain in the [B2 brief](design/0027-b2-private-value-codec-ruling-brief.md).
No codec, parser, hash or compatibility default is chosen here.

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

**Boundary refusal resolved:** Immune Stage 1 rejects offset-less `occurred_at`
before the legacy writer opens storage. `events.build_event` validates supplied
event timestamps before hashing or ID allocation, covering stage-two preparation.
The ingestion preparers validate before writer lookups; `ingestion.submit` checks
retained pairs before publication or append. The stage-two skeleton wrapper
validates retained pairs before opening storage. Append and
replay retain their integrity backstops in all versions. Regression coverage is in
`tests/test_timestamp_ingestion.py`.

Valid timestamp strings, including `Z`, `+00:00`, non-UTC offsets and fractional
precision, remain byte-identical. This closes ingestion-time refusal, not stored
string normalization to one UTC spelling. That representation change remains
outside the frozen-projector fix; compare-time normalization under ADR 0006 is
still required. The full Immune pipeline is not added to stage two.

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

### Dream emission semantics and operational contracts
**Proposed / decision-blocked; no implementation:**
[ADR 0029](decisions/0029-dream-emission-semantics.md) records a distinct emission
type, inseparable recall origin, exclusion from the reducer's Layer A event-domain
inputs, no promotion path, and process provenance that may prevent overcounting
but never create support. It consistently extends ADR 0026 without amending it.
These are proposed boundaries, not shipped Dream enforcement or a storage contract.

The complete open list is in
[ADR 0029's unresolved questions](decisions/0029-dream-emission-semantics.md#remaining-unresolved-questions):

- **Recording/durability:** concrete location outside Layer A, append-only versus
  mutable policy, durable authority, ordering, identity/retries, retention and
  recovery, including explicit resolution of Invariant 8.
- **Process-history replay/verification:** operation scope and checks establishing
  origin, identity, completeness and causal links. Emissions are excluded from
  belief replay; model regeneration is not an established history verifier.
- **Acquisition linkage/counting restrictions:** whether an observation records
  its initiating emission, where and with what authority/verification, and how
  restrictions remain deterministic within the Layer A input boundary. ADR 0021's
  constitutive mention/subject link supplies no default for this relationship.
- **Redaction/recall representation:** emission units, private dependencies, safe
  retained origin/causal records and unavailable recall; preserve counting
  restrictions without retaining protected content. Proposed ADR 0028's managed
  closure applies conditionally, with its own unresolved protocol/evidence gates.
- **Retrieval/activation provenance and feedback:** preserve the adopted generated,
  exposed (top-k), referenced (explicit citation) vocabulary; decide update timing
  and dedup, scope, credit assignment, cross-component feedback, candidate-generation
  bias and access for underexposed evidence, plus recording and replay. Denying the
  scorer a causal-provenance handle constrains this work without resolving it.
- **Dream instrumentation:** define Generative Flux over attempted cycles with
  `R_opportunity`/`R_zero`, non-deduplicated raw emission count `N`, and Inquiry
  Yield. Preserve pre-governance measurement so accuracy pressure cannot suppress
  generation upstream; no pre-recording filter is implied by process history.
- **Question/open-inquiry lifecycle:** distinguish retrieval-to-answer,
  missing-evidence acquisition-to-answer and insufficient-evidence preserved
  inquiry with expiry/indexing. Recording, scope, closure, expiry and recovery of
  open inquiries need decisions; acquisition does not settle them.
- **Spleen Dream yield:** operational inputs, calculation, consumers and relation
  to Inquiry Yield remain undefined; a metric must not give Dream salience the
  causal-provenance handle excluded by proposed ADR 0029 section 7.

Dependent implementation stops at these gaps. Existing projectors, accepted
stage limits and ADRs 0027/0028's Proposed status remain unchanged.

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
  correction with identical source, time, and payload still have the same key.
  Conflicting submissions now refuse instead of silently becoming one retry.
  The formula is explicit and unchanged; accepting both would require a decision.
  ([ADR 0004](decisions/0004-correction-appended-supersedes-via-superseding-events.md))
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
