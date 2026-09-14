# ADR 0029: Dream Emission Semantics

Status: Proposed — draft for review; not ratified and does not authorize implementation.

Date: 2026-09-14

Supersedes on acceptance: No accepted ADR. Qualifies the Dream-related derived-statement, oracle and provenance descriptions in [NYX_ARCHITECTURE.md](../spec/NYX_ARCHITECTURE.md), only as enumerated below. No existing projector gains new semantics.

Related: [ADR 0013](0013-cross-belief-identity-semantics.md); [ADR 0014](0014-cross-belief-reducer-and-hash-lineage.md); [ADR 0015](0015-candidate-scoped-verification.md); [ADR 0021](0021-bootstrap-link-treatment.md); [ADR 0023](0023-stage-two-contract.md); [ADR 0024](0024-no-authoritative-head.md); [ADR 0025](0025-incremental-result-commitment.md); [ADR 0026](0026-usage-is-not-evidence.md); proposed [ADR 0027](0027-stage-three-authority-and-acceptance.md) and [ADR 0028](0028-redaction-and-crypto-shredding.md).

Implementation: None. This draft records the settled Dream boundaries for ratification review and identifies the decisions still required for recording, recall, acquisition provenance and operational consumers. It selects no schema, projector version or handler.

## Context

ADR 0023 reserves DreamEmission separately from ClaimCandidate without ratifying
the Dream mechanism. ADR 0026 excludes Dream references and usage from evidence
and lineage, while preserving the status of an independently accepted observation
when Dream initiated the check. Neither supplies an emission recording contract.

A generated answer, the history of generating it, and a later observation are
different things. Retaining or recalling an answer must not convert its origin,
and a successful acquisition must not retroactively turn its initiating emission
into support. The architecture's general oracle language needs that distinction
explicitly stated for Dream, without claiming that the mechanism already ships.

## Decision

### 1. Distinct type and inseparable origin

A Dream emission is a distinct semantic type, DreamEmission. It is not a
ClaimCandidate, not an observation, and not evidence. It does not acquire a
candidate verification state merely because its text expresses a proposition.

**Origin is inseparable from recall.** A recalled emission carries its emission
origin; a representation that loses the origin is non-conformant. Copying,
summarizing, indexing, retrieving or displaying the emission does not remove
this obligation or establish an observed origin. An origin label is a semantic
requirement, not a storage schema or a claim that arbitrary external copies can
be controlled.

### 2. Reducer input algebra and permanent exclusion

The reducer's input algebra admits only Layer A event references. A Dream emission
is never an admissible input to belief reduction. This is an input-type boundary,
not a low confidence score, a quarantine state or a gate that might later open.

Dream emissions never transition into evidence. There is no promotion path from
emission to support, under any gate. Confirmation, agreement, repetition, an
approval signature or successful re-derivation cannot change that semantic type.
An emission ID, process-trace ID or retrieval ID cannot stand in for an evidence
event ID or resolve through the ClaimCandidate namespace.

"Event references" identifies the authoritative event domain; it does not replace
ADR 0014's envelope/payload and consistent pre-event snapshot contract with a
bare-ID API. Evaluation time and projector version remain explicit parameters.
ADR 0025 still commits to complete dependency envelopes and payloads, rather
than only their IDs. Not every Layer A event is property evidence: identity and
other supported event roles retain their own accepted semantics. No unsupported
event in the world stream may be silently skipped.

### 3. Emissions remain process history

Retained emissions belong outside Layer A as process history, never as world
assertions or ClaimCandidates. Their continued existence records generation,
not a proposition's evidentiary standing. Governance of downstream use does not
retroactively turn an attempted generation into a different kind of occurrence.

This establishes the semantic separation, not a new durable store. Architecture
section 7's process traces are separate, crash-durable and mutable; they record
the process rather than the answer. That precedent does not decide that emissions
occupy the same table, have the same mutation rules, or are reconstructible from
Layer A. In particular, it does not establish an append-only emission log.
The physical location, append/mutation policy, durability authority and retention
remain decision-blocked. No new exception to Invariant 8 is supplied by analogy
with the proposed restoration witness in ADR 0028.

### 4. Acquisition produces a separate observation

An emission may initiate acquisition that later yields a real observation. Under
ADR 0026, an independently accepted world observation remains an observation
even when Dream initiated the check. Its Layer A event and the claims it actually
supports supply the evidence; the initiating emission never does. The applicable
stage-two contract creates fresh ClaimCandidates from that observation under
ADR 0023, not by promoting or renaming the emission.

The accepted ADRs do not decide whether that observation must carry an emission
link, or where such a link is recorded. Architecture section 7 specifies
process-trace matching by hypothesis ID and semantic hash; it does not require
a backlink in the observation or equate that match with an emission identity.

ADR 0021's `constitutive` association makes a subject the referent of its recorded
mention. Causing a check does not constitute the subject of the resulting
observation in that sense. Reusing that link state for acquisition provenance
would require a further decision; omitting every causal record is not an implied
default either. The link obligation and its representation remain unresolved.
Any eventual record must obey sections 2 and 5: explaining why acquisition ran
cannot create support or manufacture source independence.

### 5. Causal asymmetry in process provenance

Recorded process provenance may **prevent overcounting of support**, and may
**never create support**. Multiple paths, emissions, exposures, citations or
attempts cannot multiply a world observation or establish independent sources.
Absence of a recorded causal relationship is not proof of independence.

This preserves ADRs 0013/0015's distinction between evidence-event identity,
provenance paths and source independence. A restriction on counting is not an
additional supporting edge. A later independent observation earns its own
applicable support; the fact that an emission caused its acquisition does not
by itself establish either independence or dependence of the observed source.

The admissible records and deterministic rule for applying such restrictions
are not specified here. A mutable process store cannot become a hidden reducer
input: any belief-affecting rule must satisfy the Layer A input boundary, accepted
lineage coverage and replay equivalence. Recording and verification of that
boundary remain open; no new restriction event or attestation mechanism is chosen.

### 6. Belief replay and process-history verification

Emissions do not participate as inputs to belief replay. Replay continues to
reduce the supported Layer A history under its recorded contracts; it neither
regenerates Dream output with a model nor treats retained output as evidence.
The separate observation in section 4 participates with its ordinary integrity
and semantic checks. Existing projectors and their frozen bytes remain unchanged.

Whether process history has its own replay or reconstruction operation, and what
verification establishes emission identity, origin, completeness and causal
links, remains unresolved. A hash or an accurate recall cannot establish world
truth. Neither ordinary log verification nor ADR 0025's inclusion proofs certify
an unspecified emission store. Under proposed ADR 0028, erased content cannot be
recovered or reported semantically verified merely to reproduce a past emission.

### 7. Usage and operational consumers

This draft **extends** ADR 0026's scope to the emission type and its causal
provenance constraints; it is consistent with, and does not amend or supersede,
0026's usage-is-not-evidence boundary. Dream references, retrieval exposures and
activation records remain outside belief evidence and lineage. This draft
supplies no exception to that exclusion and no operational storage defaults.

The activation scorer and Dream's salience path receive no causal-provenance
handle. Recording provenance for permitted process accounting does not make it
an input to those consumers. This restriction constrains future retrieval,
feedback and metric designs; it does not decide their recording contracts,
credit assignment or update rules.

The adopted observable retrieval vocabulary distinguishes **candidate generated**
(entered the retrieval candidate pool), **exposed** (crossed top-k and was supplied
to the consumer), and **referenced** (explicitly cited). These are retrieval usage
occurrences, not ClaimCandidate creation or evidence. Exposure and citation do
not prove causal influence. The broader feedback loop remains unresolved below;
the vocabulary alone does not select which occurrences reinforce activation.

### 8. Redaction covers emissions without changing their type

Yes: emissions containing or revealing protected inputs fall within proposed
ADR 0028 sections 2, 6 and 9's managed-copy erasure closure, including generated
outputs, process traces and Dream/retrieval caches outside the truth ledger.
Process-history status supplies no privacy exemption. Its content may need erasure
while a safe opaque existence/dependency record survives; it never becomes a
redacted ClaimCandidate merely to reuse that candidate's lifecycle.

This is conditional on ADR 0028's ratification and applicable implementation.
It neither ratifies that draft nor implements destruction, key custody, a sentinel
or an emission reader. The precise emission-unit, dependency-registration and
origin-preserving unavailable-result representations remain open. Redaction
cannot erase a counting restriction and thereby manufacture independent support;
how retained safe provenance enforces that constraint is part of the unresolved
recording and verification contract.

### Exact supersessions and limits

| Earlier authority | Effect upon acceptance of this draft |
|---|---|
| ADR 0013 | Consistent with its evidence-event deduplication and distinction between provenance and support; no amendment or supersession. |
| ADR 0014 | Consistent clarification of the Layer A input domain; preserve its envelope/payload, pre-event snapshot, complete delta, lineage and deterministic replay contracts. No narrowing, amendment or supersession of that API or coverage. |
| ADR 0015 | Consistent extension distinguishing emissions from verified or unverified ClaimCandidates; preserve candidate-scoped standing, support applicability and evidence deduplication. No amendment or supersession of candidate verification or gate-approved candidate creation. |
| ADR 0021 | No amendment or supersession. Its constitutive mention/subject link does not supply acquisition-link semantics. |
| ADR 0023, section 6 | Extend its reserved DreamEmission vocabulary with the distinct semantic type, without ratifying a Dream mechanism or altering the stage-two ClaimCandidate contract. No narrowing, amendment or supersession of its stage limits. |
| ADR 0024 | Consistent with its no-authoritative-head and scalar-read boundaries. An emission or recalled answer cannot select a belief head, coalesce candidates or supply the deferred common-value read contract. No extension of read authority, amendment or supersession. |
| ADR 0025 | Preserve complete dependency envelopes/payloads, logical lineage coverage and deterministic replay. No reference-only storage redesign, amendment or supersession. |
| ADR 0026 | Consistent extension to emission semantics; no change to its prohibitions or unresolved operational contracts. No amendment or supersession. |
| Proposed ADR 0027 | No amendment or supersession; not ratified by reference. Its stage-three protocol and review gates remain separate. |
| Proposed ADR 0028 | Consistent application of its existing managed-copy erasure scope to emissions, conditional on ratification. No narrowing, amendment or supersession; do not extend its event-unit schema to emissions by assumption. Its unresolved protocol and evidence gates remain open. |
| Architecture governing invariant; Invariants 3, 5, 7 and 9; sections 1–4, 7 and glossary | Qualify derived-statement and oracle descriptions for Dream: distinct emission type with inseparable origin, no promotion path under any gate, Layer A event-domain reduction, separate acquired observations, and subtractive-only process provenance. Record conditional notices in the same documentation batch. |

The sole existing file this draft claims to qualify is
`spec/NYX_ARCHITECTURE.md`. README navigation and the GAPS register describe the
proposal; they are not authority amendments. No implementation-companion edit,
schema allocation, new handler, eTPS contract or attestation mechanism is included.

## Remaining unresolved questions

These are open decisions, not implied defaults or merely excluded work. The
settled boundaries above can be reviewed independently; dependent recording,
replay and consumer implementation must halt until its required decisions are
explicitly ratified.

- **Emission recording and durability:** Which store records emissions outside
  Layer A, and is it append-only or mutable? What are its authoritative durable
  inputs, ordering, identity/retry rules, retention and recovery contract? Resolve
  Invariant 8 explicitly; neither mutable process traces nor the proposed custody
  witness authorizes an emission-history exception.
- **Process-history replay and verification:** Is there emission replay, exact
  recall, reconstruction, or more than one operation? Which recorded inputs and
  checks establish origin, identity, completeness and causal provenance without
  treating model regeneration or a commitment as semantic verification?
- **Acquisition linkage and counting restrictions:** Must an observation carry
  a link to its initiating emission, and where is that relationship recorded?
  What distinct relation, authority, verification and Layer A representation can
  prevent overcounting while supplying no support and remaining replayable?
  Neither ADR 0021's constitutive link nor no link is selected by implication.
- **Emission redaction and recall representation:** How are emission units,
  private dependencies, safe retained origin/causal records and unavailable recall
  results represented under proposed ADR 0028? How does erasure preserve necessary
  counting restrictions without retaining protected content? Its unresolved
  protocol and provider-evidence questions remain prerequisites, not resolved here.
- **Retrieval/activation provenance recording and feedback loop:** With candidate
  generated, exposed and referenced distinguished, decide update timing and dedup,
  scope, credit assignment, cross-component feedback, candidate-generation bias
  and a route for underexposed evidence. Decide recording, retention, configuration
  and replay under ADR 0026. Section 7's lack of a causal-provenance handle for the
  activation scorer constrains this work; it does not settle the feedback loop.
- **Dream instrumentation:** Operational definitions and recording remain open
  for Generative Flux over attempted cycles with `R_opportunity` and `R_zero`,
  non-deduplicated raw emission count `N`, and Inquiry Yield. Preserve their
  deliberately pre-governance intent so accuracy pressure cannot suppress
  generation upstream; process-history recording must not be interpreted as
  permission to filter emissions before measuring the raw count. No formulas,
  windows or denominators beyond that stated intent are invented here.
- **Question taxonomy and preserved open inquiry:** Keep distinct question ->
  retrieval -> answer; question -> missing evidence -> acquisition -> answer;
  and question -> insufficient evidence -> preserved open inquiry, with expiry
  and indexing. The last branch needs an explicit recording obligation and
  lifecycle, including scope, closure, expiry and recovery semantics; section 4's
  acquisition branch does not supply them. These decisions are not silently
  absorbed into an emission schema.
- **Spleen Dream yield:** Architecture section 3 names this health metric without
  defining it operationally. Decide its inputs, calculation and consumers, and
  its relationship to Inquiry Yield. Section 7 denies Dream's salience path a
  causal-provenance handle; a yield metric must not silently reopen that path.

## Ratification-readiness assessment

The type, origin, no-promotion and causal-asymmetry boundaries are recorded as
settled instructions in this Proposed draft. No accepted-ADR conflict was found:
in particular, the input algebra preserves ADR 0014's API and ADR 0025's complete
dependency contents, and does not reuse ADR 0021's link state.

This is not a complete recording or replay contract. The unresolved questions
above block dependent implementation; the draft declares none answered by
analogy. Formal ratification remains a separate explicit action. Proposed ADRs
0027/0028 keep their own statuses and review gates.

## Acceptance cases

These are requirements for future conformance, not executable coverage or
permission to implement the unresolved contracts.

- Generate, retain and recall an emission: every representation carries its
  emission origin and remains distinct from an observation and ClaimCandidate.
  A representation losing that origin is non-conformant.
- Present an emission or its ID as a reducer input or evidence dependency:
  refuse it. A label, confidence, repetition, oracle agreement or approval cannot
  open a promotion path. Preserve supported event roles and full dependency data.
- Let an emission initiate acquisition producing an independently accepted
  observation: only that new observation supplies its applicable world evidence.
  The emission remains process history. A fixture must not invent the unresolved
  causal-link schema or label the relationship constitutive under ADR 0021.
- Add paths, emissions and usage occurrences around the same observation:
  support does not multiply. Recorded process provenance can prevent overcounting
  but never supply a missing observation, source independence or positive support.
- Replay the same supported Layer A history at a shared cutoff, time and version:
  Dream generation is not invoked and emissions are not reduction inputs. No
  mutable external process record becomes a hidden input or lineage dependency.
- Keep generated, exposed and referenced retrieval occurrences distinct; repeated
  usage changes no belief evidence or lineage. Neither activation scoring nor
  Dream salience obtains a causal-provenance handle through a metric or cache.
- Measure attempted generation before downstream governance: repeated raw
  emissions remain countable in `N`. Do not claim an instrumentation acceptance
  result until the open measurement and recording definitions are supplied.
- Under a ratified erasure-capable contract, erase protected emission content
  throughout its managed closure; origin-preserving unavailable recall does not
  restore content, convert it to evidence or remove a necessary counting
  restriction. Missing emission-specific representation decisions block the test.
- Preserve the insufficient-evidence question as an open-inquiry requirement;
  an acquisition workflow alone is not coverage of expiry, indexing or closure.

## Consequences

Dream can generate without those generations becoming latent evidence awaiting
a sufficiently strong gate. Independent acquisition retains its existing route
into Layer A, and retained process history cannot lose its origin on recall.
Operational provenance and metrics remain useful only within their explicitly
bounded roles. Their recording, replay and lifecycle contracts remain open.
No implementation or commit is authorized by this draft.
