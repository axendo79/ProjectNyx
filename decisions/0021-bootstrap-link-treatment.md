# ADR 0021: Bootstrap Link Treatment

Status: Accepted

Date: 2026-09-09

Supersedes: [ADR 0019 section 5](0019-identity-bootstrap.md#5-initial-link-state-and-confidence-remain-undecided), only its deferral of link-state and confidence treatment for bootstrap associations.

Related: [ADR 0014](0014-cross-belief-reducer-and-hash-lineage.md); [ADR 0015](0015-candidate-scoped-verification.md); [ADR 0020](0020-multi-user-authority-undecided.md); architecture section 11; implementation companion section 1

Implementation: Constitutive bootstrap links and their no-confidence treatment ship under projector "1" in `src/nyx/reducer.py` and `schema.sql`. Non-constitutive link treatment remains outside the implemented stage. Status updated 2026-09-11; implementation-status statements below describe the decision-time state.

## Context

ADR 0019 defines a fresh subject as "the referent of this recorded mention" but
leaves its initial link state and confidence treatment undecided. This association
constitutes the subject rather than resolving a match against an independently
established target. Its treatment must satisfy the architecture's explicit-state
requirement without inventing matching confidence.

## Decision

### 1. Constitutive association

A bootstrap association is constitutive, not a resolved match. Subject S is the
referent of mention M by construction, so there is no matching proposition to
assess. No epistemic confidence applies to this association. This is not confidence
1.0, and no arithmetic identity is assigned.

A definite association is not an infallible mention. That S is M's referent says
nothing about whether extraction was correct, what the speaker intended, whether
the referent exists, or whether it is an existing subject. These are separate
propositions with their own decisions; none is settled here. Bootstrap likewise
establishes no real-world uniqueness.

### 2. Structural link state

Bootstrap links take the distinct link_state value `constitutive`. It expresses
the link's structural role, not a resolution outcome. The existing
`proposed|accepted|rejected|split` vocabulary describes resolution against an
independently established target and does not fit bootstrap.

`constitutive` is explicitly not a point on a resolution scale and is never
compared to one. It is not an alias for `accepted`, `resolved`, or `verified`, nor
does it define a transition to any of them. Recording the constitutive state
satisfies architecture section 11's requirement for an explicit entity-link state
before active resolved belief; bootstrap is not exempted from that requirement.
The state records the role established by ADR 0019's mention event, not a separate
acceptance of a matching hypothesis.

### 3. Confidence-ceiling computation

Constitutive links are excluded from confidence-ceiling computation. Their
presence does not make an otherwise scored path unscored end to end. Where a path
also contains links with confidence treatment established by applicable decisions,
the ceiling uses those links under that treatment, without a confidence value or
arithmetic stand-in for any constitutive link.

If exclusion leaves no links to score, no identity-link ceiling is computed for
that path. No empty-set minimum, confidence 1.0, or replacement score is assigned.
The candidate retains its applicable verification and support treatment; absence
of a bootstrap ceiling is not verification or a promotion event.

This exclusion does not supply missing confidence treatment for other link kinds.
A path containing a non-constitutive link whose required treatment is undecided
remains blocked on that decision. Such a link cannot be silently excluded or
given a default under this rule. Candidate verification remains governed by ADR
0015; no candidate confidence score is introduced.

### 4. Representation and scope

The entity_links schema's non-null state and confidence columns are an
implementation concern. Their physical treatment must represent `constitutive`
and the absence of applicable epistemic confidence without assigning a numeric
bootstrap default. This ADR does not choose that physical representation or a
database schema version. Its treatment authorizes no defaults for other link kinds.

Recorded contents must preserve the constitutive role and created associations
through replay under ADRs 0019 and 0014. Replay does not infer a resolved match,
rerun matching, or manufacture confidence from the recorded state.

## Consequences

ADR 0019 section 5's bootstrap link-state and confidence deferral is closed.
This does not resolve every stage-two dependency. Write permission and authority
over shared identity remain undecided under ADR 0020. This ADR establishes no
equivalence between constituted, accepted, resolved, and verified.

How later associations with existing subjects are stated or scored remains
separate work under ADR 0019 section 4 and ADR 0020. Whether and how a mention
assertion can be corrected is not decided here. Version "0" retains its existing
semantics and fixtures; no retrofit is authorized. Implementation is separate work.

## Acceptance cases

- **Constitutive bootstrap:** a valid mention event creates S as M's scoped
  subject with link_state `constitutive` and no applicable epistemic confidence.
  No matching result, confidence 1.0, or arithmetic identity is supplied.
- **Explicit state without promotion:** a scoped observation meeting ADR 0019's
  claim requirements has an explicit entity-link state. That state is not
  compared with resolution states and does not verify the candidate or resolve
  its identity against another subject.
- **Mention uncertainty survives:** constitutive state supplies no proof of
  correct extraction, speaker intent, referent existence, real-world uniqueness,
  or equivalence to an existing subject. It supplies no correction mechanics.
- **Bootstrap-only path:** excluding constitutive links leaves no scored links.
  No identity-link ceiling or replacement number is produced. The candidate's
  applicable verification and support treatment is retained without promotion.
- **Mixed path:** where non-constitutive links have independently decided scoring
  treatment, adding a constitutive link changes neither their computed ceiling
  nor their scores. No score is assigned to the constitutive link, and the whole
  path is not made unscored merely because it contains one.
- **Undecided later link:** a mixed path requiring unspecified treatment for a
  non-constitutive link remains blocked. A fixture cannot discard that link,
  assign it a default, or invent its authority or scoring treatment.
- **Replay and version isolation:** incremental evaluation and full replay at
  shared time, cutoff, and projector version preserve the same constitutive role,
  identities, associations, and confidence treatment. Version "0" keeps its
  existing fixtures and refuses unsupported events rather than being retrofitted.
- **No authority by construction:** constitutive state grants no write permission
  or authority over shared identity. Fixtures requiring those unresolved rules
  remain blocked under ADR 0020.
