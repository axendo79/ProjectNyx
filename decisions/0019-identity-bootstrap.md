# ADR 0019: Identity Bootstrap

Status: Accepted

Date: 2026-09-09

Related: [ADR 0013](0013-cross-belief-identity-semantics.md); [ADR 0014 section 3](0014-cross-belief-reducer-and-hash-lineage.md#3-recorded-output-ids-and-acceptance); [ADR 0015 section 3](0015-candidate-scoped-verification.md#3-candidate-identity-and-deduplication); [ADR 0018](0018-correction-supersedes-candidates.md); architecture section 11; Invariants 1, 8, and 9

Implementation: Pending; implementation is a separate task. Initial link state
and confidence treatment remain undecided and block dependent implementation.

## Context

The cross-belief ADRs assume that entities, mentions, and belief associations
already exist. They do not establish how the first ones enter Layer A. The
walking skeleton uses a belief_id as the entity key in its append index, leaving
this bootstrap question outside its single-event observation path.

An empty candidate search does not establish that an observation concerns a new
real-world subject. It records what matching found, not that no existing subject
is the referent. Bootstrap needs an explicit scope that does not depend on that
inference.

## Decision

### 1. Mention recording is a separate event

A mention is recorded by its own entity_mention_recorded event, using the existing
taxonomy entry. It precedes and is separate from the observation that makes a
claim about its subject.

The two assertions have different failure modes: mention recording can be wrong
about what text refers to, while an observation can be wrong about a value.
Separate events let either be superseded without deciding which part of a fused
event is being corrected. Supersession preserves the original Layer A records;
it does not edit either event. This decision does not specify a new mention-
correction handler or extend ADR 0018's candidate-correction semantics to mentions.

### 2. Mention recording authorizes a scoped subject

Recording a mention authorizes allocating a fresh subject whose meaning is
strictly "the referent of this recorded mention." This establishes neither
uniqueness in the world nor equivalence to any other recorded subject. It
requires no search for candidate matches.

The authority comes from the defined scope of the recorded assertion, not from
a claim that matching proved the subject new. Absence of a retrieved match never
establishes a new subject. The presence of candidate matches does not itself
establish an association with them or invalidate this scoped bootstrap.

### 3. Active claims remain scoped to the recorded subject

Claims about that scoped subject are active resolved belief once the observation
event explicitly establishes subject, property, candidate, and applicable support.
For example, the claim reads as "the device referred to in mention M has 64GB."
It is silent about any other subject.

Mention recording alone supplies no property observation. Active resolved belief
does not itself mean verified: candidate verification and support remain governed
by ADR 0015 and the applicable verification rules. Neither allocation of the
subject nor its mention association supplies verification of the property claim.

### 4. Association with an existing subject requires an admissible basis

Associating a scoped subject with an existing subject requires a recorded basis
that actually establishes the relationship. A resolver's similarity proposal,
including an empty search result, is never sufficient.

Admissible bases are a ratified list; anything not on that list refuses. The list
is deliberately not enumerated here and is extended by later decision. This ADR
authorizes no admissible basis by example, implication, or resolver confidence.

### 5. Initial link state and confidence remain undecided

Initial link state and confidence treatment are not decided here. Calling an
association provisional supplies no defaults. Their decision is later work, and
dependent implementation stays blocked on it. The scoped-subject and activation
semantics above do not waive this boundary or supply a link-state transition,
confidence value, or acceptance threshold.

### 6. Recorded identities and replay

Recorded contents must suffice for replay to reproduce every created identity
and association without rerunning matching. Consistent with ADR 0014 section 3
and ADR 0015 section 3, IDs and their associations are recorded rather than
allocated afresh during reduction or inferred from a name or value.

The mention record identifies the created mention and subject and their
association. The observation records the belief and candidate identities it
creates and the subject, property, and applicable support that establish the
claim. Replay uses those recorded identities and assignments exactly. Freshness,
association validation, and retry treatment follow the existing ADR contracts;
a retry is not another allocation or another observation.

## Consequences

This closes the identity-bootstrap gap blocking stage two by deciding how an
initial scoped subject and its claims enter the event history. It does not make
all of stage two implementable: initial link state and confidence treatment
remain blockers, and associations with existing subjects require later ratified
admissible bases.

The explicit bootstrap cost is two appends: a mention event and an observation
event. As amended by [ADR 0023 section 3](0023-stage-two-contract.md#3-existing-mentions-and-the-bootstrap-cost),
this describes bootstrap, not every ingested fact; an observation through an
existing recorded mention requires only its observation event. The walking
skeleton's single-event path becomes two for bootstrap under the identity-capable
contract. Version "0" retains its existing semantics and
its fixtures remain valid version-isolation tests; it is not retrofitted.

Layer A remains append-only. This decision does not select a physical payload
schema, a database schema version, or additional correction mechanics.
Implementation is separate work.

## Acceptance cases

Cases requiring initial link state or confidence treatment become executable
only after those decisions are ratified; fixtures must not invent defaults.

- **Separate bootstrap and observation:** record mention M and its fresh scoped
  subject S through entity_mention_recorded, then record an observation creating
  belief B and candidate C for S's RAM value of 64GB with applicable support.
  Layer A contains two events. After the mention alone there is no RAM claim;
  after the observation the active claim is about the device referred to in M.
- **No matching prerequisite:** bootstrap the scoped subject without running a
  candidate search. Repeat in a history containing a plausible existing match.
  Neither case asserts real-world uniqueness or establishes equivalence to the
  existing subject. An empty search result is not the authority for allocation.
- **Explicit claim scope:** an observation's subject, property, candidate, and
  applicable support are recorded. Missing associations are not completed from
  belief_id spelling, mention text, value equality, or matching results. Such an
  incomplete event does not authorize active resolved belief.
- **No cross-subject answer or promotion:** the scoped RAM claim does not become
  a claim about an existing subject merely because the resolver suggests that
  subject. Mention recording and bootstrap do not verify the RAM candidate.
- **Unlisted association basis:** an attempted association with an existing
  subject using an unratified basis refuses before append without mutation.
  Similarity and an empty search result do not bypass refusal. Replay refuses an
  injected association lacking an admissible basis rather than accepting it.
- **Independent correction scope:** the mention assertion and value observation
  have distinct event IDs and remain separately addressable for supersession.
  Correcting a value does not silently rewrite the mention assertion. This case
  does not invent the still-unspecified mechanics for correcting a mention.
- **Recorded IDs, cutoffs, and retry:** at shared evaluation time, log cutoff,
  and projector version, incremental evaluation and full replay reproduce the
  same complete identities, associations, claims, and support. A cutoff after
  the mention but before the observation contains the scoped subject without
  that property claim. Replay runs no matching and allocates no replacement
  IDs; retry of either committed event adds no duplicate records or evidence.
- **Deferred treatment:** no initial link state or confidence is supplied merely
  because the subject is called provisional. Implementation requiring either
  remains blocked until the corresponding decision is recorded.
- **Version isolation:** version "0" continues to reproduce its existing
  single-event observation fixtures. The identity-capable contract uses the two
  events; version "0" is neither silently upgraded nor allowed to skip an
  unsupported mention event to return an apparently complete result.
