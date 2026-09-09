# ADR 0014: Cross-Belief Reducer Shape and Hash Lineage

Status: Accepted

Date: 2026-09-08

Supersedes: [ADR 0008](0008-fold-signature-cannot-express-cross-belief-events.md), the recorded reducer-shape and hash-lineage blocker.

Related: [ADR 0003](0003-genesis-sentinels-and-hash-material-delimiters.md); [ADR 0010](0010-projection-parameters.md); [ADR 0012](0012-whole-view-equality.md); [ADR 0013](0013-cross-belief-identity-semantics.md); Invariants 8, 9, and 15

Implementation: Pending; implementation is a separate task.

## Context

ADR 0013 settles identity semantics. A merge can create several beliefs, retire
several predecessors, change mention associations, and retain conflicting values
with overlapping evidence. The one-belief-in, one-belief-out fold and its single
prior-hash chain cannot express that transition.

Reducer shape and lineage are decided together: one event reads a consistent
pre-event snapshot and produces one complete logical delta. Each changed belief's
lineage covers both its ancestry and its resulting event-derived contents.

## Decision

### 1. Snapshot read contract

The reducer receives the event envelope and payload, an explicit evaluation time,
and read-only access to a snapshot representing the log prefix immediately before
that event under the selected projector version. It determines the affected set
from identity membership in that snapshot. Neither today's identity mapping nor
a caller-selected subset is authoritative for affected-set discovery.

The read contract permits lookup and enumeration of entity status, mention
membership, all current beliefs on affected entities, historical beliefs and
predecessor relationships, observation records, claim-support assignments,
source classes, and provenance and identity-event paths. It supplies a consistent
set of records, not independently refreshed reads from a changing database.
Incremental processing and replay supply the same logical reads; replay may
supply them from in-memory state.

For merge-2, those reads include M's and C's current beliefs and mention sets,
b-M and b-C's complete pre-event contents, e-1/e-2/e-3 and their applicability,
and the paths through merge-1. Sharing e-2 does not by itself make an otherwise
unrelated entity part of the affected set. Every property on M or C participates
when its subject changes, even if its value and evidence do not change.

The reducer does not write storage, sample the clock, allocate IDs, call a model,
or read unversioned external state. Acceptance uses the same pre-event semantics.
Its validation must remain valid at the actual append position; a concurrent
change cannot turn a check against an older snapshot into authorization to append.

### 2. Complete event delta

One reduction produces one complete logical delta for the event. It includes all
new and changed entities and beliefs, current/historical status, mention
associations, successor and predecessor relationships, conflict candidates,
evidence assignments, retained provenance, and changed belief lineage values.
Unrelated records are unchanged. Historical status is identity lifecycle
information, not an instruction to set verification_state to superseded.

The reducer computes the semantic result. The caller persists it and maintains
its materialized indexes and processing progress. The caller does not finish the
identity decision by choosing IDs, selecting a conflict winner, or discarding
support or provenance during insertion. The event is not folded independently
once per affected belief.

For merge-2, the delta creates N and b-N, marks M/C and b-M/b-C historical, links
M/C to N through merge-2, moves m-A/m-B/m-C's current associations to N, and links
b-N to b-M and b-C. b-N contains the 64/128 conflict without an authoritative
scalar. Earlier b-A/b-B records and their paths remain historical and available.
Transitive resolution answers change through the new relationships; earlier
identity events are not rewritten. Any cached transitive answers are updated or
invalidated as part of publication.

### 3. Recorded output IDs and acceptance

The accepted identity event payload records the IDs assigned to every resulting
entity and belief and their output associations. Replay reads these IDs; it does
not derive replacement IDs or allocate fresh ones. Entity IDs and belief IDs have
distinct scopes.

Acceptance validates association rather than spelling:

- Every required resulting entity and belief has an assigned ID.
- IDs are fresh relative to the pre-event history and distinct within their scope,
  including within the submitted event. Historical IDs are not available for reuse.
- Every output has the correct subject, property, and predecessor relationships,
  as applicable to its record kind.
- No required output is missing and no unrelated output is introduced.

The complete output inventory is checked against the snapshot, not merely against
the outputs the payload happens to list. A valid opaque ID need not match a
preferred derivation algorithm. Its recorded association must be correct.
Validation refuses before append; replay applies the same checks against its
pre-event prefix and fails loudly on an invalid recorded transition. A retry of
an already committed event is not a second acceptance of its IDs as fresh.

### 4. Verification boundary resolved by ADR 0015

Superseded 2026-09-09 by [ADR 0015](0015-candidate-scoped-verification.md).
Verification is scoped to candidates, with no aggregate belief-level state.
Differing predecessor candidate states are not by themselves grounds to refuse
a merge. Candidate identity, inherited standing, gated corroboration, and
support-dependent restrictions follow ADR 0015. Invariant 15 remains in force.

ADR 0015 also supersedes this document's corresponding differing-state refusal
acceptance case and references below to that verification boundary as unresolved.
Other acceptance requirements remain in force. Implementation is a separate task;
any still-unspecified verification transition remains subject to the gap protocol.

**Original decision retained for context:**

### 4. Verification boundary remains unresolved

Aggregate verification state when predecessors differ is not decided. A merge
whose predecessor beliefs for a resulting belief carry differing verification
states is refused before append. The entire merge refuses; it does not publish
only the outputs whose states happen to agree. Replay also refuses such an
unsupported transition rather than inventing a result.

No minimum, maximum, or preferred-predecessor rule is implied. Dependent
implementation remains blocked pending a separate decision. This refusal does
not add a verification state or conflate verification with conflict resolution.
Agreement between predecessor states does not authorize promotion: Invariant 15
and the existing gated-promotion requirements remain in force. Any other
unspecified verification transition remains subject to the gap protocol.

### 5. Lineage covers ancestry and result

For the new cross-belief projector, each changed belief's view_version_hash is a
SHA-256 commitment to one canonical structured lineage record. That record
contains a lineage-format discriminator, the projector version, the producing
event ID and event hash, predecessor dependencies identified by belief ID and
pre-event lineage hash, and the complete resulting event-derived belief content.
Structured serialization supplies field boundaries; predecessor hashes are not
concatenated in incidental traversal order.

For a newly created belief, predecessor dependencies are all the beliefs from
which it results. For an existing belief changed by the event, its own pre-event
lineage is included. A belief with no predecessors has an empty dependency
collection. Dependencies refer to pre-event versions, avoiding cycles between
beliefs changed by the same event. Newly historical b-M and b-C therefore cover
their own prior versions; b-N covers their pre-event versions, not their newly
historical hashes.

Result coverage includes belief ID, subject, property, lifecycle status and
explaining identity relationships, predecessor links, candidate values and their
observation times, resolution status, verification information, evidence event
IDs and their claim associations, source information used in the result,
provenance paths, and event-derived timestamps. Referenced observation and
identity-event dependencies are identified by event ID and event hash so their
recorded contents are covered as well as their names. Relationships stored outside
a belief row remain part of this logical content where they explain that belief.

Evidence IDs are deduplicated within each evidence pool before counting. Distinct
provenance paths are retained separately. Dropping a candidate or provenance path,
or moving an event's support from one candidate to another, changes the covered
result even if the predecessor hashes remain the same. A merge event contributes
identity provenance; it is not counted as a new property observation.

An unchanged-value belief moved to a new subject has new lineage covering its new
ID, subject, and predecessors. Unrelated beliefs do not advance their lineage
merely because the reducer can read them. The producing event's global log-chain
commitment does not replace the explicit affected-belief dependencies.

### 6. Canonical serialization

Lineage uses the shared canonical JSON discipline in src/nyx/hashing.py: sorted
object keys, compact separators, preserved Unicode strings, and UTF-8 bytes for
hashing. It introduces no separate serializer and does not normalize recorded
timestamp strings or other recorded values.

Collections whose meaning is a set are serialized in ascending order of their
canonical UTF-8 representation. This applies to predecessor dependencies,
candidate collections, evidence collections, and collections of provenance paths.
Evidence membership is deduplicated by event ID per pool before serialization;
distinct paths to that event are not collapsed. Repeated identical set members
do not introduce additional membership. Sequences with semantic order retain it:
log events retain log order, and the edges within a provenance path retain path
order. Object-key sorting alone is not sufficient to canonicalize arrays.

The same rules govern the corresponding collections in the projected result,
not only a temporary hash input. Query order and container iteration order cannot
change output bytes. The lineage hash field itself is excluded from its own
input. Exact public API names and physical table layout are implementation
matters; they cannot alter this logical dependency and serialization contract.

### 7. Lineage is separate from whole-view equality

Lineage describes event-derived contents and ancestry. projected_as_of and other
fields derived solely by evaluating at T are not lineage inputs. Changing only
the evaluation time does not create another event in a belief's ancestry.
Event-derived timestamps remain covered.

ADR 0012's equality contract remains complete-view equality at the same explicit
T, log cutoff, and projector version. It includes projected_as_of and every other
projected field, whether covered by lineage or computed at evaluation time.
Matching lineage hashes does not establish that equality. Future time-dependent
behavior is evaluated at T, not relabeled. Lineage is not a freshness checkpoint.

### 8. Append freshness and derived progress

Append-side freshness records identify what has committed to Layer A. They are
updated with the envelope and payload in the append transaction, as required by
the existing architecture. Their affected coverage includes identity changes;
the skeleton's single belief_id standing in for an entity is insufficient.

Derived progress identifies the ordered log prefix actually materialized under
a specified projector version. It is a separate record, advanced only with the
complete derived publication. Progress uses explicit log position and event
identity; a lineage digest is not compared for equality with latest_event_hash
to infer that an event was applied. Recording time alone is insufficient because
several events may have the same recorded_at.

Readers must not present an older materialization as current merely because its
rows exist. Identity lookups and cached successor answers participate in this
freshness requirement. Ordinary reads retain the existing stale-label behavior
and do not trigger reconstruction on every read.

### 9. Atomic derived publication and recovery

The complete event delta, affected materialized indexes and resolution caches,
lineage values, and derived progress are published in one transaction. Readers
must observe a consistent publication, not a mixture assembled across its
boundary. No progress marker may claim completion while part of the delta is
missing. The append and its freshness updates remain a separate earlier
transaction; projection is not moved into the append transaction.

Acceptance under the snapshot boundary requires derived progress at the actual
pre-append prefix, so an append refuses while publication is behind. This couples
append ordering to materialization without moving projection into the append
transaction. An asynchronous worker running behind therefore blocks appends until
it catches up.

A crash after append leaves a durable accepted event and an older derived view.
Recovery remains full replay from Layer A in log order. It reconstructs identity
membership at each event, validates recorded output associations, and reproduces
the same IDs and complete results. Recovery does not trust a partial derived
snapshot or use today's identity mapping to reconstruct an earlier merge.

A crash during derived publication exposes no committed partial delta. A crash
after publication but before worker acknowledgement must not allocate new IDs,
duplicate relationships, or append a second identity event. Recorded event
identity and atomically published progress distinguish application from retry.
A resumable recovery checkpoint is a later optimization; this decision does not
authorize recovery from an unproven partial snapshot.

### 10. Version isolation

The cross-belief reducer and lineage contract require a new registered projector
version. Version "0" retains its existing supported-event semantics and lineage
rules, including ADR 0003's genesis behavior. It refuses unsupported identity
events loudly; it neither skips them nor silently selects a newer projector.
An unknown projector version also refuses under ADR 0010.

The new version replaces the one-belief fold shape and single-prior lineage rule
for its own execution. Layer A event hashing is unchanged. Historical evaluation
uses the requested version and recording-time cutoff; new semantics are not
silently installed into an old version.

## Consequences

ADR 0008's coupled shape and lineage blocker is resolved by this decision. Its
warning against ad hoc per-belief merge handling remains satisfied by the single
complete event delta. ADR 0013's identity semantics remain in force.

This is not implementation of merges, splits, recovery, or a new projector. It
does not settle differing-predecessor verification semantics, a migration
framework, or unrelated event handlers. The explicit verification refusal and
the gap protocol remain implementation boundaries. No database schema version is
changed by this document.

## Acceptance cases

The grounding log is ADR 0013's A/B/C example: e-1 reports 64 through m-A; e-2
reports 64 with established applicability through m-B and m-C; e-3 reports 128
through m-C. merge-1 creates M/b-M from A/b-A and B/b-B; merge-2 creates N/b-N
from M/b-M and C/b-C. The successful merge fixtures use agreeing predecessor
verification states. The differing-state case is tested separately.

- **Replay-time membership:** after recording the later split, replay merge-2
  using M={m-A,m-B} and C={m-C}. Today's L/R mapping cannot change its affected
  set, output IDs, provenance, or lineage.
- **Complete first merge:** merge-1 creates the recorded M/b-M IDs and retires
  the participating predecessors. An additional unchanged-value property on A
  receives its recorded new belief ID and lineage when its subject becomes M.
  C and unrelated entities retain their beliefs and lineage unchanged.
- **Recorded ID validation:** independently test a missing output, extra unrelated
  output, reused historical ID, duplicate within-scope ID, wrong subject, wrong
  property, and wrong predecessor assignment. Each refuses before append without
  mutation. A different fresh opaque spelling with correct associations is valid.
  Replay uses the recorded IDs exactly.
- **Second merge delta:** merge-2 creates N/b-N, retires M/C and b-M/b-C, changes
  all three mention associations, and preserves predecessor and successor paths.
  b-N exposes 64 and 128 without a scalar winner. The caller performs no semantic
  completion beyond persisting the computed delta.
- **Evidence and provenance coverage:** b-N's pooled history contains three
  observation events, not four. Both e-2 paths survive; e-3 supports 128, not 64.
  Holding predecessor hashes fixed while removing a path or changing a candidate's
  support association changes the result commitment. Source independence remains
  separate from event counts.
- **Differing verification states:** change one contributing predecessor's state.
  The entire merge refuses before append without mutation, including otherwise
  acceptable outputs. Replay refuses an injected unsupported transition. No
  minimum, maximum, preferred-predecessor, or conflicted-state fallback occurs.
- **Canonical order:** vary enumeration order for beliefs, predecessor sets,
  candidates, evidence, and collections of paths. Complete output bytes and
  lineage match. Preserve edge order inside each path and log event order;
  those are not arbitrarily sorted. Recorded timestamp strings are unchanged.
- **Split refusal:** omit m-C, duplicate a mention assignment, or supply a complete
  partition whose spanning observation lacks established claim applicability.
  Each refuses before append and leaves b-N and its lineage unchanged.
- **Accepted split:** with established applicability, assign m-A to L and m-B/m-C
  to R. Use the recorded successor entity and belief IDs with b-N predecessor
  links; do not revive b-A/b-B/b-C. Resolve N to multiple explained successors.
  The resulting beliefs share ancestry but their distinct subjects, IDs, and
  evidence assignments are covered by their respective lineage records. Shared
  observation support remains one event per applicable pool.
- **Historical and whole-view equality:** compare complete incremental evaluation
  and full replay before and after each accepted identity event at shared T and
  version. Before merge-1 show A/B/C; before merge-2 show M/C; before the accepted
  split show N's conflict. Different projected_as_of values fail whole-view
  equality even when lineage matches. Time-only evaluation does not advance
  event-derived lineage.
- **Separate progress:** after append and before projection, append freshness
  includes merge-2 while derived progress remains before it. Readers identify
  the older materialization as stale. Matching or differing lineage digests are
  not used as substitutes for explicit application progress.
- **Crash boundaries:** crash before append commit, after append, during derived
  publication, and after publication before acknowledgement. Observe no accepted
  event before commit, no partial committed delta, and no progress ahead of rows.
  Full replay after committed append reconstructs the same IDs, relationships,
  conflicts, and lineage without another identity append or duplicate output.
- **Version isolation:** version "0" still reproduces its supported observation
  history. At a cutoff including an unsupported identity event it refuses rather
  than skipping or upgrading. The new registered version processes the supported
  identity log; an unknown version refuses.
