# ADR 0022: Belief Container Uniqueness

Status: Accepted

Date: 2026-09-09

Related: [ADR 0013 section 1](0013-cross-belief-identity-semantics.md#1-entity-and-belief-identity); [ADR 0014 section 3](0014-cross-belief-reducer-and-hash-lineage.md#3-recorded-output-ids-and-acceptance); [ADR 0015](0015-candidate-scoped-verification.md); [ADR 0018](0018-correction-supersedes-candidates.md); [ADR 0019](0019-identity-bootstrap.md)

Implementation: Pending; implementation is a separate task.

## Context

The accepted ADRs require recorded belief IDs and correct subject and property
associations, but do not decide whether a second current belief may be created
for an already represented subject/property pair. Stage two requires this rule
for append validation and storage constraints.

## Decision

### 1. One current container per subject/property pair

(subject, property) uniquely identifies a current belief. An event naming a fresh
belief ID for a pair that already has a current belief refuses before append,
without mutation. Replay refuses an injected event of that shape rather than
accepting a second current container.

An observation about an existing pair names the existing belief ID. The writer
looks it up. Validation uses the actual pre-event snapshot under ADR 0014; a
lookup against an older snapshot does not authorize an invalid append.

The recorded association is never silently redirected. A candidate recorded
against B2 is not moved into B1 because B1 already represents the pair. The event
refuses instead. Naming the existing container does not coalesce its candidates:
ADR 0015's candidate-identity rules remain in force.

### 2. Uniqueness excludes historical beliefs

Uniqueness is over current beliefs only. Express the constraint as partial
uniqueness of (subject, property), with membership restricted to rows whose
belief lifecycle status is current. Historical rows do not participate. An
unconditional unique constraint over all belief rows would enforce the wrong
contract.

This predicate concerns identity lifecycle, not candidate verification state.
Within the selected projector's view, each pair has at most one current belief;
historical beliefs sharing a pair are expected and are not uniqueness violations.
The predicate does not choose column names, identity representations, or an
equality algorithm for either component of the pair.

Merge and split create new belief IDs and retire predecessors under ADR 0013
section 1. This decision adds no merge or split mechanics, rewrites no historical
association, and does not authorize reusing a historical belief ID.

## Rationale

A belief is the container for candidates about a property of a subject. Two
current containers for one pair would give "what is believed about S's RAM" two
answers with nothing deciding between them. ADR 0013 requires disagreement to be
represented as candidates within one belief. Allowing coexistence would also let
a writer escape an inconvenient conflict by naming a fresh container.

Requiring the writer to look up and name the existing belief is deliberate
friction of the same kind ADR 0018 introduced for correction targets. It makes
the intended association explicit and reviewable rather than silently repairing
the submitted event.

## Consequences

The belief-container uniqueness gap blocking stage two is closed. This decision
does not establish how a subject or property is identified or compared, or
whether property identity is a string, a typed reference, or another form.
Version "0" retains its existing semantics and fixtures; no retrofit is
authorized. Implementation is separate work.

## Acceptance cases

- **Duplicate current container:** B1 is current for (S, RAM). An observation
  naming fresh B2 and candidate C2 for that pair refuses before append. Layer A,
  derived records, and progress remain unchanged; C2 is not inserted into B1.
- **Existing-ID path:** with B1 current for (S, RAM), the writer looks up B1 and
  records a valid observation naming B1 and a fresh candidate C2. C2 belongs to
  B1; existing candidates remain distinct, including same-value candidates with
  different standing. No second current belief is created.
- **Current-only constraint after merge:** in a post-merge constraint fixture,
  a current belief and a historical predecessor row share the tested pair. The
  historical row does not conflict with the current row; another current row for
  that pair does. This isolates the uniqueness predicate, not the validity of a
  merge transition: subject changes, recorded output associations, and predecessor
  validity remain governed by ADR 0013. The fixture authorizes no rewriting of
  predecessor subjects to manufacture the shared pair.
- **Injected duplicate on replay:** replay a prefix containing current B1, then
  an injected observation creating B2 for the same pair. Replay refuses rather
  than keeping two current containers, redirecting C2 into B1, or choosing one
  container silently.
- **Stale writer lookup:** a writer finds no current belief for a pair, but B1
  becomes current before its event naming fresh B2 reaches the append position.
  Validation against the actual prefix refuses without mutation.
- **Version isolation:** existing version "0" fixtures retain their original
  behavior and bytes; this constraint is not silently retrofitted into them.
