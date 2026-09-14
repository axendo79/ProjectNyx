# ADR 0027 Gate 1 specification-completeness worksheet

**Status:** Non-authoritative gap inventory for the maintainer's rulings. No
decisions, schema drafts, proposed resolutions, ratification or implementation
authority are supplied by this worksheet.

**Source baseline:** `63f75c92fa5deb13f0dd4ed8e334d307365d96fc`, reviewed
2026-09-14. [ADR 0027](../decisions/0027-stage-three-authority-and-acceptance.md)
and [ADR 0028](../decisions/0028-redaction-and-crypto-shredding.md) are both
Proposed / Implementation: None. The accepted dependency ADRs constrain the
proposal; its proposed supersessions are not already in force.

## Scope and reading of the gates

The five entries below correspond exactly to the five bullets in ADR 0027's
[Remaining unresolved questions](../decisions/0027-stage-three-authority-and-acceptance.md#remaining-unresolved-questions).
They are gaps an independent implementer would have to fill to build projector
"3" from the document. A list of semantic requirements or named fields is not a
complete interoperable schema.

ADR 0027, **Remaining unresolved questions**, explicitly distinguishes those
gaps from decisions already written into the proposal:

> The following are **ratification blockers**, not permission to invent an
> implementation default. Sections 3.1-3.3 settle framing, public canonical bytes,
> algorithm selection, commitment coverage, signature scope, nonce retention,
> embedded signatures in AAD, key independence and the recovery barrier. Those
> decisions are no longer open questions.

That distinction resolves the apparent tension between section 3's "closed
structural inventory" and the open closed-schema blocker: the inventory is
written; the complete per-operation objects and validation rules are not.
Similarly, the Gate 1 checklist's inclusion of encryption/AAD and state machines
does not reopen choices explicitly marked settled above. It requires their
specified contracts and evidence in the review package. No ambiguity about the
five blockers' open status was found; this worksheet makes no ruling on them.

[Gate 1](../decisions/0027-stage-three-authority-and-acceptance.md#gate-1-specification-completeness)
requires the complete specification, positive/negative vectors and a pinned
review-candidate commit. It permits specification-development artifacts but
authorizes neither production Stage Three nor ratification.
[Gate 2](../decisions/0027-stage-three-authority-and-acceptance.md#gate-2-independent-protocol-review)
requires independent findings, scope/exclusions, remediation verification and
residual assumptions. A maintainer ruling can settle a specification choice;
it cannot substitute for independent review or produce a known-answer vector
merely by declaration.

The resolver assignments below distinguish **who rules on the missing contract**
from **who reviews the resulting protocol**. All open choices belong to the
maintainer. ADR 0027 does not require an outside expert to author the Gate 1
schemas, nor allocate each blocker to a particular reviewer. Its
[engagement-scope question](../decisions/0027-stage-three-authority-and-acceptance.md#review-record-required-before-ratification)
requires adequate storage/recovery expertise, supplied either by the independent
reviewer or by a separately scoped reviewer. The domain labels below identify
the subject matter to be covered, not a staffing decision made here.

## Accepted constraints and the proposed authority scope

| Contract | Constraint on the eventual answer |
|---|---|
| [ADR 0015 §§1–7](../decisions/0015-candidate-scoped-verification.md#decision) | Verification belongs to a ClaimCandidate, with no belief aggregate; pooling earns no verification. Candidate identity, changed-scope successors, explicit support applicability, fresh gate-approved candidates, dependency restrictions, evidence-event deduplication and round-trip standing must survive representation changes. |
| [ADR 0018, Decision and Implementation](../decisions/0018-correction-supersedes-candidates.md#decision) | Corrections name explicit candidate targets validated at the pre-event snapshot, create a fresh candidate, retain history and transfer no verification. Target eligibility remains incomplete. This is a constraint on scope, not authority to add correction handling to projector 3. |
| [ADR 0020, Decision and Consequences](../decisions/0020-multi-user-authority-undecided.md#decision) | The ADR's Status is Accepted, but the accepted decision is that multi-user authority remains **UNDECIDED**. Attribution supplies no privileges, ownership or independence. Intended reference, shared identity, evidence and permission are distinct. Historical authorization must be reproducible; fixtures cannot invent an owner. |
| [ADR 0021 §§1–4](../decisions/0021-bootstrap-link-treatment.md#decision) | Constitutive bootstrap is not a resolved identity match or verification. No numeric confidence or empty-path default applies; this does not settle other link kinds or grant authority. |
| [ADR 0022 §§1–2](../decisions/0022-belief-container-uniqueness.md#decision) | At most one current belief per exact (subject, property) pair; historical beliefs are excluded. Validate the actual pre-event association, refuse duplicates and never redirect silently. Candidate verification does not determine current-container membership. |
| [ADR 0023 §§1–6](../decisions/0023-stage-two-contract.md#decision) | Exact opaque property identity, fresh ordinary ClaimCandidates, explicit mention/subject associations and retained retry identity remain constraints. Corrections and support attachment remain deferred; ClaimCandidate is not a retrieval or Dream role. |
| [ADR 0024 §§1–3](../decisions/0024-no-authoritative-head.md#decision) | No authoritative head or recency winner; multiple-candidate scalar requests refuse. Common-value reads remain deferred. Several claims sharing one observation do not create independent corroboration. |
| [ADR 0026, Decision and Consequences](../decisions/0026-usage-is-not-evidence.md#decision) | Usage never supplies belief evidence, lineage or verification. Usage recording/replay mechanics remain undecided; an independently accepted observation is distinct from the usage that prompted it. |
| [ADR 0013 §§1–5](../decisions/0013-cross-belief-identity-semantics.md#decision), [ADR 0014 §§1–3, 5–10](../decisions/0014-cross-belief-reducer-and-hash-lineage.md#decision), subject to ADR 0015 | Fresh successor entity/belief IDs, complete partitions and affected sets, established claim applicability, pre-event validation, canonical complete lineage, atomic publication and deterministic replay constrain every new representation. The superseded differing-state merge refusal is not current policy. |
| [ADR 0025 §§1–6](../decisions/0025-incremental-result-commitment.md#decision) | Frozen old projectors, full logical commitment coverage, canonical collection treatment and explicit proof/semantic-verification limits constrain the proposed protected representation. A trusted root alone establishes neither inventory completeness nor reducer correctness. |

**0020 scope boundary, not an additional Gate 1 ruling.** ADR 0027 §9,
**Exact supersessions and limits**, states this relationship in its 0020 row:

> Narrow its blocker only for the explicit ledger-scoped stage-three capabilities, enrollment and historical authorization above. Preserve the separation between permission, attribution, intended reference and evidence; all other multi-user policy remains open.

Section 2 supplies that limited authority model within the proposal. B1/B4 must
close its record schemas, and B5 must supply its conformance evidence; none
requires a separate prior 0020 ruling for this already stated scope. The draft's
Proposed status still bars implementation before review and explicit ratification.
That ratification requirement is not an unresolved authority choice inside Gate 1.
Synthetic Gate 1 fixtures can express the proposed explicit grants and enrollment;
they cannot invent universal authority or an implicit owner.

Contributor write/read permissions, competing administrators, per-user views,
ownership, delegation between users, tenant isolation, consent disputes and
user-specific verification remain open under 0020, as §2 expressly lists.
**Only an extension depending on that excluded policy is BLOCKED BY 0020'S
UNDECIDED MULTI-USER AUTHORITY STATUS.** None of B1–B5 as scoped in 0027 requires
that extension. In every schema, historical authorization must be determined at
the pre-event prefix, never from current permissions (ADR 0014 §1; ADR 0020
Decision; ADR 0027 §2).

ADR 0027, **Remaining unresolved questions**, expressly says:

> The following remain **outside this limited stage**, rather than hidden blockers
> to its explicit capability model: how should general contributor entitlement and
> contested multi-user ownership be resolved under ADR 0020; what future contracts
> will govern corrections, scored links and restoration; and will deployment choose
> the allocated separate cutovers or ratify a combined allocation?

ADR 0018 target eligibility is likewise not silently added to Gate 1: ADR 0027
section 9 expressly leaves version-3 corrections refused. Encoding retained
supersession history does not select correction targets or confer correction
authority.

## B1. Closed operation, authorization and attestation schemas

**Exact blocker text — ADR 0027, Remaining unresolved questions, "Closed
operation schemas":**

> **Closed operation schemas:** What are the complete required/optional fields,
> types, selectors, set constraints and validation rules for each event's S and A,
> each admissible-basis attestation T, genesis/rotation records and protected
> content schema, including rejection of unknown fields? The generic envelope is
> defined, but prose inventories do not yet define interoperable event objects.

**Where the body gestures at it:** section 3 inventories S and defines the
generic U/E/A/D and attestation objects; sections 1–2 and 4–7 describe the
event-specific contents and semantics. Section 3.1 says public application
ranges belong in the closed field schema. Gate 1 explicitly requires closed
operation, authorization and attestation schemas.

**What an implementer would have to invent:** the missing closed encodings and
validation rules for each row below. These are unanswered definitions, not
permission to change the semantics already stated in the cited sections.

| Affected records | Missing definition needed to proceed | Already constraining text |
|---|---|---|
| Ordinary protected mentions and observations | Complete per-event S and private-content shapes; mapping from semantic fields to opaque selectors; required/optional members, types and constraints in those bodies | 0027 §§1/3 inherit the stage-two assertion contract; ordinary A/SIG null is already specified. ADRs 0021 §§1–4, 0022 §§1–2 and 0023 §§1–4 constrain associations, current containers, fresh candidates and retries. |
| Governance configuration/update, genesis and rotation | Closed grant/scope, enrollment, speaker-key and namespace records; per-record required members, types, set/identity constraints and validation of their references | 0027 §2 already describes trust pins, explicit grants, predecessor policy, countersignature and historical authorization. ADR 0020 Decision forbids filling any missing permission by actor attribution. |
| Merge, split and accepted association | Complete object forms for output inventories, partitions, affected-scope records, basis references and custody dispositions; field/selector and cross-reference validation | 0027 §§4–6 supply acceptance semantics; ADR 0015 §§2–3/5–7 preserves standing/applicability; ADR 0021 preserves constitutive treatment; ADR 0022 excludes duplicate current pairs. B3 supplies the still-open compound-custody component. |
| Each of the three admissible-basis attestations | Closed basis-specific relationship/scope/evidence records and protected evidence details, including enrolled speaker/namespace bindings and their validation | 0027 §4 names the three bases and what they establish. Section 3 already fixes the generic signed attestation and backward references. ADR 0020 requires both a valid relationship basis and permission covering the affected assertions. |
| Corroboration and justification/restriction records | Closed encodings of selected claims, evidence selectors, contributors, sufficient justifications, restrictions and the new candidate's scope, with field and referential constraints | 0027 §§6–7 fixes the initial gate and dependency-loss destinations in the proposal. ADR 0015 §§1/4–7 forbids a belief aggregate, contributor promotion or duplicated evidence. ADR 0024 §§1–3 supplies no scalar winner; ADR 0026 Decision excludes usage. |

Across these records, an implementer would otherwise decide where a field is
absent, optional or nullable; its permitted domain and cardinality; which arrays
are semantic sets or sequences; valid selector destinations; and how identifiers,
grants, evidence and output records cross-check. The generic rule to reject
unknown fields is already specified; the missing inventory is what lets two
implementations agree on which fields are unknown. No new field names, types,
defaults or admissible bases are selected here.

**Other accepted constraints:** ADR 0018 **Decision** and ADR 0023 §5 prevent
these schemas from inventing correction eligibility or treating a new alternative
as a correction. ADR 0014 §§1–3/5–9 and ADR 0025 §§3–6 constrain replayable IDs,
complete semantic coverage and publication. Schema closure cannot silently turn
a representation change into support attachment, coalescing or a read policy.

**Does ADR 0028 inherit it? Yes.** Its **Remaining unresolved questions /
Inherited format completeness** expressly inherits S/A/T and protected-format
closure. Sections 3–4 add erasure capabilities and four erasure event classes.
Its separate **Manifest and event schemas** blocker adds complete prefix/binding
proofs, derivative closure, location/copy acknowledgments, attempt/review/completion
records, selectors, error codes and grant references after subject retirement.
Sections 5–8 and the **Legacy capsule sufficiency**, **Authenticated pruning
format**, and **Effective replay and verification result schemas** blockers add
erasure-specific representations. Those additions do not authorize correction
handling or require projector 3 to implement projector-4 erasure handlers.

**Who resolves it:** maintainer ruling on the closed contract; independent
cryptographic review of signed/public/protected boundaries and storage/recovery
review of custody and replay implications at Gate 2. **Both** are required for
ratification readiness. **0020 scope check:** §2's capabilities, enrollment and
historical authorization are already defined within the proposal, with §9's
explicit narrowing. Closing their schemas needs no separate prior 0020 ruling.
General contributor entitlement remains outside this closure and cannot be
supplied by a schema default.

## B2. Cross-language private-value codec

**Exact blocker text — ADR 0027, Remaining unresolved questions, "Private value
codec":**

> **Private value codec:** What exact cross-language value/number domain and
> decoding rules does `nyx-private-json/1` admit, and which fixtures establish
> compatibility with existing values without changing frozen canonical bytes?
> Signing a fixed opaque byte string is settled; producing and semantically
> interpreting that string from independent value models is not.

**Further exact text — ADR 0027 §3.1:**

> Cross-language private-number/value
> decoding and its conformance vectors remain an explicit ratification blocker,
> not permission to round numbers or silently substitute RFC 8785 for Python's
> serialization.

**What an implementer would have to invent:** the complete admissible private
value domain and decoding behavior across languages, including numeric range,
precision and distinctions; handling of representations a language cannot
preserve; and the accepted/rejected private encodings and exact compatibility
fixtures. The open question covers such private-parser boundaries as duplicate
members and invalid string/number representations; this worksheet assigns no
behavior to them. A public-profile rule is not automatically a private-codec rule.

Already specified in §3.1: the writer retains exact UTF-8 private bytes, in-tree
preparation preserves integer/float distinctions and accepted value spellings,
the cryptographic layer does not decode/re-encode P, and frozen bytes must not
change. The missing domain does not reopen the public integer-only profile,
signature input, algorithm suite, or permission to round private values.

**Existing ADR constraints:** ADR 0015 §§1/3/4 preserves candidate contents,
scope and identity rather than coalescing values. ADR 0022 §§1–2 and ADR 0023 §1
preserve exact subject/property association and property identity; a codec cannot
normalize identifiers to make a second current container disappear. ADR 0024
§§1–3 gives value agreement no new selection or coalescing authority. ADR 0014
§§6–7 and ADR 0025 §§1/3–6 constrain frozen canonical content and complete replay.
ADR 0018 **Decision** precludes decoding a new value as an implicit correction
target. ADR 0020 supplies no codec-dependent ownership or permission default;
it is not a prerequisite to specifying numeric syntax as such.

**Does ADR 0028 inherit it? Yes.** Section 3 explicitly defines no separate
private-codec default; **Inherited format completeness** names the inherited
codec. Sections 5–8 additionally require available versus redacted content and
verification results to remain distinct. The sentinel's meaning and external
form are already specified in §5; missing effective-result/capsule schemas belong
to 0028's listed blockers. Destroyed plaintext cannot be decoded or certified
semantically correct because its original signature or sealed commitment survives.

**Who resolves it:** maintainer ruling on the value/number and decoding contract,
followed by produced cross-language fixtures (B5). Independent cryptographic
review covers its interaction with byte commitments, parser strictness and
authenticated decoding. **Both** for ratification readiness; external review
does not decide the application's intended value domain. No additional 0020
dependency is asserted for the codec itself.

## B3. Compound shared/ambiguous custody representation

**Exact blocker text — ADR 0027, Remaining unresolved questions, "Compound
custody representation":**

> **Compound custody representation:** What closed recorded representation and
> normalization rules preserve shared versus ambiguous provenance through multiple
> splits and merges, including a shared set containing one ambiguously partitioned
> predecessor? How do fixtures show that a merged subset neither loses remaining
> ambiguity nor invents a claim-support association?

**Where the body gestures at it:** §5.1 defines original and effective bindings,
assigned/shared/ambiguous dispositions, single-transition treatment, retained
other subjects and full-scope decryption. It requires remaining alternatives to
retain their disposition when a merge does not collapse them all.

**What an implementer would have to invent:** a complete record of combinations
of shared scope and unresolved alternatives after successive partitions; its
normalization and equality rules; and the exact composition/output rules when
only some alternatives merge. A flat set of subject IDs and a single disposition
word is not the closed compound representation requested by the blocker.
Implementers also lack the resulting canonical fixtures proving preserved
ambiguity, subject scope, explaining transitions and separation from claim support.
No particular nested structure, algebra, normalization or algorithm is proposed
here. The problem is not whether ordinary single-step ambiguity should exist:
that behavior is already specified in §5.1.

**Existing ADR constraints:** ADR 0015 §§2–7 keeps changed claim scopes, explicit
support assignments, verification restrictions, deduplication and round-trip
standing distinct from custody. ADR 0013 §§1–5 supplies fresh successor identities,
complete partitions and refusal of unsupported assignments. ADR 0021 §§1–4 does
not turn a constitutive link into a match, permission or evidence. ADR 0022 §§1–2
and ADR 0023 §§1–3 preserve one current belief per pair, explicit associations and
fresh ordinary claims; custody normalization cannot merge belief containers or
reuse historical IDs. ADR 0024 §§1–3 supplies no value-based resolution.
ADR 0018 **Decision** requires explicit correction targets and retained history;
custody transport cannot act as correction or grant correction authority.
ADR 0014 §§5–9 and ADR 0025 §§3–6 preserve complete commitment/replay coverage.

**0020 scope check:** representation of shared custody is not a ruling on shared
ownership or consent. Operations within §2's proposed grants need no separate
prior 0020 ruling. An extension assigning disputed user entitlement is
**BLOCKED BY 0020** and cannot be inferred from the subject set. General
entitlement is explicitly outside the limited stage; the compound representation
remains a Gate 1 specification gap independent of that excluded policy.

**Does ADR 0028 inherit it? Yes.** Section 3 adopts 0027 §5.1 and **Inherited
format completeness** names compound custody. Section 3.1 adds retired-selector
resolution, whole-scope authorization and prefix-frozen destructive manifests.
Sections 4.1/6 add shared-derivative scope, erasure-dependent standing and
non-resurrection. The **Manifest and event schemas** blocker asks how current
executor grants identify the frozen scope after subject IDs retire without
retargeting destruction. Erasure adds these uses of compound custody; it does not
supply the missing compound representation or equate ambiguity with claim support.

**Who resolves it:** maintainer ruling on representation and normalization;
independent storage/recovery review of composition, scope, historical replay and
erasure interactions, with cryptographic review of authenticated binding coverage.
**Both** for ratification readiness. Reviewer findings do not select ownership
policy or provide a default for 0020.

## B4. Custody inventory, provider enrollment and service wire schemas

**Exact blocker text — ADR 0027, Remaining unresolved questions, "Custody service
wire schemas":**

> **Custody service wire schemas:** What exact canonical inventory, denial and
> pending-fence member records produce section 3.3's checkpoint roots; what
> enrollment/rotation and provider-profile records bind their signers, copy IDs,
> generations and permitted wrapping algorithms? Which signed records establish
> inventory completeness rather than merely hashing an unspecified list?

**Further exact text — ADR 0027 §3.3:**

> Exact inventory/fence member schemas and provider enrollment/rotation attestations
> remain the explicit conformance blockers below, not arbitrary extension objects.

**What an implementer would have to invent:** the complete members beneath each
inventory, denial and pending root; their identities, domains, canonical set
constraints and cross-references; closed provider/witness enrollment and rotation
records; the provider-profile representation binding signers, copy/handle
generations, recovery routes and permitted wrapping parameters; and the signed
evidence by which a verifier distinguishes a complete registered inventory from
an arbitrary correctly hashed subset. No inventory schema, enrollment protocol,
wrapping choice or completeness mechanism is selected here.

Already specified in §§3.2–3.3: independent unit keys/handles, one encryption per
DEK, retained-pair retries, registered recovery copies, the checkpoint's outer
fields and signature domain, challenge binding, monotonic state, disclosure
fences and blocked recovery when proof is missing. Their existence does not
define the missing members or qualify a real provider. The text explicitly places
concrete provider/host qualification at a deployment gate.

**Existing ADR constraints:** ADR 0020 **Decision** requires reproducible
historical authorization, with no actor or operator default; provider attribution
cannot substitute for a ledger grant. ADR 0014 §§1/5–9 constrains consistent
prefixes, provenance and atomic recovery/publication. ADR 0025 §§3–6 distinguishes
complete content coverage and semantic validation from inclusion under a root.
ADR 0015 §§1/5–7 separates usable claim justification from custody and prevents
receipt counts or multiple paths becoming independent support. ADR 0026
**Decision** keeps operational usage outside belief evidence/lineage.

ADR 0022 §§1–2 constrains any subject/belief references carried in the service
records: custody does not create another current belief or redirect an existing
association. ADR 0021 §§1–4 supplies no ownership through bootstrap, and ADR
0018 **Decision** supplies no correction permission through custody. These are
scope constraints; none defines service wire fields. **0020 scope check:**
§§2/9 already supply the proposed limited authority scope for these records.
B4 has no separate prior 0020 ruling dependency; general user entitlement remains
unresolved and cannot be encoded as a provider default.

**Does ADR 0028 inherit it? Yes.** Sections 3/4.2 adopt the service and witness
boundaries; **Inherited format completeness** explicitly includes checkpoint
inventory schemas. Sections 4.1–4.2 add manifests, provider destruction receipts,
per-copy progress, completion reconciliation and restore denials. Their defined
outer receipt format/outcome meanings are not missing alternatives. The remaining
**Manifest and event schemas** and **Evidence-profile conformance** questions add
closure/copy acknowledgments, proof records, provider-profile evidence and
negative cases for forged, rolled-back or incomplete inventories.

In particular, 0028 **Remaining unresolved questions / Backup/replica deletion
acknowledgment** expressly leaves open whether destroying a wrapper handle counts
as acknowledgment for a backup/replica that never acknowledged independently,
and what evidence is required if it does not. This is a recorded unresolved
interaction with 0027 §3.2, not a license to equate the two provisions. Sections
9/11 add managed persistence, recoverable-copy and legacy-sanitization obligations;
their real-world validation remains separate from closing the schemas.

**Who resolves it:** **both**. The maintainer rules on the missing record and
evidence contract; independent cryptographic review covers signer/context and
key/wrapping guarantees, and storage/recovery review covers inventory completeness,
rollback, fences, recovery copies and acknowledgment meaning. Actual provider/host
qualification additionally requires deployment evidence under Gate 3; neither
a ruling nor a protocol review alone demonstrates physical erasure.

## B5. Interoperability vectors and rejection cases

**Exact blocker text — ADR 0027, Remaining unresolved questions,
"Interoperability evidence":**

> **Interoperability evidence:** Which published known-answer vectors and negative
> cases cover canonical Unicode/set ordering, strict Ed25519 verification,
> attestation nesting, AEAD context, fixed-key/nonce sealed bodies, retries,
> prefix changes and checkpoint reconciliation, so two implementations agree on
> both accepted inputs and bytes?

**Where the body gestures at it:** §3.1 requires identical wire objects across
implementations with fixed P/key/nonce/public inputs. Gate 1 requires positive
and negative interoperability vectors and a pinned candidate; **Acceptance cases**
enumerates semantic, isolation, failure and recovery requirements without
supplying the interoperable byte fixtures and expected results.

**What an implementer would have to invent:** the concrete inputs, canonical
bytes, intermediate/final commitments and expected accepted/rejected outcomes
that establish conformance for each listed family. The missing evidence includes
cross-language private-value cases (B2), every closed operation/basis and
authorization form (B1), compound-custody transitions (B3), and inventory/fence/
enrollment/checkpoint cases (B4). Their outputs cannot be selected before the
missing contracts are ruled on. Where the rule is already stated, generating its
expected bytes is evidence production, not a new semantic decision.

The existing **Acceptance cases** also constrain how vectors exercise wrong
capabilities/scopes/prefixes, missing enrollment, invalid partitions, lost
justifications, ineligible support, retries, publication failures and complete
replay. This inventory does not write those fixtures, choose a new test oracle,
invent rejection behavior, or treat agreement between two implementations of the
same mistake as independent protocol review.

**Existing ADR constraints:** ADR 0015 §§1–7 fixes candidate-local standing,
deduplication, explicit gate targets and round trips. ADR 0018 **Decision** and
ADR 0023 §5 preserve correction refusal pending the separate target contract;
fixtures must not make correction eligibility a default. ADR 0020 **Decision /
Acceptance cases** prohibits universal-authority fixtures and use of current
permissions for historical authorization. Fixtures for §§2/9's explicitly scoped
model need no separate prior 0020 ruling; Gate 1 permits synthetic specification
evidence without authorizing production implementation. ADR 0021 §§1–4
precludes confidence defaults; ADR 0022 §§1–2 requires duplicate-current-pair
refusal rather than repair. ADR 0023 §§1–4 preserves exact properties and retries;
ADR 0024 §§1–3 precludes head selection/coalescing; ADR 0026 **Acceptance cases**
precludes usage-created evidence. ADR 0014 §§6–10 and ADR 0025 §§1–6 constrain
canonical/replay equality, complete commitments and frozen-version fixtures.

**Does ADR 0028 inherit it? Yes.** **Inherited format completeness** expressly
requires interoperability fixtures. Its remaining blockers and **Acceptance
cases** add original-signature survival, safe legacy capsules/pruning, effective
replay/result encodings, receipt/profile evidence, partial destruction, restored
backups and erasure-aware reader boundaries. The backup-acknowledgment question
in B4 must be ruled on before its expected success/failure cases can be frozen.
Gate 1 protocol fixtures must be distinguished from Gate 3 tests of real providers,
hosts, managed copies and legacy sanitization in 0028 §§9/11.

**Who resolves it:** **both**, with an evidence-production dependency. The
maintainer rules on any still-missing expected semantics and the contract to be
frozen; vectors must then actually be produced and checked. The independent
cryptographer reviews byte/signature/AEAD/commitment conformance; storage/recovery
expertise reviews compound custody, checkpoint, crash/restore and erasure cases.
ADR 0027 requires independence of Gate 2 judgment from design assistance. It
does not say that an external reviewer must author every Gate 1 vector.

## Gate boundary and completeness accounting

**Inventory result:** five of five recorded blockers are covered, each with
source text, the definitions/evidence an implementer lacks, accepted constraints,
0028 inheritance and resolver roles. None is resolved here.

The following are not additional invented Gate 1 design choices: the specified
public canonical profile, framing, selected algorithms, signature/AAD scope,
nonce/key lifecycle principles and recovery barrier. They still need inclusion
in the evidence package and independent review. A pinned candidate commit is
also Gate 1 evidence, not an instruction to stage or commit this worksheet.

Concrete provider/host qualification, implementation conformance, fault injection
and demonstrated managed-copy/legacy cleanup belong to the stated deployment and
Gate 3 requirements. General correction, scored-link, restoration and contributor
entitlement decisions stay outside the limited stage as 0027 expressly says.
Review of its shared erasure boundary does not require ratifying or implementing
0028's erasure handlers before projector 3.

## 1. Blockers resolvable by maintainer ruling alone — dependency order

Here "ruling alone" means resolution of the missing **specification choice**,
not fulfillment of Gate 1's evidence obligations or Gate 2's independent review.
No ruling alone closes all requirements for ratification. The order below places
value/custody definitions before complete schema closure; B1 and
B4's cross-referencing records are grouped so no artificial one-way dependency
is asserted between incomplete schemas. Independent items may be considered in
either order; no item below is presumed decided by this ordering.

**0020 dependency check:** none of the scoped items below is blocked by a prior
0020 ruling. Sections 2/9 already state the limited authority model whose schemas
and evidence remain incomplete. Contributor write/read permissions and the other
excluded multi-user policies remain **UNDECIDED under 0020**; an extension relying
on them would require a prior ruling, but is not part of this ordered Gate 1 list.
Historical authorization at the pre-event prefix constrains all relevant records
and fixtures throughout the list.

1. **B2: private value/number domain and decoding semantics.** The already
   specified public wire and frozen-byte constraints apply. This ruling supplies
   the private-value definition needed by B1's protected-content schema and B5's
   cross-language fixtures. It requires no invented contributor entitlement.
2. **B3: compound custody representation and normalization.** Existing identity,
   candidate and current-container contracts constrain it. This supplies the
   compound binding definition used by B1's transition inventories, B4's binding
   references and B5's transition fixtures. Using it to decide ownership would
   exceed the scoped contract and require the excluded 0020 policy ruling.
3. **B1 and B4: complete closed operation/authorization/attestation and custody
   service record contracts.** After the preceding definitions, the outstanding
   field domains, selectors, memberships, cross-references, enrollment/profile
   records and inventory-evidence meaning remain for the maintainer to rule on.
   Their coupled closure is one ordering item, not a proposed shared schema.
   For the inherited 0028 extension, the recorded backup/replica acknowledgment
   question and erasure-specific record/evidence definitions also need rulings;
   their technical adequacy is subject to list 2. No answer is chosen here.

B5 is absent as a ruling-only closure: missing vectors and verified expected
outputs require produced evidence after items 1–3. Selecting semantics is the
maintainer's role; declaring a test passed is not a substitute for the evidence.

## 2. Blockers requiring independent review — review dependency order

These assignments identify required expertise under ADR 0027's Gate 2 and
engagement-scope question. They do not appoint a reviewer or determine whether
one qualified reviewer covers both domains. Each review follows the relevant
maintainer rulings and a pinned Gate 1 specification/evidence package.

1. **B1/B2: signed operation boundaries and private-codec interaction — independent
   cryptographer.** Review public/protected separation, complete signature and
   attestation scope, canonical/parser behavior and authenticated private decoding
   against the frozen definitions. Storage/recovery expertise covers record scope,
   durable replay and publication consequences. The review checks the chosen
   contract; it does not grant permissions or decide the application's value model.
2. **B3/B4: compound custody, inventory completeness and provider/witness protocol —
   storage/recovery reviewer plus cryptographer.** Storage/recovery review covers
   compound scope across histories, enrolled recoverable copies, prefix/fence
   reconciliation, rollback and acknowledgment meaning, including the unresolved
   0028 backup-handle interaction once ruled on. Cryptographic review covers
   authenticated bindings, enrolled signers, key/wrapping assumptions and proof
   limitations. Neither specialty alone is presumed to cover the other's scope.
3. **B5: interoperability evidence and rejection coverage — both domains.** After
   B1–B4 definitions exist, cryptographic review examines known-answer bytes and
   negative signature/AEAD/canonicalization cases; storage/recovery review examines
   custody, checkpoint, crash/restore and erasure cases. Review findings and
   remediation verification must identify the exact resulting candidate revision.
   Evidence generation may precede review; independent judgment cannot collapse
   into self-review by its designer.
4. **Provider/host and implementation assurance — storage/recovery reviewer and
   cryptographer as applicable; explicitly Gate 3, not a sixth Gate 1 blocker.**
   The separately recorded production gate additionally needs concrete evidence
   for implementations, provider profiles, backups, swap/dumps, fault recovery and
   managed erasure/legacy sanitization under 0028 §§9/11. This later review cannot
   be marked complete by a specification ruling or by this worksheet's tests.
