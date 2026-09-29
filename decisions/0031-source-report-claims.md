# ADR 0031: Report-Scoped External Content

Status: Proposed

Date: 2026-09-22

Implementation: None

Supersedes on acceptance: No accepted ADR for the report-scoped option (a) defined here. Option (b) is an undecided target, not a new origin mapping or permission to change frozen projectors.

Related: [ADR 0001](0001-observation-recorded-resolves-to-verified.md), [ADR 0006](0006-occurred-at-comparison-is-instant-based-not-lexical.md), [ADR 0019](0019-identity-bootstrap.md), [ADR 0023](0023-stage-two-contract.md), [ADR 0024](0024-no-authoritative-head.md), [ADR 0025](0025-incremental-result-commitment.md), [ADR 0026](0026-usage-is-not-evidence.md), proposed [ADR 0028](0028-redaction-and-crypto-shredding.md) and proposed [ADR 0029](0029-dream-emission-semantics.md), [review and rulings](../design/2026-09-22-review-and-next-steps.md#rulings-2026-09-22).

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
status claim. Source configuration can identify the repository, revision and path;
the choice of per-event vocabulary metadata location remains open below.
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

### 3. Writer boundary, not property identity or replay policy

Every external-content ingestion submission declares the report vocabulary it
uses. The writer checks it before Layer A append. Each claim's exact property
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
content as unrestricted direct observation; the writer's ingestion boundary must
require the declaration for that path.

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

### 4. Vocabulary hash inputs and immutable versions

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
content requires a new version and hash. The writer verifies the supplied
definition against the declared hash and refuses reassignment of an already
recorded identity/version to another hash. A derived lookup for this consistency
check can be reconstructed from per-event declarations; it does not make a
property registry or a current vocabulary a replay input. Preserve the exact
definition used for ingestion review, addressed by its identity/version/hash;
a mutable alias or URL alone is insufficient to explain the policy.

The event's vocabulary metadata is semantic source provenance: changing it on
retry is not a positional repair. Exact committed metadata survives retries and
replay. A definition update applies only to new submissions; it does not rewrite
older events or silently retry them under a new version.

### 5. Per-event location: alternatives and unresolved choice

No accepted ADR selects a vocabulary-identity location. The alternatives are:

| Location | Coverage and contract implications |
|---|---|
| Existing source.config | Source is canonical JSON carried in the envelope and covered by event_hash; candidate/dependency source provenance already retains it. This can carry identity/version/hash without adding envelope fields or changing stage-two payload shape. The exact keys and declaration layout still require a decision; arbitrary config support is not a ratification of this placement. Changing config changes the committed envelope, even though the idempotency formula uses actor_id rather than all config. |
| Dedicated envelope fields | Makes the declaration structural, but requires explicit schema, validation, hash coverage and compatibility decisions. ADR 0025 section 1 preserves existing envelopes; a new envelope contract must state the precise versioned supersession rather than adding fields to frozen historical records. |
| Payload fields | Payload_hash could bind the declaration and event_hash would bind that commitment, but current stage-two mention/observation payload shapes do not admit arbitrary extra fields. This needs explicit payload acceptance, replay and version-compatibility decisions, including placement for mention-only events. ADR 0025's unchanged payload/semantic contract cannot be silently expanded. |

An uncommitted side table or mutable writer configuration alone cannot satisfy
the immutable per-event requirement. Choosing source.config remains distinct
from selecting the definition: the entire definition need not be copied into
every event merely because its identity/version/hash is recorded.

**Maintainer ruling required — vocabulary-identity location:** choose
source.config, dedicated envelope fields, or payload fields; specify the exact
declaration layout and versioned compatibility treatment. No location is selected
by this draft. Source.config is mechanically available, not already mandated by
accepted authority. The location/layout must support the immutable-version and
complete-definition hashing requirements above.

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

Required future regression fixture: commit
902467afa54887de0d15ab9f1a9d23403e9628cc reports R092 for
decisions/0009-projection-parameters.md ->
decisions/0010-projection-parameters.md. Test separate subjects for the two paths,
preservation of the old subject's claims, and a report-scoped Git rename/similarity
claim with that commit provenance. The “0009” path must not alias the later
Python-target ADR numbered 0009, nor may “0010” become a universal identity key.
This is a fixture requirement for the unbuilt ingester, not a rename handler.

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

## Verified relationships to earlier decisions

| Decision | Relationship |
|---|---|
| ADR 0001, Decision and Consequences | Observed signals may verify the claim actually observed. Here that claim is the artifact's statement; the reported proposition gains no world verification. Other origin mappings remain distinct and unimplemented. No amendment for option (a). |
| ADR 0006, Decision | Compare timestamps as instants; reject offset-less values; preserve stored spellings. Commit-time provenance does not authorize canonicalizing occurred_at or rewriting an envelope. No amendment. |
| ADR 0019 sections 1–4 and 6, as amended by 0021/0023 | Separate mention bootstrap creates its own scoped subject; later observations name recorded identities. Renames/similarity create no accepted association basis. No amendment. |
| ADR 0023 sections 1–4 and 6 | Exact opaque property IDs, fresh ClaimCandidates, existing-mention ingestion and retained semantic contents continue. An ingestion-only vocabulary restriction is not a property registry or replay check. No new origin or authority is supplied; DreamEmission remains a reserved distinct role. No amendment for option (a). |
| ADR 0024 sections 1–3 | Candidate sets have no authoritative head; recency and value agreement do not resolve them. Displaying source reports does not supply the deferred scalar-read contract. No amendment. |
| ADR 0026, Decision and Consequences | Retrieval exposures, Dream references and activation records remain usage, never evidence or lineage. Observing an external artifact is not permission to turn repeated retrieval into another supporting signal. No usage recorder is authorized. No amendment. |
| Proposed ADR 0028 sections 9 and 11 | The index is an inventoried content copy; a future protected deployment must cover all managed copies. Public-only policy does not ratify the erasure protocol or claim its Gate 3 obligations passed. No edit proposed to that draft. |
| Proposed ADR 0029 sections 1–7 | Its DreamEmission origin and no-promotion boundary remain explicit and Proposed. Report vocabulary is no loophole for laundering an internal emission into Layer A as an artifact report or promoting its text into evidence. Independent acquisition remains a separate observation; emission recording/causal-link mechanics stay undecided. No edit proposed to that draft. |

## Exact accepted-ADR edits required on acceptance

None for option (a) as an ingestion-time policy using existing compatible event
contents: it changes neither property identity, replay validation, candidate
standing nor historical projector semantics. ADR 0023 section 1's “No property
registry” sentence remains unchanged.

The unresolved location choice may require an additional contract: dedicated
envelope or payload fields would require narrowly superseding ADR 0025 section
1's unchanged-envelope/payload promise for a newly specified format/version,
with exact fields, compatibility and validation decided first. This draft does
not authorize that edit or pretend its wording can be finalized before the
location is ruled.

Option (b) requires a separately explicit origin/state/projector contract.
It cannot change the observed-origin rule of ADR 0001 or frozen projector bytes
by implication. No exact origin-mapping amendment is selected in this draft.
No existing ADR or specification is edited.

## Proposed acceptance cases

- A directly observed artifact statement creates a verified report-scoped claim;
  the reader discloses artifact/revision provenance and does not assert the
  embedded proposition as verified world truth.
- External ingestion lacking the declared vocabulary or using an undeclared
  property refuses before append. Property case and Unicode variants remain
  distinct opaque strings; the boundary performs no identity normalization.
- Every ingested event, including mention bootstrap, has the chosen immutable
  vocabulary declaration. Changed definition bytes require a new version/hash;
  attempted reassignment of an existing identity/version refuses.
- Replay of previously accepted events is unaffected by changing or removing the
  current writer vocabulary. Direct database insertion demonstrates that normal
  replay/integrity checks are not proof of writer-policy enforcement.
- A committed retry preserves vocabulary metadata; a new version is not silently
  substituted. A conflicting semantic retry refuses.
- Changing status across commits retains separate candidates with provenance,
  never a recency-selected scalar. Missing status yields no invented status claim.
- The specified 902467a R092 rename preserves separate scoped subjects and reports
  only Git's assertion. ADR-number search cannot alias identities.
- Rebuilding the future listing index from Layer A reproduces mention text and
  associations; its stale state remains disclosed. All persisted copies are
  inventoried, and a private corpus refuses the deployment policy until its
  accepted/implemented/passed erasure requirements are met.
- Option-(a) history retains its original meaning and bytes after a separately
  ratified option (b). Neither usage nor internal Dream emissions acquire an
  evidence path through the report vocabulary.

