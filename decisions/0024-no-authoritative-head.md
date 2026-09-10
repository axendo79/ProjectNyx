# ADR 0024: No Authoritative Head

Status: Accepted

Date: 2026-09-10

Supersedes: The ordinary-observation value-recency behavior in implementation companion section 1 and architecture sections 4 and 13, for projector version "1" only. Version "0" retains its existing head and recency semantics.

Related: [ADR 0013 section 4](0013-cross-belief-identity-semantics.md#4-conflicting-values); [ADR 0015](0015-candidate-scoped-verification.md); [ADR 0022](0022-belief-container-uniqueness.md); [ADR 0023](0023-stage-two-contract.md)

Implementation: Pending; implementation is a separate task.

## Context

ADR 0023 permits one observation to record multiple explicitly scoped claims.
Claims about the same subject/property pair belong to one current belief under
ADR 0022, including when their values differ. Candidates in the same event share
its occurred_at and log position; neither distinguishes a scalar winner.

The question is broader than a tie-break. ADR 0015 removed aggregate belief-level
verification, but that did not by itself remove value selection. Resolution and
verification are separate axes. Stage two needs an explicit contract for what a
version "1" belief exposes when it contains multiple ClaimCandidates.

## Decision

### 1. No authoritative head under version "1"

A version "1" belief exposes its ClaimCandidate collection with no authoritative
head. Ordinary observations never select one, and recency does not resolve across
candidates. This explicitly supersedes the ordinary-observation recency behavior
for version "1" only: a later occurred_at or log position does not make one
candidate the belief's authoritative value.

Removing aggregate verification under ADR 0015 did not itself remove value
selection. This decision removes the latter; neither axis supplies a substitute
for the other. Candidates retain their own support, verification, recorded
observation times, and provenance.

### 2. Scalar belief requests and named-candidate reads

A scalar-value request against a belief holding more than one candidate refuses,
consistent with ADR 0013 section 4. Reading a named ClaimCandidate's value is not
a scalar belief request and remains available. Naming a candidate does not make
it the belief's authoritative head.

Whether a belief whose candidates all agree may return their common value is a
separate read contract, deliberately deferred. Until that contract is decided,
multiple candidates still cause the scalar belief request to refuse. Value
equality carries no meaning elsewhere in the project and acquires none by
implication here; it does not coalesce candidates, select one, or establish shared
verification. This decision supplies no additional scalar read contract.

### 3. Multiple claims in one observation

One observation may record multiple explicitly scoped claims about the same
belief with different values. They are accepted as separate ClaimCandidates
sharing one supporting event. That event is deduplicated by event ID in each
applicable evidence pool and in their union. Sharing it never counts as
independent corroboration.

The shared event ID, source, and recorded scopes preserve that the claims came
from one assertion. Whether one-event self-contradiction warrants a diagnostic or
restriction is separate and deferred. It does not change candidate verification
or justify refusing the record. The ordinary scope, identity, and support
validation requirements remain in force.

## Consequences

With version "1" corrections deferred under ADR 0023 section 5, stage two has no
mechanism for resolving disagreement. A subject reported as 64GB yesterday and
128GB today retains both candidates indefinitely, because the system cannot
distinguish a real change from erroneous evidence without a decided temporal-
applicability or resolution mechanism. Disagreement accumulates by design at this
stage. Resolution arrives later through corrections and gated mechanisms; this
decision does not implement or supply their remaining contracts.

Version "0" retains its existing authoritative head and recency semantics
unchanged. Its fixtures are not retrofitted. This change adds only this decision
record; implementation and changes to other files are separate work.

## Acceptance cases

- **Multi-claim event:** one valid observation records fresh C1 asserting 64GB
  and fresh C2 asserting 128GB for the same belief, with explicit scope and
  support. Both are accepted and exposed. The shared event is counted once in
  the combined evidence pool and supplies no independent corroboration. Shared
  provenance remains visible without an inferred verification restriction.
- **Scalar refusal:** a belief holding C1 and C2 refuses a scalar-value request.
  Different observation times, event positions, candidate IDs, or verification
  states do not select a winner. A variant in which both candidates assert 64GB
  still refuses; the deferred common-value contract supplies no exception.
- **Named-candidate read:** requesting C1's value returns C1's recorded value;
  requesting C2's value returns C2's. Neither request selects a belief head,
  transfers support, or changes either candidate's verification state.
- **Accumulating disagreement:** record 64GB yesterday, then 128GB today through
  the existing mention into the same current belief. Both ClaimCandidates remain
  with their own support and times, and a scalar belief request refuses. Later
  evaluation does not age out the first claim, infer an upgrade, or choose the
  newest value. Reversing arrival order likewise retains both without a head.
- **Replay:** incremental evaluation and full replay at shared evaluation time,
  cutoff, and projector version reproduce the complete candidate collection,
  support, provenance, verification, and lineage. A cutoff before the second
  observation excludes it; its later arrival does not rewrite that earlier view.
- **Version isolation:** existing version "0" observations retain their scalar
  head and occurred_at/rowid recency behavior with unchanged fixture bytes.
  Version "1" does not inherit that selection behavior.
