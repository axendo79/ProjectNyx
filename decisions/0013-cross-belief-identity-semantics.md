# ADR 0013: Cross-Belief Identity Semantics

Status: Accepted

Date: 2026-09-08

Related: [ADR 0008](0008-fold-signature-cannot-express-cross-belief-events.md); [ADR 0010](0010-projection-parameters.md); [ADR 0012](0012-whole-view-equality.md); Invariants 9 and 15

Implementation: Pending; implementation is a separate task.

## Context

Entity merges and splits affect multiple beliefs. Before the reducer shape and
hash lineage can be decided, the identity, evidence, and conflict semantics of
those transitions must be explicit. Repeated merges can expose several provenance
paths to one observation. Splits can assign every mention while leaving the
applicability of an observation to a successor's claim unresolved.

Identity bookkeeping must not manufacture evidence, choose an unsupported value,
or silently assign evidential support. These semantics resolve that prerequisite
to the cross-belief work flagged by ADR 0008.

## Decision

### 1. Entity and belief identity

Entity IDs and belief IDs are distinct. A merge creates a new entity ID. Every
resulting belief whose subject changes to the new entity receives a new belief ID,
with predecessor links to the beliefs from which it results. This includes a
belief whose value and evidence are unchanged: its subject association changed.
Beliefs belonging to unrelated entities retain their IDs.

The same subject-change rule applies to beliefs resulting from a split. Historical
belief IDs are not repurposed as newly current beliefs. Predecessor links preserve
the history through repeated merges and splits.

### 2. Split-successor resolution

Resolving a historical identity returns a structured result distinguishing a
unique current successor, multiple current successors, and no current successors.
The result includes successor IDs and the identity events explaining the paths.
Operations requiring one current entity refuse a multiple-successor result until
the caller specifies the intended successor; no successor is chosen silently.
Historical IDs remain valid for historical queries.

### 3. Evidence identity and counting

Evidence is deduplicated by event ID before every count, within the evidence pool
being counted. Deduplication is not a global allowance that consumes an event when
it is used for one claim and prevents its use for another supported claim.

Distinct observation events, provenance paths, and independent corroborating
sources are three separate quantities. Multiple paths to one event remain
available as provenance but do not create additional observations or independent
corroboration. Distinct event IDs alone do not establish source independence; the
existing source-class rules remain in force.

### 4. Conflicting values

Conflicting values after a merge produce an explicit conflict result containing
the candidate values and their evidence and provenance, with no authoritative
scalar. A caller requiring a single scalar receives a refusal rather than an
arbitrarily selected candidate.

A merge is an identity event, not a new measurement. The existing value-recency
rule does not by itself resolve a conflict created by merging previously separate
subjects. Neither the merge timestamp nor choosing the latest observation across
the predecessors silently selects a winner.

Resolution status and verification state are separate axes. No `conflicted`
member is added to the verification-state enumeration. Verified observations can
coexist with an unresolved conflict; their verification does not establish one
verified current scalar answer. Invariant 15 remains in force: reinterpretation
may hold or demote, never directly promote. A would-be promotion from pooled
evidence follows the normal gated promotion path.

### 5. Split completeness and spanning observations

An accepted split validates an exact partition of the mentions associated with
the identity immediately before the event. Every such mention is assigned to
exactly one declared successor. Omission, duplicate assignment, and assignment of
an unrelated mention are refused at append. Completeness is checked against the
pre-event identity, not merely the mentions listed in the split payload, and not
all mentions ever historically associated with its predecessors.

A spanning observation may be linked to multiple successors as provenance. A
provenance link is not evidential support. Where existing records do not establish
how the observation applies to a successor's claim, the accepted split refuses
at append. Complete mention assignment alone does not satisfy this requirement.
No support is invented, assigned arbitrarily, silently discarded, or copied to
both successors merely because the observation references both.

Where the records establish support for claims on multiple successors, the same
immutable observation event may support each applicable claim. Each evidence pool
deduplicates that event by ID; the resulting provenance paths are not independent
corroboration. A later merge of those pools still counts the event only once.

## Worked grounding

The IDs below name example records, not an ID-generation scheme. All times are
recording times on the same day, in increasing log order.

### First merge

Before `merge-1` at 10:00, the RAM beliefs are:

| Belief ID | Entity ID | Current value | Observation history | Provenance |
| --- | --- | --- | --- | --- |
| b-A | A | 64 | e-1: 64 at 09:00 | e-1 through m-A |
| b-B | B | 64 | e-2: 64 at 09:05 | e-2 through m-B |
| b-C | C | 128 | e-2: 64 at 09:05; e-3: 128 at 09:10 | e-2 and e-3 through m-C |

The example records establish e-2's applicability to the claims on B and C.
It is one observation event with multiple provenance paths. Retaining e-2 in
C's observation history does not make it evidence for the value 128.

`merge-1` merges A and B into new entity M. The resulting RAM belief b-M is new,
with predecessors b-A and b-B, value 64, and evidence events {e-1, e-2}. Both
provenance paths are retained. b-A and b-B remain historical. b-C remains on C
with the same ID, value, observation history, and provenance: sharing an evidence
event does not make C a participant in the identity merge.

Any additional property belief on A or B also receives a new belief ID when its
subject becomes M, even if its value and evidence are unchanged. An unrelated
entity's belief retains its ID.

### Second merge with overlapping evidence

`merge-2` at 11:00 merges M and C into new entity N. Its new RAM belief b-N has
predecessors b-M and b-C. Pooling {e-1, e-2} with {e-2, e-3} produces three distinct
observation events, not four. The separate routes to e-2 remain in provenance.
The number of independent corroborating sources is determined separately.

The result explicitly retains the conflicting 64 and 128 candidates and their
support histories, with no authoritative scalar. e-3 remains the observation of
128; `merge-2` does not become another RAM observation and does not settle the
conflict by recency. b-M and b-C remain historical, and the predecessor paths
through `merge-1` remain available.

### Split of the merged belief

Before a split at 12:00, N has mentions {m-A, m-B, m-C}. A payload assigning only
m-A to L and m-B to R omits m-C and is refused. In particular, e-3 is not copied
to both successors to conceal the omission. No accepted split is appended and
b-N remains unchanged.

A complete assignment m-A to L and m-B plus m-C to R satisfies the mention
partition requirement. It is accepted only if the existing records also establish
the applicability of the observations to the successor claims. Resulting beliefs
whose subjects change receive new IDs with predecessor links to b-N; old b-A,
b-B, and b-C are not revived as current records.

For a spanning observation whose recorded support establishes a claim on both
L and R, both may retain that support under the same event ID. If the observation
only mentions both subjects without establishing its support for their claims,
the complete mention partition does not cure the ambiguity and the split refuses.

After an accepted split, resolving N returns multiple current successors L and R
with the split event explaining the paths. A request requiring one entity refuses
that result until a successor is specified.

## Historical evaluation and version scope

At a cutoff before `merge-1`, replay produces the separate A, B, and C beliefs.
Between `merge-1` and `merge-2`, it produces M and C. Between `merge-2` and an
accepted split, it produces N with its conflict. A refused split has no effect on
any cutoff. Historical identity queries retain the IDs and associations valid at
the requested cutoff; later successor relationships do not rewrite earlier views.
The inclusive recording-time cutoff and shared evaluation-time rules of ADRs
0010 and 0012 remain in force.

This decision does not retrofit these semantics into projector version "0" or
select a new projector version. A caller pinned to "0" must not silently receive
new identity semantics or have an unsupported identity event silently omitted.
The versioned implementation belongs to the follow-on work.

## Consequences

These rulings settle identity semantics without selecting a reducer signature,
return shape, payload schema, ID-generation scheme, or hash-lineage formula.
The reducer shape and hash lineage require a separate follow-on decision together.
ADR 0008 remains open for them; this ADR does not supersede or close that blocker
and does not authorize working around the current one-belief fold.

Layer A remains append-only. Historical records and evidence event identities
are preserved. The structured resolution and conflict results are semantic
contracts, not a choice of API encoding. Implementation is a separate task.

## Acceptance cases

- **First merge and ID scope:** execute the A/B example. M and b-M have new IDs;
  b-M links to both predecessors and retains value 64 and {e-1, e-2}. An additional
  property on A receives a new belief ID even with unchanged value and evidence.
  C's b-C and an unrelated entity's beliefs retain their IDs and contents.
- **Repeated merge:** execute `merge-2`. N and b-N have new IDs, predecessor links
  reach b-M and b-C, and the earlier b-A/b-B paths remain traversable. No historical
  belief ID is reused as the current result.
- **Overlapping evidence:** {e-1, e-2} plus {e-2, e-3} counts as three observation
  events in the pooled history. Both e-2 provenance paths remain visible. Counts
  for a particular candidate include only events supporting that candidate.
- **Source independence:** two distinct observation events from one source class
  remain two events but do not count as two independent corroborating sources.
  Adding another provenance path changes neither count.
- **Explicit conflict:** b-N exposes the 64 and 128 candidates with their evidence
  and provenance and no authoritative scalar. A scalar-only request refuses.
  Neither e-3's later time nor `merge-2` supplies a silent winner. No `conflicted`
  verification state is introduced and no merge-driven promotion occurs.
- **Incomplete or invalid partition:** omission of m-C, assignment of one mention
  to multiple successors, duplicate assignment, an unrelated mention, or an
  undeclared destination each causes refusal at append without changing the log
  or current beliefs. A payload listing only its own subset does not prove
  completeness.
- **Pre-event membership:** validate the exact current mention set before the
  split. A mention associated only with a historical predecessor is not required
  merely because it appeared in that predecessor's history.
- **Complete supported split:** provide an exact partition and established support
  assignments. The split succeeds with new IDs for subject-changed beliefs and
  predecessor links. Historical predecessor IDs are not revived.
- **Spanning provenance without support:** provide a complete mention partition
  and an observation mentioning both successors whose applicability to their
  claims is not established. The accepted split refuses without mutation; copying
  provenance links into support sets does not satisfy validation.
- **Spanning established support:** an observation with established support for
  claims on both successors may appear in both claim pools under one event ID.
  It counts once in each applicable pool, not once globally. Re-merging the pools
  counts it once, while retaining both provenance paths.
- **Successor resolution:** exercise unique, multiple, and no-current-successor
  results. Successor IDs and explaining identity-event paths are present as
  applicable. A single-entity operation refuses the multiple result rather than
  selecting its first member. Historical queries still accept historical IDs.
- **Cutoff and replay:** evaluate the example log before each identity event and
  after it. Results preserve the corresponding historical identities, values,
  conflicts, evidence, and provenance. At a shared cutoff and projector version,
  repeated evaluation and replay agree on the complete view without rewriting
  Layer A. A refused split contributes no transition.
- **Version isolation:** a caller pinned to projector version "0" is not silently
  upgraded to these semantics, and an unsupported identity event is not silently
  skipped to return an apparently complete view.
