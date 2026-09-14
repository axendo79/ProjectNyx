# ADR 0027 B3: compound-custody ruling brief

**Status:** Non-authoritative extraction and ruling brief. All numbered ruling
questions remain unanswered. No representation, schema, normalization algorithm,
proposed resolution, implementation or ratification is supplied here.

**Baseline:** `69bd97b1f624516ae2dd809dbb1fe1ba88767263`, 2026-09-14.
ADR 0027 and ADR 0028 are **Proposed / Implementation: None**. Statements of their
requirements below describe those proposed contracts, not shipped behavior.
The B2 rulings are maintainer decisions recorded in a non-authoritative design
brief; they do not themselves ratify either ADR. Frozen projectors remain unchanged.

**Authority scope:** ADR 0027 §§2/9 already supply the scoped authority model
that B1/B4 need within that Proposed contract. **B3 has no prerequisite ruling
and can be specified independently, provided custody never implies ownership or
permission.** The remainder of ADR 0020 stays open; contested contributor
entitlement is outside this task. This is not permission to implement an
unratified contract. Historical authorization uses the event's pre-event prefix;
live disclosure uses the confirmed current security prefix. Neither can be
substituted for the other.

**Citation discrepancy:** The requested §5.2 does not exist in the inspected
revision. The signed A -> B+C custody inventory is in **§5.1**, between the merge
rule and the multi-successor/general authorization rules. All citations below
use that actual section; no missing §5.2 contract is inferred.

Sources: [ADR 0027](../decisions/0027-stage-three-authority-and-acceptance.md),
[worksheet B3](0027-gate1-worksheet.md#b3-compound-sharedambiguous-custody-representation),
[B2 rulings](0027-b2-private-value-codec-ruling-brief.md#rulings), and
[ADR 0028](../decisions/0028-redaction-and-crypto-shredding.md).

## The recorded gap

ADR 0027, **Remaining unresolved questions**, explicitly calls this a
ratification blocker:

> - **Compound custody representation:** What closed recorded representation and
>   normalization rules preserve shared versus ambiguous provenance through multiple
>   splits and merges, including a shared set containing one ambiguously partitioned
>   predecessor? How do fixtures show that a merged subset neither loses remaining
>   ambiguity nor invents a claim-support association?

Its **Gate 1: Specification completeness** explicitly includes:

> - Key hierarchy and custody schemas.
> - Compound-custody representation.

Basic custody meaning is specified; the closed representation and normalization
for compositions are not. The worksheet reaches the same boundary. An independent
implementer would otherwise have to choose how to represent shared scope that
contains unresolved alternatives, compose later transitions, preserve explanatory
history, and recognize equivalent effective results. This brief makes none of
those choices.

## Scoped authority is already described

ADR 0027 **§2**:

> Stage three uses one shared acceptance policy per ledger, with an explicitly
> enrolled human policy administrator. This is a decision about the shared kernel
> view, not about ownership of statements or a multi-tenant permission system.

ADR 0027 **§9**, effect in the ADR 0020 relationship-table row:

> Narrow its blocker only for the explicit ledger-scoped stage-three capabilities, enrollment and historical authorization above. Preserve the separation between permission, attribution, intended reference and evidence; all other multi-user policy remains open.

ADR 0027 **§3**:

> Append verifies public fields, original signatures and historical grants against
> the locked pre-event prefix, decrypts with separate permission, verifies the
> protected commitment/AEAD, and checks all live semantics. Replay never substitutes
> current permissions for historical acceptance.

These passages close the prior-authority question for this extraction, within
the Proposed scope. They do not close B1's operation schemas or B4's service
schemas. B3 cannot infer an owner from a subject, mention, actor, key holder or
custody disposition, and need not decide general multi-user policy to describe
the proposed custody representation.

## Passage inventory: specified requirements and missing representation

The following inventory quotes the custody/binding passages across ADR 0027,
including repeated requirements in its release gates and acceptance cases.
Adjacent lifecycle and barrier passages are included where they constrain the
same records. Each item distinguishes an explicit requirement from an absent
representation; an operational requirement is not automatically a new B3 blocker.
Line locators refer to the baseline above. Public-key enrollment and identifier
binding in §4 establish authority/identity bases; they are not private-unit
custody and are not treated as additional custody representations here.

### P01. ADR 0027: Stage Three Authority and Acceptance

Source: [ADR 0027:11](../decisions/0027-stage-three-authority-and-acceptance.md).

> Implementation: None. This file proposes one shared acceptance contract for merge, split and corroboration, including permanent signatures, protected storage and custody prerequisites. Existing projectors retain every current refusal.

**Specified / missing:** The status explicitly includes custody prerequisites but supplies no implementation. It assumes the later custody contract can be closed; this sentence is not a schema.

### P02. 1. Version and deployment boundary

Source: [ADR 0027:53](../decisions/0027-stage-three-authority-and-acceptance.md).

> Database schema "5" adds version-isolated authority, association, justification,
> restriction and successor indexes, permanent signed public objects, protected
> bodies, immutable unit bindings and derived effective-binding indexes. Ordinary
> opens refuse incompatible databases;
> this draft authorizes neither in-place migration nor automatic recreation.
> Recreating an explicitly selected database by replaying an exported supported
> log preserves event IDs and hashes; initialization is an operator action.

**Specified / missing:** Immutable original bindings and reconstructible effective indexes are required. Their compound record shape is not supplied here; database recreation is not a normalization rule.

### P03. 1. Version and deployment boundary

Source: [ADR 0027:61](../decisions/0027-stage-three-authority-and-acceptance.md).

> Use protected `nyx-map/2` trees with ADR 0025's canonical routing, branch encodings
> and incremental publication discipline. Replace only the format discriminator
> and leaf representation: opaque recorded keys and complete nonsecret structural
> members plus immutable protected references `{unit_id, sealed_body_hash, selector}`.
> Selectors are arrays of opaque field IDs/integer positions, never private strings.
> The three collection names and `nyx-result/1` construction remain as in ADR 0025.
> An identity record receives a recorded opaque ID; private canonical JSON is never
> a tree key. Dependencies retain envelopes and sealed bodies, not decrypted copies.
> Changed protected content or any missing member, path, support assignment or
> custody transition changes its commitment. Full logical reads decrypt references
> only with separate authorization. No reducer performs encryption or key allocation.
> Version-3 lineage uses `nyx-belief-lineage/3` and `projector_version="3"`, otherwise
> ADR 0025's result-and-ancestry construction. Complete candidate contents include
> the justifications, restrictions and support applicability specified here.
> Relevant signed decisions and their authorization history enter event dependencies
> and identity records. Merely having an unrelated authority update in the log does
> not change every belief's lineage. Bounded updates remain incremental; an identity
> operation may legitimately touch every record on its affected subjects.

**Specified / missing:** Commitments must cover custody transitions and complete structural members, with recorded protected references. This fixes coverage, not the compound member representation or its equivalence rules.

### P04. 3. Permanent signed public envelope and protected body

Source: [ADR 0027:154](../decisions/0027-stage-three-authority-and-acceptance.md).

> | S | The closed structural inventory below, including immutable original unit bindings. No private text, clear claim value, identifier string or plaintext-derived fingerprint. |

**Specified / missing:** The S row requires original unit bindings in permanent public structure. It does not close all binding/disposition fields; public/private placement is already constrained.

### P05. 3. Permanent signed public envelope and protected body

Source: [ADR 0027:157](../decisions/0027-stage-three-authority-and-acceptance.md).

> S records the event-kind-specific fields already required by this decision:
> opaque input/output entity, mention, belief, candidate and link IDs; exact opaque
> property IDs; predecessor event IDs/hashes and pre-event belief lineage hashes
> with their projector versions; mention partitions; candidate output inventories;
> support selectors and their roles/applicability; basis kinds, signed public
> attestations and protected basis references; justification IDs/rules/required
> sets; restrictions and prior/result standing; and custody dispositions in section
> 5.1. Governance additionally records public enrollment keys, adopted prefix,
> complete grants, namespace uniqueness/validity rules and policy succession.
> Ordinary mentions/observations record the corresponding bootstrap/claim structure.
> Values/text/source configuration, human identity mappings, private namespace
> identifiers, observation details and free-text reasons are solely in protected
> content. References to this event's content are `{unit_id,selector}` in S to avoid
> a self-hash cycle; references to earlier bodies also carry their committed hash.
> Unknown public fields refuse; extra private data cannot be smuggled into a public
> extension object. An operation needing unrepresentable private structural metadata
> refuses rather than silently publishing it.

**Specified / missing:** The prose inventory requires custody dispositions in S and protected references for private details. Closed event/selector/basis schemas are B1 work; compound dispositions are B3. Unknown public fields already refuse.

### P06. 3. Permanent signed public envelope and protected body

Source: [ADR 0027:227](../decisions/0027-stage-three-authority-and-acceptance.md).

> DEKs are held by a separate privileged service, never in Layer A or ordinary
> database backups. Fresh protected writes require independently erasable units,
> registered derived-key dependencies, no recoverable wrappers in ordinary stores,
> and a key-provider recovery model capable of deleting all recoverable copies.
> Key availability is not historical truth. Operational read authorization and
> secret custody remain explicit inputs; reduction allocates no keys and uses no
> key-service clock or current permission policy to validate past grants.

**Specified / missing:** Secret custody is operational input, not truth or current authorization substituted into replay. The separate service and recovery-copy requirements constrain implementation; they do not define compound subject scope.

### P07. 3.2. Key lifecycle required before the first protected append

Source: [ADR 0027:325](../decisions/0027-stage-three-authority-and-acceptance.md).

> Generate each DEK independently with a cryptographically secure random generator;
> never derive it from content, a subject ID or a recoverable ledger-wide master.
> Generate a random nonce and encrypt at most once per DEK; retain the exact body
> on retry. A changed prefix uses a new DEK/key_id, never a second encryption with
> the old pair. key_version=1 identifies that immutable DEK, not a mutable wrapper.
> Do not rotate an original committed DEK/ciphertext in place: its old ciphertext,
> descriptor and signature are permanent. Suspected compromise is not repaired by
> rewrapping and requires an explicitly authorized future response, not hidden rekeying.

**Specified / missing:** Independent unit keys, one encryption per DEK and retained ciphertext are specified. No missing B3 algorithm is implied by this lifecycle paragraph; custody composition must not rewrite key material.

### P08. 3.2. Key lifecycle required before the first protected append

Source: [ADR 0027:334](../decisions/0027-stage-three-authority-and-acceptance.md).

> The key-service boundary stores a wrapped DEK under an independently erasable,
> unit-specific protection handle. No shared subject KEK or retained master/recovery
> seed may recreate that handle after destruction. Wrapper generations may rotate
> within the service, preserving the DEK and signed key_id/version; rotation records
> every old wrapper/handle generation and destroys or keeps it in the erasure inventory.
> The wrapping algorithm, parameters and integrity binding to ledger/unit/key/version
> must be recorded in the provider profile and independently validated. They are not
> hidden defaults and are not public-log copies of the wrapper. A concrete provider
> profile is still a deployment gate; this contract does not certify one.

**Specified / missing:** Wrapper generations and binding to ledger/unit/key/version need the recorded provider profile. Provider-profile and inventory schemas remain B4; semantic subject custody cannot substitute for cryptographic key binding.

### P09. 3.2. Key lifecycle required before the first protected append

Source: [ADR 0027:344](../decisions/0027-stage-three-authority-and-acceptance.md).

> Every service replica, offline backup, escrow share and recovery route is registered
> before accepting its first protected key. A backup of a wrapper is permissible
> only if destroying this unit's handle makes that copy irrecoverable too, or if
> that exact recoverable copy participates in destruction and acknowledgment.
> Rotation never removes an older recoverable generation from the inventory merely
> because it is no longer current. Private keys/handles/recovery shares never enter
> Layer A, ordinary SQLite backups, logs or the recovery witness below.

**Specified / missing:** Recovery copies must be registered before key acceptance and older recoverable generations remain accounted for. B4 must close the records; B3 must not mistake subject deduplication for deduplication of copies.

### P10. 3.2. Key lifecycle required before the first protected append

Source: [ADR 0027:352](../decisions/0027-stage-three-authority-and-acceptance.md).

> Provisioned but uncommitted keys are staged allocations. Binding to the final
> event hash is durable before append acknowledgment. A staging allocator may
> discard an allocation only after the serialized writer and witness establish
> that its event did not commit; timeout or absence from a restored snapshot alone
> is insufficient. An uncertain append preserves the allocation and blocks reuse.
> This cleanup is not authority to destroy a committed unit. Committed destruction
> requires ADR 0028's distinct authorization and execution capabilities; projector
> 3 supplies no such handler. Identity changes alter bindings, never key material.

**Specified / missing:** Staged allocation/commit binding and refusal under uncertainty are specified. Identity transitions alter bindings, never keys; the missing compound binding representation is not a new destruction authority.

### P11. 3.3. Rollback-resistant custody checkpoint and disclosure barrier

Source: [ADR 0027:363](../decisions/0027-stage-three-authority-and-acceptance.md).

> Fresh protected ledgers require a custody witness outside the rollback domain of
> ordinary database, filesystem/VM and key-backup restoration. It may be local secure
> infrastructure or a separate service; an ordinary second file restored with SQLite
> does not qualify. The operator explicitly pins its ledger ID and public signing
> key separately from the administrator pin. This is an additional operational trust
> input, not world evidence or authority to invent a Layer A event. It survives
> restore independently and refuses conflicting histories at a recorded log position.

**Specified / missing:** The independent witness and explicit operational trust pin are specified. Its custody role is disclosure/recovery safety, not world evidence or a source of invented events.

### P12. 3.3. Rollback-resistant custody checkpoint and disclosure barrier

Source: [ADR 0027:371](../decisions/0027-stage-three-authority-and-acceptance.md).

> The witness retains monotonic generation, accepted log-prefix position/hash,
> pending fenced submissions, immutable key inventory references, and later
> committed redaction manifests, denials and destruction receipts. Authority records
> are copies of authenticated Layer A decisions, not replacements for them. Prepared
> fences and provider receipts are operational evidence with their own origins;
> neither can stand in for a committed authorization. State never disappears when
> a request completes. The checkpoint is
> `{format:"nyx-custody-checkpoint/1",ledger_id,generation,log_position,event_hash,
> inventory_hash,denial_hash,pending_hash,challenge}` signed with Ed25519 over
> F(`nyx-custody-checkpoint-signature/1`, object). Hashes are 64 lowercase hex digits;
> genesis position is 0 with null event_hash. Each root hashes the C-canonical set
> of its full public records, framed respectively with `nyx-key-inventory/1`,
> `nyx-key-denials/1`, `nyx-pending-fences/1`. The challenge is a fresh verifier-chosen
> 32-byte random value encoded as lowercase hex. A stored old signed response cannot
> prove current state. Losing contact with the witness blocks protected disclosure.
> Exact inventory/fence member schemas and provider enrollment/rotation attestations
> remain the explicit conformance blockers below, not arbitrary extension objects.

**Specified / missing:** The checkpoint outer object, canonical root calculation and challenge are specified. Inventory/fence member schemas and provider enrollment are explicitly open B4 conformance work. A hash alone does not establish inventory completeness.

### P13. 3.3. Rollback-resistant custody checkpoint and disclosure barrier

Source: [ADR 0027:389](../decisions/0027-stage-three-authority-and-acceptance.md).

> All managed decryption/disclosure, including cached plaintext and exports, holds
> a shared generation permit through its final output handoff. Identity/grant/erasure
> changes take an exclusive barrier, drain or terminate old readers and private
> derivative writers, then prepare a witness fence for the exact proposed event hash
> before committing Layer A. The fence blocks affected disclosure, not authorizes
> destruction. Record the committed prefix in the witness before acknowledging the
> append or releasing new permits. No atomic SQLite/provider transaction is claimed.
> After a crash between prepare/commit/confirmation, resolve the exact transaction
> against the authoritative log and witness; absent proof of commit or abort, keep
> the fence and report recovery unavailable. Never infer abort from an older restore.

**Specified / missing:** The exclusive transition barrier, shared permits and commit/witness ordering are specified. B3 must expose the complete changed scope that this protocol acts on; it must not invent a different barrier or atomic cross-service transaction.

### P14. 3.3. Rollback-resistant custody checkpoint and disclosure barrier

Source: [ADR 0027:400](../decisions/0027-stage-three-authority-and-acceptance.md).

> There is no cached/offline grace period for a disconnected reader and no return
> of stale private data. Public structural reads retain ADR 0014's freshness labels.
> Subject bindings/permissions used for disclosure must be published through the
> confirmed security prefix; an ordinary stale label cannot bypass that barrier.
> The same contract applies to new-unit activation. Content handed to a client
> before the barrier is outside revocation; managed buffers/leases remain in closure.

**Specified / missing:** Disclosure must use bindings published through the confirmed security prefix. This assumes a reproducible complete effective result, not an earlier as_of or stale permission shortcut.

### P15. 3.3. Rollback-resistant custody checkpoint and disclosure barrier

Source: [ADR 0027:407](../decisions/0027-stage-three-authority-and-acceptance.md).

> Before any restored store activates a key or reader, compare its prefix with a
> fresh witness response. Fetch and verify missing authoritative history and safety
> records, reject forks, and apply current denials before unwrapping any key. If
> history/proofs are unavailable, remain recovery-blocked; do not start a new empty
> witness or ledger identity over the old keys. Projector 3, even before erasure
> handlers exist, must refuse history/units the witness marks erased or unsupported.
> The witness's availability/rollback resistance is an explicit irreconstructible
> security exception alongside secret custody; logical truth still comes from Layer A.

**Specified / missing:** Recovery must verify current witness/history before disclosure and refuse unknown safety state. The operational exception does not define compound semantics or make current key availability historical truth.

### P16. 4. Closed list of admissible existing-subject association bases

Source: [ADR 0027:444](../decisions/0027-stage-three-authority-and-acceptance.md).

> A new mention still bootstraps a fresh scoped subject. Association afterward is
> an explicit accepted link or merge. `entity_link_accepted` records fresh link ID,
> source mention/scoped subject, uniquely resolved current target, admissible basis,
> and authorization. Historical assertions retain their recorded subject IDs.
> There is no implicit absorption of a pre-existing subject's whole membership.
> An ordinary accepted association link does not rewrite private-unit custody.
> It supplies a recorded identity relationship only. Custody changes require an
> explicit merge/split transition under section 5.1, never resolver lookup or an
> inferred current-canonical-subject cache.

**Specified / missing:** Accepted association leaves custody unchanged; only recorded merge/split transitions alter it. This is already closed behavior. Resolver lookup cannot manufacture a custody transition.

### P17. 5.1. Historical and effective custody are separate from claim support

Source: [ADR 0027:483](../decisions/0027-stage-three-authority-and-acceptance.md).

> Each private unit's creation manifest permanently records `original_binding`:
> either `{kind:"subjects",subject_ids:[...]}` with a nonempty canonical set of
> explicit subjects, or `{kind:"ledger",ledger_id:L}` for private governance material
> with no subject referent. The latter requires explicit ledger-wide permission;
> an empty subject list never means unrestricted. Bootstrap binds the scoped subject
> from ADR 0019. A transition's own new private unit explicitly names its successor
> subjects and any other subjects it concerns; validate that inventory at creation.
> Neither a mention ID nor an actor string is an owner. Original bindings never
> change, including after retirement, later association or erasure.

**Specified / missing:** The original binding variants, nonempty subject set, ledger-bound case and immutability are specified. The new operation's own unit must name all concerned subjects. Compound effective custody still lacks its closed representation.

### P18. 5.1. Historical and effective custody are separate from claim support

Source: [ADR 0027:493](../decisions/0027-stage-three-authority-and-acceptance.md).

> `effective_binding(unit_id, locked_prefix)` folds only accepted merge/split custody
> dispositions from that original binding. Its output records current subject IDs,
> disposition (`assigned`, `shared`, or `ambiguous`), and explaining transition IDs.
> The current index is reconstructible/cacheable, never the sole authority. Initial
> single-subject units are assigned; explicitly multi-subject units are shared.
> Ledger-bound units remain ledger-bound. Canonical subject in this draft and ADR
> 0028 means this prefix-specific recorded identity, not world uniqueness or title
> to someone else's assertions. Historical queries disclose original and effective
> bindings separately; live decrypt authorization uses the actual current prefix,
> not a user-selected earlier `as_of` that could bypass a later split.

**Specified / missing:** The effective result must expose current subjects, disposition and explaining transitions; initial assigned/shared and ledger cases are specified. A single disposition label does not define the mixed compound case named by the blocker.

### P19. 5.1. Historical and effective custody are separate from claim support

Source: [ADR 0027:504](../decisions/0027-stage-three-authority-and-acceptance.md).

> For a merge A+B -> M, replace occurrences of A or B in each affected effective
> subject set with M and deduplicate. Preserve other subjects and the original
> bindings. If all alternatives collapse to one subject, the binding becomes
> assigned; remaining shared/ambiguous alternatives retain their disposition.
> Resolve retired identifiers by following only these identity-successor edges to
> active leaves, deduplicated; return unique/multiple/none with paths. Association
> links are not successor edges. No key, ciphertext or old event is rewritten.

**Specified / missing:** Simple merge replacement, deduplication, complete-collapse behavior and successor-edge traversal are specified. Partial collapse of mixed shared/ambiguous components still requires the blocker’s composition and normalization rules.

### P20. 5.1. Historical and effective custody are separate from claim support

Source: [ADR 0027:512](../decisions/0027-stage-three-authority-and-acceptance.md).

> For A -> B+C, the signed custody inventory accounts for every retained unit whose
> effective binding contains A, including historical, provenance-only and already
> erased units. Each has exactly one explicit disposition for A:

**Specified / missing:** The complete retained-unit predicate and one explicit disposition for A are specified. Closed inventory entries and proof of completeness are not supplied by this prose; no historical, provenance-only or erased unit may be omitted.

### P21. 5.1. Historical and effective custody are separate from claim support

Source: [ADR 0027:516](../decisions/0027-stage-three-authority-and-acceptance.md).

> | Disposition | Required basis | Effective binding contribution |
> |---|---|---|
> | assigned to B (or C) | Recorded applicability establishing the unit's private scope, identified by unit/selector and basis references | B only (or C only) |
> | shared across B,C | Recorded applicability establishing both scopes | `{B,C}`, marked shared |
> | ambiguous across B,C | Scope cannot be distinguished; uncertainty is recorded explicitly | `{B,C}`, marked ambiguous |

**Specified / missing:** The three basic dispositions and their different applicability requirements are specified. Identical B/C subject membership can carry different shared/ambiguous meaning; this table does not encode nested combinations.

### P22. 5.1. Historical and effective custody are separate from claim support

Source: [ADR 0027:522](../decisions/0027-stage-three-authority-and-acceptance.md).

> With more successors, a nonempty explicitly recorded subset replaces A, with the
> same assigned/shared/ambiguous distinction. Retain all other pre-event bindings.
> Missing units, empty assignments, unrecorded fan-out and arbitrary one-child
> assignment refuse. Unknown private applicability produces an explicit conservative
> ambiguous disposition; it supplies no usable evidence to either child. This is
> custody of one indivisible unit, not copying it or its DEK into several claims.
> The separate claim-support requirements of section 5 still refuse a split if a
> live output claim's applicability cannot be established. After erasure, only
> retained structural assignments may establish a narrower custody scope; otherwise
> record ambiguity. Unknown secret content is never reconstructed to decide scope.

**Specified / missing:** Multi-successor subsets, retained other bindings, conservative ambiguity and stated refusals are fixed. The combination with existing shared/ambiguous scope needs B3 representation. Usable claim support remains separately required.

### P23. 5.1. Historical and effective custody are separate from claim support

Source: [ADR 0027:533](../decisions/0027-stage-three-authority-and-acceptance.md).

> Identity authorization covers all participating pre-event subjects and all other
> subjects affected by changed unit bindings; shared custody does not make those
> other subjects participants in the identity merge itself. The complete signed
> inventory, not a private-unit scan after publication, authorizes the transition.
> Publication atomically changes identity and effective-binding indexes. Readers
> and key-service permits are invalidated against the new prefix before disclosing
> any newly scoped content; stale grants cannot bypass the transition.

**Specified / missing:** All affected subject scope, signed pre-publication authorization and atomic identity/effective-index publication are fixed. The compound representation must make that complete scope verifiable; a later private scan cannot supply missing authorization.

### P24. 5.1. Historical and effective custody are separate from claim support

Source: [ADR 0027:541](../decisions/0027-stage-three-authority-and-acceptance.md).

> Decryption of shared/ambiguous units requires an explicit `protected_decrypt`
> grant covering every effective subject, the unit selection and purpose. Authority
> over B alone cannot reveal a B/C unit. No identity capability implies that grant,
> and successor grants are not inherited automatically. A request may fail for lack
> of decryption even when a curator has permission to propose an identity change.
> Redaction similarly requires authority over the full affected set, but execution
> does not require decryption; the destructive workflow belongs to ADR 0028.

**Specified / missing:** Whole-effective-scope decrypt permission is mandatory, separate from identity capability and from redaction execution. Representation choices must expose that scope without inventing entitlement or inherited successor grants.

### P25. 6. Dependent links and standing across a partition

Source: [ADR 0027:599](../decisions/0027-stage-three-authority-and-acceptance.md).

> Under an accepted erasure-capable projector, a redacted predecessor moved into a
> new claim scope remains redacted with a new structural candidate ID and explicit
> predecessor/unavailable-content reference; it receives no new encrypted copy or
> key. Retain opaque historical candidates even when no narrower claim assignment
> can be established; refuse a split requiring an invented output scope. Necessary
> live justification lost through erasure uses the dependency-loss column above;
> independent sufficient surviving justification holds. Custody ambiguity does not
> itself count as support. Erasing a private identity basis preserves the historical
> decision/topology but makes content-dependent use unavailable. New identity
> acceptance needing that basis refuses without independently sufficient live or
> structurally sufficient evidence. Replaying the historical decision under ADR
> 0028 is a different operation, not a fresh acceptance of its destroyed basis.

**Specified / missing:** Conditional redacted transport preserves structural history and refuses invented claim applicability. Missing compound custody cannot be filled by treating ambiguity or a retained identity link as usable content support.

### P26. 8.2. Release gate and alternatives

Source: [ADR 0027:696](../decisions/0027-stage-three-authority-and-acceptance.md).

> Projector 3/schema 5 may ship before a redaction-capability release only if the
> permanent signature, protected first write, reconstructible historical/effective
> custody, the independent witness/disclosure/restore barrier, and complete
> recoverable-copy protections above pass acceptance together.
> There is no plaintext stage-three intermediate format. Encryption, key-service
> integration and explicit validator decryption grants are part of this stage's
> cost, even though deletion, sentinel reads and erasure-overlay recovery wait for
> ADR 0028. Restore fencing and refusal of unsupported erased history cannot wait.
> The provider must already support independently erasable key custody; no early
> backup design may make future per-unit erasure impossible.

**Specified / missing:** Historical/effective custody and recovery protections are launch prerequisites even before erasure handlers. This repeats the B3 dependency rather than resolving its representation or selecting a provider.

### P27. 8.2. Release gate and alternatives

Source: [ADR 0027:707](../decisions/0027-stage-three-authority-and-acceptance.md).

> Separate releases make stage-three acceptance available earlier but require two
> versioned reader/publication contracts, schema 4 -> 5 and later 5 -> 6 explicit
> cutovers, and continued refusal by projector 3 on erased history. The second
> release can reuse sealed bodies, original signatures, bindings and `nyx-map/2`;
> it adds effective erasure views rather than repairing a plaintext intermediate.

**Specified / missing:** The separate-release path reuses original signatures and bindings. It presumes interoperable protected custody records already exist; it does not decide their form or ratify release scheduling.

### P28. 9. Exact supersessions and limits

Source: [ADR 0027:737](../decisions/0027-stage-three-authority-and-acceptance.md).

> | Architecture Invariant 8 | Add explicit operational-security exceptions for independently held secret keys and the rollback-resistant custody witness in sections 3.2/3.3. They gate availability and recovery; they do not supply alternative event or belief truth. |

**Specified / missing:** The relationship table makes the witness/secret-key availability exception explicit. Neither can supply another event/belief truth source; this row does not supersede custody's separation from permission/evidence.

### P29. Remaining unresolved questions

Source: [ADR 0027:754](../decisions/0027-stage-three-authority-and-acceptance.md).

> - **Closed operation schemas:** What are the complete required/optional fields,
>   types, selectors, set constraints and validation rules for each event's S and A,
>   each admissible-basis attestation T, genesis/rotation records and protected
>   content schema, including rejection of unknown fields? The generic envelope is
>   defined, but prose inventories do not yet define interoperable event objects.
> - **Private value codec:** What exact cross-language value/number domain and
>   decoding rules does `nyx-private-json/1` admit, and which fixtures establish
>   compatibility with existing values without changing frozen canonical bytes?
>   Signing a fixed opaque byte string is settled; producing and semantically
>   interpreting that string from independent value models is not.
> - **Compound custody representation:** What closed recorded representation and
>   normalization rules preserve shared versus ambiguous provenance through multiple
>   splits and merges, including a shared set containing one ambiguously partitioned
>   predecessor? How do fixtures show that a merged subset neither loses remaining
>   ambiguity nor invents a claim-support association?
> - **Custody service wire schemas:** What exact canonical inventory, denial and
>   pending-fence member records produce section 3.3's checkpoint roots; what
>   enrollment/rotation and provider-profile records bind their signers, copy IDs,
>   generations and permitted wrapping algorithms? Which signed records establish
>   inventory completeness rather than merely hashing an unspecified list?
> - **Interoperability evidence:** Which published known-answer vectors and negative
>   cases cover canonical Unicode/set ordering, strict Ed25519 verification,
>   attestation nesting, AEAD context, fixed-key/nonce sealed bodies, retries,
>   prefix changes and checkpoint reconciliation, so two implementations agree on
>   both accepted inputs and bytes?

**Specified / missing:** These are explicit distinct blockers: B1 objects, B2 private values, B3 compound representation, B4 service records and B5 evidence. B3 must preserve mixed ambiguity through partial merges; no canonical compound form is specified.

### P30. Ratification-readiness assessment

Source: [ADR 0027:794](../decisions/0027-stage-three-authority-and-acceptance.md).

> At the audit baseline `b7609d4`, and with this revision's proposed protocol
> clarifications, **not ready to ratify independently yet**: the specification
> blockers above belong to Gate 1 below; closing them alone does not satisfy Gate 2
> or authorize implementation. Acceptance of ADR 0028's erasure handlers is not
> itself a prerequisite. After Gates 1 and 2 and explicit ratification, Stage Three
> can be implemented against the reviewed contract. Production use with genuinely
> private data additionally requires Gate 3 and section 8.2's independent-release
> conditions. Its first durable representation, key custody and restore barrier
> must already accommodate later destruction; omitting these prerequisites would
> create legacy debt.

**Specified / missing:** Custody/restore compatibility is required in the first durable representation. Gate 1 completion alone is not independent review, ratification or implementation permission.

### P31. Gate 1: Specification completeness

Source: [ADR 0027:809](../decisions/0027-stage-three-authority-and-acceptance.md).

> - Closed operation, authorization and attestation schemas.
> - Exact canonical bytes and serialization rules, including the private value codec.
> - Encryption envelope and AAD construction.
> - Key hierarchy and custody schemas.
> - Compound-custody representation.
> - Crash, replay, rollback, restoration and erasure state machines, including the
>   shared boundary with proposed ADR 0028; reviewing that boundary does not ratify
>   or implement its erasure handlers.
> - Positive and negative interoperability vectors.
> - A pinned commit representing the review candidate.

**Specified / missing:** Gate 1 explicitly demands custody schemas and compound representation together with exact bytes and vectors. This is an evidence list, not the missing schema or an assertion that Gate 1 has passed.

### P32. Acceptance cases

Source: [ADR 0027:932](../decisions/0027-stage-three-authority-and-acceptance.md).

> - Erase a protected operation detail in an erasure-capable test harness: the
>   original public signature still verifies without any capsule substitution;
>   content-dependent semantic verification is explicitly unavailable. Changing a
>   public scope, predecessor, protected descriptor or original binding invalidates
>   the signature. Ordinary unsigned events never acquire a claimed approval.
> - Canary secrets never reach authoritative JSONL/SQLite, private index keys,
>   immutable historical leaves, retry spools, logs or backups in plaintext. Losing
>   a projection key cannot leave a recoverable plaintext source behind.
> - A -> B+C assigns individual units to B, C, shared or ambiguous exactly as
>   recorded. No implicit fan-out, key copying or support duplication occurs.
>   An ordinary accepted association leaves custody unchanged. Scope-B decryption
>   refuses shared B/C units; an explicit whole-scope grant is required.
> - Redacted candidate -> split -> merge retains unavailable secret content and
>   structural ancestry; no key or decryptable copy is created. Live dependent
>   standing holds or demotes under section 6, never promotes through custody.

**Specified / missing:** The acceptance cases require signed binding integrity, exact split dispositions, full-scope reads and no resurrection/promotion. They constrain future fixtures but supply no expected compound wire bytes.


## Shared and ambiguous custody: what remains unspecified

**Recorded requirements, §5.1:** original unit binding is immutable; effective
binding is prefix-specific and folded from recorded accepted merge/split
dispositions. Initial single-subject units are assigned; explicitly multi-subject
units are shared; ledger-bound units remain ledger-bound. An ordinary association
does not change custody. Identity transitions alter neither the original unit nor
its key/ciphertext. Historical and effective bindings remain separately visible.

The split table distinguishes shared and ambiguous dispositions even when both
name `{B,C}`. Shared scope has recorded applicability establishing both scopes;
ambiguous scope records that scope cannot be distinguished. Thus the same active
subject set alone does **not** identify the same custody meaning. Neither meaning
is a claim-support assignment or permission to read.

**Concrete composition boundary, derived from the explicit blocker:** a unit
already shared across A and another subject can retain that other subject while
A splits ambiguously into B/C. §5.1 requires retaining the other pre-event binding
and the ambiguity. The blocker explicitly asks how to represent that combination.
A later merge of only some resulting subjects must not erase unresolved
alternatives elsewhere or reinterpret uncertainty as established shared scope.
This is an illustration of the stated gap, not a proposed record shape or a
chosen result for an otherwise unspecified compound transition.

An implementer lacks the closed compound states, legal combinations, composition
rules and explanatory-transition representation needed to execute those cases
without inventing semantics. The existing single-transition table is not silent
about ordinary ambiguity; that behavior must not be reopened as an optional policy.
After erasure, retained structure alone may establish a narrower scope; otherwise
ambiguity remains explicit. Unknown content cannot be reconstructed to assign it.

## Normalization and the B2 boundary

ADR 0027 **§5.1**, merge rule, explicitly replaces A/B occurrences with M,
deduplicates subject IDs, preserves original bindings and other subjects, and
retains remaining shared/ambiguous disposition. Different preceding subject
sets can therefore converge to the same active subject set. This does not prove
that two complete recorded custody states are interchangeable: original bindings,
disposition and explaining transition history also matter.

**Unspecified:** the equivalence relation over complete compound representations,
which distinct records may denote one effective binding, whether that equivalence
requires one semantic normal form, and how such a form retains shared/ambiguous
provenance. The blocker expressly requires normalization rules but supplies no
closed semantic normalization. It would be inaccurate either to declare that
arbitrary alternative forms are permitted or to choose a unique compound form.

**Already specified, distinct issue:** canonical serialization of public objects.
ADR 0027 **§3.1** states:

> - Objects have unique string keys, sorted lexicographically by Unicode scalar
>   values, not locale or UTF-16 code units. No normalization, BOM, whitespace or
>   trailing newline. Reject invalid UTF-8, lone surrogates and duplicate keys.

> - Arrays retain sequence order unless their field is explicitly a set. Sets sort
>   by C(member) bytes, with canonical duplicate members removed as in ADR 0014;
>   role/ID uniqueness checks still reject invalid duplicate signers or assignments.
>   Absent and null are distinct; only fields explicitly defined nullable admit null.
>   Persisted/signed objects must already be canonical; do not silently repair them.

Canonical bytes for a chosen object do not decide whether another object denotes
the same compound custody meaning. Nor does semantic deduplication authorize
rewriting retained signed history.

Any eventual canonical form must remain within its applicable codec's value
domain. The profile boundary matters: §3 places original bindings and custody
dispositions in public S; §3.3's checkpoint roots likewise use the public profile.
That profile already has integer-only public numbers. B2 governs private P,
including protected applicability details; it does not admit floats into public
custody records or move those records into P. No new placement is proposed here.

The six [B2 rulings](0027-b2-private-value-codec-ruling-brief.md#rulings) constrain
any private data involved in the representation as follows:

| B2 ruling | Constraint and public/private boundary |
|---|---|
| 1: Nonfinite exclusion | New private encoding uses `allow_nan=False` and private decoding rejects bare NaN/Infinity/-Infinity. Public custody numbers already exclude all floats under §3.1. |
| 2: Exact integers | Admitted integers must remain exact; no conversion through binary64. This does not choose field ranges or resource limits. |
| 3: Binary64 preservation | Finite private floats preserve the recorded binary64 value, not arbitrary exact decimals. No silent approximation of a large integer/exact decimal. This supplies no public float permission and does not choose a numeric custody model. |
| 4: Duplicate decoded keys | Private keys collide after escape decoding by exact codepoint/UTF-8 equality, including `"x"` and `"\u0078"`; composed/decomposed forms remain distinct. Public objects already reject duplicate keys. |
| 5: Unicode | Reject lone surrogates; no Unicode normalization. A custody normal form cannot silently normalize opaque identifiers or private recorded strings. Public §3.1 independently imposes this boundary. |
| 6: Canonical private input | Validate canonical input without replacing retained authenticated P. Human-facing conversion is upstream. This does not choose a compound semantic normal form or authorize repair of signed public records, which §3.1 also forbids. |

B2's open float specification, resource bounds and explicit JCS alternative
remain B2 questions, not new B3 rulings. Its questions 1/4/6 cover value-domain,
grammar and API/limit boundaries; questions 7/9/10/11 cover conformance and
compatibility evidence. B3 can specify custody meaning independently; freezing
actual canonical objects and cross-language vectors must respect whichever
already-specified public or eventually completed private profile applies.

## The signed A -> B+C inventory (§5.1, not §5.2)

The inventory must account for **every retained unit whose effective binding
contains A**, including historical, provenance-only and already-erased units.
Each unit has exactly one explicit disposition for A. Recorded unit/selector and
basis references establish assigned or shared applicability; uncertainty produces
an explicit ambiguous disposition. More successors require a recorded nonempty
subset. Other pre-event bindings remain. Missing units, empty assignments,
unrecorded fan-out and arbitrary one-child assignment refuse.

The transition's own new private unit has its separately validated original
binding to successor subjects and any other subjects it concerns. Authorization
covers participating pre-event subjects **and** other subjects affected by changed
bindings, without making every co-bound subject an identity-merge participant.
The complete signed inventory authorizes the transition before publication;
identity and effective indexes publish atomically, and disclosure permits must
observe the new prefix. A post-publication private-unit scan is not a substitute.

What remains absent is the closed entry/container representation for compound
dispositions, the exact recorded applicability/provenance forms, validation of
their composition and normalization, and interoperable evidence of coverage.
The basic selection predicate and full-scope requirement are already stated.
Do not confuse this **identity-transition unit inventory** with §3.3's
**key-service copy inventory/checkpoint records**: the latter has its own B4
schemas/completeness blocker. Both touch unit identity and historical scope;
neither inventory can stand in for the other.

## Accepted contracts constraining the answer

All five ADRs below have **Status: Accepted**. Implementation status is narrower
than semantic acceptance; none supplies B3's missing compound representation.

**[ADR 0022 §§1–2](../decisions/0022-belief-container-uniqueness.md#decision)**:

> (subject, property) uniquely identifies a current belief. An event naming a fresh
> belief ID for a pair that already has a current belief refuses before append,
> without mutation.

> Uniqueness is over current beliefs only.

Custody normalization cannot create another current belief for the pair, silently
redirect a recorded candidate, merge candidates, rewrite historical associations
or revive a retired belief ID. This is container uniqueness, not a definition of
custody-state equality.

**[ADR 0015 §4](../decisions/0015-candidate-scoped-verification.md#4-gate-approved-corroboration-has-an-explicit-target)**:

> Gate-approved corroboration establishes a new candidate for the jointly supported
> claim, leaving the contributing candidates intact.

Its **§3** also states:

> Candidates are deduplicated by candidate identity, never by value. The same
> candidate reaching a belief by two identity paths is one candidate with two paths.

Custody transport cannot consume contributors, coalesce claims, grant verification
or count multiple paths as evidence. §§2/5/6/7 additionally constrain no pooling
promotion, dependency-specific restrictions, evidence-event deduplication and
round-trip standing. Fresh successor claim scopes and support assignments remain
distinct from custody of one indivisible private unit.

**[ADR 0018, Decision](../decisions/0018-correction-supersedes-candidates.md#decision)**:

> A correction explicitly identifies the candidate IDs it supersedes. Source
> lineage does not establish scope. The correction records a fresh candidate and
> its targets. Each target is validated against the pre-event snapshot and recorded
> in the payload so replay reproduces the same scope.

> Superseded candidates are retained with their evidence and verification history.

Custody transitions cannot stand in for named supersession or transfer standing.
ADR 0027 §9 expressly leaves correction semantics unsuperseded and version-3
corrections refused pending their separate contract. This extraction supplies no
candidate-target eligibility or correction authority.

**[ADR 0026, Decision](../decisions/0026-usage-is-not-evidence.md#decision)**:

> Dream references, retrieval exposures, and activation records never become
> evidence dependencies of a belief and never enter its lineage. Usage is recorded
> separately from world truth. Repeated use creates neither corroboration nor new
> ClaimCandidates and does not change verification or belief lineage.

Custody or erasure dependency tracking for a usage artifact is not an evidence
edge. Necessary identity-transition dependencies may enter the proposed lineage
contract; usage references do not gain that role merely by sharing custody data.

**[ADR 0020, Decision](../decisions/0020-multi-user-authority-undecided.md#decision)**:

> Existing source attribution implies no ownership, authorization, independent
> corroboration, or user-specific verification. actor_id records provenance and
> supplies no authorization policy.

> Authority over intended reference is not authority over shared identity.

> Permission to make a change and evidence that a relationship holds are separate
> requirements.

> Replay must not consult current permissions to decide whether an
> earlier identity event was valid, consistent with ADR 0014 section 1's pre-event
> snapshot contract.

ADR 0027 §§2/9 supply the scoped proposed capabilities, enrollment and historical
authorization while preserving those separations. The still-open general
contributor/ownership policy is not a prior gate for B3 representation work.

## What ADR 0028 inherits and adds

**Inheritance — §3**, referring explicitly to ADR 0027 §5.1:

> Historical/effective bindings, canonical-subject meaning, association treatment,
> merge/split custody dispositions and live-prefix decrypt scope are owned by

> No separate subject-binding or decrypt-entitlement contract is defined here.

**Remaining unresolved questions, Inherited format completeness**:

> - **Inherited format completeness:** What final closed S/A/T schemas, private
>   value codec, compound-custody representation and checkpoint inventory schemas
>   resolve ADR 0027's listed blockers, with interoperability fixtures? This draft
>   cannot freeze a different interpretation of that common protocol.

Thus 0028 inherits B3 rather than supplying a competing representation. The
following are additional uses and obligations, not resolutions of B3.

**Selection and frozen scope — §3.1**:

> For selected active subject set Q, enumerate all retained event units whose
> effective subject set intersects Q, including historical/erased units. Original
> bindings establish the audit path, not a second undocumented selection predicate.

> The reviewed request records exact original unit IDs, committed body hashes,
> original/effective binding proofs, full affected subject set and the locked prefix.
> Authorization covers every affected subject; narrowing a unit's fields requires
> explicit agreement to the whole indivisible unit. After commit this manifest is
> immutable: later identity transitions cannot expand, shrink or retarget the
> destruction.

The compound result must support current scope and explaining paths, whole-unit
authorization and a frozen destructive target. A B-only grant cannot authorize
erasing a B/C shared or ambiguous unit. Retired selectors use successor edges,
not association links or an implicit all-descendants expansion. Exact proof and
manifest schemas remain additional 0028 blockers.

**Shared derivatives and completion — §4.1**:

> Authorization freezes the original units and the complete registered derivative
> closure at the actual locked prefix. Include the effective subject sets of shared
> derivatives, even if those subjects are not original-unit targets. A grant missing
> any affected subject refuses the whole request before destruction; invalidating a
> shared cache is not permission to destroy unrelated original evidence.

**§4.2**, completion table:

> All frozen copies/generations have verified receipts, every managed persistence location has an acknowledgment, effective masks/progress are published, the witness durably records denials/receipts, and signed `redaction_completed` is committed and witness-confirmed

Custody scope must feed complete root-unit and derivative accounting; a correct
subject list alone proves neither copy-inventory completeness nor destruction.
§9 extends closure to historical generations, managed caches/exports, key recovery
routes and host persistence. Its shared-derived-object rule preserves unrelated
original evidence. The separate backup/replica acknowledgment question remains
unresolved; this brief does not equate handle destruction with acknowledgment.

**Retained provenance — §6**:

> A historical support edge remains as provenance, with its
> availability/restriction recorded; it is not counted as usable content support
> after redaction.

> `redacted` is terminal for that candidate; later recollection must be a new event
> and new candidate, not resurrection of the old erased unit.

Its operation table explicitly says:

> Refuse any required new claim assignment; preserve the historical opaque candidate. Custody may be explicitly ambiguous, which is not evidence

An erased unit still participates in custody history and split accounting, but
neither a retained hash nor a custody transition recreates usable secret support.
Structural scope may justify a redacted successor reference; an invented claim
assignment may not. Erasure does not silently undo identity topology.

**Unavailable recall — §5**:

> Named erased candidates remain addressable and return a
> typed unavailable value.

> The sentinel reports authorized logical unavailability, not completed destruction.

Readers need verified target membership and the current barrier generation, not
a decryption failure interpreted as redaction. Current authorized erasures apply
even at earlier historical cutoffs under §6. Key outage is not redaction. §§7/8
retain original commitments, signatures and safe structural history while marking
content-dependent verification unavailable; a successful custody proof cannot
certify destroyed plaintext or supply an original signature via a later capsule.

**An added schema question — Remaining unresolved questions, Manifest and event
schemas**:

> how do current executor grants name the frozen request scope after its subject
>   identifiers retire without retargeting the original destruction authorization?

That unresolved representation must connect historical binding proofs to current
execution capability without altering the already-frozen target. It is additional
0028 work, not a license to re-evaluate the original request under current grants.

## Evidence and review boundary

No implementation probe can establish the missing compound semantics before a
ruling defines them. The examples here identify required coverage; no expected
compound wire output or new test fixture has been invented. Gate 1 still needs
closed definitions, positive/negative interoperability vectors and a pinned
candidate. Gate 2 supplies independent protocol review; Gate 3 separately covers
implementation and concrete provider/host behavior. Running repository tests does
not satisfy those gates.

The maintainer owns representation and application-semantic rulings. Independent
cryptographic review covers signed/AAD/commitment boundaries and parser/vector
conformance. Storage/recovery expertise covers historical/current scope,
publication/disclosure barriers, inventory completeness and erasure interactions.
ADR 0027's **Review record required before ratification** leaves open whether the
independent cryptographer also has that expertise or needs a separately scoped
reviewer. No staffing default or self-review is supplied here.

## Ruling questions — all unanswered

1. **Closed compound representation — Needs maintainer ruling.** What complete
   recorded states and validity constraints preserve established shared scope
   alongside unresolved alternatives inside it, including repeated splits?
   What must remain distinguishable beyond the active subject set and one
   disposition label? This asks for the explicit B3 closure, not ownership policy.
2. **Composition and retained explanations — Needs maintainer ruling.** What
   complete transition rules cover further splits and partial merges of compound
   states while preserving other subjects, unresolved alternatives, immutable
   original bindings and explaining transition IDs? Which combinations refuse
   beyond the refusals already specified in §5.1?
3. **Equivalence and normalization — Needs maintainer ruling.** Which different
   recorded compound states, if any, denote the same effective binding, what
   normalization is required, and which history/disposition distinctions must
   remain visible? How is that semantic equivalence separated from merely equal
   subject sets and canonical serialization of one object? **B2 overlap:** value
   domain/grammar/limits are B2 questions 1/4/6; its six MADE rulings are constraints,
   not unanswered choices here. No duplicate float/JCS ruling is requested.
4. **Transition inventory closure — Needs both.** What closed signed entry and
   container representation binds every selected retained unit, applicability
   reference, compound disposition and full affected scope to the locked prefix?
   What independently checkable evidence demonstrates complete coverage rather
   than a correctly signed subset? Maintainer: recorded semantics and schemas;
   reviewers: cryptographic binding and storage/replay completeness. This overlaps
   B1/B4 schemas and must preserve the distinction between transition units and
   service copies. §5.1's selection predicate itself is already specified.
5. **Erasure-boundary representation — Needs both.** What complete binding proofs
   and compound-state references support frozen root-unit/derivative scope through
   later retirement, executor changes and overlapping erasures, without retargeting
   destruction or reconstructing unavailable content? Maintainer: B3/0028 schema
   decisions; cryptographic and storage/recovery reviewers: binding, replay and
   closure evidence. The current-executor/frozen-scope subquestion belongs to
   0028's stated blocker; existing logical redaction and completion rules remain.
6. **Conformance coverage — Needs both.** Which frozen positive/negative cases
   establish preserved mixed shared/ambiguous provenance, partial-merge behavior,
   inventory completeness, full-scope authorization and separation from support,
   including erased/provenance-only units? Maintainer: required corpus/outcomes
   after questions 1–5; reviewers: independent assessment. **B2 overlap:** reuse
   its questions 7/9/10/11 for codec independence/runtime/corpus requirements rather
   than selecting a second codec evidence policy here. This also intersects B5.
7. **Independent review findings — Needs outside reviewer.** Against the eventual
   pinned specification and evidence, are compound binding commitments, retained
   provenance, authorization scope and erasure/recovery uses complete and consistent,
   and what findings, exclusions and remediation remain? Cryptographic judgment
   and storage/recovery judgment must have explicit scopes; ADR 0027's engagement
   question leaves their allocation open. Reviewer findings do not choose the
   maintainer's representation or ratify the ADR.
