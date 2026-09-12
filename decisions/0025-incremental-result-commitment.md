# ADR 0025: Incremental Result Commitment

Status: Accepted

Date: 2026-09-12

Supersedes: [ADR 0014 section 5](0014-cross-belief-reducer-and-hash-lineage.md#5-lineage-covers-ancestry-and-result), only the full serialization of accumulated collections in the new projector's lineage. Its complete logical coverage and ancestry requirements remain unchanged. Also supersedes [ADR 0017](0017-schema-version-3.md), only the supported database schema version, for the storage representation required below.

Related: [ADR 0012](0012-whole-view-equality.md); [ADR 0015](0015-candidate-scoped-verification.md); [ADR 0023](0023-stage-two-contract.md); [ADR 0024](0024-no-authoritative-head.md); [ADR 0026](0026-usage-is-not-evidence.md)

Implementation: Implemented under projector "2" in `src/nyx/merkle.py`, `src/nyx/committed.py`, `src/nyx/committed_storage.py`, and the projection/storage writer dispatch. Schema version 4 is required. Acceptance coverage is in `tests/test_incremental_commitment.py`; the measured comparison is in `README.md`. Projectors "0" and "1" remain frozen.

## Context

The lineage probe measured 215,970,530 cumulative bytes for 512 observations on
one belief; the final record alone was 841,017 bytes. Event dependencies account
for 56.54% of the cumulative material and candidates for 43.24%. Snapshot string
reuse reduced elapsed time, but both accumulated collections still grow and are
serialized repeatedly. Candidate coalescing would not remove the larger term.

The commitment change alone does not remove the measured growth: publication
currently serializes the complete belief and the reducer rebuilds its collections.
A representation that stops rewriting accumulated collections is part of this
decision, not a later optimization.

## Decision

### 1. Version and semantic scope

Register projector "2" for the stage-two event and read semantics of ADRs
0019–0024 with the commitment and storage rules below. Event envelopes, payloads,
Layer A hashes, recorded IDs, candidate verification, refusals, and cutoffs are
unchanged. Projector "1" bytes and semantics are frozen; "0" is also unchanged.
Existing API defaults remain unchanged. Selection of "2" is explicit, never an
upgrade or fallback. No merge, split, correction, approval, or support-attachment
handler is authorized by specifying tree update primitives.
Because versions "1" and "2" accept the same stage-two world events, an append
through either records subject/belief freshness for both. Their derived progress
remains independent, so a materialization pinned to the other version cannot be
silently presented as current. This changes no projected version-"1" bytes.

### 2. Canonical authenticated map

Use a persistent compressed binary radix trie. A map key is a nonempty string.
Its routing bits are the 256 bits of SHA-256 of the UTF-8 canonical JSON encoding
of that string, most significant bit first. Distinct keys with an identical
routing digest refuse; no member silently replaces another through a collision.

All hashes below are lowercase hexadecimal SHA-256 of shared canonical JSON
UTF-8 bytes (sorted object keys, compact separators, Unicode preserved). Nodes
have exactly these encodings:

- Empty: `{"format":"nyx-map/1","kind":"empty"}`.
- Leaf: `{"format":"nyx-map/1","kind":"leaf","key":K,"value":V}`,
  where V is the complete canonical JSON member value, not a mutable reference.
- Branch: `{"format":"nyx-map/1","kind":"branch","bit":B,"prefix":P,"left":L,"right":R}`.
  B is an integer in [0,255]. P is the common routing prefix before bit B,
  represented as 64 lowercase hexadecimal digits with all remaining bits zero.
  L and R are nonempty child hashes; left members have bit B zero and right
  members have bit B one.

A nonempty singleton is a leaf. For two or more members, the root branches at
the first differing routing bit; recursively apply the same rule to each side.
There are no unary branches. This uniquely determines the tree from its mapping,
independent of insertion order, enumeration order, tree allocation, or process.
Branch bit positions strictly increase along a path. The empty hash is implicit
and need not be stored as a node.

Insertion follows routing bits, adds a branch at the first differing bit when
necessary, and replaces only ancestors on that path. Replacing an existing key
replaces its complete value and those ancestors; putting identical content is a
no-op. Deletion removes the leaf and collapses its unary parent. Deleting an
absent key is a no-op. These are representation primitives, not permission to
discard candidates or evidence. Nodes are immutable and addressed by their
hashes. Older roots and unchanged subtrees remain valid.

### 3. Collection keys and coverage

The accumulated collections are `claim_candidates`, `event_dependencies`, and
`identity_records`. Each has its own labeled map root:

- ClaimCandidates use their recorded `claim_candidate_id`. The leaf includes
  the entire candidate: value, scope, standing, support associations, restrictions,
  times, source, predecessors, and ordered provenance paths.
- Event dependencies use recorded `event_id`. Leaves retain the complete
  dependency object, including its event hash, envelope, and payload. This ADR
  does not reduce them to references or change redaction treatment.
- Identity records use the canonical JSON string of the complete identity
  record as their key and that complete record as their value. Identical records
  are set duplicates. A changed record has a different key; replacement of set
  membership requires removing the old member and inserting the new one.

Candidate identity deduplication and merging of distinct paths remain governed
by ADR 0015. Conflicting contents for one immutable event ID refuse. Membership
is deduplicated before any evidence count. Recorded sequence order is preserved;
set-valued fields retain ADR 0014 section 6's canonical ordering. Full logical
reads reconstruct the three collections and sort their members by canonical UTF-8
bytes, as before. No value-based candidate coalescing is introduced.

`collection_roots` maps those three exact names to their hashes. `result_root`
is the hash of `{"format":"nyx-result/1","collections":collection_roots}`.
Changing a candidate, a provenance path, or a support association changes the
corresponding leaf, collection root, and result root. Dropping a member also
changes the root. Relationships outside a belief row still enter its relevant
collection. Complete logical coverage under ADR 0014 section 5 is preserved.

### 4. Lineage record

The canonical lineage object has exactly these fields:

- `lineage_format`: `"nyx-belief-lineage/2"`.
- `projector_version`: `"2"`.
- `producing_event`: event ID and event hash, as in version "1".
- `predecessors`: the same canonical collection of belief IDs and pre-event
  lineage hashes required by ADR 0014. An existing belief includes its own prior
  lineage; a new belief without predecessors has an empty collection.
- `result`: the complete resulting belief fields except the three accumulated
  collections, `view_version_hash`, `projected_as_of`, and the two commitment
  metadata fields `collection_roots` and `result_root`.
- `collection_roots` and `result_root`: as specified above.

`view_version_hash` hashes this object. This retains ancestry and commits to the
complete result; it is not delta-only lineage. Changing only evaluation time
does not change lineage. Belief predecessor links and all other event-derived
fields remain covered. Complete-view equality still includes evaluation fields.

### 5. Incremental representation and atomic publication

Store compact belief headers containing scalar fields and commitment metadata,
with the accumulated members stored in immutable content-addressed tree nodes.
Maintain indexed record maps for beliefs, entities, mentions, links, candidates,
events, and the exact current subject/property-to-belief association. The pair
index key is the canonical JSON string `[subject_id,property_id]`. These indexes
are derived and do not introduce logical evidence or replace belief commitments.

Reduction and append validation use indexed lookups against one consistent
pre-event snapshot, not a decode of every stored record. A complete event delta
contains changed headers, records, new tree nodes, and resulting index roots.
Publication writes only changed headers, new nodes, and affected roots; it must
not reconstruct or serialize unchanged accumulated collections. Header lookup
indexes may duplicate compact headers, never the accumulated arrays.

All nodes, headers, roots, and derived progress for an event publish atomically
in one transaction, separate from the earlier Layer A append and freshness
transaction. Node loads validate canonical bytes and content hashes. A missing
or corrupt node refuses; a cached root is not permission to ignore a bad node.
Snapshots returned outside a database transaction must be detached immutable
snapshots. Full collection reads necessarily enumerate requested content, but
ordinary reads do not replay Layer A. Named-candidate reads stay indexed.

New derived node and root tables require database schema version `4`, the sole
supported database schema version. ADR 0011 initialization and validation remain
in force. Existing versions, including `3`, refuse unchanged; no migration,
automatic recreation, or metadata repair is introduced. This compatibility
change does not alter the output contracts of projectors "0" and "1" on a fresh
supported database. Node/root rows are isolated by projector version. This stage
retains created nodes; node garbage collection and resumable recovery checkpoints
are not introduced.

### 6. Proofs, replay, and integrity

An inclusion proof contains the path's branch descriptors in root-to-leaf order.
Each descriptor contains bit, prefix, and left/right child hashes. The verifier
hashes the supplied key and complete value as a leaf, reconstructs ancestors in
reverse order using the key's routing bits, validates increasing bit positions,
prefixes, hash syntax, and child associations, and compares the reconstructed
root to the caller's trusted collection root. The collection root's label and
result-root binding must in turn be checked against trusted lineage. A proof
for another key, value, collection root, or version does not establish membership.

A root supports inclusion proofs against a trusted root; it does not verify all
stored content by reading one hash. Checking all stored content requires visiting
that content. Checking whether the reducer produced the correct state still
requires replay or another semantic procedure. Roots do not establish world truth,
source independence, freshness, or freedom from omitted logical dependencies.

Full-replay recovery starts from Layer A and empty trees, ignoring derived rows
and roots. It reproduces recorded IDs, every logical field, canonical collection
roots, and lineage at each cutoff. Compare complete incremental/materialized
results with independent replay at shared evaluation time. Independently rebuild
roots from full logical collections in acceptance tests so cached roots are not
their own oracle. Retain version "0" and "1" byte fixtures, test time-only
evaluation, and inject missing/corrupt nodes and failures throughout publication
and recovery. Failed publication or recovery must expose no partial result.

### 7. Complexity and measurement

This is not an O(1)-write claim. A bounded change in a logarithmic-height tree
costs O(log n) path work plus the changed bytes. This compressed hash trie has
typical O(log n) height for distributed SHA-256 routing keys and an explicit
maximum of 256 branch levels; it does not promise worst-case logarithmic height
for adversarial key distributions. Let h be actual height and k the number of
changed members: path work is O(kh), plus serialization of changed values and
database index costs. Merges, splits, and support restrictions can touch many
records. Rewriting an unbounded value within one leaf is not a bounded change.

Complete logical reads and exhaustive integrity checks remain proportional to
content. Immutable nodes retained over many updates consume space; a compact
lineage record alone is not a storage-size measurement. The probe must report
outer lineage bytes separately from newly serialized node/publication material,
compare the same stage-two workload under versions "1" and "2", and include
actual database publication measurements. A smaller outer hash input without
removing accumulated collection rebuilds does not satisfy this decision.

## Acceptance cases

- Same mapping in different insertion orders yields identical roots; Unicode,
  empty/singleton cases, replacements, deletion and reinsertion are deterministic.
- Candidate, path, support-association, event-content and identity-record changes
  alter the appropriate root with predecessor lineage held fixed.
- Valid proofs verify; altered values, keys, branches, roots and malformed proofs
  refuse. Comparing a stored root alone is not reported as a content audit.
- Stage-two acceptance and refusals agree with version "1"; complete logical
  results agree apart from version-specific lineage hashes. No head is selected.
- Incremental, database materialization and full replay agree at every tested
  prefix, including mention-only, multi-belief and multi-claim events.
- Publication serializes changed members and paths only. Increasing prior
  history cannot cause whole-collection reconstruction on the write path.
- Freshness, retries, concurrency, crash boundaries and recovery preserve the
  existing atomic-prefix contract, including corrupt derived data.
- Version "0" and "1" bytes remain fixed; unsupported events/versions refuse;
  schema-version-3 databases refuse without mutation.

## Consequences

The commitment remains a result-and-ancestry commitment while its physical cost
tracks changed paths. Tree format and version compatibility are now explicit
contracts. Candidate retention, authority, temporal resolution, and remaining
stage-three semantics are not decided here.
