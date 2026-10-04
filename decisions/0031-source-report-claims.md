# ADR 0031: Report-Scoped External Content

Status: Accepted — ratified by the maintainer, 2026-10-04

Date: 2026-09-22

Implementation: Slice 1 complete in (B) commits `3e52ac2e359b61e36a74e69df36e518605870538`, `b5319a76643cf8e3bacd40a17f856270082671e6`, `66df05046f3ddb9fd9c07678c9aa1aeca811de1f`, `5121afd3ac3d72f73e1bf2b7267d9e8e646d1c54`, `bb27dfaade6725808b9d4c3fdbf75eb6d18cb387`, `40f6ff0d30e9ad1f4ba47a6feaa257ff51545777`, `e4e14266e3e10e89c16d63df6bcdd46c4b3133bf`, `94b965aa397a6542884bb4f73b82553a9e5544e9`; slice 1b remains deferred.

Supersedes: No accepted ADR for the report-scoped option (a) defined here. Option (b) is an undecided target, not a new origin mapping or permission to change frozen projectors.

Related: [ADR 0001](0001-observation-recorded-resolves-to-verified.md), [ADR 0006](0006-occurred-at-comparison-is-instant-based-not-lexical.md), [ADR 0019](0019-identity-bootstrap.md), [ADR 0021](0021-bootstrap-link-treatment.md), [ADR 0023](0023-stage-two-contract.md), [ADR 0024](0024-no-authoritative-head.md), [ADR 0025](0025-incremental-result-commitment.md), [ADR 0026](0026-usage-is-not-evidence.md), [ADR 0030](0030-sole-writer-and-positional-fields.md), [ADR 0032](0032-explicit-stage-two-projector-selection.md), proposed [ADR 0028](0028-redaction-and-crypto-shredding.md) and proposed [ADR 0029](0029-dream-emission-semantics.md), [review and rulings](../design/2026-09-22-review-and-next-steps.md#rulings-2026-09-22).

## Context

The shipped stage-two origin mapping makes observed-origin ClaimCandidates
verified. It does not interpret arbitrary property names or enforce whether an
external artifact's statement has been mistaken for the truth of its contents.
A source label or repeated ingestion cannot close that semantic distinction.

R3 selects report-scoped claims now (option a), with a distinct origin mapping
recorded as the future target (option b). R4 restricts the corpus, R5 permits an
inventoried derived mention-text copy, and the rename ruling preserves scoped
subjects. This ADR records the ratified direction; it does not
implement an ingester, writer enforcement, origin handler or listing API.

The maintainer's 2026-10-03 first-slice rulings R1–R8 and the 2026-10-04
scope ruling are incorporated below. Section 8 records the ratified first-slice
contract. Implementation remains None.

## Ratification

The maintainer ratified this ADR on 2026-10-04: all previously marked choices
are confirmed, including occurred_at = import time with source dates separately
in source.config.source_dates; Status, Implementation and title values end at a
blank line, heading or line beginning with "- ", with every other following line
continuing the value and internal line endings preserved; publication is exactly
{log_position, stale}, with each report carrying its belief's recorded
projected_as_of; and reviewed public-input entries are exactly {repository,
revision (full commit ID), path_prefix}, deterministically expanded to pinned
(path, blob) pairs, with exact per-event provenance and refusal outside every
reviewed entry. The protected-format dependency remains for 0027/0028 ratification.

## Ratified contract

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
carrying vocabulary identity, version, digest algorithm, canonicalization profile
and canonical-definition digest. Unrelated config fields are preserved. This
restriction is prospective: historical
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

The first vocabulary is finite and ADR-specific; the enforcement mechanism is
producer-generic. Each entry defines an exact property string, allowed value
shape, artifact scope and report meaning. Duplicate entries,
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
explicit Implementation declaration: only `adr.title.literal`,
`adr.status.literal` and `adr.implementation.literal` belong to slice 1 under
the maintainer's 2026-10-04 scope ruling. Ingestion of Git rename reports,
including the `git.rename.report` vocabulary entry, `git-rename-report` value
shape and its capture tooling, is deferred to slice 1b. The frozen R092 fixture
remains a TEST of path identity, not a fourth ingested property in slice 1.
Literal text is preserved; prose is not interpreted into
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
preservation of the old subject's claims, and the later Python ADR 0009's separate
subject. The frozen R092 transcript supplies TEST provenance, not a slice-1
Git-report claim, subject or ingestion route. The “0009” path must not alias the later
Python-target ADR numbered 0009, nor may “0010” become a universal identity key.
This is a fixture requirement for the unbuilt ingester, not a rename handler.

Check in the exact before/after artifacts and rename report, capture command,
tool configuration and revision provenance. Independently compare the capture
with pinned Git objects; routine tests need no fetch or live rename heuristic.
Include the later Python ADR 0009 as a real imported artifact. Assert distinct
subjects, retained old candidates and no aliasing across ADR numbers. Section
8(h) drafts exact TEST packaging without substituting another rename. R7 does
not require production capture tooling in slice 1: the `git.rename.report`
entry, `git-rename-report` value shape and Git-report ingestion/capture tooling
are deferred to slice 1b under the 2026-10-04 scope ruling.

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

### 8. Exact ratified first-slice contract

R1–R8 settle the policy direction. The exact representations and additional
refusal details below were confirmed at ratification, addressing worksheet B1–B6.

#### (a) Declaration keys and complete source example

Reserve `source.config.report_vocabulary`,
exactly `{identity, version, digest_algorithm, canonicalization_profile,
definition_digest}`. Identity/version follow R2; digest_algorithm is `sha256`,
canonicalization_profile is `nyx.canonical-json/1` (a label for the exact
existing serializer and section 8(b)'s set treatment, not a new wire standard),
and definition_digest is exactly 64 lowercase hexadecimal characters.
Missing/extra nested fields, wrong types or invalid digest syntax refuse new
external admission.
Unrelated config is preserved unchanged.

Record an artifact descriptor as
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
      "digest_algorithm": "sha256",
      "canonicalization_profile": "nyx.canonical-json/1",
      "definition_digest": "73eed2df21cb3fd66388b186b397301c92bedfaadcf1b51aa822de0e1a1f8e8f"
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

Store definitions at
`config/report-vocabularies/sha256/<definition_digest>.json`, using the digest
as filename rather than interpolated identity/version. Every release retains all
historical definitions, original checked-in file bytes and a manifest of their
identity/version/hash bindings; canonical bytes remain reproducible. Formatting
changes alone need no new version. No network retrieval substitutes a file.

A definition has exactly the JSON fields shown
below: format is `nyx.adr-report-vocabulary/1`; identity/version obey R2;
label/description are strings; entries is a nonempty finite set. Each entry has
exactly property, value_shape, artifact_scope, report_meaning, label, description,
all nonempty strings. Slice 1 supports only the three literal ADR
property/shape/scope combinations below.
Exact names, labels, meanings and shape/scope tags are confirmed choices.
Duplicate properties/entries/JSON keys refuse before set sorting. Unknown fields,
regexes, arbitrary JSON Schema and executable predicates refuse.

```json
{
  "format": "nyx.adr-report-vocabulary/1",
  "identity": "nyx.adr-reports",
  "version": "1",
  "label": "Literal ADR reports",
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
    }
  ]
}
```

`literal-string` accepts a nonempty literal
Unicode string without trimming/normalization. `git-rename-report` is not an
admitted slice-1 value shape; its vocabulary and ingestion contract await slice
1b. Slice 1's artifact scope is only `adr-path`.

Parse definitions as strict UTF-8 JSON,
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

Use `config/report-admission.json`, exactly
`{"format":"nyx.report-admission/1","admitted":[...]}`. Admitted is a set of
reviewed closed `{identity, version, digest_algorithm, canonicalization_profile,
definition_digest}` declarations, without duplicates. Empty admission disables
new external requests, not committed
retries. Load all retained definitions, including retired ones. Missing files,
unknown fields, duplicate keys/entries, bad digests, filename/hash mismatch,
unresolved declarations, unsupported algorithm/profile and multiple digest
bindings for one identity/version fail startup.

Use `config/public-report-inputs.json`, exactly
`{"format":"nyx.public-report-inputs/1","artifacts":[...]}`, whose reviewed set
entries are exactly `{repository, revision, path_prefix}` records with nonempty
strings and reviewed public availability. Revision is a full commit ID, never a
mutable ref. Each entry expands deterministically to the exact `(path, blob)`
pairs in that commit whose repository-relative Git path begins with the literal
path_prefix. No glob matching or wildcard beyond that literal prefix is allowed.
Each event still records its exact repository, path, revision and blob; a blob
outside every reviewed entry is refused. Reviewed entries cover the before/after
ADR artifacts and later Python ADR 0009; the rename transcript is TEST evidence,
not an admitted slice-1 artifact. A reachable URL or locally readable path confers
no permission. Trusted deployment configuration binds the local checkout to a
reviewed repository identifier; caller URLs do not.

Construct one coherent immutable policy
snapshot before exposing a writer or creating/modifying a store. Validate every
definition, allowlist, public-input entry and trusted producer binding.
Resolve each full commit ID in its bound repository and expand the literal
prefix against that pinned tree before admission; unavailable commits/blobs,
mutable refs, malformed entries or failed expansion fail startup. New requests
must match an exact repository/revision/path/blob in the reviewed expansion.
On an existing store, inspect
recorded declarations read-only against the preserved bundle; a missing historical
definition fails writer startup, not replay. Failure raises `ReportPolicyError`
with a reason and file/declaration; launcher exits nonzero. No partial snapshot,
fallback, hot reload or append is permitted. An existing writer keeps its own
snapshot; only a successful restart activates replacement policy. Preserve
bundles with releases/restore material, without a database catalog.

#### (d) Trusted binding and producer-accessible routes

Trusted deployment construction binds an
immutable external-producer policy context to the owning
`writer.WriterConnection` before giving the importer controlled access. Every
request on that connection faces policy regardless of actor_id/source_class.
The importer cannot set/clear the binding, request a policy-free connection or
select an unrestricted per-request route. The application configures the context
and public-input bundle; submitted source.config never configures producer trust.
This is controlled in-process routing, not an authentication mechanism.

Guard `storage.append_submission` after full
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

New-admission refusal uses `ReportPolicyError`
before event/payload/freshness writes, preserving event count/tip. Existing
collision refusal remains `IntegrityError` and precedes retirement checks. The
ingester/reader require explicit `projector_version` of `"1"` or `"2"`; missing
or other versions refuse without replacement. Existing legacy defaults and
frozen projector semantics remain unchanged.

#### (e) Repository-qualified path scope and retained associations

Scope is `repo-path:` followed by
`nyx.hashing.canonical_json([repository_identity, exact_git_path])`. Both are
nonempty reviewed strings; the repository identifier is recorded exactly and
the repository-relative Git path uses `/` without case/Unicode/URL normalization
or filesystem resolution. Scope spans revisions; full commit/blob IDs in each
report use the pinned object's native format, never abbreviations. Number,
similarity and rename scores are not scope keys or proof of global uniqueness.

First import bootstraps fresh mention/subject
and a constitutive link without confidence, with scope string as mention text.
Retain their recorded association. Later revisions reuse that same mention and
subject; never create a new mention and attach it to an existing subject. Validate
retained IDs against recorded mention/link; missing or inconsistent associations
refuse rather than matching by path or silently reallocating. A separately new
mention bootstraps its own fresh subject even for equal scope text. Rename
bootstraps the new path, retaining all old associations and candidates.

Retry request manifests are durable operational
data stored BESIDE THE STORE, at `<store>.imports/<run-id>/requests.json`, never
in `scratch/`. Preserve them with the backup bundle, not as disposable checkout
scratch files. Resuming an interrupted import reuses the saved complete request;
a reconstructed request with fresh IDs is not a retry.
Closed fields are format (`nyx.adr-import-requests/1`), projector_version,
associations (set of exact `{scope, mention_id, subject_id}` records) and requests
(ordered sequence of exact `{event_request, payload_request}` records containing
every semantic field). Persist explicit projector separately from ADR 0030's
semantic comparison; changing it is not an automatic retry upgrade. No new
writer queue or acknowledgment before commit is introduced.

#### (f) Literal extraction, refusal, source dates and request persistence

Decode pinned blob bytes as strict UTF-8;
invalid encoding/BOM refuses. Recognize declarations only outside code fences
(backtick/tilde runs of at least three characters, closed by the same character
with at least the opening length); unclosed fences refuse. Blockquotes/indented
examples yield no declarations. Preserve original source byte spans/line endings.

Title is a column-zero `# ` heading; preserve everything after that
delimiter without trimming or interpreting optional closing hashes.
Status/Implementation recognize exact column-zero `Status: ` / `Implementation: `
or `- **Status:** ` / `- **Implementation:** `. A Status, Implementation or title
value ends at a blank line, a heading, or any line beginning with "- " (a new
list item). Every other following line continues the value, with internal line
endings preserved; exclude only the final value line's terminal line ending.
This keeps bullet-style metadata such as "- **Date:**", "- **Scope:**" and
"- **Relates to:**" out of the Status value. Do not parse categories, supersession
prose, ADR numbers or completion from the literal values.

A candidate declaration is precisely the keyword
`Status` or `Implementation`, immediately followed by optional `**` markup,
then a colon. At column zero, detection permits only an optional `- ` prefix
and optional opening `**` before that keyword; its grammar is
`^(?:- )?(?:\*\*)?(Status|Implementation)(?:\*\*)?:`.
This detects candidates, not additional accepted extraction forms: only the four
literal prefixes above are recognized. Unsupported detected candidates refuse.
Column-zero prose such as “Implementation is separate work.” or “Status includes
the explicit partial-supersession notice.” lacks that keyword/markup/colon
sequence and is ignored, never refused or inferred as a declaration.

Missing fields produce no claim. Repeated
recognized titles/fields, empty explicit values, ambiguous/unterminated declarations
or candidate declarations with unsupported markup/delimiters
refuse the artifact's entire extraction before preparing requests. Excluded
quoted/fenced examples do not count as duplicates. No prose inference substitutes
an absent explicit declaration.

One artifact revision's extracted fields share
an observation, with exact properties, fresh candidates, explicit source
spans/support and `externally_checkable` report verifiability. Zero extracted
fields yields no property observation. No Git-report extraction, capture tool,
Git-report candidate or subject is implemented in slice 1; those await slice 1b.

**Recorded corpus survey (2026-10-04):** `git log --all -- decisions` and a
full-context, full-index, no-renames patch survey of that same locally reachable
history found 53 decision-changing commits and 92 distinct numbered Markdown
artifact revisions across 34 exact paths. An artifact revision means a unique
`(Git path, blob ID)`, not every unchanged commit snapshot. The baseline is
`a30e94acf0ef86f881a7d68b9d950aa3a6740656`; this uncommitted revision is not counted. Full reconstructed blob
bytes were checked against their native Git object digests; no fetch was used.

| Declaration form outside excluded examples | Artifact revisions containing the form |
|---|---:|
| `Status: ` | 70 |
| `- **Status:** ` | 22 |
| `Implementation: ` | 70 |
| `- **Implementation:** ` | 0 |

The rules above extract all 92 revisions and refuse 0: there are no invalid
UTF-8/BOMs, unclosed fences, repeated/empty recognized fields or unsupported
candidate declarations in the surveyed corpus. Twenty-two revisions lack an
Implementation declaration and one early escaped-heading revision lacks a
literal `# ` title; missing fields yield no claim. This gives 253 literal claims
(91 titles, 92 statuses, 70 implementation declarations), not inferred metadata.
Nineteen revisions contain column-zero keyword-led prose, including the two
examples above; all remain extractable. A broad keyword-prefix interpretation
would incorrectly refuse those 19. The ratified list-item boundary changes
22 artifact revisions' Status values by excluding following bullet metadata;
no Implementation value changes, and no extracted value contains a "- **"
metadata line. The complete path/blob change list and before/after literals are
recorded in the ratification survey handoff. These counts characterize the pinned
local history, not a production importer or every possible future declaration form.

Sample one offset-bearing import occurred_at
per prepared artifact unit and retain its spelling; store source date text
separately in `source.config.source_dates`, without using it as recorded_at.
Ordinary ADR 0030 clock assignment remains intact, with no historical-import
override. Persist complete mention/observation requests and associations before
submission by same-directory atomic manifest replacement after flushing file
data; failure stops submission. Restore retains IDs, timestamps, config and
explicit projector. If a complete request cannot name a required belief at
preparation, refuse instead of rewriting it later to win a race.

#### (g) Named reader adapter, inputs and exact return shape

Name the adapter
`nyx.reports.read_report_details(conn, claim_candidate_ids, *, projector_version)`.
Input is a readable connection, nonempty ordered sequence of distinct named
candidate IDs and explicit `"1"`/`"2"`. Read candidate, mention, subject/link and
supporting event by their recorded IDs at one consistent published prefix; do not
list an index, publish pending events or select a scalar head. Missing IDs raise
`KeyError`; absent/inconsistent report provenance raises `IntegrityError`. Caller
names both contradictory reports; no claim of exhaustiveness over unrequested
records is implied.

Return exactly `{projector_version, publication,
reports}`. Publication is exactly `{log_position, stale}` under existing
named-read freshness semantics. There is no publication.as_of. Reports retains
input order, one object per candidate, with exactly these fields:

| Field | Exact content |
|---|---|
| claim_candidate_id, belief_id, mention_id, subject_id, property_id | Recorded strings, not inferred from numbers. |
| artifact | Complete recorded report_artifact descriptor, including exact revision/blob. |
| report_scope | Exactly `{meaning: "artifact_at_revision_stated", vocabulary: <recorded declaration>, artifact_scope: <recorded kind>}`. |
| value | Complete recorded literal string in slice 1; Git report objects are deferred to slice 1b. |
| verification_state, verifiability | Candidate fields, qualified by report_scope. |
| projected_as_of | The report's belief's recorded projected_as_of, not a publication-wide or newly sampled time. |
| provenance | Exactly `{observation_event_id, occurred_at, recorded_at, event_hash, payload_hash, source, source_class, origin_type, location}`; complete recorded source and candidate's exact span. |

Document/display **“artifact A at revision R
stated X”**, with verification qualifying only that report. Return contradictory
and agreeing reports together without coalescing or recency winner. Disclose
staleness. Stored scope/provenance survives retirement without consulting current
admission. No listing or scalar-head contract is created.

#### (h) First-slice acceptance and frozen fixture packaging

The complete first-slice acceptance matrix follows under Acceptance cases.
Policy outcomes derive from R1–R8, the ratification rulings and accepted contracts.

Package exact artifacts under
`tests/fixtures/adr_reports/902467a-r092/`: before.md, after.md,
rename-report.bin, capture.json and later-python-0009.md. These are TEST inputs;
slice 1 imports only the ADR Markdown artifacts and retains the transcript as
checked-in regression evidence. The recorded capture command is
`git -c diff.renames=true -c diff.renameLimit=0 -c core.quotePath=false diff-tree --no-commit-id --name-status -r -z -M50% 902467afa54887de0d15ab9f1a9d23403e9628cc^ 902467afa54887de0d15ab9f1a9d23403e9628cc -- decisions/0009-projection-parameters.md decisions/0010-projection-parameters.md`.
Record full parent/commit/blob IDs, Git version, exact command, effective
configuration/attributes and transcript digest. Fixture provenance records
independent checks of artifacts using `git cat-file blob <pinned-blob-id>` and
native Git object hashes; verify
the frozen transcript against the pinned trees at its capture. Routine tests read
checked-in bytes/provenance without fetch or a live heuristic. Retain the
NUL-delimited transcript as binary TEST evidence. Building a Git-report capture
tool or ingesting this transcript is deferred to slice 1b; fixture packaging
does not add a producer or report property in slice 1.

Pin the frozen TEST capture provenance to Git
`2.53.0.windows.2` and the later input
`decisions/0009-python-314-re-adopted-as-target.md` at
`531a679598dfbcce45a6a0a239c85be958ec55fd`, blob
`a495d359f6f7fff2b1edcba09b9a32044aab27b6`. These are locally verified confirmed
fixture choices; deployment requires reviewed public-input entries. The R7 commit's parent is
`823b3ab776faf2635f37c8c3bcdd645c3850f784`; old/new ADR blobs are
`67e7f46e0cd558b64cebfea6af4ffda4fbb4cb81` and
`fe8f2699577a910206e558dfb8607a362db841a3`, respectively. Those object bindings
are checked facts of the already selected rename, not alternative rename choices.

## Forward compatibility and recorded dependencies

Proposed ADR 0027 section 3, component E, would make `events.source` encode only
the opaque actor_id; its private source configuration would be sealed. Proposed
ADR 0028's persistence inventory (`0028-redaction-and-crypto-shredding.md:754`)
likewise requires private source.config to be sealed. These are proposed formats,
not current restrictions on slice-1 events or ratification of protected storage.

[DEPENDENCY — decide at 0027/0028 ratification] Decide where the vocabulary
declaration lives under the protected format. It must stay readable for
interpreting report scope. This records a requirement, without selecting a public
envelope field, protected-body selector, access entitlement or erasure-surviving
representation. Slice-1 declarations in compatible source.config are unaffected;
future authority must settle placement/visibility and any format compatibility.

The declaration names `digest_algorithm` and
`canonicalization_profile` alongside `definition_digest`, as in section 8(a).
The algorithm is `sha256` and profile is `nyx.canonical-json/1`, referring
only to the described existing canonical bytes and finite definition schema.
The declaration commits identity/version and that qualified digest, not a full
definition. Bare digest naming cannot conceal which algorithm/profile produced
it; a future format does not silently reinterpret those recorded identifiers.

Enforcement is producer-generic; only the first vocabulary is ADR-specific.
Later producers—public-document quote reports, chat-message reports and MCP—add
reviewed vocabularies without changing declaration/admission/retry enforcement.
Their exact property meanings, scope, extraction and any additional value shapes
need their own complete reviewed contracts; naming them supplies no defaults or
permission to ingest private content.

A vocabulary declaration is neither an authorization nor a principal claim.
ADR 0020 keeps attribution distinct from permission; proposed ADR 0027's principal
model must not be inferred from a vocabulary identity, version, digest or actor_id.
The declaration qualifies report meaning and admission, not who owns a claim or
may supersede it.

Events carry only identity/version and the algorithm/profile-qualified digest.
A future database catalog can import repository definitions by digest without
migrating any event. The exact definitions and historical bindings remain
preserved; replay stays independent of current catalog/policy availability.
This records forward compatibility, not implementation of a catalog.

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

## Relationships to accepted ADRs at ratification

None for option (a) as an ingestion-time policy using existing compatible event
contents: it changes neither property identity, replay validation, candidate
standing nor historical projector semantics. ADR 0023 section 1's “No property
registry” sentence remains unchanged.

R1 selects the compatible source.config location. No dedicated envelope fields
or payload expansion are proposed, so no exception to ADR 0025 section 1's
unchanged-format promise is needed. Section 8's exact declaration and admission
choices are confirmed by the maintainer's 2026-10-04 ratification.

Option (b) requires a separately explicit origin/state/projector contract.
It cannot change the observed-origin rule of ADR 0001 or frozen projector bytes
by implication. No exact origin-mapping amendment is selected in this draft.
No existing ADR or specification is edited.

## Acceptance cases

### First slice: complete required matrix

These outcomes are required by R1–R8, the 2026-10-04 ratification rulings
and the accepted dependency contracts. Implementation remains None; this matrix
specifies required evidence rather than claiming those tests have run.

| Case | Required evidence |
|---|---|
| Declaration and compatibility | Both mention and observation record the closed vocabulary declaration, retain unrelated config and use unchanged envelope/payload formats. Historical undeclared events remain byte-identical and replay unchanged. |
| Declaration refusal | Missing/null/nonobject declaration, missing/extra/wrong-type fields, empty identity/version, unsupported digest algorithm/canonicalization profile, invalid or mismatched digest, unknown property, incompatible scope/value and an invented but correctly hashed definition refuse before new append; count/tip stay unchanged. Case and NFC/NFD strings remain exact, without identity normalization. |
| Definition refusal | Duplicate entries/properties/JSON keys, unknown schema fields, unsupported constraints and identity/version reassignment refuse. A merely valid caller hash never supplies reviewed trust. |
| Canonical definition fixtures | Different whitespace/object-key order preserve canonical hash; changed property/scope/constraint/description/label changes it and requires new version/hash. Set permutations preserve hash; semantic sequences retain order. Original source-byte changes alone need no version. |
| Trusted-route coverage | Try dropping declaration, relabeling actor_id/source_class and switching each route available in section 8(d)'s controlled producer boundary. All new submissions reach writer-owned classification/admission. Faithful extraction and database bypass are separately evidenced. |
| Startup and snapshot lifetime | Missing/malformed/hash-inconsistent bundles or allowlists, malformed public-input entries, mutable refs, unavailable pinned commits/blobs or failed literal-prefix expansion fail before writes. Editing policy files while running changes no loaded admission. Restart activates a complete validated policy. Historical definitions/bindings remain in release/restore material. |
| Equivalent committed retry after retirement | Commit, lose acknowledgment, retire vocabulary and restart; resubmit identical semantics and obtain the original full pair, timestamps, IDs, associations, config, predecessor and hashes without new evidence or new admission. |
| Conflicting retry after retirement | Reuse event ID/idempotency key with any semantic difference, including config-only vocabulary change; collision refuses before retirement checks, without silently returning or rewriting the original. |
| Uncommitted retry after retirement | Persist but do not commit a request, retire/restart and retry; refuse under the startup snapshot without reminting or rewriting. A still-running owner uses its unchanged pre-retirement policy. |
| Partial bootstrap under policy change | Commit mention only, retire/restart; equivalent mention retry returns original pair, pending observation refuses. Mention remains valid without a claim and grants no grandfathering. |
| Crash before append and caller restore | Persist complete semantic requests/projector/associations in durable manifests beside the store, crash and restore retained manifest plus release bundle; retry the saved complete request under startup admission. Fresh-ID reconstruction is not a retry. Retirement refuses without repair. No acknowledgment is mistaken for commit. |
| Crash after append / before publication | After committed append, fail publication or lose acknowledgment, restore a consistent store/retained-request backup and recover the committed prefix without reappend. Return original pair on retry; full replay at equal cutoff/time/version preserves content/hashes/bytes. Policy changes do not affect publication/replay. |
| Literal extraction and artifact refusal | Exercise only adr.title.literal, adr.status.literal and adr.implementation.literal, missing fields, values ending at blank lines/headings/any new "- " list item, all other following lines continuing with internal line endings preserved, and bullet-style Date/Scope/Relates-to metadata excluded from Status values, repeated/empty/ambiguous declarations, fenced/quoted examples and the precise candidate grammar. Keyword-led prose without the colon sequence, including “Implementation is separate work.” and “Status includes the explicit partial-supersession notice.”, is ignored and never refused. Unsupported detected declaration markup refuses the whole artifact before its requests. Never infer categories or implementation completion. |
| Reader report scope | Call the named adapter with verified reports; inspect candidate identity, exact repository/path/revision/blob, report scope, literal value, location and recorded provenance. Return publication exactly {log_position, stale}, without publication.as_of; each report includes its belief's recorded projected_as_of, including differing belief projection times. Present artifact-at-revision-stated, never embedded world truth; disclose stale publication. |
| Contradictory and agreeing reports | Across revisions reuse retained mention/subject and current belief with fresh candidates. Read contradictory reports together, including reverse arrival order, without latest winner. Agreeing distinct candidates remain distinct; one supporting observation is not multiplied into independent evidence. |
| Frozen rename and later Python ADR 0009 — TEST | Import checked-in exact before/after ADR Markdown and actual later Python ADR 0009; keep the frozen 902467a R092 transcript as checked TEST evidence. The renamed path becomes a separate subject, old candidates are retained, and the later Python ADR 0009 never aliases by number. No Git-report subject/property/shape, production capture tool, rename handler or merge in slice 1. The git.rename.report entry, git-rename-report shape and their ingestion/capture tooling are deferred to slice 1b. Recorded capture is independently checked against pinned objects; routine tests require no fetch. |
| First-import COMPLETION and re-run | At an explicitly selected projector, derived publication progress reaches the exact Layer A log tip and the expected literal claims, identities, scopes and support exist. verify_store success alone is insufficient: it can pass with pending events. Re-run the pinned import using its saved complete requests; event count and tip hash are unchanged. |
| BACKUP BUNDLE and restore | Back up the store with the SQLite backup API, or checkpoint and close it before copying. Preserve durable beside-store request manifests, all vocabulary definitions/historical bindings, and the exact policy/software revision with that backup bundle. Test one restore: consistent log and derived progress, expected reports, saved-request resumption and no duplicate append on re-run. A loose copy of an active SQLite main file is not the bundle. |
| Slice-1 FINISH LINE | Import a pinned public revision and complete publication; show a report's exact repository/path/revision/blob and source span; show differing reports from two revisions together without a winner; resume an interrupted import from durable saved complete requests; re-run without appending; restore from the tested backup bundle. Only the three literal ADR properties are ingested; Git-report ingestion remains slice 1b. |
| Replay versus policy / privileged bypass | Replay compatible historical/retired/undeclared events without definitions or allowlist. In a disposable test store demonstrate privileged direct insertion can bypass admission while passing ordinary checks where structurally valid; verifier success never attests writer-policy enforcement or faithful extraction. |
| Public inputs, separate dates and explicit selection | Reviewed entries are exactly {repository, revision (full commit ID), path_prefix}; repeated expansion yields identical exact (path, blob) pairs at that commit. Each event retains exact path/revision/blob. Blobs outside every reviewed entry and private inputs refuse; mutable refs and wildcard/glob expansion beyond the literal prefix refuse. Source dates stay separate from retained import occurred_at and writer-assigned recorded_at. Missing projector refuses; explicit supported selections retain all existing golden bytes, roots, hashes and recovery behavior. No implicit switch or default. |
| Deferred evidence boundary | Option-(a) history stays unchanged by future separately accepted option (b); usage/internal Dream emissions gain no evidence path. No protected deployment or listing/indexing is implemented by this slice. |

### Deferred cases retained for their own later contracts (R8)

- Slice 1b: the `git.rename.report` vocabulary entry, `git-rename-report` value
  shape, Git-report artifact descriptor, ingestion and capture tooling. The
  frozen 902467a R092 transcript remains a slice-1 TEST fixture; it is not an
  accepted fourth slice-1 property or a requirement to build that producer now.
- Rebuilding the future listing index from Layer A reproduces mention text and
  associations; its stale state remains disclosed. All persisted copies are
  inventoried, and a private corpus refuses the deployment policy until its
  accepted/implemented/passed erasure requirements are met.
- Option-(a) history retains its original meaning and bytes after a separately
  ratified option (b). Neither usage nor internal Dream emissions acquire an
  evidence path through the report vocabulary.
