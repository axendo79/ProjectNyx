# ADR 0027: Stage Three Authority and Acceptance

Status: Proposed — draft for review; not ratified and does not authorize implementation.

Date: 2026-09-13

Supersedes on acceptance: The stage-three deferrals and protected-storage representation requirements identified in the supersession table below, only under explicitly selected projector "3". No existing projector gains these semantics.

Related: [ADR 0022](0022-belief-container-uniqueness.md); [ADR 0024](0024-no-authoritative-head.md); [ADR 0025](0025-incremental-result-commitment.md); [ADR 0026](0026-usage-is-not-evidence.md); proposed [ADR 0028](0028-redaction-and-crypto-shredding.md); architecture Invariants 3, 4, 8, 9, 14 and 15.

Implementation: None. This file proposes one shared acceptance contract for merge, split and corroboration, including permanent signatures, protected storage and custody prerequisites. Existing projectors retain every current refusal.

## Context

Merge acceptance, split acceptance, and gate-approved corroboration need the same
missing foundation: permission to change a shared projection, evidence establishing
the proposed association, and a reproducible acceptance decision at the actual log
prefix. Three independent authority policies would disagree at their boundaries.

An actor ID is attribution, not authority. An operator's permission to maintain a
ledger is not evidence that two referents are identical. A speaker can establish
what they meant without gaining permission to rewrite another speaker's assertion.
This decision separates those questions once for the three operations.

## Decision

### 1. Version and deployment boundary

Register projector "3" for this stage. Versions "0", "1", and "2" remain frozen;
none gains new event handlers, acceptance rules, lineage formats, or fallback
dispatch. Defaults do not change. Projector "3" accepts the existing stage-two
mention/observation contract and adds only:

- `authority_configured` and `authority_updated`, the governance records below;
- `entity_merge_accepted` and `entity_split_asserted`;
- `entity_link_accepted` for the same admissible association bases and authority;
- `verification_completed` with `verification_kind="corroboration"`.

Every new event in the protected stage-three ledger, including ordinary mentions
and observations, uses event schema "2" and the sealed-body contract in section 3.
Governance and stage-three operations use `contract="nyx-stage-three/1"`;
ordinary stage-two-shaped assertions use `contract="nyx-stage-two-protected/1"`.
Their logical assertion semantics remain unchanged. Keep the existing envelope
hash formula, timestamp spellings and retained-pair retry contract; payload and
idempotency commitments now cover the recorded sealed body, never a plaintext hash.
Legacy schema-"0" events are interpreted only by their existing supported shape;
section 8 limits their admission to a protected writable store.
Old projectors refuse a cutoff including an unsupported event, never skip it.
Governance/acceptance envelopes use `origin_type="observed"` to record receipt of
the signed operation; they are not property observations and are never counted as
world evidence. Other origin-to-state mappings are not introduced.

Database schema "5" adds version-isolated authority, association, justification,
restriction and successor indexes, permanent signed public objects, protected
bodies, immutable unit bindings and derived effective-binding indexes. Ordinary
opens refuse incompatible databases;
this draft authorizes neither in-place migration nor automatic recreation.
Recreating an explicitly selected database by replaying an exported supported
log preserves event IDs and hashes; initialization is an operator action.

Use protected `nyx-map/2` trees with ADR 0025's canonical routing, branch encodings
and incremental publication discipline. Replace only the format discriminator
and leaf representation: opaque recorded keys and complete nonsecret structural
members plus immutable protected references `{unit_id, sealed_body_hash, selector}`.
Selectors are arrays of opaque field IDs/integer positions, never private strings.
The three collection names and `nyx-result/1` construction remain as in ADR 0025.
An identity record receives a recorded opaque ID; private canonical JSON is never
a tree key. Dependencies retain envelopes and sealed bodies, not decrypted copies.
Changed protected content or any missing member, path, support assignment or
custody transition changes its commitment. Full logical reads decrypt references
only with separate authorization. No reducer performs encryption or key allocation.
Version-3 lineage uses `nyx-belief-lineage/3` and `projector_version="3"`, otherwise
ADR 0025's result-and-ancestry construction. Complete candidate contents include
the justifications, restrictions and support applicability specified here.
Relevant signed decisions and their authorization history enter event dependencies
and identity records. Merely having an unrelated authority update in the log does
not change every belief's lineage. Bounded updates remain incremental; an identity
operation may legitimately touch every record on its affected subjects.

### 2. One explicit ledger policy, with narrowly scoped capabilities

Stage three uses one shared acceptance policy per ledger, with an explicitly
enrolled human policy administrator. This is a decision about the shared kernel
view, not about ownership of statements or a multi-tenant permission system.
Enrollment is never inferred from installation, OS username, `actor_id`, first
write, or who happened to launch Nyx.

Before any stage-three operation, the administrator explicitly pins a `ledger_id`
and an Ed25519 public-key fingerprint. `authority_configured` records that key,
the ledger ID, the exact adopted pre-event log-tip hash (or null at genesis),
policy version `nyx-stage-three-authority/1`, and the complete initial grants.
The administrator signs it. A replay verifier requires the same explicit trusted
enrollment; a self-signed key found in an otherwise untrusted log is not its own
authority. The public pin is trust configuration; all grants and changes are in
Layer A, never solely in a derived table.

The stage-three operation capabilities are:

| Capability | May authorize | Does not establish |
|---|---|---|
| `identity_curator` | Merge, split, and accepted association of the explicitly covered subjects in this ledger's shared projection, including assertions from different speakers | Correctness of reference, ownership of those assertions, or property verification |
| `corroboration_approver` | One scoped new corroboration candidate after the deterministic gate succeeds | An independent world signal merely by signing |
| `identity_attestor` | A recorded direct-world identity observation, limited to the declared observation domain | Permission to change the shared projection |
| `protected_decrypt` | Decrypt explicit units for an explicitly granted purpose and complete subject scope | Identity changes, redaction authorization, erasure execution, or a general contributor-read policy |

Each grant records a principal ID, public key, capability, and explicit scope:
either this entire ledger or an enumerated set of subject IDs. No omitted scope
means "all". Subject-scoped grants must cover every pre-event participating subject;
new successor IDs are included in the operation authorization, not automatically
in future grants. The administrator may explicitly hold multiple capabilities,
but receives none by implication. A submitted source may not self-assign a role.

`authority_updated` is signed by the administrator authorized at the preceding
prefix. It records the prior policy-event hash and the complete replacement grant
set. Administrator-key rotation also requires the new key's countersignature.
Governance uses the explicit `policy_administrator` authorization capability,
checked against the pinned enrollment/successor administrator, not a curator or
decrypt grant. It confers no implicit content access or destruction capability.
Changes take effect after their own event and do not retroactively validate or
invalidate earlier actions. Loss of the sole administrator key stops privileged
changes; no unsigned recovery or implicit replacement administrator is supplied.

The remainder of ADR 0020 stays open: contributor write/read permissions, multiple
administrators with competing authority, per-user views, ownership, delegation
between users, tenant isolation, consent disputes, and user-specific verification.
This policy gives curators explicit authority over the shared *interpretation*;
it never permits editing or suppressing someone else's historical assertion.
`protected_decrypt` is a separate service capability, including for the semantic
validator and any human reviewer. Its grant records purpose, ledger/subject scope,
and either exact units or all units within that explicit scope. No grant means no
decryption. This defines an enforcement seam, not which contributors deserve
access. A curator signature never doubles as a read grant. Redaction authorization
and execution are separate capabilities supplied only by proposed ADR 0028.

### 3. Permanent signed public envelope and protected body

The original signed public envelope remains independently signature-verifiable
after authorized erasure. Verification of the envelope and its authorization is
distinct from semantic verification of protected content. No later capsule
reproduces, substitutes for, or retroactively validates the original signature.
"Permanent" is a storage/format invariant, subject to the cryptographic assumptions
of the selected algorithms; it is not a promise against future cryptanalysis.

Use shared canonical UTF-8 JSON, canonical set ordering and lowercase hex for
binary values. Every privileged operation signs exactly this public object U
with Ed25519 ([RFC 8032](https://www.rfc-editor.org/rfc/rfc8032)):

`{"format":"nyx-public-operation/1","ledger_id":L,"projector_version":V,"contract":C,"envelope":E,"authorization":A,"structure":S,"protected":D}`.

| Component | Exact retained contents |
|---|---|
| E | `event_id`, `schema_version`, `event_type`, exact `occurred_at` and `recorded_at`, `source` containing only opaque `actor_id`, `source_class`, `origin_type`, canonical `entity_refs`, and exact `prev_event_hash`. These must equal the outer envelope fields. |
| A | `policy_event_id`, `policy_event_hash`, `principal_id`, `key_id`, `capability`, and explicit `scope`. Genesis enrollment names its own recorded policy ID with null policy hash and is checked against the externally pinned key and adopted prefix. No signature or private reason is inside A. |
| S | The closed structural inventory below, including immutable original unit bindings. No private text, clear claim value, identifier string or plaintext-derived fingerprint. |
| D | Null for an operation with no private content; otherwise `{unit_id,key_id,key_version,algorithm,codec,nonce,tag,ciphertext_hash}`. `unit_id` is the event ID, algorithm is `ChaCha20-Poly1305`, codec is canonical JSON UTF-8, and the hash is SHA-256 of recorded randomized ciphertext bytes. No DEK or wrapped DEK. |

S records the event-kind-specific fields already required by this decision:
opaque input/output entity, mention, belief, candidate and link IDs; exact opaque
property IDs; predecessor event IDs/hashes and pre-event belief lineage hashes
with their projector versions; mention partitions; candidate output inventories;
support selectors and their roles/applicability; basis kinds, signed public
attestations and protected basis references; justification IDs/rules/required
sets; restrictions and prior/result standing; and custody dispositions in section
5.1. Governance additionally records public enrollment keys, adopted prefix,
complete grants, namespace uniqueness/validity rules and policy succession.
Ordinary mentions/observations record the corresponding bootstrap/claim structure.
Values/text/source configuration, human identity mappings, private namespace
identifiers, observation details and free-text reasons are solely in protected
content. References to this event's content are `{unit_id,selector}` in S to avoid
a self-hash cycle; references to earlier bodies also carry their committed hash.
Unknown public fields refuse; extra private data cannot be smuggled into a public
extension object. An operation needing unrepresentable private structural metadata
refuses rather than silently publishing it.

For each private event unit generate one fresh 256-bit DEK and a 96-bit nonce,
encrypt once with ChaCha20-Poly1305 and its 128-bit tag
([RFC 8439](https://www.rfc-editor.org/rfc/rfc8439)). Associated data is canonical
`{format:"nyx-unit-aad/1",ledger_id,event_id,schema_version,projector_version,contract,envelope:E,authorization:A,structure:S}`.
It excludes D, signatures and final hashes. Then construct D, sign U, assemble the
stored body `{format:"nyx-sealed-body/1",public:U,signature:SIG,sealed_content:X}`,
and compute payload/idempotency/event hashes using that body. X is ciphertext hex
or null when D is null. Retain U, SIG, D and X permanently; destruction removes
decrypting keys, not the message signed. Private content never appears in E.
SIG is a canonical set of `{key_id,signature}` objects: the required primary signer,
plus the new administrator's countersignature on rotation, with no extra/duplicate
signers. Each signs exactly U. Unsigned ordinary events use null, not an empty
approval set. Final payload/event/idempotency hashes and SIG are outside U and
are independently recomputed/checked from the retained public/sealed body.
This order has no signature/encryption/hash cycle. A changed prefix requires a
fresh unit encryption with a fresh key (AAD changed), new review and new signature;
an exact retry retains the entire original body, nonce, timestamps and IDs.
No automatic plaintext-equality retry lookup is introduced for new sealed events.

Ordinary observations/mentions use the same sealed representation with A and SIG
null; this does not invent a contributor-signing requirement. Their integrity is
provided by the hash chain and body commitment, not a claimed approval signature.
Any privileged operation, enrolled authority update, attestation or erasure action
must carry its specified original signature. An embedded attestation signs exactly
`{format:"nyx-public-attestation/1",ledger_id,principal_id,key_id,policy_event_id,policy_event_hash,basis_kind,relationship,subject_ids,mention_ids,recorded_at,evidence,scope}`.
`evidence` is a canonical set of `{event_id,event_hash,unit_id,sealed_body_hash,selectors}`
references to earlier committed protected evidence units. Private detail and actual
identifier values live there, not in the attestation. The separately recorded
signature binds that public object and is included in the enclosing operation's S.
An attestation cannot refer to the enclosing operation's own unit, ciphertext,
signature or final hash: doing so would create an encryption/signature cycle.
First record any needed protected evidence under its supported assertion contract;
the acceptance operation never silently manufactures that evidence. No
unregistered private sidecar or plaintext-hash attestation is permitted.

Append verifies public fields, original signatures and historical grants against
the locked pre-event prefix, decrypts with separate permission, verifies the
protected commitment/AEAD, and checks all live semantics. Replay never substitutes
current permissions for historical acceptance. A verifier lacking decryption
permission reports semantic verification unavailable; it cannot authorize a new
content-dependent operation on that basis. Under a future authorized erasure,
original U/SIG/grants remain verifiable; content-dependent historical checks become
explicitly unavailable. Typed erasure and effective-state rules require ADR 0028.

Public metadata intentionally exposes topology, timing, membership, grant scope,
standing, ciphertext lengths and stable opaque identifiers. Randomized ciphertext
commitments avoid a public low-entropy plaintext-hash oracle, not those metadata
leaks. Public signatures attest an operation, not its truth. No plaintext-based
deduplication index, private map key or diagnostic may undo this separation.

DEKs are held by a separate privileged service, never in Layer A or ordinary
database backups. Fresh protected writes require independently erasable units,
registered derived-key dependencies, no recoverable wrappers in ordinary stores,
and a key-provider recovery model capable of deleting all recoverable copies.
Key availability is not historical truth. Operational read authorization and
secret custody remain explicit inputs; reduction allocates no keys and uses no
key-service clock or current permission policy to validate past grants.

### 4. Closed list of admissible existing-subject association bases

Upon acceptance, the following is the ratified list for this stage. Anything else
refuses, including similarity, equal display names, equal property values, an empty
search, model confidence, repeated retrieval or Dream references. Each accepted
basis records both its relationship and exactly which assertions it covers.

| Basis | Required record and relationship established | Limits |
|---|---|---|
| `speaker_reference_confirmation` | A signed confirmation from the recorded speaker, with that speaker's key binding explicitly enrolled by the administrator, identifying their exact mention and an already uniquely identified target reference | Establishes that speaker's intended reference only. It does not establish another speaker's intent. Every affected mention relying on this basis needs its own applicable confirmation; curator authorization is still required. |
| `direct_identity_observation` | An `identity_attestor` in the granted domain records a direct observation identifying the concrete referents of the named mentions and explicitly asserting sameness, distinctness, or the stated partition | Must record what was observed and how it binds each endpoint. A model derivation, structural audit, copied label or bare curator assertion is not a direct observation. No property standing is earned. |
| `authoritative_identifier_binding` | Recorded attestations bind each endpoint to an exact identifier in the same administrator-enrolled authority namespace; the enrollment records the issuing key, uniqueness domain and validity conditions | Equality supports sameness only within that recorded uniqueness domain. Distinct keys support separation only if the namespace explicitly guarantees distinct referents. Copied strings without authenticated bindings do not qualify. |

Speaker/namespace key enrollment is an explicit part of `authority_configured` or
`authority_updated`, with no inference from matching actor strings. All inputs
needed for an identifier check, including validity intervals, are recorded; replay
does not consult a live registry. Append checks applicability at the operation's
recorded instant, using instant comparisons, not today's time.

For a merge, admissible sameness edges must connect all participating subjects and
cover the mention associations being changed. A recorded, applicable distinctness
constraint vetoes the merge until separately resolved; a property-value conflict
does not prove distinct identity and is retained as candidate disagreement.
For a split, the bases must establish the declared partition, not just explain why
the old identity is suspect. Permission or complete mention assignment cannot
substitute for that evidence. The evidence and authorization can be supplied by
the same enrolled person, but must satisfy both independently recorded roles.

A new mention still bootstraps a fresh scoped subject. Association afterward is
an explicit accepted link or merge. `entity_link_accepted` records fresh link ID,
source mention/scoped subject, uniquely resolved current target, admissible basis,
and authorization. Historical assertions retain their recorded subject IDs.
There is no implicit absorption of a pre-existing subject's whole membership.
An ordinary accepted association link does not rewrite private-unit custody.
It supplies a recorded identity relationship only. Custody changes require an
explicit merge/split transition under section 5.1, never resolver lookup or an
inferred current-canonical-subject cache.

### 5. Merge and split operate on the complete affected set

Keep ADRs 0013/0014's fresh successor entities and beliefs, predecessor paths,
current-only subject/property uniqueness, and distinct ID scopes. The payload
records every output ID and association; acceptance discovers the required set
from the snapshot and rejects missing, extra, reused or wrongly associated outputs.
All current properties of each participating subject are included. Sharing an
evidence event alone does not make an unrelated subject a participant.

Candidates deduplicate by candidate ID, evidence by event ID within each pool, and
paths remain separate provenance. Merging never coalesces by value or promotes.
No belief-level verification state or scalar winner is computed.

A split records an exact partition of the current pre-event mention set into at
least two nonempty, fresh successor subjects. Each mention occurs once, and every
destination is declared. It also records candidate-output and support-assignment
inventories. Every predecessor candidate is accounted for: unchanged claim scope
and applicability retain its ID; distinct successor claim scopes receive fresh
candidate IDs and predecessor links. Historical candidates are not revived.

For every evidence-to-candidate association, the payload identifies the original
claim selector and the previously established applicability to the successor.
A path to a mention is not proof of claim support. A spanning event may support
multiple successors only through explicit established claim assignments. Otherwise
the whole split refuses. Provenance-only assignments are recorded as such; no
required usable support is silently dropped or duplicated to make a partition fit.

### 5.1. Historical and effective custody are separate from claim support

Each private unit's creation manifest permanently records `original_binding`:
either `{kind:"subjects",subject_ids:[...]}` with a nonempty canonical set of
explicit subjects, or `{kind:"ledger",ledger_id:L}` for private governance material
with no subject referent. The latter requires explicit ledger-wide permission;
an empty subject list never means unrestricted. Bootstrap binds the scoped subject
from ADR 0019. A transition's own new private unit explicitly names its successor
subjects and any other subjects it concerns; validate that inventory at creation.
Neither a mention ID nor an actor string is an owner. Original bindings never
change, including after retirement, later association or erasure.

`effective_binding(unit_id, locked_prefix)` folds only accepted merge/split custody
dispositions from that original binding. Its output records current subject IDs,
disposition (`assigned`, `shared`, or `ambiguous`), and explaining transition IDs.
The current index is reconstructible/cacheable, never the sole authority. Initial
single-subject units are assigned; explicitly multi-subject units are shared.
Ledger-bound units remain ledger-bound. Canonical subject in this draft and ADR
0028 means this prefix-specific recorded identity, not world uniqueness or title
to someone else's assertions. Historical queries disclose original and effective
bindings separately; live decrypt authorization uses the actual current prefix,
not a user-selected earlier `as_of` that could bypass a later split.

For a merge A+B -> M, replace occurrences of A or B in each affected effective
subject set with M and deduplicate. Preserve other subjects and the original
bindings. If all alternatives collapse to one subject, the binding becomes
assigned; remaining shared/ambiguous alternatives retain their disposition.
Resolve retired identifiers by following only these identity-successor edges to
active leaves, deduplicated; return unique/multiple/none with paths. Association
links are not successor edges. No key, ciphertext or old event is rewritten.

For A -> B+C, the signed custody inventory accounts for every retained unit whose
effective binding contains A, including historical, provenance-only and already
erased units. Each has exactly one explicit disposition for A:

| Disposition | Required basis | Effective binding contribution |
|---|---|---|
| assigned to B (or C) | Recorded applicability establishing the unit's private scope, identified by unit/selector and basis references | B only (or C only) |
| shared across B,C | Recorded applicability establishing both scopes | `{B,C}`, marked shared |
| ambiguous across B,C | Scope cannot be distinguished; uncertainty is recorded explicitly | `{B,C}`, marked ambiguous |

With more successors, a nonempty explicitly recorded subset replaces A, with the
same assigned/shared/ambiguous distinction. Retain all other pre-event bindings.
Missing units, empty assignments, unrecorded fan-out and arbitrary one-child
assignment refuse. Unknown private applicability produces an explicit conservative
ambiguous disposition; it supplies no usable evidence to either child. This is
custody of one indivisible unit, not copying it or its DEK into several claims.
The separate claim-support requirements of section 5 still refuse a split if a
live output claim's applicability cannot be established. After erasure, only
retained structural assignments may establish a narrower custody scope; otherwise
record ambiguity. Unknown secret content is never reconstructed to decide scope.

Identity authorization covers all participating pre-event subjects and all other
subjects affected by changed unit bindings; shared custody does not make those
other subjects participants in the identity merge itself. The complete signed
inventory, not a private-unit scan after publication, authorizes the transition.
Publication atomically changes identity and effective-binding indexes. Readers
and key-service permits are invalidated against the new prefix before disclosing
any newly scoped content; stale grants cannot bypass the transition.

Decryption of shared/ambiguous units requires an explicit `protected_decrypt`
grant covering every effective subject, the unit selection and purpose. Authority
over B alone cannot reveal a B/C unit. No identity capability implies that grant,
and successor grants are not inherited automatically. A request may fail for lack
of decryption even when a curator has permission to propose an identity change.
Redaction similarly requires authority over the full affected set, but execution
does not require decryption; the destructive workflow belongs to ADR 0028.

### 6. Dependent links and standing across a partition

Constitutive links retain their historical meaning and ADR 0021's no-confidence
treatment. New non-constitutive links admitted here have `link_state="accepted"`,
`basis_kind` from section 4 and `confidence_treatment="recorded_basis"`; there is
no numeric confidence. This is an explicit treatment for these links, not an
alias for constitutive and not a confidence of 1.0. Their usability is determined
by the recorded basis and restrictions. Probabilistic/scored links remain outside
this stage; a path requiring one refuses rather than silently dropping its ceiling.

The split inventories all inbound/outbound dependent links. Retire changed current
links with `link_state="split"`, retaining their original endpoints and basis.
Create recorded fresh successor links only where the old basis establishes the
new endpoints. Unchanged links retain their IDs. An ambiguous link remains a
historical unresolved relationship, with its possible successors disclosed; it
cannot be used as active support. If any accepted output claim requires that link
and lacks established alternative applicability, refuse the split. Invalidate
transitive successor caches atomically with the complete delta.

Each candidate carries explicit justifications: kind, exact claim scope, required
evidence IDs/claim selectors, required identity paths, and approving event where
applicable. Original direct-observation justification refers to its observation;
corroboration justification refers to its signed approval and evidence set.
Restriction records identify the candidate or specific support/path they constrain.
Supersession, questioning, quarantine and their history are never erased by a move.

The deterministic restriction rule for identity operations is:

| Prior standing | Applicable usable justification survives | Necessary justification becomes unusable |
|---|---|---|
| `verified` | Hold `verified` | `questioned`, with the failed dependency and identity event recorded |
| `unverified` | Hold `unverified` | `questioned` when a required support/path fails |
| `questioned` | Hold `questioned` | Hold `questioned`, retain/add the dependency failure |
| `quarantined` | Hold `quarantined` | Hold `quarantined`, retain/add the dependency failure |
| `redacted` (only under an accepted erasure-capable projector) | Hold `redacted`; structural/history transport only | Hold `redacted`; never recreate or decrypt destroyed content |

For a newly scoped split candidate, apply the predecessor's restrictions and this
same rule to justifications explicitly applicable to the new scope. A justification
for the unresolved predecessor is not automatically applicable to both children.
If claim applicability itself is unknown, section 5 refuses the split rather than
creating an unsupported candidate and labeling it questioned. Supersession remains
a relation/lifecycle restriction, not a verification aggregate.

Under an accepted erasure-capable projector, a redacted predecessor moved into a
new claim scope remains redacted with a new structural candidate ID and explicit
predecessor/unavailable-content reference; it receives no new encrypted copy or
key. Retain opaque historical candidates even when no narrower claim assignment
can be established; refuse a split requiring an invented output scope. Necessary
live justification lost through erasure uses the dependency-loss column above;
independent sufficient surviving justification holds. Custody ambiguity does not
itself count as support. Erasing a private identity basis preserves the historical
decision/topology but makes content-dependent use unavailable. New identity
acceptance needing that basis refuses without independently sufficient live or
structurally sufficient evidence. Replaying the historical decision under ADR
0028 is a different operation, not a fresh acceptance of its destroyed basis.

Losing one of several *separately recorded sufficient* justifications does not
invalidate an unaffected surviving one. A justification's recorded dependencies
are conjunctive; the reducer does not discover a new substitute subset while
recomputing. Removal of adverse evidence or restoration of a path never promotes.
Restoring standing needs a separately gated event; generic restoration handlers
and their broader permissions are not introduced here.

### 7. Corroboration is a separate, reproducible gate

The approval payload records one fresh candidate ID, current subject/property and
belief ID, exact claim value and scope, contributing candidate IDs, selected
evidence IDs and claim selectors, source classes, sufficient justification, and
the authorization from section 3. Its `verification_basis` is
`{"kind":"corroboration","policy":"nyx-corroboration/1","minimum_source_classes":2}`.
The gate creates this candidate at `verified`; contributors remain unchanged.

Acceptance independently checks that every selected event supports that exact
claim, that its identity path is usable, and that there are at least two distinct
recorded source classes after event-ID deduplication. Count the underlying world
evidence, not approval events, candidates or paths. Layer B outputs, usage,
re-derivation and structural audits are not independent world evidence. Equal
payload hashes neither establish claim identity nor establish independence.
The approver cannot waive the existing two-source floor by signing.

This initial gate admits contributing candidates at `unverified` or `verified`
with no applicable question, quarantine, supersession or redaction restriction on
the selected claim/support. Question-resolution and quarantine-restoration gates
remain separate work; an approval cannot launder them into a new candidate.
An alternative single-human-confirmation gate is not implemented by this contract.
The proposed gate is an executable constraint, not an oracle called during replay.

An approval is not bundled into a merge/split to promote at the same transition.
It is a subsequent event against the published identity prefix. It leaves N
contributors plus one new candidate, with no retention or coalescing policy.
Dependencies point backward in the log; reject cycles and self/future dependencies.

### 8. Publication, reads and verification

Append authorization and semantic validation occur under the same write lock.
Append records freshness for every affected identity/belief; full delta publication
and derived progress commit separately and atomically under ADR 0014. Readers
retain stale disclosure, including mention/link and successor reads. Resolving a
historical identity returns unique/multiple/none with explaining paths; a caller
requiring one successor must explicitly select it when multiple exist.

Full replay starts from the log and trusted enrollment, not present permissions or
derived tables. At common cutoff, evaluation time and projector version, all IDs,
standing, paths, authorizations, roots and lineage equal incremental publication.
The same usable evidence, restrictions and applicable gate history must produce
the same standing through merge → split → remerge. This compares corresponding
claim scopes, not candidate counts or revived historical IDs.

### 8.1. Protection before the first durable write

Secret-bearing material must be encrypted before its first durable write. This
includes the authoritative append-only event stream, any JSONL ingestion/export
or retry spool, SQLite source/projection tables, historical roots and lineage,
indexes, process traces, caches, diagnostics, WAL/journal/temp files, backups and
recoverable key wrappers. The protected body in section 3 is the authoritative
representation from inception; a projection-local encryption key cannot erase
plaintext already in an immutable source log. Apply ADR 0028 section 9's closure
inventory as a storage acceptance checklist without importing its erasure handlers.
The invariant is defined here independently of whether that draft is accepted.

Derived private data uses source-unit references or independently erasable keys
with durable exact dependency registration. Reducer-generated private content
must not reach persistent storage through an unregistered cache or index.
Rebuild reconstructs structure and original protected references without random
re-encryption; any unavoidable new derived ciphertext is a disposable protected
cache, never the sole record of lineage or semantics. Missing live decryption
authority/key availability blocks semantic replay; it is not a redaction sentinel.
Before ADR 0028 ships, projector 3 refuses erased history rather than inventing
availability/standing semantics. It grants no power to destroy committed keys.

Independent stage-three launch permits fresh protected writable ledgers only.
Do not mix new protected events into an unconverted plaintext ledger and claim
the resulting history is erasable. Legacy logs remain readable under their old
contracts. Enrollment/conversion into an erasure-managed ledger is an explicit
later operation under ADR 0028's legacy checks, preserving original IDs/hashes
and reporting any uncleared plaintext debt. No silent rewriting of legacy events
or frozen projector fixtures is permitted.

### 8.2. Release gate and alternatives

Projector 3/schema 5 may ship before a redaction-capability release only if the
permanent signature, protected first write, reconstructible historical/effective
custody and complete recoverable-copy protections above pass acceptance together.
There is no plaintext stage-three intermediate format. Encryption, key-service
integration and explicit validator decryption grants are part of this stage's
cost, even though deletion, sentinel reads and erasure recovery wait for ADR 0028.
The provider must already support independently erasable key custody; no early
backup design may make future per-unit erasure impossible.

Separate releases make stage-three acceptance available earlier but require two
versioned reader/publication contracts, schema 4 -> 5 and later 5 -> 6 explicit
cutovers, and continued refusal by projector 3 on erased history. The second
release can reuse sealed bodies, original signatures, bindings and `nyx-map/2`;
it adds effective erasure views rather than repairing a plaintext intermediate.

A combined first release can introduce protected storage and erasure together,
avoid deploying schema 5 as an intermediate, and exercise identity/erasure
interactions before any new version freezes. It delays stage three until key
destruction, leases, sweeping and recovery all work, and increases the first
release's validation scope. If the early storage/key prerequisites cannot be met,
delay or combine the cutover; do not ship the former plaintext/sign-full-payload
design. Keep the draft version allocations for the separate path, but actual
release scheduling and any combined version allocation remain unratified.

### 9. Exact supersessions and limits

| Earlier ADR | Effect upon acceptance of this draft |
|---|---|
| [0013](0013-cross-belief-identity-semantics.md), sections 1–5 and version scope | Preserve fresh identities, support applicability, complete partitions and conflict refusal; supply the missing authorization and projector-3 acceptance boundary. Property conflict does not itself veto identity. |
| [0014](0014-cross-belief-reducer-and-hash-lineage.md), sections 1, 3–9 | Preserve the snapshot/delta, coverage, progress and recovery contracts; add replayable authorization dependencies. Use ADR 0025's incremental representation under a distinct lineage version. Do not reinstate its superseded differing-state refusal. |
| [0015](0015-candidate-scoped-verification.md), sections 3–5 and implementation deferral | Make split justification transport, dependency-loss destinations and the initial corroboration gate concrete. Narrow initial corroboration inputs as section 7 states; retain candidate identity, no aggregate, no pooling promotion and round-trip standing. |
| [0018](0018-correction-supersedes-candidates.md) | No correction semantics superseded. Shared-identity authority does not grant correction authority or settle candidate-target eligibility. Version-3 corrections remain refused pending that separate contract. |
| [0019](0019-identity-bootstrap.md), section 4 | Replace the empty admissible-bases list with section 4's closed list for projector "3". Preserve separate bootstrap and recorded IDs; do not turn a new mention into an implicit existing-subject association. |
| [0020](0020-multi-user-authority-undecided.md) | Narrow its blocker only for the explicit ledger-scoped stage-three capabilities, enrollment and historical authorization above. Preserve the separation between permission, attribution, intended reference and evidence; all other multi-user policy remains open. |
| [0021](0021-bootstrap-link-treatment.md), section 3 | Preserve constitutive treatment; settle nonnumeric, recorded-basis usability for this stage's accepted links. Other link kinds and scored matching remain undecided. |
| [0023](0023-stage-two-contract.md), stage-three deferral | Discharge merge/split/corroboration deferral only in projector "3". Preserve stages "1"/"2", fresh ordinary candidates, exact properties, retained retries, correction refusal and no support attachment. |
| [0002](0002-payload-stored-plaintext-in-v0.md) | End the plaintext exception for all new protected stage-three writes; preserve old event bytes and require explicit legacy conversion. |
| [0007](0007-payloads-keyed-by-event-id-not-payload-hash.md) | Preserve event-unit identity and independent keys; new payload hashes commit to recorded sealed bodies. Equal plaintext does not pool keys or define retry identity. |
| [0025](0025-incremental-result-commitment.md), sections 2-6 and schema selection | Introduce schema 5 and protected `nyx-map/2` members/opaque keys under projector 3; preserve canonical routing, incremental publication, complete commitments and frozen projector 2. |

## Acceptance cases

- Erase a protected operation detail in an erasure-capable test harness: the
  original public signature still verifies without any capsule substitution;
  content-dependent semantic verification is explicitly unavailable. Changing a
  public scope, predecessor, protected descriptor or original binding invalidates
  the signature. Ordinary unsigned events never acquire a claimed approval.
- Canary secrets never reach authoritative JSONL/SQLite, private index keys,
  immutable historical leaves, retry spools, logs or backups in plaintext. Losing
  a projection key cannot leave a recoverable plaintext source behind.
- A -> B+C assigns individual units to B, C, shared or ambiguous exactly as
  recorded. No implicit fan-out, key copying or support duplication occurs.
  An ordinary accepted association leaves custody unchanged. Scope-B decryption
  refuses shared B/C units; an explicit whole-scope grant is required.
- Redacted candidate -> split -> merge retains unavailable secret content and
  structural ancestry; no key or decryptable copy is created. Live dependent
  standing holds or demotes under section 6, never promotes through custody.

- An unconfigured ledger, ungranted actor, wrong capability, missing subject scope,
  changed action body, foreign-ledger signature or stale-prefix signature refuses
  without append. Historical authorization survives later grant revocation; an
  action after revocation refuses. No test silently appoints an operator as owner.
- A speaker's confirmation affects only their own asserted reference. Cross-speaker
  identity changes require curator permission and an admissible basis covering all
  changed associations. Similarity, names, same values and model agreement refuse.
- Replay all three listed bases without a live registry/oracle. Missing enrollment,
  unbound identifiers, expired namespace attestations, unlisted bases, or unresolved
  identity contradiction refuse at append and on an injected replay transition.
- Execute ADR 0013's A/B/C merges: complete fresh outputs, all properties, preserved
  e-2 paths, evidence deduplication and explicit conflict. Differing candidate states
  survive without an aggregate; unchanged unrelated beliefs retain their lineage.
- Reject incomplete/duplicate/foreign mention partitions, missing candidate outputs,
  and spanning observations with no established successor support. A valid scoped
  split uses its recorded fresh candidate IDs and never copies verification by ID.
- Split an identity with dependent accepted links: transport only established
  endpoints, retire old links, disclose unresolved successors, and refuse an output
  requiring ambiguous support. Constitutive links never receive a numeric default.
- Losing the only sufficient justification changes verified to questioned; an
  unaffected independent justification holds verification. Existing question and
  quarantine restrictions survive every identity path. No removal promotes.
- Pool two eligible unverified candidates from independent source classes: merge
  holds them; a separate valid approval creates only the new verified candidate.
  Duplicate events/paths, one source class, restricted support, self-reference and
  an approver signature alone fail the gate.
- Preserve justified standing on merge/split/remerge with unchanged applicability,
  restrictions and gate history; fresh scoped candidates do not coalesce on remerge.
- Crash before append, after append, during publication and before acknowledgement:
  no partial committed delta or progress; retained retries and full replay converge.
- Full prefix/cutoff replay reproduces authority state, links, complete candidates,
  roots and lineage. Versions "0"/"1"/"2" retain golden bytes and refuse new events.

## Consequences

Stage three becomes implementable under one explicit trust policy, with no implicit
owner and no repeated authority decisions per handler. Its cost is enrolled signing
keys, recorded attestations, a larger acceptance inventory, and potentially broad
dependency recomputation on identity changes. No source-independent truth guarantee
is claimed for signatures. General multi-user permissions, candidate corrections,
mention correction, unrestricted restoration, scored matching, retention, and
redaction are not ratified by this draft. Implementation remains a separate task.
