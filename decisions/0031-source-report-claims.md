# ADR 0031: Report-Scoped External Content

Status: Proposed

Date: 2026-09-22

Implementation: None

Supersedes on acceptance: No accepted ADR for the report-scoped option (a) defined here. Option (b) is an undecided target, not a new origin mapping or permission to change frozen projectors.

Related: [ADR 0001](0001-observation-recorded-resolves-to-verified.md), [ADR 0006](0006-occurred-at-comparison-is-instant-based-not-lexical.md), [ADR 0019](0019-identity-bootstrap.md), [ADR 0021](0021-bootstrap-link-treatment.md), [ADR 0023](0023-stage-two-contract.md), [ADR 0024](0024-no-authoritative-head.md), [ADR 0025](0025-incremental-result-commitment.md), [ADR 0026](0026-usage-is-not-evidence.md), [ADR 0030](0030-sole-writer-and-positional-fields.md), [ADR 0032](0032-explicit-stage-two-projector-selection.md), proposed [ADR 0028](0028-redaction-and-crypto-shredding.md) and proposed [ADR 0029](0029-dream-emission-semantics.md), [review and rulings](../design/2026-09-22-review-and-next-steps.md#rulings-2026-09-22).

## Context

The shipped stage-two origin mapping makes observed-origin ClaimCandidates
verified. It does not interpret arbitrary property names or enforce whether an
external artifact's statement has been mistaken for the truth of its contents.
A source label or repeated ingestion cannot close that semantic distinction.

R3 selects report-scoped claims now (option a), with a distinct origin mapping
recorded as the future target (option b). R4 restricts the corpus, R5 permits an
inventoried derived mention-text copy, and the rename ruling preserves scoped
subjects. This draft specifies that direction for ratification; it does not
implement an ingester, writer enforcement, origin handler or listing API.

The maintainer's 2026-10-03 first-slice rulings R1–R8 are incorporated below
as a **proposed contract**, not acceptance. Section 8 supplies the exact draft
choices still requiring review; every such choice is marked
[DRAFT — maintainer to confirm]. Status remains Proposed and implementation
remains None. Neither these rulings nor the draft examples authorize code.

## Proposed contract

### 1. What a report-scoped claim asserts

A report-scoped claim asserts that an identified artifact, at an identified
revision or observation context, contained a particular statement or property.
Its subject is the artifact referred to by the recorded mention, and its
property definition states the report scope. For example, “file F at commit C
states its status as Accepted” is different from “the decision is accepted.”

The observed signal is the artifact's statement. Under ADR 0001, verified is
honest for that limited claim: the writer recorded a direct observation of what
the artifact said. It does not verify the statement's embedded world claim,
the author's authority, correct extraction by assumption, or source independence.
Source/revision provenance and the claim's explicit subject/property/candidate
associations must remain available. No verification is obtained from a property
name suffix alone.

An ingester records only what it actually observed under its declared report
vocabulary. A missing status line is absence of that observation, not a fabricated
status claim. Source configuration records the repository, exact path, revision/
blob identity and source location. R1 selects source.config for the per-event
vocabulary declaration; section 8(a) drafts the exact keys.
occurred_at uses ADR 0006's existing offset-bearing timestamp rules and preserves
accepted spelling. No timestamp canonicalization or recording-time import rule is
introduced.

A later contradictory report creates another ClaimCandidate in the appropriate
existing belief container, with its own event provenance. It does not select a
new authoritative head by recency, coalesce agreeing claims, or implement
correction/temporal-resolution semantics deferred by ADRs 0023 and 0024.

### 2. Option (b) is the recorded target

A distinct origin mapping for reported content is the recorded target. Its
origin name, verification-state mapping, supported event contract and projector
version/contract are undecided. This draft supplies no string value, default
state, handler, fallback to observed, or automatic upgrade.

Option-(a) events remain valid when option (b) exists: an observation that an
artifact said something remains an observation about that artifact. Neither its
claim scope, immutable origin, IDs nor committed bytes are retroactively changed.
New origin semantics must have an explicitly accepted versioned contract, leaving
the frozen historical projectors reproducible. A report's availability does not
create a promotion path for the reported proposition.

### 3. Writer boundary, not property identity or replay policy (R1–R3)

Every external-content ingestion submission declares the report vocabulary it
uses, on both mentions and observations, in a closed nested source.config object
carrying vocabulary identity, version and canonical-definition SHA-256. Unrelated
config fields are preserved. This restriction is prospective: historical
undeclared events and equivalent committed retries are unchanged. It changes
neither envelope nor payload format. The writer checks new admission before
Layer A append. Each claim's exact property
string must be admitted by that vocabulary with report-scoped meaning, explicit
artifact applicability and compatible value shape. Missing declarations,
undeclared properties, a vocabulary/hash mismatch, or a definition that asserts
embedded propositions as world truth refuse before mutation.

The declaration is ingestion policy supplied to the writer, not a global property
registry. Property IDs remain exact opaque nonempty strings under ADR 0023
section 1: no normalization, synonym mapping, namespace inference or identity
derived from labels. Existing beliefs and their exact subject/property uniqueness
remain unchanged. This proposal requires no property-creation event.

Each event on this external-content path, including its mention bootstrap,
records immutable vocabulary identity, version and hash. A mention-only event
carries that declaration without inventing property claims. It is not permissible
to evade enforcement by omitting the ingestion declaration and relabeling external
content as unrestricted direct observation. Classification is writer-owned and
applies at the common writer boundary on every submission route available to
the producer. Trusted deployment configuration binds the producer, never a
caller-supplied actor_id or source_class. Only reviewed identity/version/hash
combinations are admitted; a correct hash over a caller-invented definition
is insufficient. Section 8(d) drafts the concrete binding and route coverage.

The boundary is trusted in-process importer code with controlled writer access,
not authentication against arbitrary code with equivalent database privileges.
The writer cannot detect external content from arbitrary submitted text.
Three claims must be evidenced separately:

- **Authorized-route enforcement:** given the configured producer binding, the
  producer cannot evade new-admission checks by dropping metadata, changing
  actor_id/source_class or switching any route available inside that boundary.
- **Faithful extraction:** deterministic extraction and pinned artifact fixtures
  establish what the importer read; vocabulary admission alone proves neither
  correct extraction nor the embedded proposition.
- **Direct-database bypass:** equivalent database privileges can bypass policy;
  integrity/replay success does not prove that writer admission ran.

**Replay does not re-check vocabularies.** It uses the already recorded events
under the selected projector, with ordinary integrity, scope and transition
validation. Replay does not consult a current vocabulary, network service,
mutable configuration or admission-policy registry. Changing an ingester's
vocabulary cannot invalidate or reinterpret historical claims.

**The writer is the trust boundary; direct database writers bypass this check.**
Normal envelope/payload/hash checks do not prove that an authorized ingestion
policy ran or that an artifact was faithfully extracted. The standalone verifier
must not claim vocabulary enforcement from replay success. Existing logs receive
no invented metadata and no retroactive admission-policy test.

### 4. Vocabulary hash inputs, immutable versions and policy changes (R2/R4)

The vocabulary is finite and ADR-specific. Each entry defines an exact property
string, allowed value shape, artifact scope and report meaning. Duplicate entries,
unknown schema fields and unsupported constraints refuse. Identity and version
are nonempty case-sensitive strings, without normalization or implicit latest.
Section 8(b) drafts the complete closed schema and finite entries.

Hash the complete declared vocabulary definition, not merely a vocabulary name
or a list of admitted properties. The hash input includes its identity and
version, the exact property strings, each property's report meaning and artifact
scope, and all value-shape/admission constraints used by the writer. A changed
scope or constraint must change the committed definition just as a changed
property does. Human labels which form part of that definition are covered too.

The proposed definition is an explicit canonical JSON object containing those
contents, hashed as lowercase SHA-256 of its UTF-8 bytes through Nyx's existing
shared canonical serializer. Its own resulting hash, mutable deployment paths,
retrieval timestamps and signatures about the definition are not recursively
part of the definition being hashed. Property collections represented as sets
use the accepted canonical UTF-8 ordering; recorded property strings are never
normalized. This reuses the accepted hashing discipline and claims no new
cross-language canonicalization guarantee.

A definition is immutable within its identity/version. A change to any covered
content, including descriptions and labels, requires a new version and hash.
Formatting and object-key order alone do not change canonical definition bytes
or require a new vocabulary version. Sets and ordered sequences are identified
explicitly; section 8(b) defines their treatment. The original JSON file's
formatting is distinct from the canonical hash input.

Definitions are immutable repository files. A reviewed allowlist controls
admission. At startup the writer loads and validates the complete definitions
and allowlist and uses that immutable snapshot for its lifetime; only restart
activates a new policy. A declared hash must match the reviewed complete
definition, and an identity/version cannot be rebound to a different hash.
Retirement removes admission only: historical definitions and their
identity/version/hash bindings remain retained, and every release preserves its
definition bundle. A mutable URL or current allowlist alone is insufficient.
There is no database vocabulary catalog in this slice. Database replay consults
neither the definitions nor the allowlist. Section 8(c) drafts startup failures
and section 8(b) drafts file and original-source-byte preservation details.

The event's vocabulary metadata is semantic source provenance: changing it on
retry is not a positional repair. Exact committed metadata survives retries and
replay. A definition update applies only to new submissions; it does not rewrite
older events or silently retry them under a new version. Preserved metadata
alone does not establish admissibility of an uncommitted request:

- An equivalent committed retry returns its complete original pair under
  ADR 0030, even after the vocabulary is retired.
- A conflicting retry refuses, including a source.config-only conflict.
- An uncommitted request faces the policy snapshot loaded at writer startup;
  a retired vocabulary refuses without rewriting the request.
- A committed mention remains valid but does not grandfather a pending
  observation. Its equivalent retry returns the mention's original pair; the
  uncommitted observation faces new admission under the startup snapshot.
- A running writer continues its loaded policy even if repository policy files
  change. Retirement becomes active only in a successfully restarted writer.

### 5. Per-event declaration and first-slice extraction (R1/R5)

R1 selects source.config, not dedicated envelope or payload fields. Source is
canonical JSON covered by event_hash and retained in candidate/dependency
provenance. The closed declaration does not close unrelated config fields or
require copying the definition into every event. It is semantic metadata under
ADR 0030: changing it is not positional repair, and the idempotency formula's
actor_id coverage alone does not establish equivalence.

R5 restricts extraction to the literal ADR title, explicit Status declaration,
explicit Implementation declaration and one Git rename-report type used by the
frozen fixture. Literal text is preserved; prose is not interpreted into
categories and implementation completion is not inferred. Missing fields yield
no claim; repeated or ambiguous declarations refuse that artifact's extraction.
Rules are deterministic, with exact grammar drafted in section 8(f).

Every report records repository identity, exact path, revision/blob identity
and source location. Identity is a recorded repository-qualified path scope
spanning revisions, reused only through retained associations; every candidate
identifies its revision. A renamed path is a separate subject and ADR numbers
never establish identity. Section 8(e) drafts the path representation and the
mention/subject association contract.

Complete semantic requests are persisted before submission, retaining IDs,
associations, timestamps, config and explicit projector selection for retries.
This is caller retention, not a new writer queue or acknowledgment before Layer A
commit. Source dates remain distinct from import timestamps; ordinary recorded_at
assignment stays with the ADR 0030 writer. Inputs come from a reviewed
public-corpus allowlist. Section 8(f) drafts retention and source-date details.

R6 requires a report-detail adapter over named-record reads returning candidate
identity, artifact, exact revision, report scope, value and recorded provenance.
Its meaning is **“artifact A at revision R stated X”**, never X being verified
world truth. Contradictory reports appear together without a latest winner.
Section 8(g) drafts the name, inputs and complete return shape. No listing index
is required or implemented by this reader contract.

### 6. Rename identity and ADR numbers

A renamed file is a separate scoped subject under the current ADRs. Ingestion
records the new path through its own mention/subject bootstrap; it does not reuse
the old subject because Git reports a rename or because both files contain the
same ADR number. A recorded Git rename/similarity result asserts only what Git
reported in the specified repository/commit context. It is a report-scoped claim,
not an entity link, an admissible association basis, or a merge.

ADR numbers are metadata and searchable text, never subject, mention or belief
identity. Recorded opaque IDs and associations govern replay. Matching number,
title, text or similarity supplies no exception to ADR 0019 section 4's
unratified association-basis boundary.

R7 requires a checked-in frozen public regression fixture: commit
902467afa54887de0d15ab9f1a9d23403e9628cc reports R092 for
decisions/0009-projection-parameters.md ->
decisions/0010-projection-parameters.md. Test separate subjects for the two paths,
preservation of the old subject's claims, and a report-scoped Git rename/similarity
claim with that commit provenance. The “0009” path must not alias the later
Python-target ADR numbered 0009, nor may “0010” become a universal identity key.
This is a fixture requirement for the unbuilt ingester, not a rename handler.

Check in the exact before/after artifacts and rename report, capture command,
tool configuration and revision provenance. Independently compare the capture
with pinned Git objects; routine tests need no fetch or live rename heuristic.
Include the later Python ADR 0009 as a real imported artifact. Assert distinct
subjects, retained old candidates, commit-scoped Git-report meaning and no
aliasing across ADR numbers. Section 8(h) drafts exact packaging and capture
parameters without substituting another rename.

### 7. Corpus policy and derived-copy inventory

The maintainer's policy is:

> public corpus only until the erasure requirements (Gate 3 of proposed ADR 0027 together with proposed ADR 0028 9 and 11) are accepted, implemented and passed.

[Proposed ADR 0027 Gate 3](0027-stage-three-authority-and-acceptance.md#gate-3-implementation-and-operational-assurance)
owns the assurance gate. Proposed ADR 0028 sections 9 and 11 own the applicable
persistence/erasure obligations. Passing a protocol review alone does not lift
this policy. No current privacy, encryption, deletion or secure-erasure guarantee
is claimed. This draft does not deem the repository, a local path, or every
artifact publicly available merely because it can be read; the ingested corpus
must actually be public.

R5 permits mention text in a derived listing index for public corpora, with this
explicit planned-copy inventory:

| Planned copy | Source and reconstruction | Boundary |
|---|---|---|
| Listing-index mention text with recorded subject/mention references | Derived from accepted entity_mention_recorded payloads and recorded associations; rebuildable by replay of Layer A under the selected contract | Public content only; no sole durable facts, identity inference or authoritative-head selection |
| Persisted copies of that index, including database pages/WAL, backups, exports and serialized caches | Copies of the same derived content, included in the deployment's copy inventory | They are not erased merely by dropping the live index; any future protected deployment must satisfy the applicable managed-copy closure |

This inventory records a permitted future copy, not a shipped table or a new
index schema/API. Publication must disclose staleness under the existing
progress/freshness contract. Listing, search ranking, embeddings and retrieval
usage mechanics remain separate work.

R8 defers option-(b) origin mappings, protected deployment and listing/indexing,
each requiring its own accepted contract. This slice remains option (a),
public-only and explicitly selected stage-two projector semantics. R5 of the
2026-09-22 review permits the inventoried future copy above; it does not make
that copy a dependency of the R6 reader or authorize an index in this slice.

### 8. Exact first-slice draft choices required before acceptance

R1–R8 settle the policy direction. The exact representations and additional
refusal details below are unconfirmed, addressing worksheet B1–B6. A marker
applies to its accompanying paragraph, table or example. Acceptance must
explicitly resolve every marker; no marked choice is an implementation default.

#### (a) Declaration keys and complete source example

[DRAFT — maintainer to confirm] Reserve `source.config.report_vocabulary`,
exactly `{identity, version, definition_sha256}`. Identity/version follow R2;
the digest is exactly 64 lowercase hexadecimal characters. Missing/extra nested
fields, wrong types or invalid digest syntax refuse new external admission.
Unrelated config is preserved unchanged.

[DRAFT — maintainer to confirm] Record an artifact descriptor as
`source.config.report_artifact`, candidate-ID-keyed locations as
`report_locations`, and an extractor identifier as `extractor`. The complete
illustrative observation source below drafts all these names and example values;
the vocabulary digest is computed from (b). Lines are one-based inclusive;
byte spans are zero-based half-open spans in unmodified artifact bytes. A mention
has an empty locations object; each observation candidate has its own span.

```json
{
  "actor_id": "adr-importer",
  "config": {
    "operator_note": "preserved unrelated config",
    "report_vocabulary": {
      "identity": "nyx.adr-reports",
      "version": "1",
      "definition_sha256": "af84b5817bb785950774ab04cea9603d4c110c8ec3ac41405d5f2925ec9d5247"
    },
    "report_artifact": {
      "kind": "adr-path",
      "repository": "https://example.org/public/ProjectNyx.git",
      "path": "decisions/example.md",
      "revision": "1111111111111111111111111111111111111111",
      "blob": "2222222222222222222222222222222222222222",
      "subject_scope": "repo-path:[\"https://example.org/public/ProjectNyx.git\",\"decisions/example.md\"]"
    },
    "report_locations": {
      "candidate-example": {"start_line": 3, "end_line": 3, "start_byte": 22, "end_byte": 38}
    },
    "extractor": "nyx.adr-literal/1"
  }
}
```

#### (b) Definition schema, repository files and canonical hashing

[DRAFT — maintainer to confirm] Store definitions at
`config/report-vocabularies/sha256/<definition_sha256>.json`, using the digest
as filename rather than interpolated identity/version. Every release retains all
historical definitions, original checked-in file bytes and a manifest of their
identity/version/hash bindings; canonical bytes remain reproducible. Formatting
changes alone need no new version. No network retrieval substitutes a file.

[DRAFT — maintainer to confirm] A definition has exactly the JSON fields shown
below: format is `nyx.adr-report-vocabulary/1`; identity/version obey R2;
label/description are strings; entries is a nonempty finite set. Each entry has
exactly property, value_shape, artifact_scope, report_meaning, label, description,
all nonempty strings. Only these four property/shape/scope combinations are
supported. Exact names, labels, meanings and shape/scope tags are draft choices.
Duplicate properties/entries/JSON keys refuse before set sorting. Unknown fields,
regexes, arbitrary JSON Schema and executable predicates refuse.

```json
{
  "format": "nyx.adr-report-vocabulary/1",
  "identity": "nyx.adr-reports",
  "version": "1",
  "label": "Literal ADR and Git reports",
  "description": "Statements observed in pinned public artifacts, not world-truth assertions.",
  "entries": [
    {
      "property": "adr.title.literal",
      "value_shape": "literal-string",
      "artifact_scope": "adr-path",
      "report_meaning": "The ADR artifact at the recorded revision stated this literal title.",
      "label": "Title declaration",
      "description": "Preserves the observed heading text."
    },
    {
      "property": "adr.status.literal",
      "value_shape": "literal-string",
      "artifact_scope": "adr-path",
      "report_meaning": "The ADR artifact at the recorded revision stated this literal Status declaration.",
      "label": "Status declaration",
      "description": "Does not interpret acceptance or supersession authority."
    },
    {
      "property": "adr.implementation.literal",
      "value_shape": "literal-string",
      "artifact_scope": "adr-path",
      "report_meaning": "The ADR artifact at the recorded revision stated this literal Implementation declaration.",
      "label": "Implementation declaration",
      "description": "Does not infer implementation completion from prose."
    },
    {
      "property": "git.rename.report",
      "value_shape": "git-rename-report",
      "artifact_scope": "git-commit-report",
      "report_meaning": "Git reported this rename and similarity for the recorded commit and parent under the recorded capture configuration.",
      "label": "Git rename report",
      "description": "Establishes neither shared subject identity nor a rename handler."
    }
  ]
}
```

[DRAFT — maintainer to confirm] `literal-string` accepts a nonempty literal
Unicode string without trimming/normalization. `git-rename-report` accepts exactly
`{"status":"R092","old_path":<string>,"new_path":<string>,"similarity_percent":92}`;
paths are exact nonempty Git paths, percentage is an integer (not boolean), and
only the R7 pinned pair is supported. Its artifact descriptor extends (a) with
exactly parent_revision, old_blob, new_blob, capture_command, git_version and
capture_config. Its blob identifies the captured report bytes, not an ADR blob.
The report artifact has its own path-scoped subject, not an old/new subject link.

[DRAFT — maintainer to confirm] Parse definitions as strict UTF-8 JSON,
refusing duplicate keys, nonfinite numbers, invalid Unicode and unsupported fields
before hashing. Entries is explicitly a set: after duplicate refusal, sort by
ascending `nyx.hashing.canonical_json(entry).encode("utf-8")`. No other arrays
are supported by this schema. Ordered requests, source spans and reader inputs
are sequences and retain their order. Hash the complete validated definition
with sorted entries as
`hashlib.sha256(nyx.hashing.canonical_json(definition).encode("utf-8")).hexdigest()`.
Labels/descriptions and every definition field are included; its digest, paths,
signatures and retrieval timestamps are not injected into that object. Reuse the
existing serializer; this does not ratify another wire contract.

#### (c) Reviewed allowlist, public inputs and startup failures

[DRAFT — maintainer to confirm] Use `config/report-admission.json`, exactly
`{"format":"nyx.report-admission/1","admitted":[...]}`. Admitted is a set of
reviewed closed `{identity, version, definition_sha256}` triples, without
duplicates. Empty admission disables new external requests, not committed
retries. Load all retained definitions, including retired ones. Missing files,
unknown fields, duplicate keys/entries, bad digests, filename/hash mismatch,
unresolved triples and multiple hashes for one identity/version fail startup.

[DRAFT — maintainer to confirm] Use `config/public-report-inputs.json`, exactly
`{"format":"nyx.public-report-inputs/1","artifacts":[...]}`, whose set entries
are closed `{repository, path, revision, blob}` records with nonempty strings,
full pinned Git object IDs and reviewed public availability. Include the rename
transcript and later Python ADR 0009. No wildcard, mutable ref, reachable URL or
locally readable path confers permission. Trusted deployment configuration binds
the local checkout to a reviewed repository identifier; caller URLs do not.

[DRAFT — maintainer to confirm] Construct one coherent immutable policy
snapshot before exposing a writer or creating/modifying a store. Validate every
definition, allowlist and trusted producer binding. On an existing store, inspect
recorded declarations read-only against the preserved bundle; a missing historical
definition fails writer startup, not replay. Failure raises `ReportPolicyError`
with a reason and file/triple; launcher exits nonzero. No partial snapshot,
fallback, hot reload or append is permitted. An existing writer keeps its own
snapshot; only a successful restart activates replacement policy. Preserve
bundles with releases/restore material, without a database catalog.

#### (d) Trusted binding and producer-accessible routes

[DRAFT — maintainer to confirm] Trusted deployment construction binds an
immutable external-producer policy context to the owning
`writer.WriterConnection` before giving the importer controlled access. Every
request on that connection faces policy regardless of actor_id/source_class.
The importer cannot set/clear the binding, request a policy-free connection or
select an unrestricted per-request route. The application configures the context
and public-input bundle; submitted source.config never configures producer trust.
This is controlled in-process routing, not an authentication mechanism.

[DRAFT — maintainer to confirm] Guard `storage.append_submission` after full
committed-retry comparison and before new assignment/insertion. Guard
`storage.safe_append_event`, direct `storage._append_stage_two` access and shared
locked append helpers on that bound connection before new insertion, retaining
exact-pair retry behavior. `ingestion.submit`, `skeleton.record_mention`,
`skeleton.record_observation` and internal wrappers reach the same guard; wrappers
opening connections obtain the trusted binding from deployment construction.
Preparers can diagnose early but cannot replace append enforcement. No unchecked
helper is exposed to the producer. Raw SQL, unbound opens and arbitrary code with
equivalent database access are outside this controlled boundary, not protected
submission routes. Replay/publication of committed events performs no admission.

[DRAFT — maintainer to confirm] New-admission refusal uses `ReportPolicyError`
before event/payload/freshness writes, preserving event count/tip. Existing
collision refusal remains `IntegrityError` and precedes retirement checks. The
ingester/reader require explicit `projector_version` of `"1"` or `"2"`; missing
or other versions refuse without replacement. Existing legacy defaults and
frozen projector semantics remain unchanged.

#### (e) Repository-qualified path scope and retained associations

[DRAFT — maintainer to confirm] Scope is `repo-path:` followed by
`nyx.hashing.canonical_json([repository_identity, exact_git_path])`. Both are
nonempty reviewed strings; the repository identifier is recorded exactly and
the repository-relative Git path uses `/` without case/Unicode/URL normalization
or filesystem resolution. Scope spans revisions; full commit/blob IDs in each
report use the pinned object's native format, never abbreviations. Number,
similarity and rename scores are not scope keys or proof of global uniqueness.

[DRAFT — maintainer to confirm] First import bootstraps fresh mention/subject
and a constitutive link without confidence, with scope string as mention text.
Retain their recorded association. Later revisions reuse that same mention and
subject; never create a new mention and attach it to an existing subject. Validate
retained IDs against recorded mention/link; missing or inconsistent associations
refuse rather than matching by path or silently reallocating. A separately new
mention bootstraps its own fresh subject even for equal scope text. Rename
bootstraps the new path, retaining all old associations and candidates.

[DRAFT — maintainer to confirm] Retain caller manifests at
`scratch/imports/<run-id>/requests.json`, preserved with caller restore material.
Closed fields are format (`nyx.adr-import-requests/1`), projector_version,
associations (set of exact `{scope, mention_id, subject_id}` records) and requests
(ordered sequence of exact `{event_request, payload_request}` records containing
every semantic field). Persist explicit projector separately from ADR 0030's
semantic comparison; changing it is not an automatic retry upgrade. No new
writer queue or acknowledgment before commit is introduced.

#### (f) Literal extraction, refusal, source dates and request persistence

[DRAFT — maintainer to confirm] Decode pinned blob bytes as strict UTF-8;
invalid encoding/BOM refuses. Recognize declarations only outside code fences
(backtick/tilde runs of at least three characters, closed by the same character
with at least the opening length); unclosed fences refuse. Blockquotes/indented
examples yield no declarations. Preserve original source byte spans/line endings.

[DRAFT — maintainer to confirm] Title is a column-zero `# ` heading; preserve
everything after that delimiter except its terminal line ending, without trimming
or interpreting optional closing hashes. Status/Implementation recognize exact
column-zero `Status: ` / `Implementation: ` or
`- **Status:** ` / `- **Implementation:** `. Preserve the entire value, including
following nonblank continuation lines up to a blank, heading or next recognized
declaration, with internal line endings unchanged. Do not parse categories,
supersession prose, ADR numbers or completion from the literal values.

[DRAFT — maintainer to confirm] Missing fields produce no claim. Repeated
recognized titles/fields, empty explicit values, ambiguous/unterminated declarations
or column-zero Status/Implementation-like forms with unsupported delimiters
refuse the artifact's entire extraction before preparing requests. Excluded
quoted/fenced examples do not count as duplicates. No prose inference substitutes
an absent explicit declaration.

[DRAFT — maintainer to confirm] One artifact revision's extracted fields share
an observation, with exact draft properties, fresh candidates, explicit source
spans/support and `externally_checkable` report verifiability. Zero extracted
fields yields no property observation. Git extraction accepts only the pinned,
independently checked R092 transcript, producing (b)'s object and commit/parent/
blob/tool provenance. It creates neither an identity association nor rename action.

[DRAFT — maintainer to confirm] Sample one offset-bearing import occurred_at
per prepared artifact unit and retain its spelling; store source date text
separately in `source.config.source_dates`, without using it as recorded_at.
Ordinary ADR 0030 clock assignment remains intact, with no historical-import
override. Persist complete mention/observation requests and associations before
submission by same-directory atomic manifest replacement after flushing file
data; failure stops submission. Restore retains IDs, timestamps, config and
explicit projector. If a complete request cannot name a required belief at
preparation, refuse instead of rewriting it later to win a race.

#### (g) Named reader adapter, inputs and exact return shape

[DRAFT — maintainer to confirm] Name the adapter
`nyx.reports.read_report_details(conn, claim_candidate_ids, *, projector_version)`.
Input is a readable connection, nonempty ordered sequence of distinct named
candidate IDs and explicit `"1"`/`"2"`. Read candidate, mention, subject/link and
supporting event by their recorded IDs at one consistent published prefix; do not
list an index, publish pending events or select a scalar head. Missing IDs raise
`KeyError`; absent/inconsistent report provenance raises `IntegrityError`. Caller
names both contradictory reports; no claim of exhaustiveness over unrequested
records is implied.

[DRAFT — maintainer to confirm] Return exactly `{projector_version, publication,
reports}`. Publication is exactly `{log_position, as_of, stale}` under existing
named-read freshness semantics. Reports retains input order, one object per
candidate, with exactly these fields:

| Field | Exact draft content |
|---|---|
| claim_candidate_id, belief_id, mention_id, subject_id, property_id | Recorded strings, not inferred from numbers. |
| artifact | Complete recorded report_artifact descriptor, including exact revision/blob. |
| report_scope | Exactly `{meaning: "artifact_at_revision_stated", vocabulary: <recorded declaration>, artifact_scope: <recorded kind>}`. |
| value | Complete recorded literal string or Git report object. |
| verification_state, verifiability | Candidate fields, qualified by report_scope. |
| provenance | Exactly `{observation_event_id, occurred_at, recorded_at, event_hash, payload_hash, source, source_class, origin_type, location}`; complete recorded source and candidate's exact span. |

[DRAFT — maintainer to confirm] Document/display **“artifact A at revision R
stated X”**, with verification qualifying only that report. Return contradictory
and agreeing reports together without coalescing or recency winner. Disclose
staleness. Stored scope/provenance survives retirement without consulting current
admission. No listing or scalar-head contract is created.

#### (h) First-slice acceptance and frozen fixture packaging

The complete first-slice acceptance matrix follows under Proposed acceptance
cases. Policy outcomes derive from R1–R8 and accepted contracts; tests for marked
representations remain contingent on confirmation of those drafts.

[DRAFT — maintainer to confirm] Package exact artifacts under
`tests/fixtures/adr_reports/902467a-r092/`: before.md, after.md,
rename-report.bin, capture.json and later-python-0009.md. Capture with
`git -c diff.renames=true -c diff.renameLimit=0 -c core.quotePath=false diff-tree --no-commit-id --name-status -r -z -M50% 902467afa54887de0d15ab9f1a9d23403e9628cc^ 902467afa54887de0d15ab9f1a9d23403e9628cc -- decisions/0009-projection-parameters.md decisions/0010-projection-parameters.md`.
Record full parent/commit/blob IDs, Git version, exact command, effective
configuration/attributes and transcript digest. Independently check artifacts
using `git cat-file blob <pinned-blob-id>` and native Git object hashes; verify
the frozen transcript against the pinned trees at capture. Routine tests read
checked-in bytes/provenance without fetch or a live heuristic. Retain the
NUL-delimited transcript as binary evidence.

[DRAFT — maintainer to confirm] Use Git `2.53.0.windows.2` for capture and pin
the later input `decisions/0009-python-314-re-adopted-as-target.md` at
`531a679598dfbcce45a6a0a239c85be958ec55fd`, blob
`a495d359f6f7fff2b1edcba09b9a32044aab27b6`. These are locally verified proposed
fixture choices, still requiring public-input review. The R7 commit's parent is
`823b3ab776faf2635f37c8c3bcdd645c3850f784`; old/new ADR blobs are
`67e7f46e0cd558b64cebfea6af4ffda4fbb4cb81` and
`fe8f2699577a910206e558dfb8607a362db841a3`, respectively. Those object bindings
are checked facts of the already selected rename, not alternative rename choices.

## Verified relationships to earlier decisions

| Decision | Relationship |
|---|---|
| ADR 0001, Decision and Consequences | Observed signals may verify the claim actually observed. Here that claim is the artifact's statement; the reported proposition gains no world verification. Other origin mappings remain distinct and unimplemented. No amendment for option (a). |
| ADR 0006, Decision | Compare timestamps as instants; reject offset-less values; preserve stored spellings. Commit-time provenance does not authorize canonicalizing occurred_at or rewriting an envelope. No amendment. |
| ADR 0019 sections 1–4 and 6, as amended by 0021/0023 | Separate mention bootstrap creates its own scoped subject; later observations name recorded identities. Renames/similarity create no accepted association basis. No amendment. |
| ADR 0021 sections 1–4 | Bootstrap is constitutive without numeric confidence; it proves neither faithful extraction nor shared subject identity. Retained-mention reuse creates no new association with an existing subject. No amendment. |
| ADR 0023 sections 1–4 and 6 | Exact opaque property IDs, fresh ClaimCandidates, existing-mention ingestion and retained semantic contents continue. An ingestion-only vocabulary restriction is not a property registry or replay check. No new origin or authority is supplied; DreamEmission remains a reserved distinct role. No amendment for option (a). |
| ADR 0024 sections 1–3 | Candidate sets have no authoritative head; recency and value agreement do not resolve them. Displaying source reports does not supply the deferred scalar-read contract. No amendment. |
| ADR 0026, Decision and Consequences | Retrieval exposures, Dream references and activation records remain usage, never evidence or lineage. Observing an external artifact is not permission to turn repeated retrieval into another supporting signal. No usage recorder is authorized. No amendment. |
| ADR 0030 sections 1–6 | Keep sole-writer exclusion, complete semantic collision checks before new admission, original committed-pair return and separate append/publication recovery. Caller request persistence is not a durable writer queue or historical recorded_at override. No amendment. |
| ADR 0032, Decision | Require explicit projector_version on the ingester and adapter, preserve accepted names/legacy allowlist and frozen bytes. No default, upgrade or fallback. No amendment. |
| Review rulings R3–R5 (2026-09-22) | Report-scoped option (a), immutable per-event declaration and public-only policy remain. An inventoried future listing copy is permitted but deferred; it is not required for report-detail reads. These rulings do not independently ratify this ADR. |
| Proposed ADR 0028 sections 9 and 11 | The index is an inventoried content copy; a future protected deployment must cover all managed copies. Public-only policy does not ratify the erasure protocol or claim its Gate 3 obligations passed. No edit proposed to that draft. |
| Proposed ADR 0029 sections 1–7 | Its DreamEmission origin and no-promotion boundary remain explicit and Proposed. Report vocabulary is no loophole for laundering an internal emission into Layer A as an artifact report or promoting its text into evidence. Independent acquisition remains a separate observation; emission recording/causal-link mechanics stay undecided. No edit proposed to that draft. |

## Exact accepted-ADR edits required on acceptance

None for option (a) as an ingestion-time policy using existing compatible event
contents: it changes neither property identity, replay validation, candidate
standing nor historical projector semantics. ADR 0023 section 1's “No property
registry” sentence remains unchanged.

R1 selects the compatible source.config location. No dedicated envelope fields
or payload expansion are proposed, so no exception to ADR 0025 section 1's
unchanged-format promise is needed. Section 8's exact declaration and admission
choices still need maintainer confirmation and explicit acceptance.

Option (b) requires a separately explicit origin/state/projector contract.
It cannot change the observed-origin rule of ADR 0001 or frozen projector bytes
by implication. No exact origin-mapping amendment is selected in this draft.
No existing ADR or specification is edited.

## Proposed acceptance cases

### First slice: complete required matrix

These outcomes are required by R1–R8 and the accepted dependency contracts.
Tests of section 8's unconfirmed names/shapes/algorithms await their confirmation;
the matrix itself does not convert a draft choice into a ruling.

| Case | Required evidence |
|---|---|
| Declaration and compatibility | Both mention and observation record the closed vocabulary declaration, retain unrelated config and use unchanged envelope/payload formats. Historical undeclared events remain byte-identical and replay unchanged. |
| Declaration refusal | Missing/null/nonobject declaration, missing/extra/wrong-type fields, empty identity/version, invalid or mismatched hash, unknown property, incompatible scope/value and an invented but correctly hashed definition refuse before new append; count/tip stay unchanged. Case and NFC/NFD strings remain exact, without identity normalization. |
| Definition refusal | Duplicate entries/properties/JSON keys, unknown schema fields, unsupported constraints and identity/version reassignment refuse. A merely valid caller hash never supplies reviewed trust. |
| Canonical definition fixtures | Different whitespace/object-key order preserve canonical hash; changed property/scope/constraint/description/label changes it and requires new version/hash. Set permutations preserve hash; semantic sequences retain order. Original source-byte changes alone need no version. |
| Trusted-route coverage | Try dropping declaration, relabeling actor_id/source_class and switching each route available in section 8(d)'s controlled producer boundary. All new submissions reach writer-owned classification/admission. Faithful extraction and database bypass are separately evidenced. |
| Startup and snapshot lifetime | Missing/malformed/hash-inconsistent bundles or allowlists fail before writes. Editing policy files while running changes no loaded admission. Restart activates a complete validated policy. Historical definitions/bindings remain in release/restore material. |
| Equivalent committed retry after retirement | Commit, lose acknowledgment, retire vocabulary and restart; resubmit identical semantics and obtain the original full pair, timestamps, IDs, associations, config, predecessor and hashes without new evidence or new admission. |
| Conflicting retry after retirement | Reuse event ID/idempotency key with any semantic difference, including config-only vocabulary change; collision refuses before retirement checks, without silently returning or rewriting the original. |
| Uncommitted retry after retirement | Persist but do not commit a request, retire/restart and retry; refuse under the startup snapshot without reminting or rewriting. A still-running owner uses its unchanged pre-retirement policy. |
| Partial bootstrap under policy change | Commit mention only, retire/restart; equivalent mention retry returns original pair, pending observation refuses. Mention remains valid without a claim and grants no grandfathering. |
| Crash before append and caller restore | Persist complete semantic requests/projector/associations, crash and restore retained manifest plus release bundle; retry identical contents under startup admission. Retirement refuses without repair. No acknowledgment is mistaken for commit. |
| Crash after append / before publication | After committed append, fail publication or lose acknowledgment, restore a consistent store/retained-request backup and recover the committed prefix without reappend. Return original pair on retry; full replay at equal cutoff/time/version preserves content/hashes/bytes. Policy changes do not affect publication/replay. |
| Literal extraction and artifact refusal | Exercise literal title/Status/Implementation, missing fields, preserved multiline text, repeated/empty/ambiguous declarations, fenced/quoted examples and all confirmed grammar forms. Missing fields invent no claim; ambiguity refuses the whole artifact before its requests. Never infer categories or implementation completion. |
| Reader report scope | Call the named adapter with verified reports; inspect candidate identity, exact repository/path/revision/blob, report scope, literal value, location and recorded provenance. Present artifact-at-revision-stated, never embedded world truth; disclose stale publication. |
| Contradictory and agreeing reports | Across revisions reuse retained mention/subject and current belief with fresh candidates. Read contradictory reports together, including reverse arrival order, without latest winner. Agreeing distinct candidates remain distinct; one supporting observation is not multiplied into independent evidence. |
| Frozen rename and later Python ADR 0009 | Import checked-in exact before/after ADRs, pinned R092 transcript and actual later Python ADR 0009. Distinct old/new/Python path subjects, old candidates retained, commit-scoped Git-report subject/meaning and no number-based aliases; no rename handler or merge. Capture is independently checked against pinned objects, routine tests require no fetch. |
| Replay versus policy / privileged bypass | Replay compatible historical/retired/undeclared events without definitions or allowlist. In a disposable test store demonstrate privileged direct insertion can bypass admission while passing ordinary checks where structurally valid; verifier success never attests writer-policy enforcement or faithful extraction. |
| Public inputs, separate dates and explicit selection | Unreviewed/private inputs refuse. Source dates stay separate from retained import occurred_at and writer-assigned recorded_at. Missing projector refuses; explicit supported selections retain all existing golden bytes, roots, hashes and recovery behavior. No implicit switch or default. |
| Deferred evidence boundary | Option-(a) history stays unchanged by future separately accepted option (b); usage/internal Dream emissions gain no evidence path. No protected deployment or listing/indexing is implemented by this slice. |

### Deferred cases retained for their own later contracts (R8)

- Rebuilding the future listing index from Layer A reproduces mention text and
  associations; its stale state remains disclosed. All persisted copies are
  inventoried, and a private corpus refuses the deployment policy until its
  accepted/implemented/passed erasure requirements are met.
- Option-(a) history retains its original meaning and bytes after a separately
  ratified option (b). Neither usage nor internal Dream emissions acquire an
  evidence path through the report vocabulary.
