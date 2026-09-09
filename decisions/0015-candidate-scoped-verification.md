# ADR 0015: Candidate-Scoped Verification

Status: Accepted

Date: 2026-09-09

Supersedes: [ADR 0014 section 4](0014-cross-belief-reducer-and-hash-lineage.md#4-verification-boundary-resolved-by-adr-0015), the refusal of merges with differing predecessor verification states.

Related: [ADR 0013](0013-cross-belief-identity-semantics.md); [ADR 0014](0014-cross-belief-reducer-and-hash-lineage.md); [ADR 0012](0012-whole-view-equality.md); Invariants 3, 4, 9, and 15

Implementation: Pending; implementation is a separate task.

## Context

ADR 0014 refused merges with differing predecessor verification states because
no aggregate state for the resulting belief had been decided. ADR 0013 already
separates conflict resolution from verification and retains candidate values with
their evidence and provenance. The verification question belongs to those
candidates, not to the belief containing them.

Distinct claims can agree on a value while having different support histories or
restrictions. Conversely, multiple identity paths can reach the same candidate.
Combining claims by value would erase those distinctions; counting paths as
candidates or evidence would manufacture corroboration.

## Decision

### 1. Verification belongs to a candidate

A candidate is a claim with its own support and its own verification state.
Verification is scoped to the candidate, not to the belief. A belief holding a
conflict holds candidates; there is no aggregate belief-level verification state
and none is computed. This applies also when the candidates agree on a value.

A verification question identifies a candidate. A belief's conflict result exposes
the candidates and their individual support, states, and provenance. ADR 0013's
refusal of a scalar request for an unresolved conflict remains in force. Verified
support for one candidate does not select it as the authoritative scalar answer.

### 2. Identity operations do not earn verification

Verification is inherited, never earned by pooling. A merge is structural: it
changes which claims are compared, not their epistemic standing. Differing
candidate verification states are not by themselves a reason to refuse a merge.
No minimum, maximum, or preferred-predecessor aggregate is substituted.

Two unverified predecessors whose combined evidence would clear a threshold remain
unverified pending gated promotion. The merge event is neither a property
observation nor a verification approval. Invariant 15 remains in force: identity
reinterpretation may not directly promote. Changes in usable support are governed
by the dependency rule below, not by a blanket state change on merge.

### 3. Candidate identity and deduplication

Candidates are deduplicated by candidate identity, never by value. The same
candidate reaching a belief by two identity paths is one candidate with two paths.
Distinct candidates that agree on a value remain distinct, including candidates
with different support histories or verification states.

A candidate ID is assigned at candidate creation and recorded rather than inferred
from value equality. Candidate identity carries through an identity operation when
the claim and established support applicability are unchanged. A change in the
containing belief's ID does not alone require a new candidate ID.

A split producing distinct claim scopes records fresh candidate IDs with
predecessor links and explicit support assignments. For example, "the unresolved
device has 64GB" becoming "L has 64GB" and "R has 64GB" creates two independently
assessable claims. Sharing an observation does not make them one candidate.
Verification of one successor claim does not verify the other merely because
both share evidence or ancestry.

Unresolved support applicability refuses under ADR 0013. Complete mention
assignment does not authorize copying support or verification to claims for
which the records do not establish applicability. Replay uses the recorded fresh
IDs and assignments; it does not allocate replacement candidates.

### 4. Gate-approved corroboration has an explicit target

Gate-approved corroboration establishes a new candidate for the jointly supported
claim, leaving the contributing candidates intact. The approval event records:

- The new candidate's ID.
- Its claim scope.
- The contributing candidate IDs.
- Its evidence dependencies.
- Its verification basis.

The approval verifies neither the belief nor every candidate asserting that value.
It establishes the approved standing of the new candidate through the existing
gated verification requirements. The contributing candidates do not acquire that
standing merely by contributing evidence.

Replay reproduces the new candidate from its recorded ID rather than minting
another. Reapplying the same recorded approval cannot create additional candidates
or additional evidence. This decision specifies the logical recorded contents,
not a new event-type name or a physical payload schema.

### 5. Restrictions follow actual dependencies

A candidate's standing is recomputed against which of its support remains usable,
not against whether anything anywhere was quarantined. Restrictions follow the
approval's actual dependencies. If quarantined evidence was necessary to a
candidate's justification, that justification fails; a candidate not depending
on it is unaffected. Questioned or quarantined support and its applicable
restrictions cannot be erased by moving the candidate through identity operations.

Recomputation remains subject to the no-promotion gate. Removing adverse evidence
never silently raises standing. A new identity path is not a restoration or a
verification approval. A surviving justification must be applicable to the
candidate's actual claim and usable support.

This decision does not invent a blanket demotion destination or additional
restoration transitions. Existing applicable verification rules govern those
transitions; any still-unspecified transition remains subject to the gap protocol.
Failure of a necessary justification cannot be treated as continued verification
on that justification while the transition is unresolved.

### 6. Evidence counts across candidates

Evidence is deduplicated by event ID before counting, including when an evidence
pool spans multiple candidates. A corroboration candidate's evidence overlaps its
predecessors' and must not be counted twice. Candidate count, provenance-path
count, distinct evidence-event count, and independent source-class count are
separate quantities. Existing source-class independence rules remain in force.

This is not global consumption of an event. The same event may support distinct
claims where applicability is established, as ADR 0013 permits. Each relevant
pool counts its event IDs once; a union of those pools also counts each event ID
once while retaining distinct candidates and provenance paths.

### 7. Round-trip invariant

The same usable evidence, applicable restrictions, and gated verification history
produce the same standing regardless of identity path. Merge -> split -> remerge
preserves justified standing, not candidate IDs or counts. A split into distinct
claim scopes may require fresh candidates; remerging does not coalesce those
candidates by value or common ancestry.

Compare standing for corresponding claims with established support applicability.
The invariant does not equate different claims or require unchanged standing when
support usability, applicable restrictions, or gated verification history changes.
It does require that identity paths alone cannot create verification, remove a
restriction, or multiply evidential support.

## Worked grounding

Use ADR 0013's A/B/C log: e-1 reports 64 at 09:00 through m-A; e-2 reports 64 at
09:05 with established applicability through m-B and m-C; e-3 reports 128 at
09:10 through m-C. e-2 remains in C's observation history and is not support for
128. The following adds explicit candidate states as fixture preconditions, not
as new origin-to-state mappings:

| Belief | Candidate | Claim value | Support | Verification state |
| --- | --- | --- | --- | --- |
| b-A | c-A | 64 | e-1 | verified |
| b-B | c-B | 64 | e-2 | questioned |
| b-C | c-C | 128 | e-3 | unverified |

The fixture supplies the recorded justification and restriction history for these
states. No state is inferred merely from the number of events in the table.

At 10:00, merge-1 creates M/b-M from A/b-A and B/b-B. c-A and c-B remain distinct
with their respective states. At 11:00, merge-2 creates N/b-N from M/b-M and
C/b-C. b-N contains c-A, c-B, and c-C: three candidates, two distinct values, no
aggregate verification state, and no authoritative scalar. The pooled observation
history contains {e-1, e-2, e-3}; both identity paths to e-2 remain available.

For the identity-preserving round trip, split N at 12:00 with m-A assigned to L
and m-B/m-C to R, with records establishing unchanged claim and support
applicability for c-A on L and c-B/c-C on R. Remerge L and R at 13:00 into a new
entity and belief. c-A remains verified, c-B questioned, and c-C unverified.
New containing belief IDs and additional provenance do not alter those states.

In a separate scoped-split fixture, a candidate c-U for "the unresolved device
has 64GB" produces recorded c-L and c-R with distinct successor claim scopes,
predecessor c-U, and established support assignments. Remerging retains c-L and
c-R as distinct candidates even when they share an observation and value. Their
standing follows their applicable support, restrictions, and gated history; the
round trip does not require reviving c-U or equating the two successor claims.

## Consequences

This decision supersedes ADR 0014 section 4's differing-state refusal, including
the corresponding refusal acceptance case and statements that this boundary is
unresolved. Merges are not refused solely because candidate states differ. Other
acceptance checks and refusals under ADRs 0013 and 0014 remain in force.

Candidate-scoped verification replaces the aggregate belief-state assumption for
these semantics. ADR 0014's result and lineage coverage includes the candidate
identities, claim scopes, verification information, support assignments, and
provenance that explain the result. ADR 0012's complete-view equality remains a
comparison at the same evaluation time, log cutoff, and projector version.

Distinct agreeing claims and gate-approved candidates may increase candidate
count. Count is not a corroboration measure. No retention policy or candidate
coalescing rule is introduced. Implementation, storage layout, migration, and
projector-version selection are separate work; version "0" is not silently
changed by this document. Layer A remains append-only.

## Acceptance cases

- **Differing states in A/B/C:** execute both merges with the grounding states.
  Neither refuses solely because states differ. b-N exposes c-A verified, c-B
  questioned, and c-C unverified, with their own support and no aggregate state.
  c-A and c-B are not collapsed despite agreeing on 64. A scalar conflict request
  refuses under ADR 0013.
- **Pooling does not promote:** use an A/B variant with both candidates unverified
  and independent source classes whose combined evidence clears the threshold.
  merge-1 leaves both unverified and routes would-be promotion through the gate;
  neither the merge nor merge-2 creates a verified candidate on its own.
- **Same identity, multiple paths:** arrange two established identity paths to the
  same candidate without changing its claim or support applicability. The result
  contains one candidate with both paths. Different candidate IDs with the same
  value remain distinct. Additional paths change neither standing nor counts of
  observations or independent corroborating sources.
- **Recorded corroboration target:** approve the joint A/B claim in the unverified
  variant. The event records c-AB, its scope, contributing c-A/c-B IDs, e-1/e-2
  dependencies, and verification basis. c-AB is verified; c-A and c-B remain
  unverified. No other same-value candidate or containing belief is verified by
  that approval. Replay and retry reproduce c-AB without minting another ID.
- **Cross-candidate evidence counting:** count the union of c-A, c-B, and c-AB's
  evidence. It contains two observation events, not four. Adding C's history
  yields three distinct events, not another count of e-2. Retain all provenance
  paths. A same-source-class variant does not acquire independence from distinct
  candidate or event IDs.
- **Necessary support quarantined:** after the approval, quarantine e-2 in a
  fixture where it is necessary to c-AB's justification. That justification fails;
  c-AB cannot retain verification on it. A candidate supported independently by
  e-1 and not depending on e-2 is unaffected. Carry the applicable restriction
  through merge, split, and remerge; no identity event restores the justification.
- **No promotion by removal:** remove or restrict adverse evidence without a
  gated approval. Recomputation does not raise a candidate's standing, including
  when the removal happens before a split or remerge. Applicable questioned and
  quarantined restrictions remain visible through the identity paths.
- **Identity-preserving round trip:** execute the 12:00 split and 13:00 remerge
  from the grounding fixture with unchanged applicability and verification
  history. The corresponding c-A/c-B/c-C states remain verified/questioned/
  unverified. Compare justified standing, not containing belief IDs or lineage.
- **Distinct-scope round trip:** split c-U into recorded c-L and c-R with explicit
  support assignments and predecessor links. Replay uses their recorded IDs.
  Remerge retains both claims and their justified standing, without combining
  them by value. Shared evidence counts once in a combined pool. In a separate
  variant, a gate approval for L does not verify R through shared ancestry or
  evidence; this changed gated history is not an unchanged-history round trip.
- **Unresolved applicability:** supply a complete mention partition but no
  established support assignment for a successor claim. The split refuses before
  append without mutation under ADR 0013; fresh IDs cannot cure the ambiguity.
- **Replay and cutoffs:** compare incremental evaluation with full replay before
  and after each merge, approval, restriction, split, and remerge at shared T,
  cutoff, and projector version. Complete results agree, including candidate IDs,
  states, assignments, restrictions, and paths. Later identity or verification
  events do not rewrite earlier-cutoff results.
