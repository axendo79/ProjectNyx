# Bridge feedback for Nyx

**Input for discussion — not a decision.**

Date: 2026-10-15. This document records capabilities implemented by nyx-bridge
outside Nyx and options for future ADR discussions. Recommendations below are
proposals for discussion only. They accept no ADR, close no gap, authorize no
implementation, and supply no missing defaults.

## Evidence and authority boundary

Nyx authority was read from `origin/main` at
`31f93bb93b6748e4e3f619c0fb0f70d7599f6929`, using
`git -C D:\ProjectNyx show origin/main:<path>`. The README shipped-state overview
and decision-to-code map, applicable ADR chains and GAPS entries were read before
the relevant specification mechanics. Later accepted amendments and each ADR's
Status and Implementation markers govern historical body text.

Bridge source coordinates below are relative to `D:\nyx-bridge-wt-v2`, clean at
`0fe99625b4694efd0144a1922f7fe4f65269b4af`. They identify that revision, not future
line numbers. Both v1 and v2 code, `BRIDGE_V2.md`, the compact renderer, operation
contract and shared path guard were inspected. Bridge v1 remains the default;
v2 is an explicit treatment requiring `nyx3` and projector `"3"`.

The private evidence source is
`D:\eTPS-private\runs\run11-launch-006-diagnosis.md`, read for findings only.
The following are abstract paraphrases, with no corpus text, private task facts,
message identifiers, questions, expected answers or extraction examples:

- **D1 — Capture and rendering:** stored source hashes and candidate support
  survived, but the earlier answer injection omitted establishing public source
  IDs, ordering, supporting events and ending evidence. A hash-to-public-ID join
  required an external journal. The diagnosis did not demonstrate a projector-3
  inability to retain history or provenance.
- **D2 — Extraction contract:** key drift and type-invalid operation output lost
  updates or weakened transition chains. Complete, parseable output still failed
  the typed contract. No extraction cap exhaustion or extraction timeout was
  demonstrated. Whole-batch validation and visible rejection were recommended.
- **D3 — Checkpoints:** a question about a recorded public-message prefix could
  use a message-to-log-position binding. This requires neither general world
  valid-time semantics nor selecting a newest candidate as truth.
- **D4 — Context and accounting:** a required memory injection could be refused
  before answer dispatch. Extraction had already occurred, while reply-dependent
  telemetry hid some of its accounting. Other provenance failures occurred with
  complete injections delivered, so context loss does not explain every failure.

The additional source-only audit records are
`D:\eTPSDotty\2026-10-15-nyx-bridge-pr1-2687f51-audit.md` (**A1**) and
`D:\eTPSDotty\2026-10-15-nyx-bridge-pr1-0fe9962-audit.md` (**A2**), with their
request files. A1 identified uncertain post-commit receipt completion and a
Git-ancestor guard dependent on protected-root membership. A2 closed both
findings by source inspection at the pinned bridge revision. Neither audit
executed tests; reported bridge suite counts are not independent verification.
This feedback likewise inspects bridge code/tests without rerunning the bridge
suite or making model calls. Nyx documentation and test results are recorded
separately in the worktree's local `scratch/EVIDENCE.md`.

The governing accepted boundary includes [ADR 0013](../decisions/0013-cross-belief-identity-semantics.md),
[ADR 0014](../decisions/0014-cross-belief-reducer-and-hash-lineage.md) as amended by
[ADR 0015](../decisions/0015-candidate-scoped-verification.md), and
[ADR 0023](../decisions/0023-stage-two-contract.md), with later projector-3
extensions in [ADR 0034](../decisions/0034-forward-state-transitions.md) and
[ADR 0035](../decisions/0035-adr-0034-implementation-boundaries.md).
The [architecture](../spec/NYX_ARCHITECTURE.md) invariants and sections 1, 8 and 10,
and [implementation companion](../spec/NYX_V0_IMPLEMENTATION.md) sections 4, 6
and 7, remain subject to those accepted amendments.

[Proposed ADR 0036](../decisions/0036-strict-payload-keys.md) and
[Proposed ADR 0037](../decisions/0037-o3-mention-discovery.md) are **unratified,
Implementation: None**. Their shared version/schema bundle is also prospective.
Nothing in this feedback makes a frozen projector strict or installs O3.

## 1. Public message identity, position and source-hash binding

**What the bridge built.** V1 computes an exact UTF-8 content hash and stores it
with extractor metadata (`nyx_bridge/memory.py:31-47`,
`nyx_bridge/memory3.py:47-51`), but deduplicates by content alone
(`nyx_bridge/server.py:214-219`). V2 preflights every delivered user message's
structured public ID and positive integer position, calculates the exact-content
SHA-256, verifies a supplied hash, and rejects identity, ordering and position
conflicts before extraction or ingestion (`nyx_bridge/v2.py:30-81`). Identical
text under distinct delivered IDs remains distinct input. Accepted/empty receipts
are reused on an identical retry (`nyx_bridge/v2.py:149-158`).

Each bootstrap, assertion and transition carries public ID, public position,
content hash, extractor version, operation index and batch hash in `source.config`
(`nyx_bridge/memory_v2.py:76-120`). The producer supplies identity; the model
supplies neither identity nor provenance. The check establishes consistency with
delivered bytes, not authenticity of the producer or truth of an assertion.

**Why it was needed.** D1 and D3 show that retained hashes alone did not expose
the establishing public source or a public checkpoint to the answering model.
Neither a digest nor a candidate's value can recover an omitted public ID.

**Nyx coverage.** [ADR 0030 sections 2-3](../decisions/0030-sole-writer-and-positional-fields.md#2-semantic-and-positional-contents)
already preserve complete caller-owned `source.config` as semantic event contents,
including on retry. ADRs 0014/0015 preserve event provenance and distinct candidate
identity. These provide storage and commitment primitives, but no general public
delivery-ID namespace, order, exact-message-hash admission or delivery receipt
contract. [ADR 0031](../decisions/0031-source-report-claims.md) has a specific
pinned-artifact report contract; its source spans are not a general conversation
protocol. Proposed ADR 0036 addresses raw payload duplicate members and explicitly
does not add exact-text authentication. Proposed ADR 0037 discovers mentions and
associations; it does not establish message identity. Neither covers this missing
delivery contract.

**Options and recommendation.** Keep mechanical capture and conflict validation
in the adapter now, using accepted source retention. A future ADR could define a
shared delivery-binding/checkpoint contract if multiple consumers need native
interoperability; it would need explicit identity, retry, empty/rejected delivery
and reconstruction rules. Treat authentication, speaker authority and world
truth as outside this capability. The recommendation is adapter ownership today,
with native standardization considered only through a separately accepted ADR.

## 2. Whole extraction-operation batch validation and atomic rejection

**What the bridge built.** V2 rejects repeated JSON members and non-JSON numeric
constants, enforces the exact operation schema, permits string assertion values,
and requires JSON null for expiry (`nyx_bridge/contract_v2.py:52-100`). Its
batch validator permits at most one operation per exact subject/property key and
requires a known key with live targets for replace/expire
(`nyx_bridge/contract_v2.py:103-114`). `record_batch` obtains one pre-batch target
map and validates everything before submitting a mention, observation or transition
(`nyx_bridge/memory_v2.py:50-62,76-82`). It chooses every live candidate in sorted
ID order as the transition target set (`nyx_bridge/memory_v2.py:57,102-115`).

Schema/operation failure returns an explicit rejected receipt and HTTP 422,
without answer generation; identical rejected input reuses rejection semantics
(`nyx_bridge/v2.py:75-80,173-177`). Rendering keeps the failure visible
(`nyx_bridge/memory_v2.py:180-185`). Unlike the earlier conversion of malformed
extraction to an empty fact list (`nyx_bridge/server.py:188-197,246`), rejected
input is not reported as successfully remembered.

Atomic rejection here means **no Nyx event from an invalid extracted batch**.
It does not mean no adapter audit write, a transaction over an entire chat
request, or all-or-nothing storage on an unexpected I/O failure. Earlier accepted
messages remain accepted. Valid operations submit independently through Nyx
(`nyx_bridge/memory_v2.py:71-74,81-122`); a later failure can leave a durable prefix.
The preflight relies on the supported fresh, single-process trial boundary;
Nyx still validates each event at its locked append prefix.

**Why it was needed.** D2 identifies actual extraction-contract failures, including
key drift and invalid operation types. Visible whole-batch rejection prevents a
caller from treating a missing update as a complete memory ingestion. Validation
cannot prove that an `add` was semantically the right operation or that empty
extraction omitted nothing.

**Nyx coverage.** ADR 0034 R5 and section 4 already refuse an entire *event* when
any explicit target is invalid. ADRs 0023/0030 govern exact property scope,
fresh IDs and append-time validation. They do not define an extractor language,
one-operation-per-key restriction, delivery receipts or a multi-event extraction
batch. Choosing all live targets is bridge policy; Nyx's event contract permits
an explicitly named eligible target set. Proposed ADR 0036 would cover recursive
duplicate-member refusal in strict Nyx payload text under a new explicit profile.
It would not validate this operation array or make several events atomic, and its
no-side-effect refusal boundary differs from the bridge's rejection journal.
Proposed ADR 0037 supplies no batch-ingestion contract.

**Options and recommendation.** Keep extractor schema, all-live target selection
and batch preflight in the adapter. Add a separate ADR only if Nyx is to expose
a native multi-event batch or durable batch receipt, explicitly deciding commit,
retry, partial failure and replay semantics. Model prompting, semantic key repair
and benchmark-specific extraction rules are outside the kernel capability.
The recommendation is to retain adapter preflight and the existing per-event
kernel checks; the diagnosis does not establish a need for a new storage transaction.

## 3. Poisoning on an uncertain receipt

**What the bridge built.** V1 already marks a trial failed when a memory write
raises (`nyx_bridge/server.py:240-244`). V2 also guards receipt finalization:
read the post-ingestion cutoff, append the result journal entry, flush and fsync,
then publish the reusable in-memory receipt (`nyx_bridge/v2.py:88-101`;
`nyx_bridge/memory_v2.py:35-44`). If the cutoff read or journal completion raises,
the trial is poisoned and that delivery is marked failed. Future chat refuses
before another store read, extraction or write (`nyx_bridge/v2.py:138-146`).
Unexpected ingestion failures preserve the committed prefix and poison the trial
(`nyx_bridge/v2.py:178-184`).

This is a fresh-trial policy, not tail recovery. The journal may be absent,
partial or already written when completion becomes uncertain. Once finalization
has returned normally, a later rendering or reply failure leaves the accepted
receipt reusable (`nyx_bridge/v2.py:152-154,184-198`). Inspected regressions cover
cutoff, write, fsync, postwrite and post-finalization failures
(`tests/test_v2.py:173-253`).

**Why it was needed.** D4 shows that extraction/ingestion can precede a failed
reply, so reply success cannot be the only evidence of processing. The specific
uncertain-receipt duplicate-ingestion defect comes from A1, not the diagnosis:
post-commit finalization could fail before caching a receipt, allowing an identical
public delivery to create more candidates. A2 records the repair's source-level
closure. This is additional failure-boundary evidence, not a new pilot result.

**Nyx coverage.** ADR 0014 section 9 and ADR 0030 sections 1-3 already preserve
committed appends across publication failure and support retry of an exact
retained semantic request without reminting. They do not map one public delivery
to a fully completed sequence of newly prepared events and an external receipt.
A public ID/hash alone is not the retained semantic request for that sequence.
Neither Proposed ADR 0036 nor Proposed ADR 0037 adds those batch receipts or
crash-safe adapter resumption. ADR 0030's automatic recovery of its clock refusal
is a different contract; the bridge's permanent trial latch does not amend it.

**Options and recommendation.** Keep poisoning and fresh-trial refusal in the
adapter for this deployment. A future native recovery ADR would need durable
batch membership, exact retained submissions, receipt authority, commit points
and reconstruction before authorizing resumption. Partial salvage, guessing the
uncommitted tail and changing Nyx's existing recovery are outside scope. The
recommendation is to retain the fail-closed adapter policy; no kernel poisoning
flag or alternative event-retry rule is proposed here.

## 4. Compact live/retained rendering with sources and checkpoints

**What the bridge built.** The earlier projector-3 adapter reduces each candidate
to subject, property, value and a coarse display status
(`nyx_bridge/memory3.py:110-139`). V2 joins public event reads to complete public
live/retained candidate reads, emits candidates in global assertion log order,
and preserves establishing/ending sources, hashes, event positions and exact
ending relations (`nyx_bridge/memory_v2.py:124-179`). Checkpoints include empty
questions and rejected deliveries. A selected delivered position resolves to its
recorded log cutoff; each candidate gets prefix status independently of tip status
(`nyx_bridge/memory_v2.py:131-145,175-185`). Public positions and Nyx positions
differ, including because mention bootstrap consumes events.

The compact serializer emits metadata, a shared source table, checkpoints,
event-to-source bindings, distinct candidate rows and failure rows
(`nyx_bridge/render_v2.py:13-41`). Its inspection parser reconstructs the evidence
shape with per-render candidate/event aliases (`nyx_bridge/render_v2.py:44-70`).
This preserves logical identity relationships, exact strings and full source
hashes; it does not preserve original internal UUID bytes in the prompt. Those
remain in the store/journal. The common legend supplies fixed meanings and
omitted nulls (`nyx_bridge/contract_v2.py:27-43`). Chat injects that complete render
(`nyx_bridge/v2.py:187-194`). No candidate, checkpoint or failure is ranked,
coalesced, selected or truncated. Compact round-trip and prompt-exposure tests
were inspected (`tests/test_v2_compact.py:45-104`), not executed here.

**Why it was needed.** D1/D3 show loss at the capture/render boundary despite
retained supporting evidence and replay agreement. D4 supplies context pressure
as a reason to remove repeated representation. It does not prove that this compact
format fits every budget or improves model accuracy. Repeated values still need
separate candidates and establishing sources.

**Nyx coverage.** ADRs 0015/0023/0024 already preserve distinct candidates without
a scalar winner. ADR 0034 R3/R10 and section 7, bounded by ADR 0035, already expose
live/retained candidates, provenance and ending event/position. Their historical
read contract can describe a recorded log prefix; it does not establish external
world-validity intervals. No accepted contract defines the compact prompt format
or public-message-to-log checkpoint table. Proposed ADR 0037 would make discovery
and same-prefix detail traversal explicit for admitted public corpora; it would
not render prompts, bind public deliveries or supply checkpoints for empty/rejected
input. Proposed ADR 0036 supplies none of those presentation capabilities.

**Options and recommendation.** Keep compact serialization, source legends and
checkpoint assembly in the adapter, consuming the complete accepted reads.
A future ADR could standardize a reusable evidence/checkpoint interface if native
cross-consumer guarantees are required, separately deciding its reconstruction
inputs. Budget pruning, a public answer-status vocabulary, world valid time and
candidate retention are outside this rendering change. The recommendation is
adapter ownership with completeness and alias round-trip checks, not a new reducer.

## 5. Trial-store path guard

**What the bridge built.** The shared guard resolves paths, rejects a Git ancestor
whether `.git` is a directory or worktree pointer, protects imported/pinned source
roots, and follows linked-worktree `gitdir`/`commondir` metadata to protect the
main checkout (`nyx_bridge/store_paths.py:6-49`). Git-ancestor rejection precedes
all artifact-root exceptions. The narrow opt-in for a broad artifact container
does not permit stores under a Git checkout or another protected source root.

Nyx and control-store constructors call the guard before creation
(`nyx_bridge/memory.py:20-26,70-74`); projector-3/v2 inherit the Nyx constructor.
The helper validates before opening its adjacent log
(`nyx_bridge/run_slot.py:36-42`), and v2 requires an absent adjacent audit path
(`nyx_bridge/memory_v2.py:19-28`). Fresh paths and fresh processes isolate trials.
Inspected synthetic regressions cover unrelated Git roots, linked main checkouts
and opt-in refusal (`tests/test_store_paths.py:24-85`;
`tests/test_v2_admission.py:55-72`).

**Why it was needed.** The diagnosis does not establish a path-isolation failure.
Its experiment context explains why artifact isolation matters, but the direct
defect evidence is A1: an unrelated Git tree under external TEMP escaped a
protected-container-dependent check. A2 confirms that the unconditional ancestor
check closes it by source inspection. This distinction avoids attributing a guard
defect to a memory-answer result.

**Nyx coverage.** [ADR 0011](../decisions/0011-database-schema-versioning.md)
requires explicit fresh initialization and schema validation, with schema support
amended through ADRs 0025/0035. ADR 0030 supplies writer exclusion. Neither
prohibits stores in Git trees, pins experiment repository paths, or protects
adapter logs/control files. Proposed ADRs 0036/0037 do not supply that isolation
policy. Their side-effect/migration boundaries are not a filesystem deployment guard.

**Options and recommendation.** Keep this policy in the adapter/harness and share
its guard across every trial artifact creator. A generic Nyx deployment-path ADR
could be discussed only if a broader product requirement emerges. Repository
names, control stores and experiment artifact placement are outside kernel
semantics. The recommendation is adapter ownership; this evidence does not call
for embedding local path pins in Nyx.

## 6. Consumer-side enumeration in place of O3

**What the bridge built.** The legacy adapter reads all public events to discover
belief IDs in first-recorded order, then reads each materialized belief
(`nyx_bridge/memory.py:49-62`). The earlier projector-3 adapter scans the log for
mention labels, beliefs and candidate recording order, then calls the public
candidate-set reader (`nyx_bridge/memory3.py:110-139`). V2 maintains process-local
subject/belief maps during its own writes (`nyx_bridge/memory3.py:18-21`;
`nyx_bridge/memory_v2.py:91-121`), enumerates them for keys/live counts, and scans
public events again for counts and provenance rendering
(`nyx_bridge/memory_v2.py:46-62,142-179`). No bridge SQL or private Nyx API is needed.

This is enumeration of the supported bridge-owned fresh log, not a public generic
subject/mention listing, resumable discovery service or indexed search. Process
maps are not restart recovery. Full log reads and complete candidate injection
remain proportional to retained content; no measured scalability claim follows.

**Why it was needed.** D1/D3 required traversing retained candidates back to
their events and public sources; D2 required exact known keys and live-target
counts before extraction. The diagnosis did not identify an O3 index defect or
measure discovery performance. The reason enumeration lives in the consumer is
the shipped absence of O3, corroborated by the source and gap register.

**Nyx coverage.** Accepted ADRs 0014/0025 supply snapshot and named-record
primitives, with candidate reads under ADRs 0024/0034. The
[GAPS register](../GAPS.md) still marks public listing/search **O3, unbuilt**.
Proposed ADR 0037 directly addresses this missing native discovery surface:
typed subject/mention/property/belief listings, literal exact/prefix mention
search, deterministic pages, unavailable-versus-empty distinction, global
staleness, same-prefix traversal, atomic index publication and replay verification.
Its own ID/text ordering is not the bridge's assertion-log display order.
It excludes values/source free text from the index/pages and does not supply
extractor live-target counts or final model injection. Existing named details and
adapter source joins would still be needed. Proposed ADR 0036 supplies the shared
version/adoption boundary, not discovery on its own.

**Options and recommendation.** Keep current consumer enumeration for the bounded
trial. For a reusable public Nyx discovery surface, recommend progressing the
existing Proposed ADR 0037 and its shared Proposed ADR 0036 bundle through review
and explicit ratification, rather than inventing a parallel listing contract.
A separate ADR would be needed for requirements beyond that proposal; implementation
must wait. Semantic retrieval, ranking, private-corpus admission and budgeted
evidence selection are outside O3. This is the one capability here whose native
discovery portion already has a directly relevant Proposed ADR.

## Boundaries for future discussion

The [GAPS register](../GAPS.md) retains unresolved origin-to-state mappings,
retention/coalescing, usage recording, additional scalar reads and other deferred
semantics. Nothing here fills them. The bridge's observed-origin and uniform
verifiability conventions do not implement the architecture's user-stated split
or establish independent truth. A compact display does not become a verification
signal, an identity resolver or a scalar selector.

Bridge receipts/journals are external process evidence. Empty/rejected deliveries
and public checkpoint mappings are not all reconstructible from Nyx events alone.
Importing that operational state into Nyx would require an explicit commit-point,
authority and replay contract consistent with Constitution invariants 8/9;
the adapter journal is not precedent for a new authoritative kernel store.
[ADR 0026](../decisions/0026-usage-is-not-evidence.md) also supplies no operational
usage recorder and permits no use of exposures or receipts as world evidence.

[ADR 0031 section 7](../decisions/0031-source-report-claims.md#7-corpus-policy-and-derived-copy-inventory)
and the R4 gap retain the public-corpus restriction. Proposed ADR 0037 preserves
it. Permission to inspect private diagnosis findings for this document neither
admits private trial content to a native index nor lifts that restriction.
The document reproduces no such content and designates no store or treatment.

Future native work would need separately accepted authority and acceptance cases.
This feedback changes only discussion material under `design/`.
