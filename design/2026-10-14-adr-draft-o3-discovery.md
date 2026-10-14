# ADR TBD: O3 Public Mention Discovery in a Same-Database Derived Index

Status: Proposed draft, not ratified, does not authorize implementation

Date: 2026-10-14

Implementation: None. No listing API, search index, schema migration, test or usage recorder is implemented by this design draft.

Supersedes on acceptance: Nothing yet. Proposed database compatibility amendments are limited by the shared V6 contract. Frozen projector semantics, hashes and existing APIs remain unchanged.

Related: [O3 worksheet](2026-10-14-o3-listing-search-worksheet.md), [strict-payload draft](2026-10-14-adr-draft-strict-payload-keys.md), [ADR 0010](../decisions/0010-projection-parameters.md), [ADR 0011](../decisions/0011-database-schema-versioning.md), [ADR 0012](../decisions/0012-whole-view-equality.md), [ADR 0013](../decisions/0013-cross-belief-identity-semantics.md), [ADR 0014](../decisions/0014-cross-belief-reducer-and-hash-lineage.md), [ADR 0015](../decisions/0015-candidate-scoped-verification.md), [ADR 0019](../decisions/0019-identity-bootstrap.md), [ADR 0021](../decisions/0021-bootstrap-link-treatment.md), [ADR 0022](../decisions/0022-belief-container-uniqueness.md), [ADR 0023](../decisions/0023-stage-two-contract.md), [ADR 0024](../decisions/0024-no-authoritative-head.md), [ADR 0025](../decisions/0025-incremental-result-commitment.md), [ADR 0026](../decisions/0026-usage-is-not-evidence.md), [ADR 0030](../decisions/0030-sole-writer-and-positional-fields.md), [ADR 0031](../decisions/0031-source-report-claims.md), [ADR 0032](../decisions/0032-explicit-stage-two-projector-selection.md), [ADR 0034](../decisions/0034-forward-state-transitions.md), [ADR 0035](../decisions/0035-adr-0034-implementation-boundaries.md).

## Context

Baseline: worksheets branch commit `165363d`, based on `5acc188`. Named typed
reads and complete snapshot enumeration ship, but callers have no public listing
or mention-text discovery contract. Full snapshots are not bounded indexed pages.
Mention-only subjects are real recorded entities; joining only beliefs loses them.
Identical mention text can name distinct scoped subjects. Matching is discovery
of recorded associations, never a canonical identity or winning claim.

Josh's 2026-10-14 ruling in
`D:\ProjectNyx\scratch\nyx-ruling-2026-10-14-c-b.md` selects worksheet option B,
for Proposed drafting only: a public same-database index published with the
complete derived delta. Unapproved worksheet answers remain recommendations.
MUST clauses below define the proposed acceptance contract, not authority to code.

## Maintainer rulings carried into this draft

1. **R-O1 — Total order and stable pagination:** include an explicit tie-breaker
   and define continuation. O5-O6; acceptance A4.
2. **R-O2 — Projection changes:** invalidate cursors or retain a real snapshot;
   never silently skip or duplicate. Recommend restart on changed publication,
   with no retained snapshots. O6; A4/A5.
3. **R-O3 — Unavailable versus empty:** missing index is unavailable; a valid
   zero-match search is empty. O3/O7/O9; A3/A7.
4. **R-O4 — Replay:** index construction is deterministic/verifiable; identical
   input and projector yield logically identical results at the same index format.
   O8-O10 and shared V5; A6/A7.
5. **R-O5 — Page limits:** 100 default, 1,000 maximum, explicitly subject to
   worksheet confirmation. O5 and conflict Q12; A3. They remain proposed limits.
6. **R-O6 — Preserve every matching mention:** no canonical entity, deduplication
   by text/value or truth selection. O1-O4; A1/A2/A8.
7. **R-O7 — No read side effects:** no usage/exposure records or other search
   mutation. O11 and shared V3/V8; A9.
8. **R-O8 — Scope/review:** preserve history and old projectors; cover failure,
   compatibility/replay; review all worksheet answers and strict-projector
   interaction. O8-O12, shared V1-V9, conflict review and A5-A12.

## Shared version boundary by reference

Adopt the **single shared section V1-V9** in the
[strict-payload draft](2026-10-14-adr-draft-strict-payload-keys.md#shared-version-boundary).
This is the same recommended contract S1 references there, not a second version.
It separates the index format from belief-projector semantics, proposes schema 6
and isolated "2"/"3"/"4" rows, and specifies ingestion, enrollment, atomic
publication, mixed-log refusal, replay, working-copy migration and recovery.

O3 on "2"/"3" does not require strict payload admission, and O3 backfill never
strict-validates old envelopes. Strict "4" operates with O3 disabled; enrolled
"4" publishes strict projection and index together. O3 under "2"/"3" is
unavailable after a strict-schema append under V4; old rows survive, and "4"
handles the mixed history. Frozen replay may refuse unknown formats even beyond
an earlier cutoff. Both decisions must approve the single proposed schema-6
layout before implementation; none of these identifiers is reserved here.

## Proposed discovery contract

### O1. Corpus, identity and evidence boundary

Index only the already permitted public corpus, under ADR 0031 section 7.
Permission to copy mention text is not proof that a readable local artifact is
public. Preserve existing report-admission restrictions and managed-copy inventory.
No new private-data classifier, encryption, erasure mechanism or report importer
is supplied. Proposed [ADR 0027](../decisions/0027-stage-three-authority-and-acceptance.md)
and Proposed [ADR 0028](../decisions/0028-redaction-and-crypto-shredding.md) remain
unratified; the public-only restriction is not lifted by this decision.

Every result is a typed recorded ID/association. Subject/mention/belief/candidate
scopes never cross-resolve even with identical spelling. Property IDs are exact
opaque strings, not a registry. Matching text, paths, ADR numbers, proximity,
recency, source counts or index order establishes neither identity equivalence
nor corroboration/standing. Read/search creates no gap/absence event.

Return every matching mention once by mention ID. Identical text on different
subjects yields separate hits; multiple properties on one subject do not multiply
its mention hit. Preserve all recorded candidates and provenance through named
details, including disagreeing/agreeing candidates and "3"/"4" live/retained
sets with ending relations. No canonical/winning value or scalar selection is
added. Discovery is an index of mentions and associations, never a truth mechanism.

### O2. Operations and scope

Proposed new read-only Python operation shapes, with keyword-only arguments:

| Operation | Required inputs beyond connection | Optional inputs |
|---|---|---|
| `list_subjects` | `projector_version` | `lifecycle="all"`, `page_size=100`, `cursor=None` |
| `list_mentions` | `projector_version` | `subject_id=None`, lifecycle/page/cursor as above |
| `find_mention` | `text`, `mode`, `projector_version` | `subject_id=None`, lifecycle/page/cursor as above |
| `list_properties` | `projector_version` | `subject_id=None`, lifecycle/page/cursor as above |
| `list_beliefs` | `projector_version` | `subject_id=None`, `property_id=None`, lifecycle/page/cursor as above |

There is no projector default. Support "2"/"3", plus "4" only with the shared
strict bundle; "0"/"1"/unknown selection refuses before work. Names above are
proposed API contract. Any new CLI mirrors these semantics, requires
`--projector-version`, and keeps the existing inspection CLI's defaults intact.

A supplied scope ID/property must be a nonempty string in its declared scope;
`None` means unfiltered, never a wildcard. No trimming or alias resolution.
`lifecycle` accepts exactly `all` or `current`; recommend `all` as default.
This is subject/belief lifecycle, never a ClaimCandidate "current" flag.

- Subjects include every recorded subject, including mention-only subjects.
- Mentions include each recorded mention with its subject ID, recorded text,
  recording event ID and associated subject lifecycle. Mentions have no invented
  independent lifecycle; a `current` filter tests the associated subject.
- Properties return distinct exact property IDs among matching belief containers
  in the selected subject/lifecycle scope. Global listing deduplicates exact
  property strings across subjects; it does not imply one shared belief.
- Beliefs expose ID, subject, property and recorded lifecycle,
  with typed handles for complete candidate/provenance reads at the same prefix.
  Filters constrain containers, never silently discard retained candidates.

A known subject with no matching belief/property yields a successful empty page.
An absent supplied subject yields `unknown_scope`, with the same published-prefix
and global-staleness disclosure. An unrecognized property filter is a valid
zero-match filter, not a registry lookup. A valid global search with no matching
mentions yields an empty page. Do not translate a historical subject to a successor; existing
merge/split/association limitations remain.

### O3. Literal text matching

`mode` is required and exactly `exact` or `prefix`. Text is a nonempty string;
empty input refuses (`invalid_query`). Unfiltered enumeration uses listing calls.
Match exact decoded Unicode sequences, case-sensitive and without normalization.
`exact` is equality; `prefix` is literal starts-with. `%`, `_`, backslash, quotes
and query-like operators are literal characters, not SQL/FTS grammar. NFC/NFD
and case variants remain distinct; supplementary scalars match by their preserved
UTF-8 representation. Report titles/numbers do not acquire a new identity rule.

Operate on UTF-8 byte keys with binary comparison. For encoded prefix P, the
candidate range is `[P, successor(P))`: find its rightmost byte below 255,
increment it and truncate the suffix. If there is none, the upper bound is absent.
An upper bound need not itself be valid UTF-8. Verify literal starts-with for
returned text. Do not use default SQLite LIKE/collation to approximate the rule.
Text/IDs that cannot encode under the accepted UTF-8 hashing contract refuse
rather than being normalized or replaced; this adds no private-codec domain.

### O4. Result and publication metadata

Every successful page has `format="nyx-o3-page/1"`, `status="ok"`, `items`,
`returned_count`, `end` and `next_cursor` (null at end), with metadata containing:

- selected projector and index format;
- applied log position, event ID and event hash (0/null/null for ready genesis);
- append-tip position, event ID and hash, read in the same transaction;
- global `stale = applied_position < tip_position` after anchor validation;
- exact operation/scope/filters/text/mode and the declared order.

Do not include candidate values, source free text or derived snippets in the
index/page. Mention text is the only copied payload free text. Result IDs/event
references permit provenance traversal; report values retain the meaning
"artifact at revision stated X" when read through existing details.

`returned_count` is this page's count, not an uncomputed total. `end=true` with
zero items is a valid complete empty result **at that published prefix**. A stale
empty result does not say no match exists at append tip. Even fresh empty means
absence only from recorded query scope, never absence in the world.

Page contents, joins, applied prefix, current tip and cursor check come from one
SQLite read transaction per request. No read transaction remains open between
pages. Detail traversal must carry the returned prefix handle: a new adapter
returns same-prefix details or `restart_required` if publication advanced, never
labels newer details with an older search prefix. Existing named APIs are not
silently given this new argument/behavior. Specialized report-reader guards stay
"1"/"2"; generic candidate details do not broaden them.

### O5. Total ordering and limits

**Recommended ordering change from worksheet Q9, requiring confirmation:**
listings sort by ascending UTF-8 bytes of their relevant ID (subject, mention,
property or belief). Matching search sorts by `(mention_text_utf8, mention_id_utf8)`.
The mention ID is the explicit final tie-breaker for equal text, never subject,
value, ranking or recency. Listing IDs are unique in each selected scope; append
the same relevant ID as the final key if a future display field is introduced.
New display sorting would require a new query/order version, not a silent change.

Thus the search key is unique, even with equal text/timestamps. Row identity is
(projector, kind, relevant exact ID); filtering/joining cannot duplicate it.
Property listing emits distinct property IDs before pagination. No sort changes
canonical candidate collections, evidence order or recorded identity.

Recommend `page_size=100`; maximum 1,000, still subject to worksheet confirmation.
Require an actual integer 1..1,000 (booleans are not sizes). Oversized, fractional,
zero, negative or malformed sizes refuse; never silently clamp. Fetch one extra
eligible row to determine continuation; return at most page_size rows. Page size
bounds response size, not a universal latency, bytes or examined-row guarantee.

### O6. Cursor binding and publication change

Use keyset continuation, never offsets. Proposed cursor encoding is unpadded
base64url of canonical JSON with exactly `format`, `query`, `genesis`, `prefix`
and `last_key`. Require canonical encoding on decode (including lowercase hex
keys); refuse equivalent but differently encoded tokens. `genesis` has exactly
`event_id` and `event_hash`; `prefix` has exactly `log_position`, `event_id` and
`event_hash`. Empty-prefix nulls follow O4; positive hashes use the accepted
lowercase SHA-256 syntax. The query descriptor has defaults explicitly populated,
without normalizing any user string.
The query descriptor includes operation, exact scope/filters/text/mode, page size,
projector, index format, order name, source (`live` or `replay`) and `as_of`
(null for live, the exact explicit evaluation timestamp for replay).
Last keys are arrays of lowercase hex
UTF-8 byte strings: one ID for listings, text plus mention ID for search. The
format is `nyx-o3-cursor/1`; listing order is `id-utf8/1`, search order
`text-id-utf8/1`. Cursor parsing rejects extra/missing fields, duplicate JSON
members, wrong types, invalid encoding/key arity and mismatched query bindings.
This is cursor-format validation, not a change to old payload parsing.

The exact `query` fields are `operation`, `projector_version`, `index_format`,
`order`, `source`, `as_of`, `subject_id`, `property_id`, `lifecycle`, `text`, `mode`
and `page_size`. Use null for inapplicable optional fields; reject a supplied
filter that the operation does not support. Lifecycle is always explicit, and
replay uses the same operation-specific query descriptor with source/time added.
The canonical serializer is the existing shared one; cursor numbers are only
actual integer page sizes/log positions. No payload numeric domain is changed.

Bind to logical store genesis and exact prefix/event hash, not a pathname.
A byte-identical store copy with the same log is the same logical cursor input;
a cursor does not authorize a writer or claim to detect arbitrary database swaps.
At ready genesis no nonempty page exists and no continuation is issued.
Cursors are opaque checkpoints, not credentials, evidence or usage records;
no signature secret, durable cursor store, expiry clock or cross-call transaction
is proposed. Verify that the last key identifies an eligible row at that prefix;
otherwise refuse `invalid_cursor`. No issued-page provenance is inferred from
possession of a stateless token.

If publication position/event identity changes, return `restart_required` with
new prefix metadata and no items. Never silently restart, continue into newer
rows, reinterpret a cursor for another projector, or claim retained snapshots.
A new append without publication changes tip/staleness only; same-prefix
continuation is allowed and discloses the new tip. Publication at a tied timestamp
still changes log position and invalidates the old cursor. Rebuild at identical
input/prefix/format produces identical logical rows, so continuation may remain
valid; changing format/query/order is a binding failure, not silent conversion.
V4's mixed unsupported-profile state yields unavailable before continuation.

Apply `key > last_key` in the declared total order, after scope/match filtering.
At unchanged prefix, concatenating pages equals the complete ordered query result
with no omissions/duplicates. Explicit end is distinguishable from an unavailable
index and from a page that merely reached its limit.

### O7. Availability and failure classification

Validate request grammar/selector first; read supported schema/index metadata,
log profile inventory, anchors and version associations next, then validate
cursor query binding/prefix and scope. A syntactically invalid token is
`invalid_cursor`; an otherwise valid token at missing/incompatible readiness
gets `unavailable`, not restart or empty. Prefix advance gets `restart_required`.
Responses other than `ok` never carry a purported complete successful item page.

| State | Required result |
|---|---|
| Supported, ready, valid index; zero matches | `ok`, empty items/count 0, end true. |
| Ready genesis | `ok` empty, applied 0/null/null; no derived_progress row. |
| Missing tables/readiness, disabled/unbuilt, old schema | `unavailable` with `index_missing`, `index_not_ready` or `schema_requires_migration`. |
| Unknown format, wrong anchor/version, ahead-of-log/projection metadata, detected corrupt row/join | `unavailable` with a specific integrity reason; no rows as empty success. |
| Valid publication behind global append tip | Serve `ok` labeled stale, including stale emptiness. |
| "2"/"3" selected on strict-envelope mixed log | `unavailable: unsupported_log_profile` under V4. |
| Malformed request/limit/mode or token binding | Typed `invalid_query`/`invalid_page_size`/`invalid_cursor`; no mutation. |
| Valid cursor at advanced publication | `restart_required`, no silent skips/duplicates. |
| Supplied absent subject at valid prefix | `unknown_scope`, prefix/global stale metadata retained. |
| Unsupported selected projector/deferred historical semantics/corrupt Layer A | Explicit refusal; no fallback, repair or successful empty page. |

A format/prefix marker establishes publication association, not completeness
against arbitrary corruption. Query checks validate metadata and returned rows;
explicit exhaustive replay verification (O10) detects omitted/extra rows even
when metadata looks intact. This proposal claims neither per-query full-log
verification nor tamper-proof indexes. Detected invalidity makes readiness unusable
until explicit reconstruction; no query writes an invalidation marker.

### O8. Logical index and prospective schema

For one prefix/version define `I = index(replay(raw_log, as_of, projector), format)`.
It contains separate subject membership, mention membership/text/subject joins,
and belief subject/property/lifecycle associations. Do not derive membership by
an inner join through beliefs or copy candidate values/snippets/source text.
All records come from the complete replay snapshot, not incomplete
`projected_mentions` under "2"/"3". Deltas incrementally update the same function.

Propose the following **schema-6 additions**, alongside V6's precise committed
constraint amendment. This is reviewable prospective DDL, not shipped schema.
Columns holding ID keys/text bytes are BLOBs containing exact UTF-8; logical
validation independently checks the associated strings and source records.

```sql
CREATE TABLE o3_builds (
    projector_version TEXT PRIMARY KEY CHECK (projector_version IN ('2','3','4')),
    index_format TEXT NOT NULL CHECK (index_format = 'nyx-o3-index/1'),
    log_position INTEGER NOT NULL CHECK (typeof(log_position) = 'integer' AND log_position >= 0),
    event_id TEXT,
    event_hash TEXT,
    CHECK ((log_position = 0 AND event_id IS NULL AND event_hash IS NULL)
        OR (log_position > 0 AND event_id IS NOT NULL AND event_hash IS NOT NULL))
);
CREATE TABLE o3_subjects (
    projector_version TEXT NOT NULL CHECK (projector_version IN ('2','3','4')),
    subject_id TEXT NOT NULL,
    subject_key BLOB NOT NULL CHECK (typeof(subject_key) = 'blob'),
    lifecycle_status TEXT NOT NULL CHECK (lifecycle_status IN ('current','historical')),
    constituting_mention_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    PRIMARY KEY (projector_version, subject_id),
    UNIQUE (projector_version, subject_key)
);
CREATE TABLE o3_mentions (
    projector_version TEXT NOT NULL CHECK (projector_version IN ('2','3','4')),
    mention_id TEXT NOT NULL,
    mention_key BLOB NOT NULL CHECK (typeof(mention_key) = 'blob'),
    subject_id TEXT NOT NULL,
    text_bytes BLOB NOT NULL CHECK (typeof(text_bytes) = 'blob'),
    event_id TEXT NOT NULL,
    PRIMARY KEY (projector_version, mention_id),
    UNIQUE (projector_version, mention_key),
    FOREIGN KEY (projector_version, subject_id)
        REFERENCES o3_subjects(projector_version, subject_id)
);
CREATE TABLE o3_beliefs (
    projector_version TEXT NOT NULL CHECK (projector_version IN ('2','3','4')),
    belief_id TEXT NOT NULL,
    belief_key BLOB NOT NULL CHECK (typeof(belief_key) = 'blob'),
    subject_id TEXT NOT NULL,
    property_id TEXT NOT NULL,
    property_key BLOB NOT NULL CHECK (typeof(property_key) = 'blob'),
    lifecycle_status TEXT NOT NULL CHECK (lifecycle_status IN ('current','historical')),
    PRIMARY KEY (projector_version, belief_id),
    UNIQUE (projector_version, belief_key),
    FOREIGN KEY (projector_version, subject_id)
        REFERENCES o3_subjects(projector_version, subject_id)
);
CREATE INDEX idx_o3_mentions_text ON o3_mentions
    (projector_version, text_bytes, mention_key);
CREATE INDEX idx_o3_mentions_subject ON o3_mentions
    (projector_version, subject_id, mention_key);
CREATE INDEX idx_o3_subjects_lifecycle ON o3_subjects
    (projector_version, lifecycle_status, subject_key);
CREATE INDEX idx_o3_beliefs_subject ON o3_beliefs
    (projector_version, subject_id, lifecycle_status, belief_key);
CREATE INDEX idx_o3_beliefs_property ON o3_beliefs
    (projector_version, property_key, lifecycle_status, belief_key);
CREATE INDEX idx_o3_beliefs_subject_property ON o3_beliefs
    (projector_version, subject_id, property_key, lifecycle_status, belief_key);
CREATE INDEX idx_o3_event_profile ON events (schema_version);
```

A build row means ready; absence means no ready publication, never genesis.
Rows without readiness are unusable, and initial/disable operations leave no
unassociated rows. Enrolled-version configuration belongs to the explicit owner
(V3), so loss of readiness cannot silently disable its publication obligation.
No o3_builds foreign key forces an invented genesis event/progress row.

For positive position, readiness must equal the selected derived_progress
position/event, and its event hash/ID must match Layer A at that exact position.
At zero, require no selected projection members/roots/relations that would imply
a nonempty applied prefix and no derived_progress row. Metadata ahead of log,
wrong genesis encoding, mixed version joins or inconsistent lifecycle refuses.
Validate nonempty IDs, exact key/string encoding, supported lifecycle, recording
reference and every recorded association; SQL constraints alone are insufficient.

Property rows are a distinct enumeration over `o3_beliefs`, avoiding an extra
registry or property-creation event. Current-only belief uniqueness remains
ADR 0022's authoritative projection constraint; index validation checks it rather
than inventing a new historical uniqueness rule. Subject/mention recording events
come from their record's `event_id`. Beliefs gain no invented birth/last-event
field; named candidate details and recorded dependencies supply their provenance.

The metadata-only event schema index supports V4 mixed-profile refusal through
binary key-range probes below/above the old schema string "0", without decoding
payloads or enumerating full snapshots. It is rebuildable metadata access, not
a discovery fact or alteration of envelope bytes/triggers/hash material.

No build timestamp, random generation ID, read count or clock enters logical
membership. Disabling an index removes only its own ready/row set atomically.
Retained tree nodes and all old version rows stay untouched. Exact addition
layout and identifiers require confirmation with V6; ordinary opens never install
these tables or index.

### O9. Publication, explicit migration and history

Use V3-V8 enrollment and transaction boundaries. Schema-6 writer opening requires
an explicit `indexed_projectors` set supplied from caller-retained deployment
configuration; an empty set is an explicit disabled choice, never inferred from
missing readiness. This affects publication availability, not replay membership.
Before accepting new work the owner reconciles that desired set: explicitly build
missing requested versions from Layer A, or explicitly remove disabled versions'
O3 rows/readiness. A declared ready version may not advance its projection without
joint index publication. Failed reconciliation blocks new work; an exact committed
retry can still return. Restart requires the same explicit configuration and repeats
reconciliation; no cross-database configuration commit, persistent queue or latch
is assumed. Readiness is not the sole copy of an obligation or configuration.
Old schema-4/5 owner behavior stays unchanged. No auto-disable on missing rows,
inferred latest version or change to logical index contents is permitted.

Publish changed subject/mention/belief rows with the complete projection delta,
relations, nodes/headers/roots, build anchor and derived_progress in one transaction.
Maintain isolated builds for each selected version, even when their rows happen
to agree. Append and its metadata-index maintenance are the earlier transaction;
no append sets O3 readiness. Failed publication leaves the durable event pending
and the previous complete pair, never progress ahead of rows. Reader isolation
must demonstrate wholly before/after states. An exact retry creates no evidence,
rows or new prefix and does not require pending publication to return its pair.

Schema 4/5 retains supported existing API behavior and gives O3 unavailable without
mutation. Only explicit new-copy migration creates schema 6. Full backfill then
replays Layer A and publishes readiness; migration alone is not a ready index.
All failure states/source preservation/committed-table constraints follow V6/V7.
On schema 6, replay rebuild atomically replaces only the selected projection/index
pair, ignoring damaged old rows. Preserve other versions and no checkpoint shortcut.

Historical discovery is a separately named explicit operation, proposed
`replay_discovery(raw_log, *, as_of, projector_version, query, cursor=None)`.
It validates the full raw input and applies the inclusive recording-time cutoff,
then enumerates O8 in memory. It never queries today's index for an earlier answer
or publishes historical state. Return O4's page shape plus the evaluation time,
with query source `replay`. Missing persistent O3 readiness does not block explicit
replay; invalid/unsupported raw input still refuses. Derive historical prefix,
genesis and append tip from that supplied raw input, not current materialization.
Historical `stale` discloses distance from that supplied append tip; it does not
claim missing results within the explicitly evaluated historical cutoff.

Historical continuation repeats complete explicit replay and uses O5/O6 order,
limits and cursor binding, including the exact `as_of` and replay source. If the
resolved historical prefix changes (including a new event tied at the cutoff),
return restart_required. An append beyond the cutoff may change tip/staleness while
the same resolved prefix remains valid. Live publication alone does not invalidate
a replay cursor. Never accept live/replay cursors interchangeably or claim to retain
an old index snapshot. Frozen full-log refusals remain V5; "4" handles supported
mixed historical replay. These mechanics remain subject to confirmation.

### O10. Determinism, completeness and independent verification

For identical raw log, cutoff/evaluation time, projector and index format,
incremental publication, fresh full replay and rebuild MUST yield identical sorted
logical rows, readiness prefix/event identity and query results. Query row order
is O5, not database insertion order. Source text/IDs remain exact; physical pages,
transient plan costs and copy timestamps are outside logical equality.

Explicit verification independently replays from Layer A and enumerates the
complete expected O8 membership without calling the production index builder or
query as oracle. Compare every row/field/key/join and counts, checking both missing
and extra rows, format and anchors. Verify the selected projection's own lineage,
relations and complete logical records separately; matching index digests or a
Merkle inclusion proof cannot prove complete search. For "4" independently check
raw strict pairs; schema-"0" historical duplicates keep old interpretation.
No source fetch, current policy reinterpretation, model or usage inputs during replay.

### O11. Read-only operation and copy inventory

Run queries through enforced read-only storage. No Layer A append, progress write,
publication, rebuild/repair, source fetch/extraction, admission reclassification,
durable usage/exposure/reference record or persistent query cache. Repeated
searches change no count/tip/lineage/candidate standing/support. Report stale or
unavailable state to the caller; create no remediation event.

Inventory mention-text copies in O3 BLOBs, database pages/WAL/journals/free pages,
backups/restore working copies, exports/serialized caches, response pages/cursors
(which contain search text and possibly last mention text), and operator-controlled
output copies. These are permitted public derivatives, not proof of privacy or
erasure. Managed report/request/vocabulary inventory remains part of backup.
Restore preserves bundle inputs, validates schema/anchors/rows and proves
rebuild equivalence on an isolated working copy; never auto-enroll from query code.

ADR 0026 excludes usage from evidence. Proposed [ADR 0029](../decisions/0029-dream-emission-semantics.md)
remains unratified; this draft defines no retrieval/activation/Dream logging.

### O12. Complexity, limits and scope

Indexed literal prefix/exact queries must use O8 access paths, with no full
snapshot or Layer A payload enumeration in the ordinary query path. Scoping or
lifecycle filters can require examining more rows than the returned limit;
global distinct-property enumeration can also cost proportional to matching
associations. State these costs honestly. No relevance/embedding/FTS ranking,
semantic retrieval, scalar winner, identity resolver, retention/GC policy or
measured latency threshold is inferred.

Prospective measurements separately report fixed corpus shape/runtime, rows/bytes,
cold/warm queries, examined keys, publication overhead and rebuild cost. Existing
store-scaling timings are not O3 benchmarks. Work counters and plans must detect
an accidental whole-snapshot scan; they do not establish universal constant work.

## Conflict review of all 19 O3 worksheet answers

These are recommended answers, not approvals. **Consistent** identifies alignment
with the ruling/accepted authority; **Open** identifies a real maintainer choice;
**Conflicting** identifies a difference and concrete resolution options. Only the
ruling's repeated requirements are already binding for drafting.

| Q | Worksheet recommendation | Classification and resolution |
|---|---|---|
| 1 | B | Consistent; explicitly selected for drafting. Same-database atomic derived index, not a sidecar. |
| 2 | 2+3 initially | Consistent for the initial old-profile release. **Conflicting if treated as a closed lifetime set:** strict "4" would lack O3. Options: extend the same format to "4" at strict adoption (recommended V1-V9), or keep 2/3-only and defer mixed-store O3 until a separately ratified extension. Never relabel "4" rows as "3". Extension remains Open. |
| 3 | Yes: admitted public corpus only | Consistent with ADR 0031/R4; the restriction remains binding, not newly approved privacy machinery. |
| 4 | Mention only | Open copy-scope mechanic, consistent with the permitted inventory. Recommend O1/O4/O8; no values/snippets/source text. Expanded text needs explicit copy/privacy/scope review. |
| 5 | Exact+prefix | Open mode choice. Recommend both under O3. FTS/semantic ranking is separate and unapproved. |
| 6 | Exact case/Unicode, no normalization | Consistent with exact recorded identity and the narrow discovery role; confirm O3's exact grammar, empty refusal and literal operators. |
| 7 | Yes: mention-only/every mention ID | Consistent; every match is expressly required by R-O6. Include subject membership without a belief join. |
| 8 | All lifecycle default | Open; recommend all, with explicit current-container/subject filter. Current-only can be chosen but cannot erase retained candidate detail or invent candidate "current". |
| 9 | Ascending relevant UTF-8 ID | **Conflicting with O5 search order:** listings retain ID order, but search proposes text then mention-ID tie-breaker for a direct prefix access path. Both meet R-O1 if fixed in the contract. Choose `Text` (recommended), or `ID` and revise search cursor/order/access-cost cases to ID-only, potentially sorting/scanning the match range. No hidden relevance/recency alternative. |
| 10 | Label valid older publication | Open freshness service choice. Recommend labeled stale O4/O7; explicit Refuse is compatible but sacrifices pending-prefix access. An unsupported/corrupt index is unavailable in either choice, not stale success. |
| 11 | Restart on prefix advance | Consistent with R-O2's required explicit behavior. Snapshot retention is an alternative only with a separately specified implementation/storage contract. Recommend O6 restart. |
| 12 | 100/1000 | Open, explicitly withheld from final approval by the ruling. Recommend those limits in O5; reject rather than clamp invalid sizes. Confirm separately below. |
| 13 | Replay-only historical discovery | Open; recommend O9 explicit raw replay, never today's index at an old cutoff. Historical pagination must use its own query binding. |
| 14 | Atomic rows/delta/progress | Consistent with selected B and accepted atomic publication. O8/O9/V4 include format/prefix metadata and relations. No after-publication update posing as complete. |
| 15 | Explicit working-copy migration/backfill | Open operational choice, consistent with freeze/no-auto-migration. Recommend V6/V7/O9. Alternative requires an equally explicit database contract, not silent installation. |
| 16 | Yes: no durable read usage | Consistent; required by R-O7 and usage/evidence boundary. No other search side effects either. |
| 17 | Yes: complete candidates/retained relations | Consistent; required by no-winner ruling and ADRs 0024/0034. Discovery does not extend specialized report-reader versions. |
| 18 | Unavailable missing/invalid readiness | Consistent; missing is expressly ruled unavailable, detected invalidity cannot masquerade as empty. No per-query full-audit claim. |
| 19 | Yes: ready 0/null distinct from unbuilt | Consistent; necessary to distinguish R-O3 states without violating positive-only derived_progress. Exact O8 representation remains a proposed mechanic. |

The two conditional/actual conflicts are scope extension (Q2) and search order
(Q9), not changes to the ruling. The recommended resolutions form one coherent
V1-V9/O5 design. All Open choices are pending; adoption of B does not ratify
page limits, mode/lifecycle/copy policies or schema by implication.

All 12 payload worksheet answers are separately classified in the
[strict draft's conflict review](2026-10-14-adr-draft-strict-payload-keys.md#conflict-review-of-all-12-payload-worksheet-answers).
Together the two reviews cover all 31 questions, including each selected option.
None of the other 29 answers is automatically approved. No unreviewed answer is
used as authority; proposed mechanics are grouped into the final word-answer
questions for review.

## Prospective acceptance cases

No tests are written here. Future implementation must pass every applicable case,
the full pytest suite and doc checker against the ratified mechanics. Independent
oracles must not use the new index or production query to prove themselves.

| Test | Fixture/action | Required observation |
|---|---|---|
| A1 — Discovery/traversal | Public ordinary and ADR-report stores; start with text rather than opaque IDs; traverse subjects -> properties -> beliefs -> named details | Complete typed traversal, scoped artifact/revision/report meaning, all candidates/provenance. No new report-reader version or truth assertion. |
| A2 — Membership/identity | Mention-only prefixes, identical text across subjects, multiple properties, identical spelling across ID kinds, agreeing/disagreeing candidates, frozen R092 rename/later Python ADR fixture | Every matching mention once; mention-only subjects retained; exact properties/scoped paths distinct; no join multiplication, text/value coalescing or identity inference. |
| A3 — Grammar/empty/limits | Case/NFC/NFD/supplementary Unicode, literal `%`/`_`/quotes/backslash, exact vs prefix, empty query, 1/100/1000 sizes and invalid boolean/zero/1001/fraction; unknown subject vs mention-only subject | Literal byte-preserving matches and all validation reasons; zero-match ready search is empty, absent scope distinguished, page count/end/continuation correct. Default/max remain subject to approval. |
| A4 — Order/cursors | Enough equal-text and equal-timestamp hits for multiple pages; vary insertion/SQL plan; changed mode/query/size/filter/scope/projector/format/order/genesis/key, malformed/extra/duplicate token fields | Total order with ID tie-breaker; concatenated pages equal independent full result without omissions/duplicates. Invalid bindings refuse. Prefix advance returns restart, no implicit snapshot. Same-prefix deterministic rebuild can continue. |
| A5 — Freshness/concurrency | Append unrelated new subject without publication; continue an old page, then publish; real concurrent read transaction across publication; detail read after advance | Global stale metadata changes on append even when every hit is fresh; before/after pages each coherent. Unpublished matching mention not falsely absent at tip. After publication old cursor/detail handle restarts. Equal timestamps still invalidate by position. |
| A6 — Replay/history | Every tested position/time/version, including genesis, mention-only, multi-claim, ordinary reports, "3" transitions and "4" mixed old/strict histories; varied insertion order | Full logical rows/joins/query results equal independently enumerated replay; own-version lineage verified. Inclusive historical cutoff excludes later rows/relations; full-log unknown/invalid suffix refusal preserved. Historical/live cursors never cross-resolve. |
| A7 — Corruption/completeness | Missing tables/builds, fake ready genesis, wrong format/anchor/prefix/version/key/encoding/lifecycle/join, missing/extra/misassociated row, self-consistent tampering | Missing/invalid readiness unavailable, never successful empty. Independent exhaustive replay comparison detects omitted/extra rows even with matching metadata/count. Corrupt derived data is never its own rebuild oracle. |
| A8 — Forward state/no head | "3"/"4" correction/replacement/expiry, agreeing and disagreeing candidates, retained filter controls | Complete live/retained candidates/ending relations agree with replay; belief lifecycle remains distinct. Order/lifecycle/count selects no scalar or standing. Report transitions and deferred events still refuse. |
| A9 — Read-only/copies | Enforced read-only queries, repeated exposure, missing/stale index, attempts to trigger repair/fetch/usage, backup/restore with managed outputs | Zero append/publication/progress/network/extraction/usage/persistent-cache writes. Count/tip/lineage/support/standing unchanged. Copy inventory includes text-bearing cursor/output; source bundle stays byte-identical. |
| A10 — Adoption/rollback | Supported 4/5 originals and distinct copies, exact 6 DDL/constraints, source duplicate payloads, failure at each migration/backfill/rebuild write, existing other-version rows | Old APIs/bytes/IDs/refusals preserved. Migration rollback complete; failed separate backfill leaves no new ready build. Explicit replay recovery atomically replaces selected pair and preserves all other versions. No open/query migration. |
| A11 — Crash/joint version | Process death before/after append commit, during each index/projection/relation/progress write, after publication before ack; strict duplicate at genesis and with pending event; enrolled/disabled O3 | No partial ready publication or progress ahead of rows; durable append recovered once. Strict invalid input allocates/publishes nothing. Strict use does not need O3/diagnostic. V4 mixed old O3 unavailable; selected "4" succeeds; committed retries return original pair. |
| A12 — Work/frozen boundaries | SQL tracing/work counters on growing unrelated corpora and large match sets; production builder/query disabled during audit; frozen fixtures and all selector guards | Prefix range access without full snapshots/payload scans, honest examined-row costs, changed-member publication only where applicable. Independent oracle still detects defects. No old Merkle/root/hash/default change, private ingestion, semantic ranking or usage subsystem. |

## Consequences and alternatives

The proposal supplies public discovery without making an index authoritative.
Option B's transaction gives one complete published prefix; crashes between Layer A
and publication are visible as lag. Working-copy schema adoption and exhaustive
replay verification add operational work. Restart pagination can require repeated
first pages during heavy writes; this is explicit rather than a silent moving view.

Worksheet A scanning would avoid new DDL but not the query completeness/version
contract or full-snapshot cost. C would require independent store binding,
prefix publication and backup/recovery. Neither is the selected B contract.
Sharing the strict semantic boundary would unnecessarily remove O3 from "2"/"3";
the single referenced V1-V9 section separates those versions while making joint
"4" publication explicit.

Before implementation the maintainer must ratify this draft, the shared bundle
and every remaining choice, number the ADRs and commit authority through
[AGENTS.md](../AGENTS.md#adr-commit-protocol). Separate implementation and
maintainer completion-marker commits follow. This design work closes no gap and
updates no authority/status marker.

## Remaining maintainer questions

Each is answerable in one word; recommended answers are in parentheses. Mechanics
approval is explicit review of the cited package, not approval of other proposals.

1. Approve the referenced V1-V9 version/schema/mixed-store/adoption bundle, extending O3 to "4" at strict adoption? **Yes/No** (`Yes`).
2. For search order, use O5 text bytes then mention-ID tie-breaker, or worksheet ID-only order? **Text/ID** (`Text`).
3. Approve O1-O4/O8's mention-only copy, exact+prefix query, typed scope/result and schema mechanics? **Yes/No** (`Yes`).
4. Default lifecycle scope to all recorded subjects/containers or current only? **All/Current** (`All`).
5. Serve a valid older index labeled stale, or refuse lagged results? **Label/Refuse** (`Label`).
6. Confirm default 100 and maximum 1,000 page sizes? **Yes/No** (`Yes`).
7. Approve O6-O12's restart cursors, explicit historical replay, enrollment/recovery, read-only/copy and verification mechanics? **Yes/No** (`Yes`).
