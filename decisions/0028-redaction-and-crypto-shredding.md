# ADR 0028: Redaction and Crypto-Shredding

Status: Proposed — draft for review; not ratified and does not authorize implementation.

Date: 2026-09-13

Supersedes on acceptance: [ADR 0002](0002-payload-stored-plaintext-in-v0.md), [ADR 0007](0007-payloads-keyed-by-event-id-not-payload-hash.md), [ADR 0014](0014-cross-belief-reducer-and-hash-lineage.md), [ADR 0025](0025-incremental-result-commitment.md), and proposed [ADR 0027](0027-stage-three-authority-and-acceptance.md) only as enumerated below. Narrows architecture Invariants 8/14 and sections 5/11 for key custody, erasure granularity and replay.

Related: [ADR 0015](0015-candidate-scoped-verification.md); [ADR 0026](0026-usage-is-not-evidence.md); proposed [ADR 0027](0027-stage-three-authority-and-acceptance.md).

Implementation: None. Encryption, key custody, authorization, typed sentinel, erasure sweep, proof plumbing and recovery are all future implementation. The string `state_machine.REDACTED` and a missing payload are not implementations of this contract.

## Context

Architecture section 5 requires an authorized erasure to leave a typed REDACTED
result even at a historical cutoff preceding the erasure. The envelope and its
hash remain; content-based evidential support does not. Current projectors cannot
perform that replay. Payloads and many derived copies are plaintext.

ADR 0025 makes deleting only the payload row insufficient. Candidate records,
event dependencies, identity-record keys, immutable Merkle leaves, old roots,
lineage serializations and detached snapshots can retain the same private content.
Erasure must cover every managed copy, not merely the current belief head.

A commitment can survive erasure; verification of the erased plaintext cannot.
This decision preserves authenticated commitments and explicit proof boundaries,
without pretending that a hash or a deletion receipt reconstructs destroyed data.

## Decision

### 1. Version and storage boundary

Register projector "4" and database schema "6" for erasure-aware storage and reads.
Projector "4" inherits the proposed stage-three contract only after ADR 0027 is
ratified; acceptance of this draft alone does not ratify that draft. Its authority
enrollment/signature mechanism is a prerequisite, not an implicit owner fallback.
The revised ADR 0027 already supplies sealed event schema "2", protected
`nyx-map/2`, independently erasable keys and replayable custody history. Projector
4 adds erasure capability, terminal standing, erasure-aware leases, overlays and
execution recovery on the existing protection/restore barrier; it
does not introduce encryption only after a plaintext projector 3 has shipped.
See section 11 for separate versus combined release requirements.

Versions "0", "1", "2", and "3" keep their unredacted semantics and bytes. They
are not taught to interpret REDACTED as an ordinary value. A request pinned to an
old version that touches erased history refuses with an explicit unsupported-
redacted-history result; it is not silently upgraded or served from an old cache.
Erasure of managed copies applies to every version's storage, not only version 4.
The original frozen projectors remain reproducible on retained unredacted logs.

Schema "6" is selected explicitly and adds manifests, protected object storage,
key bindings, erasure progress and authenticated pruning records. No generic
in-place database migration is authorized. Legacy import into an erasure-managed
store is a separate, explicitly invoked conversion with the checks in section 9.
It does not rewrite legacy Layer A envelopes or claim their payload format changed.

### 2. Data classes and the indivisible erasure unit

An original event's private payload is one erasure unit, identified by its opaque
`event_id`, never by content equality. Independently recorded identical payloads
have independent keys. The initial contract supports whole-event private-payload
erasure; a request for a field within that unit must explicitly authorize the
wider whole-unit erasure. There is no silent widening or invented selective-key
scheme. A multi-subject event may therefore require a wider authorized scope.

Separate nonsecret replay structure from private content before encryption:

| Class | Treatment |
|---|---|
| Private claim values, mention text, source documents/configuration, credentials, free-text reasons and mappings from opaque IDs to people | Encrypt within the event's private unit; redactable. Credentials are never put in an envelope or clear diagnostic. |
| Structural replay data | Retain opaque event/subject/belief/candidate/link IDs, exact opaque property IDs, output inventory, partitions, predecessor/successor relationships, dependency roles/selectors, justification/rule IDs, restrictions, contract versions and nonsecret source-class IDs. No copied values, text, names or secrets. |
| Envelope and audit controls | Retain envelope hashes, committed body/ciphertext hashes, order/times, opaque signer/key IDs, signatures, grants, reason class and request/completion references. Needed to explain what existed and why it is unavailable. |
| Derived content, embeddings, search snippets, process traces, Dream/retrieval caches and generated outputs dependent on private data | Reconstructible and subject to the erasure closure, even outside the truth ledger. Usage remains non-evidence under ADR 0026. |
| Nyx private encryption/signing keys, key-service access credentials and secret RNG/derivation state | Outside the truth ledger; never copied to a payload, trace, Merkle leaf, backup of the log, or committed source configuration. Captured source credentials remain encrypted private content. Public nonces, ciphertext and AEAD tags are retained under ADR 0027 section 3.1; they are not forbidden secret RNG state. |

Every new event records the permanent public object and canonical structural
manifest from ADR 0027 section 3, sufficient to replay its
identity and support topology without the private values. Fields whose contents
are private use opaque references rather than embedding the contents in an ID or
property string. The manifest is committed with the encrypted body. In particular,
an identity-record map key cannot be canonical JSON of a private record, as it is
in the older tree format.

Opaque IDs, metadata, topology and commitments can themselves reveal relationships;
their retention is an explicit limitation, not a claim of anonymization. A request
to erase structurally required metadata cannot be fulfilled while preserving this
same auditable chain. It must be reported as outside this erasure contract. Existing
PII inside a legacy envelope is not removable through payload crypto-shredding.

### 3. Key binding and custody

Use a fresh random 256-bit data-encryption key (DEK) for each event unit. Encrypt
once with ChaCha20-Poly1305, using the 96-bit nonce and 128-bit authentication tag
defined by [RFC 8439](https://www.rfc-editor.org/rfc/rfc8439). A key is never reused
for a second encryption. The writer retains ciphertext and nonce for retries;
it does not re-encrypt a retry. Decryption verifies authentication before decoding.
Use a maintained cryptographic library, not a new implementation of the primitive.

Use ADR 0027 section 3's exact `nyx-unit-aad/1` associated data, `nyx-public-operation/1`
signed public object and `nyx-sealed-body/1` stored representation, with the event's
recorded projector/contract. Do not redefine a second encryption or signature
construction here. Swapping ciphertext, manifests, authority scope, events or
ledgers must fail authentication, signature or committed-hash validation.

ADR 0027 sections 3.1-3.3 also govern exact C/F wire bytes, domain labels, key
generations/wrapper rotation and the rollback-resistant witness. In particular,
AAD includes embedded attestation signatures inside S and excludes only enclosing
SIG, D and final hashes; `D.aad_hash` commits to those exact framed AAD bytes.
There is no second serialization, signature suite or private-codec default here.

DEKs live in a separate privileged key service, indexed by opaque key-unit ID and
version. They are not wrapped solely by a recoverable master key inside SQLite.
The service must support independently destroying a unit and all recoverable key
versions/replicas, idempotent destruction, and durable non-resurrection tombstones.
Only an explicitly granted `protected_decrypt` principal may request scoped
decryption; ordinary code, the local operator and an identity curator have no
implicit access. Only the erasure executor can invoke
destruction against a committed authorized request. Administrator/approver signing
keys are separate from data keys and survive content erasure.

No DEKs or recoverable historical wrappers may appear in ordinary database backups.
A key-service backup/replica is managed erasure scope: deletion must be acknowledged
there before completion. If a provider cannot prevent recovery of a destroyed
version from its retained backup, it does not satisfy this contract. Key-service
outage is not evidence of redaction. Missing keys without an authorized committed
request are integrity/recovery errors, not REDACTED.

Use ADR 0027 section 5.1's two distinct concepts: immutable `original_binding`
in the creation manifest and `effective_binding(unit_id, locked_prefix)` derived
from recorded identity/custody transitions. "Canonical subject" means the same
prefix-specific identity in both documents. A current-binding table or key-service
cache is not historical authority. Ordinary accepted association links do not
change custody; only explicitly accepted merge/split custody dispositions do.
Merge A+B -> M deterministically substitutes M in the effective sets and retains
the originals. Split A -> B+C must record B, C, shared B/C or ambiguous B/C for
each affected unit, including retired/erased units. It never silently fans out
plaintext, support or DEKs. Unknown applicability remains explicitly ambiguous.

Read/decrypt requests use the live locked prefix, even for historical content.
They need a separate purpose/unit-scoped grant covering every effective subject
of a shared/ambiguous unit; a B-only reader cannot decrypt B/C content. A subject
identity transition invalidates old permits before publication is externally
readable. It does not confer successor grants or restore any erased key. This
enforces capabilities without deciding who among contributors should receive them.

### 3.1. Retired identifiers and frozen destructive scope

Resolve the request's subject selectors at the actual locked append prefix, using
recorded identity-successor edges only. Record the supplied selectors, resolved
active scope and explaining transition IDs in the signed request:

| Selector | Admission |
|---|---|
| Active subject | Use that subject |
| Retired subject with one active successor | Resolve to that successor and review the resulting current scope, including units originally bound to other merged predecessors |
| Retired subject with multiple active successors | Refuse unless the request explicitly names its intended nonempty successor subset; there is no implicit "all descendants" |
| Retired subject with no active successor | Refuse subject selection; an explicit event/unit request may still be reviewed against its retained binding history |

For selected active subject set Q, enumerate all retained event units whose
effective subject set intersects Q, including historical/erased units. Original
bindings establish the audit path, not a second undocumented selection predicate.
Ledger-bound units require an explicit unit/ledger selector and ledger-wide grant.
An explicit unit request avoids subject expansion but does not bypass authority
over that unit's complete effective scope. The same scope calculation applies to
shared and ambiguous units. For example, selecting B after A -> B+C includes a
B/C ambiguous unit only with B-and-C authorization; a B-only grant refuses the
whole request rather than skipping the unit or pretending to erase only its B part.

The reviewed request records exact original unit IDs, committed body hashes,
original/effective binding proofs, full affected subject set and the locked prefix.
Authorization covers every affected subject; narrowing a unit's fields requires
explicit agreement to the whole indivisible unit. After commit this manifest is
immutable: later identity transitions cannot expand, shrink or retarget the
destruction. A pre-merge request for A does not acquire B's units on A+B -> M;
a post-merge request resolving A to M reviews M's full scope anew. An already
destroyed unit stays destroyed and can be referenced by later requests without
recreating its key. Equal plaintext never identifies a second erasure target.

This freezes the destructive root units. Registered secret-bearing derivatives
are part of each unit's erasure obligation: the request includes their closure
inventory/root at the barrier. No new derivative may be created from those units
after the barrier. Discovery of a previously omitted managed copy is an incomplete
execution/inventory failure, not authority to select new original evidence units.

This replaces literal one-key-per-entity destruction with per-event keys plus
canonical-entity binding. It reconciles architecture section 11 with ADR 0007's
independently destroyable events. Subject-wide erasure is an authorized batch of
units, not destruction of one shared key with unenumerated collateral effects.

### 4. Authorization and two-phase execution

Add `redaction_authorizer` and `erasure_executor` capabilities through ADR 0027's
explicit enrollment/update records, under policy `nyx-erasure-authority/1`.
They confer no identity-merge or world-verification privilege. The first signs an
exact request; the second executes and signs completion receipts. A principal may
hold both only through explicit grants. Source attribution, a text request, Layer B
or being the local operator supplies neither capability by itself.
The four capabilities remain separate: read/decrypt; identity association/merge/
split; authorize redaction; execute destruction. Explicit grants may combine roles,
but none implies another. The erasure executor verifies the retained public signed
request, historical grant and exact unit manifest and may destroy by opaque unit
ID without a decrypt grant. A semantic/capsule validator that needs live content
must separately hold `protected_decrypt`; its access is not inherited by executor
or authorizer. The general contributor-read policy remains open under ADR 0020.

Use new `redaction_requested`, `redaction_execution_recorded`, `redaction_reviewed`
and `redaction_completed` event types; do not overload
an observation or treat the existing unused `redaction_applied` name as a workflow.
All four use the permanent signed-public-envelope construction
of ADR 0027 with projector
"4" and contract `nyx-redaction/1`. Required recorded request contents are:

- request ID, authorizing principal/key and historical grant references;
- reason class: `credential`, `PII`, `legal`, or `user_request`; optional private
  explanation is sealed, never required as plaintext for future authorization;
- exact target event/unit IDs, hashes, binding prefix and full affected subject set;
- structural replay capsules and original commitment inventories for legacy units;
- the managed storage/replica scope and the rule version for dependency closure.

These authorization, manifest, closure and receipt fields are permanent public
structure. The optional private explanation uses the request event's own sealed
unit; erasing it cannot invalidate the request's original signature or make its
authority unverifiable. Completion publicly signs its request hash, per-store
receipts, executed closure root, effective publication progress and redaction-set
hash. Receipt formats contain opaque IDs/status only, never plaintext diagnostics.

Append verifies permission against the actual prefix, unit existence, complete
scope, and capsule/commitment consistency. Validate live content with separate
permission; already-erased overlapping targets use their previously verified
authorized commitments/capsules, never a requirement to recover their plaintext.
No worker may start deletion based solely on a prepared or signed-but-uncommitted
request. The request is irreversible once committed; cancellation cannot resurrect
keys. Revoking its signer later does not cancel that historical authorization.

Execution order is mandatory:

1. Acquire the exclusive disclosure barrier and prepare the witness fence under
   ADR 0027 section 3.3. Commit the authorized request and synchronous erasure
   barrier, then confirm its exact manifest/prefix in the witness. The current
   redaction set immediately includes its target units, even before key destruction.
2. Revoke decrypt access and invalidate reader leases for affected units and
   derived generations. From the committed barrier, affected content reads may
   return only the sentinel response specified in section 5. Block affected
   belief/state reads that require an unpublished masked generation until that
   generation is published. An old stale label is not permission to disclose
   content scheduled for erasure, even while the key still exists.
3. Only after witness confirmation, destroy the original unit keys and dependent derived keys in all managed
   key-service copies. Persist idempotent destruction receipts, without key data.
4. Sweep every managed materialization, retained tree generation, dependency
   cache, snapshot, trace and index; publish masked records and erasure-aware
   progress atomically. Complete the legacy cleanup obligations in section 9.
5. Append `redaction_completed`, referencing the request, destruction receipts,
   exact closure inventory or its canonical root, per-store acknowledgements and
   published redaction-set hash. Completion describes execution, not a new grant.

Startup reconciles the witness and every outstanding request, including a
previous completion invalidated by a subsequently discovered copy, and rolls
forward where its prerequisites remain available. A crash
before request commit erases nothing; after any subsequent step it resumes the
same idempotent request. A key already destroyed is a successful retry only when
its service tombstone binds it to that request or section 4.1's verified prior
receipt establishes destruction under an overlapping authorization. Never turn missing data
of unexplained origin into a completion receipt. Completion cannot precede any
managed replica/cache acknowledgement or mask publication.

Overlapping requests form a union of erased units. A later request may reference
an already verified capsule and destruction receipt, but cannot reissue a key or
reconstruct erased plaintext. Each request retains its own authorization and
completion accounting; replay exposes all applicable request references.

The key service and rollback-resistant witness are explicit exceptions to
reconstructible operational state: secret key
material is intentionally unavailable from the truth ledger. The ledger remains
the durable authority for *why and which* keys may be destroyed; service receipts
record execution, not world truth. No atomic transaction across SQLite and the key
service is assumed. Roll-forward and fail-closed fencing govern the crash window;
their liveness depends on recoverable history and the provider/witness guarantees.

The credential fast path is restricted to an explicitly pre-granted automated
`redaction_authorizer` with reason scope `credential` and enumerated ingestion
domains. It must still append a signed request before destruction; it bypasses
waiting for a human, not durable provenance. Completion records human review as
pending until a later `redaction_reviewed` references the request. A rejected review
cannot restore the secret; it records the erroneous erasure. Without that grant,
automation can block exposure and propose, but cannot destroy keys.

### 4.1. Frozen closure, receipts and non-atomic execution

Execution is a resumable manifest-driven operation, not an all-or-nothing key
transaction. Never roll back destruction or compensate by recreating a DEK.
Authorization freezes the original units and the complete registered derivative
closure at the actual locked prefix. Include the effective subject sets of shared
derivatives, even if those subjects are not original-unit targets. A grant missing
any affected subject refuses the whole request before destruction; invalidating a
shared cache is not permission to destroy unrelated original evidence.

Each manifest entry names `{kind,unit_id,key_id,key_version,sealed_body_hash,
effective_subject_ids,provider_id,copy_ids}`; kind is `original` or `derived`.
copy_ids is the complete enrolled set of recoverable provider copies/generations,
including backup wrappers and recovery shares. The signed request also binds its
prefix, original/effective-binding proofs, structural capsules and closure-rule
version. `manifest_hash` is H(F(`nyx-erasure-manifest/1`, the complete manifest
object)); the final closed schemas for its proofs/capsules remain a ratification
blocker. An executor cannot replace those fields with an implementation-defined
list of IDs and call it the same authorization.

A provider destruction receipt's public object is exactly
`{format:"nyx-key-destruction-receipt/1",ledger_id,provider_id,provider_key_id,
request_event_id,request_event_hash,manifest_hash,unit_id,key_id,key_version,
copy_id,provider_generation,outcome,prior_receipt_hash,recorded_at}`.
Sign F(`nyx-key-destruction-receipt-signature/1`, object) with the enrolled provider's
Ed25519 key; container `{public:object,signature:hex_signature}`. outcome is
`destroyed` or `already_destroyed`; the latter requires a verified prior receipt
for this same unit/key/version/copy (possibly under an overlapping authorized
request), named by H(F(`nyx-key-destruction-receipt/1`, prior_container)).
prior_receipt_hash is otherwise null. Timestamp is an offset-bearing recorded
string, not proof of destruction. provider_generation is monotonic. Provider
signatures report custody facts and never authorize the request themselves.

`destroyed` acknowledges that the addressed live/recovery copy is irrecoverable
under the enrolled provider profile, all relevant decrypt permits/buffers are
revoked, and the non-resurrection tombstone is durable in the witness. A timeout,
HTTP success, absent key row or lost receipt is not that evidence. Query/reconcile
the provider and witness after acknowledgment loss; if evidence cannot be obtained,
mark the copy unknown and do not claim completion. Copies outside the provider
profile, including a surviving backup handle, invalidate its completion claim.
A signature proves who attested, not physical deletion; the trust/host limits in
section 9 remain explicit. A lying provider is outside that trusted guarantee,
not detectable merely by hashing its receipt.

Append `redaction_execution_recorded` for attempts/progress/failures with request
ID/hash, immutable manifest_hash, monotonic attempt number, per-copy receipt
references, exact unknown/outstanding entries and nonsecret error codes. It is
signed by an explicitly currently granted executor and contains no private body.
Provider/witness receipts survive a crash before this diagnostic append; reconcile
them into the log on restart without repeating successful destruction. This
operational record changes neither original targets nor candidate truth.

`redaction_reviewed` is a public signed record naming request ID/hash, reviewer
principal, outcome `confirmed` or `erroneous`, and an opaque reason code. Its signer
needs a current explicit `redaction_authorizer` grant covering the original reason
and entire frozen scope; executor or decrypt permission alone is insufficient.
It clears review debt only, never cancels an erasure or restores secret material.
Loss/revocation of an executor requires a newly explicitly granted executor. Loss
of the sole administrator with no eligible executor blocks further execution;
there is no automatic recovery authority. Historical authorization still stands.

### 4.2. Failure states and restoration

Report execution separately from the logical redaction set and verification state.
Per-copy progress is `not_started`, `destroyed` (verified receipt), or `unknown`;
never infer successful erasure from inability to decrypt. A committed request's
logical redaction is permanent even when execution fails.

| State/window | Required response and restart behavior |
|---|---|
| Before request commit, including a prepared witness fence | No committed-key destruction. Normal reads only before the fence; fenced reads block. Establish commit/abort from authoritative history, never from absence in an old snapshot |
| `pending`, request committed and witness-confirmed, zero or some copies destroyed | Sentinel/pending responses under section 5; persist receipts per copy and resume exactly the outstanding manifest entries. A crash is not a cancellation |
| `failed`, last attempt errored or a copy's outcome is unknown | Preserve barrier, disclose error and per-copy state. Retry only after resolving the condition; never label remaining copies erased. Zero deletions still does not permit undoing committed authorization |
| `irrecoverably_partial`, some destruction is established and remaining obligations cannot be completed under the surviving evidence/authority/provider contract | Retain destroyed and unknown/outstanding sets permanently; expose the unrecoverable failure, never completed. No automatic fallback, widened targets or recovery of destroyed material. External recovery of the missing prerequisites may permit a later explicit retry; it cannot undo the already irreversible loss |
| Mask published but receipts/closure acknowledgments incomplete | Continue pending/failed disclosure; masking is not physical completion |
| `completed` | All frozen copies/generations have verified receipts, every managed persistence location has an acknowledgment, effective masks/progress are published, the witness durably records denials/receipts, and signed `redaction_completed` is committed and witness-confirmed |

`erasure_pending=true` means completion is outstanding, including failed and
irrecoverably partial requests; return execution_state/error separately. Partial
success is never reported as batch success. A new request may reuse prior verified
receipts but cannot erase evidence of a failed attempt. Discovery of an omitted
copy after claimed completion records an execution failure and withdraws the
current success claim; it never rewrites the historical completion event. The
same-copy closure obligation persists, but new independent units need new authority.

The rollback-resistant witness required by ADR 0027 section 3.3 retains exact
committed requests/manifests and their chain anchors, pending fences, denials,
provider inventories/generations, receipts and completion references. It must
survive restoration of both the ordinary log and old key-service backups. Its
own recovery must preserve monotonic state and all acknowledged tombstones;
restoring it from an older backup is prohibited. A second co-restored SQLite
table or signed-but-replayable checkpoint alone is insufficient.

Before any restored process unwraps a key, starts a reducer with private content,
serves a cache/export, or resumes writes, obtain a fresh challenge-bound witness
checkpoint and reconcile the restored ledger with its anchored prefix. Fetch
and verify missing authoritative events, requests and receipts; reject a fork.
Then install the current denial set in every provider/reader, revoke old permits,
reconcile partial requests and publish erasure-aware state. A restored wrapper
must be rejected before unwrap if its unit/generation is denied. Raw unit handles
must also be physically unrecoverable under the provider profile; a software
deny list alone cannot render an exported raw DEK cryptographically forgotten.

Missing witness/history, unexplained provider rollback, an unresolved prepared
fence or lost monotonic proof means recovery-blocked with no secret disclosure,
not a new genesis or an empty redaction set. Public diagnostic reads may report
that status without asserting fresh history. Old projector 3 readers use this
same mandatory barrier and refuse erased/unsupported history; they need not
implement projector-4 sentinel/standing semantics to prevent resurrection.

### 5. Typed REDACTED and reader plumbing

Define an immutable tagged type, distinct from Python `None`, strings, JSON null,
and a verification-state enum:

`RedactedPayload(event_id, committed_payload_hash, redaction_request_ids, reason_classes)`

Its canonical external form is
`{"kind":"REDACTED","event_id":E,"committed_payload_hash":H,"redaction_request_ids":[...],"reason_classes":[...]}`.
Sets use canonical ordering. It contains no private values, snippets or hashes
newly computed from guessed plaintext. An ordinary user value equal to that JSON
object is still wrapped as an available value; tags belong to the reader's result
type, never to untrusted payload content.

Payload reads return a discriminated union `AvailablePayload(data)` or
`RedactedPayload`, accompanied by the surviving envelope and structural manifest.
No existing event yields an unqualified missing row. A missing/corrupt ciphertext
or key without authorized erasure raises `IntegrityError`; unauthorized deletion
is never normal absence. An unavailable key service yields an availability error.
The committed request and synchronous barrier in section 4 are the logical
non-disclosure boundary, not physical key destruction or later mask publication.
A content read whose target membership can be verified from that committed
request returns the sentinel plus separate `erasure_pending` status immediately;
it needs neither decryption nor a masked projection to construct that response.
The sentinel reports authorized logical unavailability, not completed destruction.
This does not permit serving a partially masked belief, collection, snapshot or
standing result from a stale derived generation.

| In-flight phase | Affected reader response |
|---|---|
| Before authorization is committed | Normal authorized reads apply until the exclusive prepare fence is acquired; then affected disclosure blocks pending commit/abort reconciliation. An uncommitted request never produces REDACTED or authorizes destruction. |
| After authorized request/barrier commit, before key destruction | Targeted content reads return `RedactedPayload` with `erasure_pending=true`; no affected plaintext is disclosed. Belief/state reads needing the unpublished masked generation remain blocked. |
| After destruction, before masking is published | The same sentinel/pending response remains available from verified request membership. Affected belief/state reads still block; missing keys explained by that request are not mistaken for unexplained corruption. |
| After masking is published | Affected belief/state reads may return the masked generation and typed sentinels once its redaction generation/progress is checked. `erasure_pending` stays true until the applicable requests complete; it becomes false only after completion, not merely after masking. |

There is no safe belief/state answer from an affected unmasked generation in the
middle two phases. If a reader cannot establish the current barrier generation
or verify target membership, it must block or report unavailability, not return
old content or invent a sentinel. ADR 0027 section 3.3 supplies the common
exclusive-fence/shared-permit protocol, including already in-flight responses;
section 4.2 supplies recovery. Disconnected readers have no offline grace period.
The concrete provider/host must demonstrate this protocol before deployment.

For new protected events, authorized erasure destroys decrypting keys while the
permanent public object, signatures and sealed body remain. Their unexplained
absence/corruption is still an integrity failure even for an erased unit; a
redaction request is not permission to lose the signed message or ciphertext.
Only explicitly authorized legacy pruning may replace an old private body with
the safe commitment/capsule representation in sections 7/8.

Thread this union through stored event reads, pending-event reads, replay,
rebuild, candidate value reads, belief collections, mention text, snapshots,
proof/content inspection and serialization. A genuinely unknown record may still
return ordinary absence. Named erased candidates remain addressable and return a
typed unavailable value. Raw legacy readers must not recover a value from any
retained version cache. Structural identity lookup remains possible where its
retained topology suffices; it does not return the erased mention text.

Every managed reader checks a redaction generation as well as derived progress.
Detached snapshots/long-lived readers are leases under that generation and must
be invalidated or terminated before completion. This changes the future reader
lifetime contract explicitly; a freely copied plaintext dictionary cannot be
revoked. Erasure guarantees cover managed storage and processes, not data already
exported, copied by a client, or captured outside that boundary.

### 6. Standing, dependencies and deterministic replay

Treat dependency roles separately: `payload_content`, `envelope_fact`, and
`structural_relation`. A historical support edge remains as provenance, with its
availability/restriction recorded; it is not counted as usable content support
after redaction. Envelope-only facts survive only for claims explicitly justified
by retained envelope fields. A payload hash or structural candidate ID cannot
support the proposition previously encoded by the erased value.

For an erased claim's own content, candidate `verification_state` becomes
`redacted` and its value becomes the sentinel. Preserve prior standing, approval
IDs, restrictions and predecessor history as structural audit information.
`redacted` is terminal for that candidate; later recollection must be a new event
and new candidate, not resurrection of the old erased unit. Identity lifecycle
and supersession remain separate axes. No aggregate belief state is introduced.

For a candidate whose own content survives but whose dependencies are erased:

| Condition | Result |
|---|---|
| At least one previously recorded sufficient justification survives, and no candidate-wide restriction applies | Hold prior standing; erasure does not discover a replacement justification or promote |
| Necessary content justification fails, prior `verified` or `unverified` | `questioned`, recording exactly which required support became unavailable |
| Prior `questioned` or `quarantined` | Hold that state and retain/add the dependency failure |
| Only adverse/opposing content disappears | Hold standing; no automatic promotion or scalar winner |

Propagation walks actual transitive justification dependencies to a fixed point
on the support DAG. A justification's required set is conjunctive; distinct
sufficient justifications are separately recorded. No unaffected candidate is
demoted merely for sharing an entity. An affected derived artifact whose content
itself includes or reveals the erased input is erased, not merely relabeled
questioned. Preserve its opaque existence/dependency record; regenerate only from
surviving inputs and never restore its old encryption key.

Erasing the private basis for an accepted identity link preserves the historical
decision and structural topology, but makes that basis unavailable to any claim
justification requiring its content. Recompute those dependent justifications;
do not silently undo a merge, invent a split, or treat the retained link ID as
replacement evidence of identity. An independently sufficient surviving basis
can retain usability without earning new standing.

The Stage Three tables apply under projector 4 with these explicit cases:

| Operation after redaction | Permitted transition |
|---|---|
| Merge carrying a redacted candidate | Carry its unavailable-content reference and historical standing; it remains redacted |
| Split with a structurally established successor claim scope | A fresh scoped candidate may carry only the predecessor's structural/redacted reference; no fresh DEK, ciphertext copy or recovered value |
| Split without established claim applicability | Refuse any required new claim assignment; preserve the historical opaque candidate. Custody may be explicitly ambiguous, which is not evidence |
| Surviving candidate losing necessary content/path justification | Verified/unverified -> questioned; questioned/quarantined hold; independent sufficient justification holds prior standing |
| New link/merge/split needing an erased identity basis | Refuse unless independent live or retained structural evidence suffices for that specific acceptance; a historical accepted link is not replacement evidence |
| Corroboration | Erased/restricted content cannot be a contributor; no verification from ciphertext hashes, custody or approval alone |
| Recollection of an erased value | New independently observed event and candidate; never revive or decrypt the old unit |

Redaction takes precedence over the ordinary split-standing table for the erased
claim's own content. Supersession/lifecycle remain distinct structural axes. An
identity operation cannot clear an erasure barrier, generate a replacement key for
a destroyed original/derived object, or serialize a cached plaintext copy into a
new successor. General correction, restoration and mention-correction handlers
remain outside the stage; this table does not authorize them.

At any `as_of`, use the full currently committed redaction-request set, including
requests after that cutoff, as architecture section 5 requires. Do not use current
key availability to determine the set. Authorization validation still uses each
request's original pre-event prefix. The replay inputs are explicit:

`(ordered_chain, as_of, projector_version="4", current_redaction_set)`.

Ordinary event semantics retain the inclusive recording-time cutoff. The redaction
overlay is the explicit exception, disclosed by `redaction_set_hash`; it cannot
revive erased content by choosing an earlier time. Requests and completions have
their own recording-time audit history; content availability follows the current
request set. Tests compare complete sweep and replay results under the same inputs.

### 7. Commitments that remain verifiable after erasure

New encrypted events retain ADR 0027's schema "2". Their `payload_hash` commits to
the exact `nyx-sealed-body/1` body `{format,public,signature,sealed_content}`, with
its permanent U, SIG, structural manifest, protected descriptor and recorded
ciphertext. It is not an unsalted plaintext fingerprint. Envelope hashing keeps
the existing formula; idempotency uses the source/time/canonical-body construction
on that recorded sealed body. Exact retries retain it. Ciphertext randomness is
chosen by the writer, never replay. Prefix changes require fresh encryption and,
for signed event classes, new review and signatures as specified in ADR 0027;
no plaintext-content deduplication is implied.

Original-signature verification binds the signed classes in ADR 0027 section 3:
authority enrollment/updates (including required rotation countersignatures),
accepted identity association/merge/split operations, gate-approved corroboration,
and the original public attestations embedded in their S. It also binds this
decision's signed redaction requests, execution records, completions and
credential-review records. Provider receipts and witness checkpoints have their
own specified signature domains and enrollment checks.
For those classes, check each specified original signed object/signature directly
against retained public keys and the applicable historical grant or enrollment
trust pin. A required missing signature is a failure, not an unsigned-event fallback.

Ordinary observations/mentions with null A/SIG have no original approval signature
to verify. Verify their envelope/hash chain and sealed-body commitments under their
recorded contract; do not infer approval authority from source attribution.
Explicitly unsigned legacy events likewise stay unsigned and receive their
version's envelope/hash-chain and available payload-integrity checks. After
authorized legacy pruning, verify the retained commitments and signed erasure/
capsule authorization under section 8; recomputation requiring erased plaintext
is unavailable, not passed. A later capsule never supplies an original signature.
The future integrity reader dispatches on the recorded event schema/contract,
never on a guessed payload shape or mere absence of a key:

| Recorded representation | Mandatory checks and reported limit |
|---|---|
| Legacy available payload | Existing canonical payload/idempotency recomputation and envelope-chain checks remain unchanged |
| Schema-2 sealed body, live or authorized erased | Recompute payload and idempotency hashes from the complete retained sealed-body dictionary; verify nonce/tag/descriptor shape, ciphertext/AAD commitments and applicable original public signatures without a DEK |
| Live sealed content with a permitted decrypting verifier | Additionally authenticate AEAD, decode protected content and perform content-dependent semantic validation; unavailable permission/service is an explicit verification limit or availability failure |
| Explicitly authorized legacy pruning | Verify original envelope/chain, the precise signed pruning/capsule authorization and safe structural proofs; mark original payload/idempotency-preimage and erased semantic checks unavailable, never passed |
| Missing, altered or pruned data without the corresponding committed authorization | IntegrityError; neither a key outage nor a missing row is an erasure authorization |

Every branch verifies the full ordered log's event hashes, predecessor links,
ordering and duplicate constraints **before** any cutoff/as_of filtering. A
retained ciphertext mutation still fails after destruction. The shipped
`integrity.verified_log` in `ab6d403` assumes the decoded original payload is
recoverable; it currently has no authorized-pruning result. Future versioned
plumbing must expose the above check categories and cannot report its ordinary
full-verification success for legacy content whose preimage has been destroyed.
The exact typed result/capsule schemas remain ratification blockers below.

Erasure removes neither a required original signed public message nor its protected
commitment. For signed and unsigned protected events alike, a permitted verifier
can authenticate, decrypt and semantically check live content. After authorized
destruction, those content checks are unavailable; applicable original signatures
and the separately signed erasure authorization/completion remain verifiable.
A valid signature proves attribution and integrity of a commitment, never the
truth of the erased claim.

Projector "4" reuses ADR 0027's protected `nyx-map/2` format with ADR 0025's
deterministic routing/branch rules and opaque record-ID keys. A member's value
consists of its
complete structural fields plus protected-content references. Each reference
contains the source event/unit ID, committed sealed-body hash, and exact content
selector. Candidate value, mention text and private source fields are references,
not copied plaintext. Event dependencies bind envelopes and entire sealed bodies;
identity records use recorded opaque IDs, not their private content as keys.
Full logical reads dereference while available; after erasure they expose the
sentinel without changing the historical ciphertext commitment.

Changing protected content changes the sealed-body commitment and every dependent
root; dropping a candidate, path, reference or support association changes its
structural member and root. This preserves complete *commitment* coverage. It does
not preserve access to erased logical content, nor require re-encryption on each
belief update. Ciphertext and nonsecret branch descriptors may remain indefinitely
after all decrypting keys are destroyed.

Keep two explicitly labeled commitments:

- `original_lineage_hash`: the immutable commitment to what was published under
  its original projector at that event prefix. It is never rewritten as if it had
  always committed to a sentinel.
- Version-4 `view_version_hash`: hash of canonical
  `{"format":"nyx-effective-belief/1","projector_version":"4","original_lineage_hash":H,"erasure_overlay_root":R,"effective_result_root":S}`.
  R covers the relevant authorized erasures and restrictions; S covers the complete
  effective structural result and protected/sentinel references. Evaluation-only
  fields remain excluded. Unrelated erasures do not enter a belief's R.

Original version-4 lineage uses `nyx-belief-lineage/4` with original pre-event
predecessor hashes and result roots over structural members/protected references,
following ADR 0025's ancestry construction. The effective hash is the separate
current-erasure view binding. Public responses expose both labels and the global
redaction-set hash; they never claim the effective result opens an old root.

For a new-format root, a verifier can still hash stored ciphertext descriptors,
leaves and branches and reconstruct the same original root after key destruction.
It can prove membership of the committed encrypted object against a trusted root.
It cannot decrypt, authenticate plaintext without its key, verify the old claim's
truth, or re-execute content-dependent semantic acceptance after that content is
gone. Append requires permitted semantic validation of live content. Replay with
live content performs those checks when authorized; otherwise it reports semantic
verification unavailable, not a successful full semantic replay.

For old ADR 0025 leaves, the whole private value was inside the hashed node and
some keys also contained private content. Destroy those node bodies and keep an
authenticated pruning record: original node hash, safe branch position/proof,
and the committed redaction request/capsule explaining its removal. Never retain
a plaintext key inside that proof; pruning may have to cover a larger subtree.
Branches above it use the original child hash, so ancestor/root recomputation
still reaches the original trusted root. A pruned hash is an opaque commitment,
not a newly serialized ordinary node or the hash of REDACTED.

Proof APIs distinguish `available_content_proof`, `sealed_object_proof`, and
`authorized_pruning_proof`. The last proves an authorized opaque subtree commitment
under the old root, not key/value inclusion inside the destroyed subtree. A missing
node without the committed pruning authorization remains corruption. Old
unsalted hashes can leak equality or permit guesses; retaining them preserves
auditability, not information-theoretic forgetting.

### 8. Replay capsules are durable before destruction

Before erasing a legacy payload or old leaf, append the needed nonsecret structural
replay capsule as part of the authorized request. It records that event's envelope
hash, opaque output inventory, original candidate/identity/support topology,
justification and restriction history, and the original lineage/root commitments
needed to identify historical publications. It contains no claim value, mention
text, private map key or copy of the erased payload. Build and validate it against
the full log while the content exists, not against a possibly corrupt materialization.

For new schema-2 events the committed structural manifest supplies this topology
from the outset. For legacy input, the signed capsule is an explicit historical
attestation of the structural result. It does not prove the erased plaintext's
semantic correctness. After destruction, replay verifies envelopes, ciphertext or
pruning commitments, capsule authorization, structural consistency and the current
erasure rules; semantic checks needing destroyed content are reported unavailable.
They are not silently reported passed. Live permitted content still gets full checks.

Full replay reconstructs effective results from Layer A, capsules and the current
redaction set, ignoring all old derived rows. Sweep must equal that result. Original
roots for destroyed legacy representations come from the authenticated capsules;
they cannot be independently reconstructed from nonexistent plaintext. This is an
explicit narrowing of ADR 0025's full-content rebuild oracle after erasure.
The signature scope in section 7 applies here as well. No capsule substitutes for
an original signature. A legacy event that was unsigned
stays unsigned; its capsule signs only the present structural attestation, never
purports to be the old author's signature. A hypothetical legacy privileged
operation signed over private plaintext cannot be enrolled for destruction while
claiming permanent original-signature verification: refuse that conversion unless
its original signed message can remain permanently public without retaining the
target secret. Do not re-sign, rewrite or call a later capsule equivalent. Revised
projector 3 creates no such legacy format. All signatures in permanent public
envelopes, including protected identity attestations, remain directly verifiable.

No private capsule may remain solely in derived storage. If a safe sufficient
capsule cannot be constructed, refuse enrollment of that legacy unit into this
workflow; do not promise replay while deleting required unrecorded structure.

### 9. Complete managed-copy erasure

Within these Proposed contracts, this section and section 11 are authoritative
for the concrete deployment and erasure obligations; proposed
[ADR 0027 Gate 3](0027-stage-three-authority-and-acceptance.md#gate-3-implementation-and-operational-assurance)
is authoritative for the assurance gate. Evidence that these applicable
obligations are satisfied is consumed under Gate 3 and is what its assurance
verifies. The obligations and the gate must be read together; the gate's evidence
and authorization requirements are not restated here.

Secret-bearing material must be encrypted before its first durable write. Durable
plaintext representations that cannot themselves be securely erased are prohibited.
This applies first to authoritative Layer A, not only to its derived projections.
The append-only ledger retains signed public objects and randomized sealed bodies;
never a private plaintext payload, even as a JSONL retry/import intermediate.
Wrapping a projection key later cannot undo an immutable plaintext source append.
This invariant starts with revised projector 3; it is not postponed to projector 4.
Prefer references to event units.
Unavoidable derived plaintext is encrypted under its own independently erasable
key, with a registered exact input-dependency set. The reverse dependency index
is reconstructible; it is not the sole record authorizing erasure or topology.
Sensitive plaintext in memory is short-lived and not permitted in logs/crash dumps.

The following is the mandatory closure inventory. It covers the current SQLite
shape and the proposed Stage Three additions; an absent/unimplemented location
still needs this rule before it is introduced. A deployment must enumerate actual
stores/replicas and demonstrate the rule, not merely attest that its main database
is encrypted.

| Persistent or recoverable location | Required representation and erasure obligation |
|---|---|
| Authoritative event storage, JSONL source/import/export/retry spools and queues | Permanent public envelope plus registered sealed content before append/fsync. No decoded payload/config/attestation text. Current authoritative storage is SQLite; historical/future JSONL is not exempt. Legacy plaintext logs are conversion debt, not erasable by deleting projections. |
| SQLite `events`, `payloads`, source/config records | `events.source` contains only opaque metadata in the new format; private source configuration is sealed. `payloads` holds sealed bodies, not JSON plaintext in a column merely named ciphertext. Each original unit has an independent DEK outside SQLite. |
| `resolved_beliefs`, all `projected_*`, stage-three authority/association/justification/restriction/successor/custody tables | Nonsecret structure and protected references; unavoidable private caches use separately erasable registered keys. No copied clear candidate values, mention text or identity basis. Authority's public grant metadata stays public; private principal mappings do not. |
| All historical projector representations, `committed_nodes`, `committed_roots`, lineage and predecessor records | Enumerate every retained generation, including unreachable nodes. Protected leaves/opaque keys from first write. Old private inline bodies require actual cleanup; retain only safe hashes/pruning certificates. Original protected roots remain reconstructible. |
| SQL indexes, FTS/source/text/vector indexes, embeddings and lookup keys | No private plaintext or unsalted low-entropy content-derived lookup fingerprint. Use opaque keys/references, volatile rebuilding or independently erasable encrypted objects; do not create plaintext FTS tables as a convenience. |
| SQLite WAL, rollback/super journals, temp databases, sort spills, freelists, page caches written to disk | Application receives/persists only sealed secret data. Decrypted query intermediates must not spill; disable that path or use independently erasable encrypted scratch storage. Checkpoint/VACUUM and ordinary full-disk encryption alone do not establish per-unit erasure. |
| Persistent caches, Dream/retrieval output, model prompts/results, `process_traces`, `gaps`, `entity_links`, derived artifacts | Exact input-unit closure registered before persistence; encrypted content or safe structural refs only. Usage remains non-evidence but remains subject to privacy/erasure. No unregistered plaintext worker cache. |
| Logs, diagnostics, exceptions, telemetry, crash/core dumps and debugging traces | Opaque event/error codes only; no payload repr, keys or private authorization explanations. If private diagnostics are indispensable they are registered encrypted artifacts, not ordinary logs. |
| Exports, replication streams, database backups, VM/filesystem snapshots and archived builds/data fixtures | Managed copies preserve sealed form and participate in inventory/barriers. No hidden decryption-on-export path or managed plaintext spool. A permitted client can retain plaintext already handed to it outside this boundary; disclose that limit and never count its copies as erased. This exception permits no durable plaintext write by Nyx and adds no export command or entitlement. |
| Replay capsules, pruning proofs, attestation objects and signed requests/completions | Retain public structure, original commitments/signatures and safe selectors only; no private copied value/map key or plaintext-hash replacement commitment. Original signatures are checked against their own retained public messages. |
| DEKs, wrapped DEKs, KEKs/master keys, key-service replicas, backups, escrow and recovery shares | Register every recovery path. Destroy all recoverable unit keys/wrappers/versions; a backup wrapper decryptable with a retained KEK invalidates completion. Keys never enter truth-ledger backups. Provider tombstones/receipts must survive restore. |
| Swap/pagefiles, hibernation images, process/VM snapshots and temporary plaintext buffers | Deployment must prevent recoverable plaintext persistence or protect it under independently erasable ephemeral keys with no retained recovery route. A language-level object deletion is not a memory/swap erasure guarantee. |

Key custody is the explicit secret-storage exception: the service must protect
its own persistent key material with a verified destruction/recovery mechanism,
not write raw DEKs to a file and rely on ordinary file deletion. Destroying one
unit must not require loss of unrelated units or be reversible through a master
key, escrow share or restored backup. No cryptographic completion claim is valid
until that provider and the host persistence configuration meet these obligations.
An adversary/client that already copied plaintext or keys outside managed scope
cannot be forced to forget them; this is an explicit threat-model limit.

Complete inventories and dependency registrations must be durable before any
private derivative is persisted, and erasure barriers must block in-flight writers
as well as readers. A new private representation may not be introduced without
adding it to the closure inventory and its crash/restore acceptance checks.

The closure includes all projector versions' `resolved_beliefs`, `projected_*`
tables, `committed_nodes`, historical roots, stored lineage records, source/text
indexes, embeddings, process traces, serialized snapshots, temporary/spill files,
WALs, replicas, managed exports/backups and caches. Clear structural headers may
remain; private inline values, identity-record keys and duplicate dependencies
may not. Enumerate retained *historical* nodes too, not just nodes reachable from
the current root. Replacing a current root does not erase old immutable leaves.

Purge or protect a shared derived object if any erased input can be recovered from
it. If it also contains unrelated surviving information, invalidate the whole
derived object and rebuild a new protected object from surviving inputs. Original
independent evidence remains intact. Do not reuse its old key or retain a wrapper
through which an erased copy can be recovered. No content-equality deduplication
may silently combine independent original erasure units.

For legacy plaintext databases, row deletion, `VACUUM` or checkpointing alone is
not a crypto-shredding guarantee: old pages, WALs, snapshots and storage history
may retain the bytes. Conversion must inventory managed copies, import into an
encrypted fresh store, validate capsules/roots, and retire every managed plaintext
copy using a storage-level sanitization process appropriate to that medium. If
that cannot be established, report legacy erasure incomplete and do not append
completion. No claim is made that a new encryption key erases already-written
plaintext or uncontrolled copies. No such destructive conversion is executed by
the acceptance of this document alone; it is a separately authorized operation.

New-format immutable ciphertext nodes need not be physically deleted to erase
their plaintext. Legacy private node bodies and inline lineage serializations do.
Retain only nonsecret descriptors, original hashes and authenticated pruning
records, and publish new effective roots. The erasure sweep is authorized pruning,
not a general candidate-retention or coalescing policy. Cost may be proportional
to the full dependent history; ADR 0025's bounded-write claim does not make erasure
O(log n). Completion includes every registered store, not just the main database.

### 10. Exact supersessions and limits

| Earlier ADR | Effect upon acceptance of this draft |
|---|---|
| [0002](0002-payload-stored-plaintext-in-v0.md) | Continue the end of the plaintext exception already required by revised ADR 0027 for protected writes. Preserve legacy bytes as historical inputs; require explicit protected conversion and cleanup rather than pretending `ciphertext` was already encrypted. |
| [0007](0007-payloads-keyed-by-event-id-not-payload-hash.md) | Preserve event-ID identity and independent erasure. Narrow plaintext content-hash lookup: new payload hashes bind sealed bodies, so hash equality is not the corroboration lookup. Bind per-event keys to canonical subject sets; never pool keys by content. |
| [0014](0014-cross-belief-reducer-and-hash-lineage.md), sections 1, 5–9 | Add typed content unavailability, structural capsules, redaction-set inputs, an erasure read barrier and dual commitment disclosure. Preserve complete affected-set/delta, ancestry, ordinary freshness and atomic publication; historical plaintext completeness after erasure is intentionally impossible. |
| [0025](0025-incremental-result-commitment.md), sections 2–6 | Keep version "2" frozen; reuse revised ADR 0027's protected leaves/opaque keys in version 4 and add original versus effective commitments and authenticated pruning. Supersede unconditional retention of private node bodies and full-content reconstruction after authorized erasure. Incremental storage and complete commitment coverage remain required. |
| Proposed [0027](0027-stage-three-authority-and-acceptance.md), sections 1, 3, 5.1, 6 and 8 | Preserve permanent original signatures, sealed bodies, historical/effective custody and first-write protection. Add projector-4 redacted standing and the erasure overlay; narrow content-dependent historical semantic replay only after authorized destruction. Never replace original signature verification with a capsule. Projector 3 still refuses erased history. |
| Architecture Invariant 8 and sections 5/11 | Make separate key custody/destruction and ADR 0027's independent anti-rollback witness explicit operational-security exceptions, backed by ledger intent and resumable manifest execution. Neither is an alternative source of world-truth semantics. Replace a literal shared entity key with independently erasable event keys and recorded canonical-subject binding. |

### 11. Release gate, audit reconciliation and remaining decisions

Within these Proposed contracts, this section and section 9 are authoritative
for the concrete deployment and erasure obligations; proposed
[ADR 0027 Gate 3](0027-stage-three-authority-and-acceptance.md#gate-3-implementation-and-operational-assurance)
is authoritative for the assurance gate. Evidence that these applicable
obligations are satisfied is consumed under Gate 3 and is what its assurance
verifies. This section must be read with that gate; its evidence and authorization
requirements are not restated here.

The previous draft pair was not safe to ship sequentially: ADR 0027 section 3
required signatures over complete private payloads, section 1 retained plaintext
`nyx-map/1` members, and protection began only in ADR 0028's projector 4. A later
capsule could not preserve those original signatures after erasure. Revised ADR
0027 supplies the permanent public signature and protected storage prerequisites
itself. Its narrowly scoped key/read/custody contract is independently adoptable;
it does not require accepting this draft's destruction capabilities.

The persistence audit found these missing or insufficient enforcement points in
the earlier text; the cited current sections now make the obligations explicit:

| Prior weakness | Reconciliation |
|---|---|
| 0027 sections 1/3 froze full private payload signatures and plaintext trees | Permanent public U/SIG and randomized protected commitments, sealed first writes and protected trees start in revised 0027 sections 1/3/8.1 |
| 0028 sections 1/7 postponed protection to projector 4 | Projector 4 reuses schema-2 sealed bodies and `nyx-map/2`; it adds erasure semantics, not late encryption |
| 0028 section 2 required manifests but did not enumerate the original signed/public versus protected fields | 0027 section 3's explicit inventory governs; private source config, basis details and reasons cannot leak through public envelope fields |
| 0028 sections 3/4 left decrypt scope and post-identity unit selection underspecified | Separate capability checks, immutable original bindings, recorded effective dispositions and prefix-frozen exact manifests in sections 3/3.1/4 |
| 0028 section 8 could be read as replacing a destroyed original signature with a capsule | Explicit prohibition and refusal of incompatible legacy signed-message conversion; original public signatures verify directly |
| 0028 section 9 named SQLite/WAL/spills/backups but did not explicitly bar plaintext authoritative JSONL, ingestion/retry spools or all immutable source paths | Encryption before the first durable write now explicitly covers every authoritative and intermediate path |
| Generic indexes/caches/snapshots/log coverage omitted concrete SQL temp/FTS, swap/hibernation/dumps, in-flight derivative writers and recovery shares | Mandatory location table, registered closure before writes, barriers and restore tests in section 9 |
| 0028 section 9's legacy sanitization obligation did not prevent new plaintext stage-three debt | Independent Stage Three permits only fresh protected writable ledgers; legacy conversion is separate, explicit and incomplete until all managed plaintext copies are addressed |

Two deployment paths remain coherent, conditional on these storage guarantees:

- **Protected Stage Three first:** projector 3/schema 5 already implements sealed
  ingestion, separate key custody, explicit decrypt grants, permanent signatures,
  protected historical trees, deterministic bindings and the independent witness/
  disclosure/restore barrier. Projector 4/schema 6 later adds signed erasure
  requests, destruction execution, typed readers, sweeps and overlay recovery.
  This exposes stage-three functionality earlier but pays key integration
  up front and requires two explicit version cutovers and old-reader refusals.
- **Combined or delayed cutover:** deliver protected Stage Three and erasure in
  one first release. Avoid deploying an intermediate reader/schema, and validate
  identity/erasure interactions together, at the cost of delaying stage three and
  expanding the first release's operational scope. A combined projector/schema
  allocation needs ratification before implementation; no frozen version absorbs it.

Do not ship Stage Three first if any permanent-signature, first-write, custody or
recoverable-copy prerequisite is missing. Version count alone does not choose a
release. The separate path remains the draft's numbered allocation, not a decision
that it must ship first. Neither draft's acceptance is itself a deployment or
legacy-data-destruction authorization.

Remaining decisions/validation gates are explicit:

- General contributor entitlement, multi-user ownership/consent disputes, competing
  administrators and per-user views remain open under ADR 0020. Capabilities do
  not decide who deserves a grant or resolve a contested erasure request.
- Select and validate a concrete key provider and host persistence/recovery
  configuration. Its independently erasable wrappers/replicas/escrow, rollback
  resistance, crash behavior and swap/dump controls must meet section 9 before any
  managed-erasure deployment can claim compliance. This draft specifies the
  requirements, not a verified provider or tested production system.
- Inventory and classify actual legacy datasets, replicas and storage media; choose
  and verify their sanitization/conversion procedure separately. Irrecoverable
  immutable plaintext or a private original signed message may make enrollment
  impossible. Report that limit instead of weakening replay/signature guarantees.
- Ratify release sequencing and any combined version allocation. Broader correction,
  restoration, mention correction and scored matching remain outside these drafts.

## Remaining unresolved questions

The following are **ratification blockers**. The inherited public wire profile,
nonce/AAD classification, independent key lifecycle, manifest-driven execution,
receipt outcomes, restore checkpoint and pending-read boundary are proposed rules
above, not unanswered alternatives.

- **Inherited format completeness:** What final closed S/A/T schemas, private
  value codec, compound-custody representation and checkpoint inventory schemas
  resolve ADR 0027's listed blockers, with interoperability fixtures? This draft
  cannot freeze a different interpretation of that common protocol.
- **Manifest and event schemas:** What complete canonical schemas govern the
  manifest's prefix/binding proofs, derivative dependency closure, location/copy
  acknowledgements, execution attempts, credential review and completion records?
  Which selectors, error codes and required evidence distinguish every state in
  section 4.2 without free-text or provider-dependent replay interpretation, and
  how do current executor grants name the frozen request scope after its subject
  identifiers retire without retargeting the original destruction authorization?
- **Legacy capsule sufficiency:** What closed versioned capsule representation
  binds original producer versions, predecessors, output topology, justification
  history and full-log validation attestations without private values, and what
  decidable sufficiency checks require refusal of an incompatible legacy unit?
  How are inherited low-entropy hashes and public topology classified before
  authorizing any legacy enrollment?
- **Authenticated pruning format:** What exact node/proof tags and safe routing
  representation authenticate an erased legacy subtree against its old root
  without retaining private keys or claiming knowledge of its preimage? Section
  7 chooses opaque authorized pruning plus a separate effective root; a tombstone
  that supposedly hashes to the erased leaf is not an alternative. Which
  insufficient-proof cases require refusal?
- **Effective replay and verification result schemas:** What exact canonical
  erasure-overlay members, redaction-set ordering and producer-version references
  make sweep and replay reproduce effective roots, and what typed verification
  result records passed structural checks separately from unavailable legacy
  preimage and semantic checks? Section 7 fixes their meaning but not their
  complete interoperable serialization.
- **Evidence-profile conformance:** Which enrolled provider/witness profiles and
  fixtures establish the meaning and completeness of copy inventories,
  independently erasable recovery handles, signed destruction receipts,
  exceptional lost-evidence states and legacy-media cleanup acknowledgements?
  What negative fixtures prevent a forged, rolled-back or incomplete receipt
  inventory from being reported completed?

**Deployment validation remains outstanding:** can the selected key service,
witness and host prove the claimed boundary under replica loss, offline backups,
pre-erasure restores, paging, hibernation and crash dumps; and which actual legacy
datasets have a demonstrably complete sanitization path? A signed provider receipt
is accountable evidence under that trust model, not mathematical proof that an
unknown copy does not exist. An unavailable copy or unverified recovery path
cannot be presumed destroyed.

**Outside this draft's limited authority model:** who deserves grants in contested
contributor/ownership cases under ADR 0020; which later policies settle general
restoration/correction; and should deployment use the separate allocated cutovers
or ratify a combined allocation? These questions do not confer implicit authority
or postpone the mandatory first-write protection in ADR 0027.

## Ratification-readiness assessment

**Not ready to ratify:** the inherited blockers and the five additional protocol
schema/evidence questions above remain. This revision resolves the execution and
restoration model, but does not claim that unspecified proof objects or provider
profiles are interoperable, implemented or tested. Stage Three can precede this
capability only under ADR 0027's protected-first-write, historical-custody,
independent-key and rollback-resistant disclosure contract. A projector-3 build
that omits those prerequisites must be revised or delayed/combined; version count
does not justify an irreversible plaintext intermediate.

## Acceptance cases

- Verify the original Stage Three public signature before and after erasing its
  private basis and a redaction request's private reason. Both signatures remain
  directly verifiable; content checks become unavailable, never replaced by a
  capsule signature. Refuse erasure enrollment of a legacy signature whose message
  would require keeping the target secret permanently recoverable.
- Merge A+B -> M: an earlier authorized A-unit manifest stays fixed; a later
  retired-A selector resolves to M and reviews M's full scope. Split A -> B+C:
  an unspecified retired-A request refuses; explicit B includes shared/ambiguous
  B/C units only with B-and-C authority. Ordinary association changes no custody.
- An executor with execution capability and no decrypt grant destroys exactly the
  publicly authorized units. A decrypt-only or curator-only actor cannot authorize
  or execute that destruction. Identity publication revokes stale read permits.
- Redact -> split -> merge never recreates plaintext or a decrypting key. Custody
  ambiguity remains explicit; it never supplies a missing claim justification.
- Place canaries in every row of section 9's closure table, including authoritative
  JSONL, SQLite source fields, WAL/temp/FTS, swap/dump test surfaces and wrapped-key
  backups. Test first-write prevention and restoration, not just current-row
  deletion. Any recoverable managed secret prevents successful completion.

- Two content-identical events use separate keys. Erasing one preserves the other's
  payload, identity and support. A multi-subject unit requires approval of its full
  scope; neither a field request nor a later split silently widens destruction.
- No source actor, model, curator capability or unsigned request authorizes erasure.
  Altered scopes/signatures, stale prefixes and ungranted reasons refuse. Replay
  verifies the historical grant even after rotation/revocation. An explicitly
  granted credential fast path records intent before destruction and retains review debt.
- Swap ciphertext, event IDs, ledger IDs or manifests: authenticated/committed
  reads refuse. Missing keys/rows without authorized erasure fail loudly; a key
  outage is not redaction. Neither `None` nor the literal string/object "REDACTED"
  can be mistaken for the typed sentinel.
- Redact content supporting an otherwise retained claim: a necessary failed
  justification demotes to questioned; an independently sufficient surviving
  justification holds. Erasing the claim's own value yields terminal redacted.
  Erasing counterevidence never promotes. Envelope-only justified facts survive.
- Query before and after the erasure time with the same current redaction set:
  neither exposes the old value. Sweep and full replay agree completely on values,
  sentinels, states, paths, effective roots, request references and redaction-set hash.
- New-format roots verify from sealed descriptors after key destruction. Old-format
  roots recompute using authenticated opaque subtree hashes; available-content
  proofs are not claimed for pruned content. An unauthenticated missing node fails.
- Remove a candidate, path or support association while keeping original lineage
  fixed: the effective result/root changes. Unrelated erasures do not change that
  belief's effective commitment. Original roots are never relabeled sentinel roots.
- Corrupt a legacy materialization before capsule creation: full-log validation
  catches it. Remove a capsule or its signed commitment: redacted replay refuses.
  Successful replay labels unavailable historical semantic checks accurately.
- Plant private canaries in current/historical Merkle nodes, full-payload dependency
  copies, identity keys, lineage serializations, snapshots, traces, WAL/spill data
  and managed backups. Completion requires removal or demonstrated cryptographic
  unavailability in every registered store. A forgotten old generation fails the test.
- Crash between every adjacent protocol step, including each replica/key deletion
  and before completion. Startup rolls forward; affected reads never serve secret
  stale copies; no request creates duplicate erasures or acknowledges an incomplete
  sweep. A long-lived plaintext reader must release/revoke before completion.
- Restore an old managed database/key backup after completion: committed requests
  and the key service's non-resurrection state prevent plaintext resurrection. A
  provider permitting rollback of destroyed keys fails deployment acceptance.
- Unredacted projector "0"/"1"/"2"/"3" byte fixtures remain unchanged. Old readers
  touching erased history refuse explicitly; version "4" supplies the new contract.

## Consequences

Erasure becomes a complete protocol spanning authority, payload storage, derived
copies, proof semantics and recovery. It preserves auditable existence and
commitment relationships while deliberately sacrificing erased-content recovery
and retrospective semantic re-verification. The cost is separate key custody,
versioned formats/readers, dependency tracking, potentially full-history sweeps,
and a strict legacy-cleanup boundary. Full privacy cannot be promised for retained
structural metadata, historical unsalted hashes or uncontrolled exported copies.
No redaction implementation or destructive action is authorized by this draft.
