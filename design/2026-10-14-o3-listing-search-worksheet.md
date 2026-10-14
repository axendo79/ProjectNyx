# O3 listing and search: decision worksheet

**Status: Non-authoritative design draft.** Prepared 2026-10-14 against
`5acc188` on `main`, using Python 3.14.2. Current behavior, alternatives and
recommendations below are decision support. They select no schema, query default,
publication mechanism or implementation authority.

The target is [GAPS: Listing and search surface - O3, unbuilt](../GAPS.md#listing-and-search-surface--o3-unbuilt).
The maintainer must record an accepted contract before dependent work. This
worksheet does not implement an index, retrieval system, MCP server or usage log.

## 1. Decision in one paragraph

Select the smallest public discovery contract that lets a caller find recorded
subjects, mentions, exact properties and belief containers without already
knowing opaque IDs. Decide whether it scans existing materialization, publishes
an index atomically with that materialization, or maintains a separately tracked
sidecar. Independently decide text matching, complete-result scope, pagination,
freshness, version support and historical access. A text match returns recorded
associations; it cannot establish entity identity, an authoritative value or
evidence of absence in the world.

## 2. Exact current surface and evidence

All file:line references identify the baseline above. The old review's
[O3 finding](2026-09-22-review-and-next-steps.md#22-omissions) and
[section 4.3 sketch](2026-09-22-review-and-next-steps.md#43-listing-index)
remain useful design context. Its proposed table, after-publication update and
display ordering are not accepted defaults. Later accepted ADRs and shipped code
govern the current state.

| Existing surface | What a caller can do today; what the surface establishes |
|---|---|
| Inspection CLI | [cli.py:33-52](../src/nyx/cli.py) declares exactly `belief`, `subject`, `mention`, `replay`, `verify`, `status`, `events`. Belief/subject/mention require a named ID. There is no public `list_subjects`, `find_mention` or text-search command. |
| Subject read | [cli.py:112-125](../src/nyx/cli.py) reads a named subject and filters a full snapshot's beliefs by exact subject and optional property. `--property` is exact opaque identity. This is already a per-subject belief enumeration, not global discovery or indexed prefix search. |
| Snapshot enumeration | [storage.py:672-714](../src/nyx/storage.py), [reducer.py:42-69](../src/nyx/reducer.py) and [committed.py:113-143](../src/nyx/committed.py) expose complete snapshots, `records(kind)`, `beliefs()` and current subject/property lookup. A Python caller can enumerate/filter these. No paginated, freshness-bearing public discovery contract is thereby defined. |
| Named identity | [storage.py:742-817](../src/nyx/storage.py) exposes entity/mention/link status and record readers. Records and freshness are read consistently. Missing mention/link status uses log-wide freshness when the subject is unknown. Raw identity readers warn on stale results, including stale absence. |
| Named belief and candidates | [storage.py:578-610,819-849,1035-1084](../src/nyx/storage.py) reads named belief/candidate records and exact subject/property associations. [reducer.py:167-171](../src/nyx/reducer.py) refuses multiple-candidate scalar requests; single-candidate scalar selection is also deliberately unimplemented. Discovery cannot add a scalar read by implication. |
| Projector-3 transitions | [storage.py:1141-1196](../src/nyx/storage.py) returns live and retained candidate sets, with validated ending relations. [forward.py:18-46](../src/nyx/forward.py) provides the equivalent snapshot read. A retained candidate is still available and is not silently removed from a belief's history. |
| Named report reader | [reports.py:108-130](../src/nyx/reports.py) requires an ordered, nonempty, distinct sequence of candidate IDs and explicit projector `"1"` or `"2"`. It returns report provenance and publication position, preserving input order. It neither discovers IDs nor supports projector `"3"`; O3 must not silently extend its version contract. |
| Event enumeration | [cli.py:76-84](../src/nyx/cli.py) validates the complete log, then optionally filters envelopes by inclusive recording-time lower bound and limit. Payloads are not emitted. This is not mention-text search. |
| Explicit historical access | [storage.py:548-575](../src/nyx/storage.py) and [projection.py:250-301](../src/nyx/projection.py) provide explicit replay/whole-view evaluation; CLI belief/subject/replay support `--as-of`. The ordinary materialized lookup path does not reconstruct on every read. |
| Materialized representation | [schema.sql:141-220](../schema.sql) has versioned projected records, current subject/property uniqueness, committed nodes/roots, append freshness and derived progress. No listing/FTS/text-prefix table exists. [committed_storage.py:14-62](../src/nyx/committed_storage.py) reads committed record roots; for `"2"`/`"3"`, `projected_mentions` is not the authoritative complete mention map to scan. |
| Publication/recovery | [storage.py:851-904,953-1032](../src/nyx/storage.py) publishes complete deltas and progress transactionally and rebuilds a selected projection from Layer A. Append/freshness is the earlier transaction. No listing publisher or separate search-index checkpoint is present. |
| Mention-only subjects | [reducer.py:194-218](../src/nyx/reducer.py) creates subject, mention and constitutive link in one mention event, without a belief. A listing derived by inner-joining only beliefs would omit valid recorded subjects. |

Thus the precise limitation is an absent **public discovery/query contract**, not
an inability to inspect any collection with Python or SQL. Full snapshots already
contain the needed recorded associations. Full content reads cost proportional
to that content; a complete snapshot is not a cheap bounded listing API.

### Small synthetic reproduction, 2026-10-14

Fresh temporary schema-5 stores were tested under each of `"1"`, `"2"`, `"3"`:

1. Append and publish two mentions with identical text `Public ADR`, distinct
   mention IDs `m1`/`m2` and subjects `s1`/`s2`. Both subjects exist and there are
   no beliefs yet. Matching text does not alias the subjects.
2. Publish one observation with two fresh candidates on `s1`, property `p`, belief
   `b1`, values `Accepted` and `Proposed`. Both remain; a scalar read raises
   `ValueError`. Complete published snapshot equals full replay at the same time.
3. Append a third mention `m3`/`s3` without publication. The snapshot still has
   two subjects/two mentions/one belief/two candidates. Progress is position 3;
   log tip is 4. Global status is stale. Missing `m3` status is also stale.
4. Publish the pending mention. Three subjects are then present and global status
   is fresh. No retrieval, implicit association or world observation was invented.

| Selected projector | Published subjects / mentions before pending publication | Beliefs / candidates | Applied / appended position | Absent `m3` labeled stale |
|---|---|---|---|---|
| `"1"` | 2 / 2 | 1 / 2 | 3 / 4 | `True` |
| `"2"` | 2 / 2 | 1 / 2 | 3 / 4 | `True` |
| `"3"` | 2 / 2 | 1 / 2 | 3 / 4 | `True` |

A compact repeatable probe follows. Run with `.venv/Scripts/python.exe` from the
checkout root. These synthetic stores contain public invented text and are
deleted when the temporary directories close.

```python
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from nyx import ingestion, projection, storage

at = "2026-10-14T12:00:00Z"
source = {"actor_id": "worksheet", "config": {}}
for version in ("1", "2", "3"):
    with TemporaryDirectory() as directory:
        with closing(storage.init_db(Path(directory) / "probe.sqlite", create=True)) as conn:
            conn.clock = lambda: at
            def mention(number):
                return ingestion.prepare_mention(
                    conn, mention_id="m" + number, subject_id="s" + number,
                    text="Public ADR", source=source, source_class="worksheet",
                    occurred_at=at, origin_type="observed", event_id="e-m" + number)
            for number in ("1", "2"):
                ingestion.submit(conn, mention(number), at, version)
            snapshot = storage.read_snapshot(conn, version)
            assert len(snapshot.records("entities")) == 2 and snapshot.beliefs() == {}
            claims = [dict(
                claim_candidate_id="c" + number, belief_id="b1", mention_id="m1",
                subject_id="s1", property_id="p", value=value,
                verifiability="externally_checkable")
                for number, value in (("1", "Accepted"), ("2", "Proposed"))]
            request = ingestion.prepare_observation(
                conn, claims=claims, source=source, source_class="worksheet",
                occurred_at=at, event_id="e-o", projector_version=version)
            ingestion.submit(conn, request, at, version)
            assert storage.read_snapshot(conn, version).complete() == (
                projection.project_snapshot(storage.read_all_events(conn), at, version).complete())
            storage.append_submission(conn, mention("3"), version)
            status = storage.read_projection_status(conn, version)
            assert status["stale"] and status["derived_progress"]["log_position"] == 3
            assert status["append_freshness"]["log_position"] == 4
            missing = storage.read_mention_status(conn, "m3", version)
            assert missing["record"] is None and missing["stale"]
            storage.materialize_pending(conn, at, version)
            assert len(storage.read_snapshot(conn, version).records("entities")) == 3
            print(version, "mention-only subjects and stale absence preserved")
```

These are tiny correctness probes, not benchmarks or evidence of an existing O3
implementation. [The scaling measurements](2026-09-22-store-scaling.json) concern
ingestion/verification/storage, not latency or capacity of a future listing API.

## 3. Accepted constraints on every option

| Authority | What the discovery contract must preserve |
|---|---|
| [Architecture invariants 1/8/9](../spec/NYX_ARCHITECTURE.md#constitution-invariants-every-component-obeys) and [fold = replay](../spec/NYX_ARCHITECTURE.md#executable-invariants-not-just-reviewed-ones) | Layer A remains append-only and authoritative for reconstructible content. An index cannot hold the only fact, association, correction or obligation. It is a derivative, not a second truth log. Discovery must not alter reducer inputs, evidence or lineage. |
| [ADRs 0010](../decisions/0010-projection-parameters.md), [0012](../decisions/0012-whole-view-equality.md) | Recording-time cutoffs are inclusive; ties retain log order. Historical knowledge at T is not external validity at T. Compare complete results at shared time, prefix and projector. Ordinary materialized reads do not silently replay. |
| [ADR 0013](../decisions/0013-cross-belief-identity-semantics.md), [0014 sections 1/8/9](../decisions/0014-cross-belief-reducer-and-hash-lineage.md#8-append-freshness-and-derived-progress), amended by [0015](../decisions/0015-candidate-scoped-verification.md) | Typed scopes and recorded associations govern results. Freshness uses applied versus appended position, not lineage equality or timestamps. Complete derived publication is atomic. Matching text, paths and candidate/evidence counts are different things. Unimplemented merge/split/successor rules gain no handler from O3. |
| [ADRs 0019](../decisions/0019-identity-bootstrap.md), [0021](../decisions/0021-bootstrap-link-treatment.md), [0022](../decisions/0022-belief-container-uniqueness.md), [0023](../decisions/0023-stage-two-contract.md) | Include mention-only subjects; constitutive links have no invented confidence. Properties are exact opaque strings with no registry/normalization inferred. One current belief per exact subject/property; same spelling in distinct ID scopes does not alias. |
| [ADR 0024](../decisions/0024-no-authoritative-head.md) and [0034 section 7](../decisions/0034-forward-state-transitions.md#7-reads) | Discovery and display order select no authoritative head. Return all named candidates through detail reads, including agreeing candidates and projector-3 retained candidates with relations. Retained candidates are not evidence erased by a listing filter. No scalar/common-value read is added. |
| [ADR 0025 sections 1/5/6](../decisions/0025-incremental-result-commitment.md#5-incremental-representation-and-atomic-publication), [0034 sections 1/10](../decisions/0034-forward-state-transitions.md#10-event-types-frozen-readers-and-store-transition) | Preserve frozen projector bytes, logical commitments, refusals and roots. Derived listing indexes are not new evidence collections or additions to frozen Merkle roots. A result-root inclusion proof does not prove search completeness. Versions remain explicit and isolated. |
| [ADR 0026](../decisions/0026-usage-is-not-evidence.md) | Reads/exposures/reference counts do not create evidence, candidates, standing or lineage. Usage logging, durability, retention and activation remain undecided; no convenient search telemetry becomes a new authoritative store. |
| [ADR 0030](../decisions/0030-sole-writer-and-positional-fields.md), [0032](../decisions/0032-explicit-stage-two-projector-selection.md) | One owning writer publishes mutations. New selectors are named `projector_version`, required and without fallback; new parsers use required `--projector-version`. Do not copy the grandfathered CLI's default-`"0"` alias into new entry points. |
| [ADR 0031 section 7](../decisions/0031-source-report-claims.md#7-corpus-policy-and-derived-copy-inventory), sections 1/6 | Public corpus only. Mention-text copies are permitted only as inventoried derivatives reconstructible from Layer A; that permission does not choose a schema/API. Keep artifact/revision/path provenance and report meaning. ADR numbers and renamed paths do not infer identity. |
| [ADR 0011](../decisions/0011-database-schema-versioning.md), amended by [0035 section 1](../decisions/0035-adr-0034-implementation-boundaries.md#1-schema-versions-4-and-5) | Fresh schema 5; existing schema 4 supports `"0"`/`"1"`/`"2"` unchanged; `"3"` requires 5. A new table/version requires an explicit accepted compatibility/migration contract. Reads/opening do not migrate or repair. |

Proposed [ADR 0027](../decisions/0027-stage-three-authority-and-acceptance.md)
and Proposed [ADR 0028](../decisions/0028-redaction-and-crypto-shredding.md)
remain unratified. Their protected-storage/copy-erasure work is not supplied by a
plaintext index. ADR 0031's public-only restriction remains in force until its
stated requirements pass. Public input still produces content copies in database
pages/WAL, backups, exports, caches and client responses; inventory those copies
without claiming they are already erased or encrypted.

## 4. Three concrete options

Effort is comparative scope, not a delivery estimate. All three need accepted
query semantics; the differences concern representation and publication.

### A. Read-only listing and exact/prefix filtering over existing materialization

- **Contract:** a new bounded response API enumerates existing versioned records
  in one consistent read transaction, joins recorded associations, filters mention
  text and returns IDs/metadata with global progress and freshness. No new
  persistent content index; returning a page does not make the scan bounded work.
- **Replay/determinism:** define sorting/filtering as a pure function of the
  selected published prefix. Compare this function against replay-derived records
  at the same prefix; no reduction or lineage changes. No replay on ordinary reads.
- **Schema/migration:** none to the database. For `"2"`/`"3"`, enumerate the
  committed maps, not a convenient but incomplete projected table. Version the
  response/matching contract independently of the frozen belief projector.
- **Existing stores:** available on currently supported schema/version pairs once
  the API is accepted and built. No rebuild beyond already required projection
  recovery. Large snapshots/scans remain costly; do not promise indexed search.
- **Tests:** exact typed joins, mention-only subjects, match grammar, UTF-8 order,
  prefix pagination, stale/missing data, read-only SQL enforcement and replay
  parity. Meaningful work counters must reveal enumeration growth.
- **Effort:** lowest; a viable small-corpus first slice with an explicit scan cost.

### B. Same-database listing index published with each complete derived delta

- **Contract:** maintain separate versioned subject/mention and belief/property
  projections for discovery, copying mention text only. Update index rows and
  their format/prefix metadata in the **same transaction** as the existing delta
  and `derived_progress`. Queries return one published prefix and global lag.
  There is no index update afterward presented as already complete.
- **Replay/determinism:** index contents are a deterministic function of recorded
  prefix plus explicit projector/index-format versions. Rebuild from empty by
  replay, ignoring old index rows. Neither the new index nor its checkpoint enters
  existing belief lineage/committed roots. Validate index completeness separately.
- **Schema/migration:** new tables/indexes and an accepted database schema version
  with explicit working-copy migration and backfill. Exact DDL, index format and
  supported old/new versions belong in the ADR, not an implementation guess.
  Preserve primary event bytes, IDs and frozen projector results. Do not extend
  `derived_progress`'s schema casually; the index format/build association also
  needs explicit metadata.
- **Existing stores:** old supported stores retain old API behavior unchanged.
  O3 is unavailable until an explicit successful migration/backfill; opening a
  store never installs tables. Failed backfill publishes no ready index; full
  recovery rebuilds selected version/index together. A later rebuild preserving
  other projector/index rows must be tested.
- **Tests:** all A semantics plus all-prefix replay/index equality, missing/extra/
  misassociated rows, invalid index format/prefix, atomic backfill, crash after
  append and during publication, reader isolation, rollback and recovery. Include
  key-range/operation-count evidence that prefix queries avoid whole snapshots.
- **Effort:** medium/high. It adds migration and publication obligations but gives
  one clear atomic boundary and avoids a cross-database consistency protocol.

### C. Independently published sidecar with its own validated prefix

- **Contract:** a single owner builds a disposable versioned sidecar from Layer A
  prefixes, asynchronously if desired. Sidecar rows and their own format/prefix
  marker commit atomically there. A query validates its anchor's event ID/hash
  against the primary store and reports both index and primary-projection lag.
  It must join only detail records available at the same prefix, or explicitly
  refuse; relabeling newer details as the sidecar prefix is excluded.
- **Replay/determinism:** the exact/prefix index remains deterministic and fully
  rebuildable. No sidecar fact, cursor or job is sole durable authority. Rebuild
  ignores damaged sidecar state; model/time/current usage cannot be hidden inputs.
- **Schema/migration:** primary DDL may stay unchanged, but a separate sidecar
  schema, format, store-identity binding, backup inventory and refusal/recovery
  contract are required. A pathname alone is not an adequate store binding.
- **Existing stores:** can be explicitly indexed without primary migration. A
  missing, swapped, ahead-of-primary or corrupt sidecar returns unavailable;
  it must not present empty results as complete. Independent lag complicates
  pagination and coordinating candidate-detail reads after projector-3 transitions.
- **Tests:** all A semantics and independent-prefix equivalence, swapped primary/
  sidecar, missing anchors, corruption, interrupted rebuild, publication lag,
  backup/restore, concurrent reads and both progress comparisons. Never compare
  one index against itself as proof of completeness.
- **Effort:** highest operational complexity for this slice. It suits independent
  scaling only when that benefit justifies another consistency/recovery boundary.

FTS, embedding similarity, relevance ranking, activation and retrieval exposure
recording are separate contracts, not an unstated fourth option. The review's
later retrieval-by-meaning step explicitly identifies those decisions. None is
necessary for exact/prefix discovery and none is authorized here.

## 5. Recommendation (not a ruling)

**Recommend B: a public-only same-database derived index, with exact and literal
prefix matching on mention text and atomic publication.** Start with explicitly
selected projectors `"2"` and `"3"`; leave `"0"` and `"1"` behavior unchanged.
This follows the accepted copy permission while deciding publication more
precisely than the old design sketch. A is a credible smaller alternative if
measured corpus size makes scanning acceptable. C adds a coordination problem
that the immediate discovery goal does not require.

The following is a proposed contract to make that recommendation reviewable. It
is **not an implemented API, accepted default or SQL schema**.

### Proposed result and matching rules

- Separate `list_subjects`, `list_mentions`, `list_properties` and `list_beliefs`
  operations. `find_mention` supports explicit `exact` or `prefix` mode. Names
  describe proposed operations; final signatures/serialization go in the ADR.
  New API calls require `projector_version` and use no implicit version choice.
- Return typed IDs and recorded joins. Subject listing includes mention-only
  subjects. Mention search returns **every matching mention**, with its subject
  ID; same text on two subjects produces two hits. Property listing returns exact
  recorded property IDs in the chosen scope, not a property registry. Belief
  listing returns containers/associations and lifecycle, with links to complete
  candidate reads. No candidate value, snippet or source free text is copied into
  the index.
- Preserve mention text, exact property strings and IDs without normalization.
  Matching is case-sensitive on exact decoded Unicode sequences; `prefix` means
  literal starts-with. `%`, `_`, backslash and quotes are literal data, never SQL
  patterns/operators. NFC and NFD stay distinct. Empty search strings refuse;
  unfiltered enumeration uses listing operations. Never parse an ADR number or
  path similarity into an identity match.
- Include all recorded lifecycle statuses by default, with an explicit `current`
  filter available. Every row exposes its recorded lifecycle when applicable.
  This adds no merge/split/successor algorithm. Projector-3 belief details preserve
  complete live and retained sets with their ending relations; neither ordering
  nor a lifecycle filter supplies an authoritative scalar.
- Deterministic display order: ascending UTF-8 bytes of the relevant ID (subject,
  mention, property or belief) within the selected scope. This is response order,
  not a rewrite of canonical candidate collections or evidence ordering. Property
  listings deduplicate exact property strings; mention hits deduplicate by
  mention ID, never by text, subject similarity or candidate value.

### Proposed prefix, pagination and freshness rules

- Every response carries projector version, index-format version, applied
  `log_position` **and event ID**, global append tip, `stale`, query scope,
  returned count and a continuation cursor or explicit end. Validate the index's
  format and prefix association; no row-presence or hash-only shortcut proves
  completeness. Read content, joins and this metadata in one SQLite transaction.
- Represent a successfully built empty prefix as position 0/event ID null in the
  index's own readiness/response contract. Existing `derived_progress` has no row
  at genesis and requires positive stored positions; do not insert a fake zero
  row or confuse an unbuilt index with a ready empty one.
- Global lag matters for discovery: a pending event about a previously unknown
  subject can add a match. A matched subject's fresh status alone cannot certify
  that the search contains every subject. Empty results when stale mean no match
  in the published prefix, not no match at the append tip. Even fresh emptiness
  means absence from recorded scope, never proof of world absence or a new
  `gap_recorded` event.
- Recommend page size 100 and maximum 1,000, as **proposed operational limits**
  for maintainer approval. The cursor binds the exact operation, scope/filters,
  query text/mode, order, index format, projector and applied prefix/event ID,
  plus the last returned key. It conveys no authority or evidence. Reject malformed
  or mismatched cursors. No offset pagination that silently shifts rows.
- A subsequent page is allowed only while that applied prefix still matches;
  otherwise return an explicit restart-required result. Do not hold a read
  transaction across client calls or claim to retain old index snapshots.
  An appended but unpublished event may change freshness while the same published
  page prefix remains valid; disclose the new tip. Once publication advances,
  continuation must restart. This sacrifices uninterrupted paging during writes
  for a small and honest first contract.
- Missing, mismatched or corrupt index/build metadata means unavailable, not an
  empty successful page. An older **valid** publication can be served labeled
  stale. Reads never publish, repair, rebuild, fetch sources or append usage.
- Historical discovery is an explicitly requested replay operation at a supplied
  `as_of`, separate from ordinary listing. Its IDs/content follow the selected
  historical prefix; do not apply latest index rows to an old cutoff. No retained
  history index or resumable recovery checkpoint is introduced. Frozen projectors
  still refuse transitions they do not support if the cutoff reaches them.

### Proposed physical and operational boundary

Do not make a single subject/mention/property inner-join table the whole index:
it loses mention-only subjects and can multiply mention hits by property count.
The ADR should define separate subject/mention membership and belief/property
associations, exact keys, prefix lookup representation, readiness/format metadata
and constraints. Text encoding, query range bounds and indexes must implement
the literal Unicode contract rather than SQLite's default `LIKE` case behavior.
No DDL is selected by this worksheet.

Recommend one new database schema contract with an explicit compatibility matrix
for existing 4/5 stores, migration of working copies, atomic backfill/ready state
and refusal on incomplete builds. New O3 queries on unmigrated stores return
unavailable; existing supported APIs keep their accepted behavior. Assign the
actual schema/index-format identifiers only in the authority change. Primary
projector numbers and belief/Merkle formats need not change merely because a
separate derivative is added; any actual semantic change requires its own version.

The writer publishes index changes with the complete delta and progress. Recovery
reconstructs both from Layer A under the selected versions; verified existing
materialization can be an acceleration only under an explicitly decided matching
prefix contract. There is no lazy repair from query code. Extend the managed-copy
inventory and backup/restore validation to the new rows/metadata, WAL/database
pages, serialized caches/exports and operator-controlled output copies. Keep
public-only admission. No confidentiality or erasure guarantee is implied.

## 6. Exact maintainer questions

These short answers would pin the recommendation. If A/C is chosen, rewrite the
physical/publication part of the ADR before any implementation; other applicable
query questions still need answers.

| No. | Question | Short answer choices | Recommended answer |
|---|---|---|---|
| 1 | Which representation/publication option? | `A` / `B` / `C` | `B` |
| 2 | Which projectors get the initial O3 contract? | `2` / `2+3` / `1+2+3` | `2+3` |
| 3 | Restrict indexed content to the already admitted public corpus? | `Yes` / `No` | `Yes` |
| 4 | Which payload text may the index copy? | `Mention only` / `Expanded text` | `Mention only` |
| 5 | Which search modes ship first? | `Exact+prefix` / `Exact only` | `Exact+prefix` |
| 6 | Is matching case-sensitive and without Unicode normalization? | `Exact` / `Normalized` | `Exact` |
| 7 | Include mention-only subjects and every matching mention ID? | `Yes` / `No` | `Yes` |
| 8 | Which lifecycle scope is the listing default? | `All` / `Current` | `All` |
| 9 | Use ascending UTF-8 ID order without relevance/recency selection? | `Yes` / `No` | `Yes` |
| 10 | Serve valid older results with global stale disclosure? | `Label` / `Refuse` | `Label` |
| 11 | Invalidate continuation when the applied publication prefix changes? | `Restart` / `Retain snapshots` | `Restart` |
| 12 | Approve page size/max as 100/1,000? | `100/1000` / numeric pair | `100/1000` |
| 13 | Handle historical discovery through explicit replay only? | `Replay` / `History index` | `Replay` |
| 14 | For B, publish index rows/metadata atomically with delta and progress? | `Atomic` / `Separate` | `Atomic` |
| 15 | Require explicit working-copy schema migration/backfill before O3 use? | `Explicit` / `Alternative` | `Explicit` |
| 16 | Keep search reads free of durable usage/exposure writes? | `Yes` / `No` | `Yes` |
| 17 | Preserve full candidate details, including projector-3 retained relations, with no scalar winner? | `Yes` / `No` | `Yes` |
| 18 | Make missing/invalid index readiness unavailable rather than empty success? | `Unavailable` / `Alternative` | `Unavailable` |
| 19 | Distinguish ready empty prefix 0/null from an unbuilt index? | `Yes` / `No` | `Yes` |

A `No` or `Alternative` that changes a binding invariant, privacy restriction,
frozen projector or usage boundary requires an explicit authority resolution; it
does not authorize implementation by implication. Page limits are operational
recommendations, not measurements. Empty query refusal, literal metacharacters,
typed result fields, exact deduplication, cursor validation and scope distinctions
above must appear explicitly in the ratified contract, not disappear into tests.

## 7. Acceptance matrix the eventual ADR must require

This is proposed acceptance work. No production tests or implementation are added
by this worksheet.

| Case | Required observation |
|---|---|
| Discovery without known IDs | Starting with only exact/prefix mention text, traverse typed subject -> exact property -> belief -> all named candidates and provenance. Repeat for public ADR reports with contradictory revisions; preserve artifact/revision meaning and scoped path identities. |
| Mention-only and duplicate text | A committed/published mention with no belief appears. Two identical texts on different subjects return separate mentions. Multiple properties do not duplicate a mention hit. Missing optional report fields do not create property observations. |
| Exact text/identity | Case variants, NFC/NFD, supplementary Unicode, `%`, `_`, quotes and backslashes match the literal grammar. Exact opaque properties stay distinct; ADR-number reuse and the frozen rename fixture never alias subjects. |
| Typed and complete candidate reads | Same spelling in entity/mention/belief/candidate scopes never cross-resolves. Agreeing and disagreeing candidates survive. Projector-3 live/retained candidates and relations agree with replay. No display sort, retained filter or result count selects a head or corroboration. |
| Empty and limited results | Distinguish empty prefix scope, no matches, limit/end, unknown/missing ID, stale index and unavailable index. Stale empty search does not claim absence at the tip. Fresh absence stays confined to the recorded query scope and creates no event. |
| Prefix pagination | Stable keyset order, exact cursor binding, no duplicates/omissions across pages at one prefix. Reject changed query/version/format, malformed cursor and advanced publication. Equal recording timestamps with distinct positions do not share a cursor checkpoint. |
| Append/publication gap | Append an unrelated new subject while publication lags. Global search is stale even when every returned subject is fresh. Before/after publication observations come from one complete transaction each; absent/unpublished mentions remain explainable. |
| Crash and corruption | Inject failure at each index-row/metadata/progress write and rebuild boundary. No partial ready index or progress-ahead-of-rows result. Delete/add/misassociate rows and corrupt anchors/format metadata; independent replay comparison catches them. |
| Recovery and history | From empty derived state, replay reproduces every listing row and query result at every tested prefix/time/version, including mention-only prefixes and projector-3 transitions. Rebuild ignores corrupt index contents and preserves other projector rows. Explicit old cutoffs contain no later matches or relations. |
| Schema/store transition | Old schema-4/5 stores keep supported old reads and refuse unavailable O3 without mutation. Explicit migration/backfill on a distinct working copy preserves Layer A and all old results/roots/IDs. Failure rolls back metadata and readiness; backup/restore preserves inventory and rebuild equivalence. |
| Read-only and evidence boundary | Run discovery through enforced read-only connections; no append, publication, repair, network fetch, extraction, source-policy reclassification or durable usage write. Event count/tip, lineage, candidate standing and support are unchanged by repeated searches. |
| Frozen versions and evidence limits | Keep existing byte fixtures, refusal boundaries, explicit projector guards and named report-reader version limits. An inclusion proof is never labeled a proof of complete search. Index equality uses an independent replay-derived enumeration, not the new index as its own oracle. |
| Measured work | Benchmark fixed workloads only after implementation, recording runtime, corpus shape, rows/bytes, cold/warm query cost, publication overhead and rebuild cost separately. For B, deterministic work counters guard against accidental full snapshot enumeration on prefix queries. No unmeasured latency threshold is inferred here. |

Useful existing suites to extend include
[read surface](../tests/test_read_surface.py),
[CLI](../tests/test_cli.py),
[reducer boundary](../tests/test_reducer_boundary.py),
[incremental commitment](../tests/test_incremental_commitment.py),
[forward reads](../tests/test_forward_reads.py),
[report reader](../tests/test_report_reader.py),
[rename](../tests/test_report_rename.py),
[schema compatibility](../tests/test_database_schema_versioning.py), and
[store transition](../tests/test_store_transition.py).
They constrain existing behavior; their existence is not O3 acceptance coverage.

## 8. Future ADR outline only

**ADR number TBD; Status: Proposed; Implementation: None. No ADR file is created.**

1. **Problem and scope:** O3 discovery without known IDs, public-only corpus,
   exact/prefix first slice, evidence baseline and explicit exclusion of semantic
   retrieval, ranking, usage logging, private storage and new identity semantics.
2. **Maintainer rulings:** answers 1-19, exact operation signatures, typed response
   fields, lifecycle/property/mention scope, Unicode matching, empty-query rule,
   deterministic order and candidate-detail traversal without a head.
3. **Completeness and versions:** index/query format, required projector selection,
   valid prefix/event identity, global freshness, unavailable versus stale versus
   empty, pagination/restart semantics and explicit historical replay operation.
4. **Chosen representation:** for B, exact DDL, keys, literal prefix access path,
   metadata/ready-state contract, atomic delta/index/progress publication and
   full-replay reconstruction. For A/C, replace this section with the selected
   scan or independently anchored sidecar contract rather than mixing options.
5. **Schema and adoption:** exact supported database matrix and any narrow
   supersession of ADR 0035, explicit working-copy migration/backfill, rollback,
   backup/restore, unchanged source IDs/event bytes and frozen projector results.
6. **Copy and authority inventory:** mention text plus all managed persisted
   copies/outputs; accepted public-only restrictions; no new truth/usage authority,
   no world-absence event from a query and no private erasure claim.
7. **Acceptance and release:** full matrix above, independent replay comparison,
   crash/corruption/read-only evidence, measured work scope and limits; maintainer
   authority commit first, separate implementation/full checks second, separate
   maintainer implementation-complete marker last.

Neither this worksheet nor the old section-4.3 sketch closes O3. Only the future
accepted decision and its separately validated implementation can do so.
