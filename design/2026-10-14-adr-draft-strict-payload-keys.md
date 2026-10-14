# ADR TBD: Strict Payload Keys Under a New Explicit Projector

Status: Proposed draft, not ratified, does not authorize implementation

Date: 2026-10-14

Implementation: None. Design draft only; no parser, projector, schema, diagnostic or migration is implemented by this file.

Supersedes on acceptance: Nothing yet. Proposed additive envelope/projector dispatch and database compatibility amendments are enumerated below. No frozen projector is tightened.

Related: [payload worksheet](2026-10-14-duplicate-key-payloads-worksheet.md), [ADR 0002](../decisions/0002-payload-stored-plaintext-in-v0.md), [ADR 0003](../decisions/0003-genesis-sentinels-and-hash-material-delimiters.md), [ADR 0007](../decisions/0007-payloads-keyed-by-event-id-not-payload-hash.md), [ADR 0010](../decisions/0010-projection-parameters.md), [ADR 0011](../decisions/0011-database-schema-versioning.md), [ADR 0012](../decisions/0012-whole-view-equality.md), [ADR 0014](../decisions/0014-cross-belief-reducer-and-hash-lineage.md), [ADR 0015](../decisions/0015-candidate-scoped-verification.md), [ADR 0023](../decisions/0023-stage-two-contract.md), [ADR 0024](../decisions/0024-no-authoritative-head.md), [ADR 0025](../decisions/0025-incremental-result-commitment.md), [ADR 0026](../decisions/0026-usage-is-not-evidence.md), [ADR 0030](../decisions/0030-sole-writer-and-positional-fields.md), [ADR 0031](../decisions/0031-source-report-claims.md), [ADR 0032](../decisions/0032-explicit-stage-two-projector-selection.md), [ADR 0034](../decisions/0034-forward-state-transitions.md), [ADR 0035](../decisions/0035-adr-0034-implementation-boundaries.md).

## Context

Baseline: worksheets commit `165363d`, based on `5acc188`. The worksheet's
four-projector, two-append-route probes show that supplied payload text can retain
repeated object members while its decoded canonical content passes integrity and
replay checks. Last occurrence wins under the shipped decoder. This is parser
information loss, not a hash collision or a demonstrated breach of the accepted
canonical-content commitment.

This draft transcribes Josh's binding-for-drafting ruling in
`D:\ProjectNyx\scratch\nyx-ruling-2026-10-14-c-b.md`, dated 2026-10-14. It selects
worksheet option C and grants drafting authority only. Remaining worksheet
recommendations are individually reviewed below; consistency does not mean
approval. MUST clauses make the proposal testable, not implementable before
ratification. Historical text and interpretation remain protected.

## Maintainer rulings carried into this draft

1. **R-S1 — Decoded equality:** compare fully decoded object keys, including
   escaped equivalents. Contract S2; acceptance T1.
2. **R-S2 — Recursive early refusal:** reject duplicates at every nesting level
   before persistent mutation, projection, ID allocation or other side effects.
   S2-S4; T1-T3.
3. **R-S3 — History:** preserve historical payload bytes and interpretation;
   no retroactive validation or changes to older projectors. S5-S6/V1-V4; T4-T6.
4. **R-S4 — Selection:** strict admission applies only under an explicitly
   selected new projector. S1/V1-V3; T3/T5.
5. **R-S5 — Diagnostic:** an optional read-only diagnostic changes no projection
   state and is no prerequisite for the strict profile. S7; T7.
6. **R-S6 — Review:** specify failures, compatibility, migration and replay;
   resolve the O3/projector boundary and review every worksheet answer without
   implied approval. S3-S8/V1-V9, conflict review, T2-T10.

## Proposed contract

### S1. Recorded profile and explicit selection

Recommend a new plaintext profile selected by recorded envelope
`schema_version = "1"` and explicitly selected `projector_version = "4"`.
These are **proposed, unreserved identifiers**, subject to maintainer confirmation.
Today's envelope version is `"0"`, distinct from database schema 4/5.
[Shared version boundary](#shared-version-boundary) supplies the single V1-V9
contract referenced by both ADR drafts.

Every new selector requires `projector_version`, without a default, environment
inference or fallback. New command parsers require `--projector-version`.
Omission/unsupported selection refuses before preparation, storage opening,
ID allocation or publication. Existing ADR 0032 legacy defaults stay unchanged.

New "4" appends MUST record schema "1". Relabeling an uncommitted "0" request
is a semantic change, never retry repair. Schema "1" presented to "0"-"3"
refuses; it never reaches the old last-wins decoder. S5 treats exact old retries.

### S2. Duplicate-key predicate

For each object in the original payload text, decode the complete member names
according to JSON string escape rules while retaining its ordered member pairs.
Refuse any two names in the **same object** that decode to the same string,
regardless of distance, equal values or value types. Check before converting
members to a mapping. Recurse into every object, including arrays, claim objects
and arbitrary nested claim values. One duplicate refuses the whole payload.

Compare exact decoded strings. No case folding, trimming, Unicode normalization,
identifier parsing, raw-escape comparison or locale collation:

| Fragment | Strict outcome |
|---|---|
| `{"name":1,"name":2}` | Duplicate; refuse. |
| `{"name":1,"\u006eame":1}` | Duplicate even with equal values; refuse. |
| `{"claims":[{"value":{"x":1,"\u0078":2}}]}` | Nested duplicate; refuse. |
| `{"a":{"x":1},"b":{"x":2}}` | Different objects; no duplicate. |
| `{"Name":1,"name":2}` | Distinct keys; ordinary shape checks still apply. |
| `{"\u00e9":1,"e\u0301":2}` | Distinct decoded Unicode sequences. |
| `{"text":"{\"x\":1,\"x\":2}"}` | String contents are inert, not recursively parsed JSON. |

Unique keys waive no existing schema, taxonomy, hash, origin, scope, identity,
value, dependency or report-policy checks. Scope is payload JSON, not a global
change to envelope `source`/`entity_refs` strings, policy parsing, Merkle nodes or
all 44 decoder call sites. Wider strict-envelope admission needs separate review.

### S3. Refusal order and the no-side-effect boundary

Validate original strict raw text at the outermost boundary before a helper
allocates event/subject/mention/belief/candidate IDs, creates a store or lockfile,
writes a retained-request manifest, publishes pending events, performs extraction
or network work, or mutates persistent state. Caller-supplied IDs are data;
refusal neither allocates nor remints them. Pure parsing and read-only lookup
are permitted. Append no rejection, audit or usage record on refusal.

The shipped submit wrapper publishes pending events before append. A strict
wrapper MUST validate raw input before reaching that action: invalid input
cannot flush unrelated pending work. Mapping preparation cannot recover members
already discarded by a caller; never claim original-text validation without
receiving that text. Mapping-based preparation checks its final serialized
payload before its own ID allocation; raw-input preparation checks original text.

Ordinary semantic requests and retained Envelope/Payload pairs independently
validate raw text at their public append boundaries. Under the append lock,
recheck the exact text to be stored, then apply ordinary pre-event validation at
the actual prefix. Earlier preparation is no substitute. Do not canonicalize
away duplicates first or trust an already-decoded mapping as proof.

Duplicate refusal preserves all logical rows: envelope/payload, count/tip,
freshness, progress, relations, committed headers/nodes/roots, O3 readiness/rows
and caller-retention outputs. Allocator/mutation spies must show zero calls at
the outer boundary; count/tip checks alone are insufficient. A low-level path
cannot undo caller allocation but must allocate nothing itself and mutate nothing.

### S4. Commitment, retained text and errors

**Recommended mechanic, awaiting confirmation:** otherwise valid unique-key
whitespace/member-order/escape variants remain admissible. Retain supplied
plaintext `ciphertext` unchanged; hash decoded canonical content with the existing
serializer and ADR 0003 formula. The envelope hash covers the recorded schema;
`payload_hash` acquires no original-text meaning. Exact-text authentication is
outside this change. Normal mapping preparation still emits canonical JSON.

Use an `IntegrityError` subtype with reason `duplicate_payload_key`, the decoded
repeated key and an unambiguous object path: a sequence of decoded string names
and integer array indexes, empty at root. Report the second occurrence in a
deterministic left-to-right traversal, without entire payload values. The subtype
name is an implementation detail; reason/path meanings are proposed API contract.
Malformed JSON, unsupported profile, hash mismatch and deferred semantics remain
distinguishable failures. Syntax may fail before key checking on invalid JSON;
syntactically valid duplicate-bearing JSON MUST yield the duplicate reason.

No float encoder, integer range, Unicode value domain, timestamp spelling,
resource cap, private codec, erasure or cross-language conformance guarantee is
introduced. Existing failures in those domains still refuse without mutation.
Passing this predicate alone is not acceptance of a Nyx event.

### S5. Historical records and committed retries

Recorded schema "0" retains its old decoder, including recursive last-wins
historical duplicates. Reads/replay/recovery/O3 backfill MUST NOT relabel,
canonicalize, strict-validate or rewrite these payloads. Preserve historical
hashes, IDs, values, provenance and every frozen version's own lineage/roots.
Not every legacy log is a valid "3"/"4" log: unsupported events and unresolved
semantics still refuse under the selected projector.

A committed retry is retrieval, not new admission. Verify the stored pair under
its recorded profile and compare every ADR 0030 caller-owned semantic field,
including schema, exact ciphertext and source.config. Exact old-profile retries
return the original pair under their original supported writer contract.
Recommend also permitting "4" to return an exact committed schema-"0" pair,
using old decoding solely to identify/verify that record. If no exact committed
match exists, the old-schema submission to "4" refuses. This exception never
admits a new old-format event as strict.

New schema-"1" requests validate strictly before retry key calculation. Corrupt
stored strict duplicates fail even when repeated byte-for-byte. Text-only,
schema-only or config-only changes are conflicting semantic reuse even with
equal canonical hash/idempotency key. Preserve the formula; do not evade collisions.
Exact retries precede target eligibility and optional O3 readiness requirements;
they reassign no position, allocate nothing and trigger no publication.

### S6. Reads, projection and verification retain raw access

Strict-format reads, incremental reduction, publication, replay and standalone
verification MUST validate original stored text before using its decoded mapping.
A decoded-only replay API cannot establish this: the new "4" raw-log adapter
must obtain and validate the associated Payload text. Existing decoded-log
signatures stay frozen for "0"-"3". A "4" call lacking raw text refuses rather
than assuming canonical origin. Dispatch follows the recorded profile, never
current date/software, diagnostic results or O3 presence.

A forged strict duplicate with self-consistent last-wins hashes fails read,
publication, replay and independent verification. Recovery publishes no partial
"4" result/index. Old-format counterparts retain old parsing. The independent
verifier inspects raw pairs independently of the production strict helper;
this predicate's independence is not a complete private-codec proof. Never repair,
skip, truncate, substitute a sentinel or fall back.

### S7. Optional diagnostic is independent

**Recommended inclusion, awaiting confirmation:** an independently invoked
read-only audit reports event ID, recorded schema, object path and decoded
repeated key in log order, then deterministic member order. It may report every
duplicate occurrence. Syntax/unavailable-content failures are separate and never
a clean scan. Old duplicates are findings, not newly invalid old events; strict
duplicates are integrity findings.

Use enforced read-only access. Change no acceptance policy, readiness,
publication, freshness, persistent cache, evidence, standing, lineage or usage.
Neither success nor failure enables/blocks strict use. It is not migration,
a startup scan or a rollout prerequisite; strict use can omit it. No persistent
diagnostic subsystem is proposed.

### S8. Authority and remaining gaps

Keep append-only Layer A, candidate-scoped evidence, no scalar winner or
value-based coalescing, exact recorded identity, existing origin refusals,
report-transition refusal, sole writer/positions and the public-corpus restriction.
Neither parser validity nor discovery is verification evidence or a usage event.

Proposed [ADR 0027](../decisions/0027-stage-three-authority-and-acceptance.md),
Proposed [ADR 0028](../decisions/0028-redaction-and-crypto-shredding.md) and
Proposed [ADR 0029](../decisions/0029-dream-emission-semantics.md) remain unratified.
The draft [B2 brief](0027-b2-private-value-codec-ruling-brief.md) records separate design
rulings. This plaintext profile neither implements its private codec nor relaxes
canonical private input or resolves numeric/resource blockers. No gap is closed.

## Shared version boundary

This is the **single shared section V1-V9** for this draft and the companion O3
ADR draft. S1 references it here; O3 references this same section rather than
copying a second version. All V clauses are one recommendation awaiting
ratification, not additional maintainer rulings. The future authority changes
must carry this shared contract with both decisions.

### V1. Separate semantic and index versions

Recommend **separate version boundaries with integrated publication**. Strict
payload support needs a new belief projector; discovery alone changes no frozen
belief semantics/Merkle formats. O3 initially serves "2"/"3" on supported
old-envelope histories and additionally "4" when strict adoption is authorized.
Do not make "3" strict or renumber "2"/"3" for O3.

Proposed bundle: projector `"4"`, strict envelope schema `"1"`, lineage
`nyx-belief-lineage/4`, database schema `6`, index `nyx-o3-index/1`, response
`nyx-o3-page/1`, cursor `nyx-o3-cursor/1`. Names are unreserved proposals.
Database/envelope/projector/index versions are independent axes. Schema 6 has
one layout containing the strict committed-table amendment and O3 tables;
there cannot be two different layouts called 6. Implementing this bundle requires
both contracts ratified, even when index building is disabled for some versions.

### V2. Projector capability matrix

| Projector | Replay envelope profiles | New append profile | Claim semantics | Proposed O3 |
|---|---|---|---|---|
| "0" | "0", unchanged | "0", unchanged | Frozen legacy fold/refusals | Unsupported. |
| "1" | "0", unchanged | "0", unchanged | Frozen stage two | Unsupported. |
| "2" | "0", unchanged | "0", unchanged | Committed stage two; transitions refuse | Format 1 on a supported publication. |
| "3" | "0", unchanged | "0", unchanged | ADRs 0034/0035 forward operations/refusals | Format 1 on a supported publication. |
| Proposed "4" | "0" old decoding; "1" strict decoding | "1" only; exact old retrieval by S5 | Projector-3 claim semantics, separately tagged lineage and strict input domain | Same format 1, isolated "4" rows, including mixed histories. |

"4" inherits "3" refusals: merge/split, support attachment, undecided standing
transitions and report-scoped transitions. It adds no report producer admission
or specialized report-reader version. Existing report importers/readers retain
"1"/"2" guards. Historical reports in a supported copied log may replay and be
found through generic "4" discovery/named-candidate reads with provenance;
that extends neither specialized API nor permission for new "4" report imports.

At any valid old-envelope prefix supported by "3", "4" preserves complete
records, IDs, associations, candidate fields, live/retained sets, ending relations,
progress and evaluation fields. Only version-keyed rows, lineage tag and values
derived from it may differ. Verify each version's own lineage; remove no arbitrary
provenance fields to force equality. Logical O3 rows agree after removing only
projector keys for those equal records; metadata retains its own version key.

### V3. Ingestion and index enrollment

Explicit "4" selection chooses strict new admission whether O3 is ready,
missing or disabled. Recorded envelope schema selects decoding; index metadata
never does. S3 raw validation precedes allocation and all submit-wrapper
publication, then S5 recognizes committed retries, then locked pre-event
validation/ADR 0030 positional assignment govern new acceptance.

Append's earlier transaction commits Layer A and append freshness only, with no
O3 row/readiness or derived-progress advance. New acceptance requires the selected
projection at the pre-append tip. An enrolled O3 build must also be coherent there;
missing/invalid enrolled state refuses new acceptance pending explicit recovery
or disable. A never-enrolled/explicitly disabled index does not block strict use.
Exact committed retrieval remains possible while publication is pending.

Enrollment is an explicit sole-writer operation. Replay builds and atomically
publishes the complete index/projection at one prefix before readiness. Explicit
disable deletes that projector's readiness and index rows atomically, making O3
unavailable while leaving Layer A/projection untouched. No query/open/append
implicitly installs, enables, backfills, disables or repairs the index.

Schema-6 owners require a caller-retained explicit `indexed_projectors` set,
including an explicit empty set when disabled. A separate explicit reconciliation
operation builds requested missing indexes or removes disabled publications before
new acceptance; failure blocks new work, not exact committed retrieval. Restart
repeats this explicit configuration/reconciliation; readiness loss never silently
disables publication. No index row is the sole copy of a configuration/obligation.
Old schema-4/5 owner behavior is unchanged. The companion O9 clause supplies the
same operational sequence; ordinary opening itself performs no backfill.

### V4. Complete publication and mixed stores

For an enrolled version, one derived transaction commits the complete reducer
delta (including headers/nodes/relations), changed O3 rows, prefix/format metadata
and derived_progress. Failure rolls back all derived writes; the earlier accepted
append survives. Unenrolled versions publish normally without O3 readiness.

One store may hold separate "2"/"3"/"4" publications/indexes at independent
progress. Publishing/rebuilding one never relabels, deletes or advances another.
Index rows never enter any belief lineage/result root. Global freshness is the
Layer A tip, never freshness of just the returned subjects.
Compatible old-envelope appends can make multiple projections stale; strict
appends manufacture no old-projector publication and do not change their frozen
freshness-row rules. Discovery compares to the global tip directly.

**Mixed-log recommendation:** after the first strict-schema event commits,
O3 selected as "2"/"3" returns `unavailable`, reason `unsupported_log_profile`,
even if old rows remain. Preserve those rows as derivatives; do not silently
serve them as the mixed-store discovery view. Query checks the recorded schema
inventory in its read transaction, without strict decoding under an old projector.
Use explicitly selected "4" for mixed discovery. Unsupported-log unavailability
precedes continuation handling. An old-prefix export/store remains usable by its
old contract; no API silently creates one. This new O3 rule changes no existing
named-read API.

"2" O3 also refuses a requested publication reaching a "3" transition. At a
supported earlier publication, a valid old-envelope transition suffix may remain
pending and that index may be served stale. An unknown envelope schema differs:
frozen full-log integrity refuses it even beyond the cutoff (V5).

### V5. Replay and index reconstruction

Fixed raw Layer A input, evaluation time/cutoff, projector and index format yield
deterministic decode/reduction/index results. Dispatch follows each recorded
profile. No runtime date, model, network source, diagnostic, query count or current
index is a hidden input. Recovery starts at genesis with empty derived state;
rebuild complete records, lineage, relations and index membership independently.

Index rebuild is an explicit writer operation: validate/replay Layer A, atomically
replace the selected projection/index pair at one requested prefix, ignore prior
O3 rows as an oracle. No resumable checkpoint is authorized. Ordinary query code
never replays or reconstructs as a fallback.

Whole-log integrity precedes inclusive recorded_at cutoff reduction. Ties retain
insertion/hash-chain order. Frozen "0"-"3" cannot validate schema "1" anywhere
in the full supplied log, including beyond an earlier cutoff. An earlier `as_of`
does not promise frozen replay access to a mixed store. "4" validates both
profiles across the full log, then applies the cutoff with "3" claim semantics;
a malformed strict suffix also fails "4" integrity before an earlier cutoff.
Valid unsupported old-format reducer events retain cutoff-dependent refusals.

Raw adapters/verifiers retain raw text through integrity. Physical B-tree pages,
row insertion order and build telemetry need not be byte-identical; complete
sorted logical rows, readiness prefix identity and query results must be.
Cursors are query state, not evidence or a durable replay obligation.

### V6. Database compatibility and narrow amendment

| Database schema | Existing selected behavior | O3 | Strict "4" |
|---|---|---|---|
| 4 | "0"/"1"/"2" unchanged; "3" refuses | Unavailable without migration | Refuse unchanged. |
| 5 | "0"-"3" unchanged | Unavailable without migration | Refuse unchanged. |
| Proposed 6 | Frozen outputs/refusals on supported logs preserved | Explicit ready builds for supported "2"/"3"/"4" | Explicit "4", V2 profiles. |
| Other/missing/malformed | ADR 0011 refusal/preservation | No repair/fallback | No repair/fallback. |

Recommend fresh 6 after joint acceptance; retain existing 4/5 without open-time
migration. Narrowly supersede ADR 0035 section 1 only to admit 6, choose fresh 6
and define explicit working-copy migration. Keep ADR 0011 exact metadata checks.
Today's software refuses 6; this is not a claim of present support.

Schema 6 preserves Layer A columns/bytes/triggers/positions/formulas. Rebuild
exactly `committed_nodes`/`committed_roots` with
`CHECK (projector_version IN ('2','3','4'))`, copy/verify every old row unchanged,
and add O3's proposed tables/indexes. All other table DDL stays unchanged;
`candidate_relations` already has a projector key. Keep positive-only
`derived_progress` and no genesis row. Never silently widen schema-4/5 constraints.

### V7. Working-copy transition and readiness

1. Hash/back up a consistent source snapshot with its managed report/request
   inventory; preserve source/bundle. Copy to a distinct new working store.
   Do not migrate the only original or keep two continuing writers.
2. Explicitly migrate a validated 4/5 copy to 6. For 4 apply exact accepted 4-to-5
   then proposed 5-to-6 changes within one migration transaction. Verify old rows
   and unrelated DDL. Any failure rolls back all schema/metadata changes.
3. Before strict appends, prove "4" versus "3" complete equivalence and own-lineage
   validity at every pre-existing position. If "3" cannot replay the source,
   refuse; invent no legacy/stage conversion. For a "2" reference also apply
   ADR 0034's exact "2"/"3" comparison. Preserve duplicates, IDs and frozen bytes.
4. Explicitly enroll/backfill desired O3 versions through replay. Ready empty
   uses its own 0/null metadata, never a fake progress row. Migration alone leaves
   O3 unavailable. Backfill failure creates no ready build, or preserves a prior
   valid build on later rebuild; it exposes no partial readiness. Migration and
   backfill are separate explicit transactions with visible failure states.
5. Strict writing may start after strict prefix proof without a diagnostic or
   index. When both are desired, independently prove "4" index equivalence
   before enrollment; test joint publication and backup/restore. The maintainer
   later designates the adopted working store; this draft designates none.

Migration never labels history strict. A mixed log could contain later "0"
envelopes from an explicitly selected older writer; "4" decodes them by recorded
old profile without claiming a wholly strict history. Recommend pinning the
sole operator writer to "4" after adoption; add no durable authority latch.
Older software already refuses schema 6. Existing explicit "2"/"3" mixed-store
calls keep frozen validation/refusals, never convert to "4". Historical import
remains outside scope.

### V8. Shared failures and recovery

| Boundary | Outcome |
|---|---|
| Strict duplicate before append | Typed refusal; no new IDs/state/pending publication. |
| Accepted append, publication pending | Durable event and prior complete derived/index prefix; globally stale if otherwise usable. |
| Failure inside derived/index publication | Whole derived transaction rolls back, readiness/progress included. |
| Missing/corrupt enrolled index | O3 unavailable; new acceptance refuses incoherent enrolled state; explicit recovery/disable required. |
| Failure during rebuild | Prior valid pair preserved or no ready build; failure is never empty success. |
| Unknown profile/corrupt log/deferred semantics | Fail loud without partial projection/index or conversion. |
| Successful full recovery | One complete version-isolated projection/index prefix with original IDs. |

Reads repair nothing and record no usage. Structural/query checks detect visible
corruption; exhaustive independent replay comparison establishes completeness.
A prefix marker alone cannot prove every row exists. No per-query full audit or
claim of tamper-proof readiness is implied.

### V9. Ratification and delivery dependency

Shared bundle, strict clauses and O3 schema/query clauses remain proposed.
Confirm identifiers, mechanics and conflict resolutions before implementation.
The maintainer records numbered decisions and narrow amendments through the
[authority protocol](../AGENTS.md#adr-commit-protocol). Agents neither set the
authority environment variable nor commit authority files. Separate implementation
commits and separate maintainer completion markers follow acceptance. This design
commit is neither ratification nor an implementation-complete marker.

## Conflict review of all 12 payload worksheet answers

Answers below are the worksheet's **recommendations**, not received answers.
**Consistent** means no conflict; **Open** means a choice needs the maintainer.
Repeated ruling requirements are identified. No unreviewed answer is approved.

| Q | Recommended answer | Classification and disposition |
|---|---|---|
| 1 | C | Consistent; explicitly selected for drafting. |
| 2 | Yes: historical bytes/meaning | Consistent; required by R-S3. No retroactive strict scan. |
| 3 | Yes: exact old duplicate retry | Consistent with history/ADR 0030; S5 retains original-contract retrieval. Additional "4" retrieval is a proposed mechanic within remaining question 1. |
| 4 | Yes: recorded envelope/new projector | Consistent with C/R-S4. Exact identifiers, base semantics and schema remain Open; V1-V9 recommend one bundle. |
| 5 | Yes: recursive objects/arrays | Consistent; required by R-S2. |
| 6 | Exact: decoded, no normalization | Consistent; decoded equality is ruled, exact case/Unicode preserves accepted identity/serialization. |
| 7 | Yes: equal-value duplicates refuse | Consistent; key repetition, not unequal values, triggers R-S1/R-S2. |
| 8 | No: canonical input not required | Open. S4 recommends permissive unique-key spellings. Canonical-only also satisfies duplicate refusal but narrows admission; decide explicitly. |
| 9 | No: no original-text commitment | Open. S4 recommends unchanged canonical-content hashing. Raw authentication is separate option-D work, never a silent payload_hash change. |
| 10 | Yes: numbers/B2/resources outside | Consistent with narrow scope/blockers. Confirm the scoped mechanics rather than importing a Proposed codec. |
| 11 | Yes: independent optional diagnostic | Open on inclusion. R-S5 requires independence if included; S7 recommends that operation, never a gate. |
| 12 | Yes: working-copy/prefix proof | Consistent with history and ADR 0034 precedent; Open adoption choice. V7 recommends it explicitly with source/prefix limits. |

None of the 12 recommended answers directly conflicts with the binding ruling.
Treating Open choices as approved, conflating this profile with canonical private
input, or promising frozen cutoff access through an unknown later envelope would
conflict with S4/S8/V5. A different canonical-input/raw-commitment answer requires
rewriting S4 and its acceptance cases before ratification.

The companion O3 draft individually reviews all 19 O3 answers, including its
projector-scope tension. Both use V1-V9; neither imports unapproved recommendations
as authority. Together these reviews cover all 31 worksheet questions.

## Prospective acceptance cases

No tests are added. A future implementation MUST pass these cases, full pytest
and the documentation checker against the ratified contract. Changed answers
require changed clauses/tests, not implementation guesses.

| Test | Inputs/boundaries | Required observation |
|---|---|---|
| T1 — Predicate | Root/nested/array objects, deep claim values, distant/equal-value duplicates, escaped names/slash/quote/backslash, supplementary scalar versus equivalent surrogate-pair escape; separate objects/case/NFC/NFD controls | Every same-object decoded duplicate refuses, controls do not. Independent raw-pair parser agrees; JSON strings stay inert. |
| T2 — No side effects | Strict preparer, submit with unrelated pending work, ordinary append and retained-pair append; genesis/populated stores | Zero allocator/retention/publication calls on duplicates. Complete DB, count/tip, freshness/progress/relations/roots/O3 unchanged; no outer-boundary store/lockfile/manifest. Multi-claim rejection is all-or-nothing. |
| T3 — Selection/backstops | Missing/unknown selector, strict envelope through old projector, uncommitted old request through "4", bypassed preparation, ciphertext substitution | Refuse unchanged; locked raw check catches substitution. No hidden default or old-decoder tightening; no model/network/ID allocation to validate keys. |
| T4 — History/retries | Old duplicates in every originally supported version and supported copied "3"/"4" prefixes; exact versus text/config/schema-only changed retry; retry after later transitions | Old text/pairs/IDs/decoded content and old own-version hashes/roots/lineage unchanged. Exact retry publishes nothing and returns original; conflicts refuse. No new old-profile admission under "4". |
| T5 — Corruption/mixed log | Inject strict duplicates with recomputed last-wins hashes, malformed/unknown profile, missing raw text; old-profile controls; cutoffs before/at strict boundary and tied timestamps | Strict read/replay/publication/verifier fail, including bad suffix beyond cutoff. Frozen readers refuse new profile anywhere without skipping. Valid "4" mixed replay preserves old interpretation/cutoffs. |
| T6 — Commitment/equality | Unique whitespace/order/escape variants, base-admitted numeric/Unicode/compound values and timestamp spellings; incremental/materialized/genesis replay | S4 proposed admission, exact text retention and canonical hashes hold. Complete results/lineage equal within each projector. "3"/"4" differ only by V2; no head/coalescing/support transfer. |
| T7 — Diagnostic | Old/strict duplicates, repeated audit, syntax/unavailable content, enforced read-only access | Deterministic findings/distinct errors; zero state/usage writes. Strict use works when diagnostic is absent, unrun or reports historical duplicates. |
| T8 — Adoption | Schema 4/5 copies, genesis, supported ordinary/report history, old duplicates, unsupported source; injected migration/backfill failures | V6/V7 matrix, exact row/unrelated-DDL preservation, source/bundle unchanged, every-position proof/own lineage and original IDs. Migration rollback complete; later failed backfill has no new ready build. |
| T9 — Joint O3 | Absent/disabled/enrolled index, strict append/publish/rebuild, isolated "2"/"3"/"4" rows, corrupt metadata, actual process death at commit boundaries | V3/V4/V8 outcomes. Duplicate refusal advances no index. Disabled O3 does not block strict use; enrolled publication atomic. Selected recovery preserves other versions. Mixed old O3 unavailable; "4" index replay-identical. |
| T10 — Scope/independence | Existing fixtures/refusals/APIs, report guards, Proposed-codec controls; disable/monkeypatch production decoder/reducer during independent audit | Frozen contracts hold; independent predicate/completeness oracles detect faults. No B2/erasure/report-admission/merge/split/origin/usage/private-corpus feature appears. |

## Consequences and alternatives

Strictness becomes recorded and replayable without rewriting evidence. A mixed
history is not certified duplicate-free; only strict-profile records carry that
admission guarantee. Canonical-content hashes still do not authenticate original
text spelling.

Worksheet A remains optional independent visibility. B would tighten existing
projector admission under a different exception contract; the ruling chose C.
D needs separate exact-text commitments. Sharing O3's semantic version would
alter frozen "2"/"3" or needlessly require strict adoption for discovery;
V1 instead versions the index separately and integrates storage/publication.

Implementation remains blocked until open mechanics/shared bundle are explicitly
ratified. ADR numbering and the maintainer authority commit are administrative
prerequisites, not permission supplied by these questions.

## Remaining maintainer questions

Each accepts one word; recommended answers are in parentheses. Confirmation
covers the identified package, not any Proposed ADR elsewhere.

1. Approve V1-V9's proposed identifier/version/mixed-store/adoption bundle, including S5's "4" old-retry retrieval exception? **Yes/No** (`Yes`).
2. For otherwise valid unique-key plaintext, allow noncanonical spellings or require canonical input? **Permissive/Canonical** (`Permissive`).
3. Preserve canonical-content commitments without an original-text commitment in this decision? **Yes/No** (`Yes`).
4. Approve S2-S6 parser/error/raw-replay mechanics, leaving envelope JSON, numbers, B2 and resource decisions outside this change? **Yes/No** (`Yes`).
5. Include S7's independently optional read-only diagnostic? **Yes/No** (`Yes`).
