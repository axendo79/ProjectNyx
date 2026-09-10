# ADR 0023: Stage Two Contract

Status: Accepted

Date: 2026-09-10

Supersedes: [ADR 0019's consequences](0019-identity-bootstrap.md#consequences), only the unconditional statement that every ingested fact requires two appends. That cost describes bootstrap.

Related: [ADR 0014](0014-cross-belief-reducer-and-hash-lineage.md); [ADR 0015](0015-candidate-scoped-verification.md); [ADR 0017](0017-schema-version-3.md); [ADR 0018](0018-correction-supersedes-candidates.md); [ADR 0020](0020-multi-user-authority-undecided.md); [ADR 0021](0021-bootstrap-link-treatment.md); [ADR 0022](0022-belief-container-uniqueness.md)

Implementation: Pending; implementation is a separate task.

## Context

Stage two introduces candidate records and identity relations under projector
version "1", using database schema version 3 under ADR 0017. Bootstrap and current
belief uniqueness are decided, but implementation requires a complete contract
for property identity, candidate creation, existing-mention ingestion, retries,
and correction scope. Durable names must also distinguish claim records from
retrieval and Dream concepts.

## Decision

### 1. Property identity

A property is identified by an explicit opaque nonempty string in a dedicated
recorded field, compared exactly. There is no case folding, Unicode normalization,
synonym matching, or parsing from belief_id. A display label establishes no
equivalence. No property registry or property-creation event is required at this
stage.

This identity supplies the property component of ADR 0022's current-only
(subject, property) uniqueness rule. The writer looks up and names the existing
belief where one exists; a conflicting fresh belief ID is refused, not redirected.

### 2. Ordinary observations create fresh ClaimCandidates

Each asserted claim in an ordinary observation gets a fresh recorded candidate ID
supported by that observation event. Naming an existing candidate ID refuses
before append without mutation; replay refuses the same invalid creation. Exact
event retries remain idempotent and are not new candidate creations.

One observation may support multiple explicitly scoped claims. Each has its own
fresh candidate ID and recorded applicability. Sharing the observation does not
make those candidates one claim or multiply the evidence event when pools are
combined. ADR 0015's identity and evidence deduplication rules remain in force.

For one claim scope, N distinct agreeing observations produce N ClaimCandidates.
Gate approval does not compact them: ADR 0015 section 4 leaves contributing
candidates intact, so approving those N produces N+1 candidates. Identity
deduplication collapses repeated paths to one candidate, never distinct candidates
that agree. No accepted decision supplies retention or coalescing.

Attaching support to an existing candidate is deliberately out of scope. It would
require decisions on claim continuity, explicit targeting and applicability,
verification effects, dependency history at each cutoff, correction scope, and
retry rules. The accepted ADRs constrain these matters but do not supply the
support-attachment contract. This stage does not infer it from value agreement.

### 3. Existing mentions and the bootstrap cost

An observation through an existing recorded mention appends one event. It names
the existing mention and subject, then looks up and names the current belief for
the subject/property pair. If that pair has no current belief, its creation
follows ADRs 0019 and 0022 with a fresh recorded belief ID.

A genuinely new mention still creates its own scoped subject through a separate
entity_mention_recorded event. It cannot silently attach to an existing subject.
ADR 0019 section 4 and ADR 0020 continue to govern that separate association case.

ADR 0019's "two appends per ingested fact" is amended to describe bootstrap: a
mention event followed by its observation. It does not apply to every ingested
fact. Subsequent observations through the already recorded mention require only
their observation event; they do not create another mention or subject.

### 4. Retry identity

Retries use the writer's retained recorded IDs and submitted contents. There is
no reminting, no matching, and no new idempotency formula. A retry of a committed
event does not create another identity, candidate, or item of evidence.

If the mention committed but the observation did not, the retry uses that recorded
mention and the retained observation submission. The committed mention remains
valid without a property claim; failure of the observation does not remove it
from Layer A.

### 5. Corrections are deferred under version "1"

Version "1" corrections are deferred for this stage. Append and replay refuse
correction_appended events until the candidate-target eligibility contract is
complete, including events that supply explicit targets. They are not processed
with the old belief-level semantics or reinterpreted as ordinary observations.

ADR 0018 remains the governing correction semantics for later implementation.
This is an explicit stage boundary, not a replacement supersession rule. Version
"0" keeps its existing correction behavior, including its existing refusals.

### 6. Vocabulary

The candidate records stage two creates are ClaimCandidates. Stage-two candidate
tables, identifiers, and API names must distinguish this claim role from the
other uses of "candidate".

RetrievalCandidate and DreamEmission are reserved for the unbuilt retrieval and
Dream mechanisms without ratifying either mechanism. Hypothesis is not narrowed:
it already covers model inference in the process-trace design and has an existing
hypothesis_id. Retention for grading does not establish a Layer A world claim.

candidate_entity_id names an identity-resolution target and is not a
ClaimCandidate. There is no global rename of "candidate".

## Consequences

This closes the remaining stage-two contract gaps identified by the audit within
the scope above. ClaimCandidates retain their own support and verification;
there is no aggregate belief-level verification state. The decision introduces
no new origin-to-state mapping, authority policy, or candidate confidence score.

Constitutive links retain ADR 0021's treatment. Merge, split, and gate-approved
corroboration remain stage three. Existing-subject association authority and
mention-correction mechanics are not supplied here. Version "0" is not
retrofitted. Implementation is separate work.

**Untested implementation hazard:** if each update serializes the whole
accumulated candidate collection for lineage, cumulative work on a frequently
updated belief may be quadratic. This should be measured. It is not a measured
result or a decision to change lineage coverage, discard candidates, or introduce
retention or coalescing.

## Acceptance cases

- **Exact property identity:** repeated use of the identical nonempty property
  string identifies the same property. Case variants and distinct Unicode
  sequences remain distinct even when labels look alike. An empty string or a
  missing property field refuses; belief_id spelling and display labels do not
  fill it in or establish equivalence.
- **Fresh candidates for agreement:** N distinct agreeing observations about one
  pair name its current belief and N fresh candidate IDs. All N candidates and
  their event support survive. No value-based coalescing or gate approval occurs.
- **Existing candidate refuses:** a distinct observation naming an existing
  candidate ID refuses before append without mutation. Replay refuses an injected
  event of that shape. No support is attached to the existing candidate.
- **Multiple explicit claims:** one observation creates separate ClaimCandidates
  for its explicitly scoped claims with recorded support applicability. Each
  applicable pool counts that event once; their union also counts it once.
  Mention provenance alone does not invent support for another claim.
- **Existing-mention path:** after bootstrap, another observation naming the
  existing mention, subject, and current belief adds one event and a fresh
  ClaimCandidate. No new mention or subject is created, and a conflicting fresh
  belief ID still refuses under ADR 0022.
- **New-mention isolation:** a genuinely new mention creates its own scoped
  subject even if its text resembles an earlier mention. It is not silently
  associated with the earlier subject or its belief.
- **Retry across the bootstrap boundary:** commit the mention, then fail before
  the observation commits. The mention remains valid without a property claim.
  Retrying with retained IDs and contents completes the observation once; retry
  after completion creates no duplicate records or evidence and reruns no matching.
- **Different standing survives:** using explicit pre-event standing and history
  preconditions as in ADR 0015, preserve same-value ClaimCandidates with different
  standing independently. The fixture supplies no new production origin mapping,
  gate approval, or aggregate verification state.
- **Correction boundary:** version "1" refuses corrections at append and replay,
  with or without explicit targets, without appending or silently converting them
  to observations. Version "0" retains its existing correction fixtures and bytes.
- **Vocabulary and scope:** ClaimCandidate references do not resolve through
  identity-resolution targets, retrieval items, or process-trace hypothesis IDs.
  Reserving names creates no retrieval or Dream implementation and does not rename
  candidate_entity_id or narrow Hypothesis.
- **Replay:** at shared evaluation time, cutoff, and projector version, complete
  incremental results and full replay agree on identities, exact property strings,
  associations, candidates, support, verification, and lineage. Replay allocates
  no replacement IDs and preserves the stage refusals above.
