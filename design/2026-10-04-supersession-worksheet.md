# Stage-two supersession decision worksheet

**Status:** Non-authoritative decision worksheet. Every option below remains
unselected. This file supplies neither ratification nor implementation authority.
The maintainer resolves contract choices; implementation and acceptance evidence
follow an accepted contract. No recommendation is presented as decided.

**Source baseline:** `0cdd6bf`, read on 2026-10-04. Style follows
`design/2026-10-03-adr-0031-worksheet.md`. ADR Status and Implementation markers,
including amendments, govern over their decision-time body text.

## Scope and completeness accounting

Subject: a later statement explicitly superseding older ClaimCandidates, while
preserving the event log, candidate histories and fold/replay equivalence.
"Newer" alone supplies no correction target, eligibility, authority, validity
interval or scalar winner. Ordinary stage-two observations remain alternatives.

**Correction implementation is blocked.** ADR 0018 decides explicit targets,
fresh replacement candidates and retention, but not target eligibility. ADR 0023
section 5 refuses every correction under projector "1"; ADR 0025 preserves those
refusals under "2" and freezes "1". No worksheet option changes that boundary.
Backdated meaning remains open under ADR 0005, separately from recording-time
assignment under ADR 0030. A complete future contract must address S1–S10 below
or explicitly keep a case outside its supported domain with a decided refusal.

The downstream labels come from this queue: eTPS `supersession_current` and
contradiction tasks, and status changes in the public ADR corpus. No eTPS files
were inspected, and this worksheet does not supply an eTPS API contract.
"Blocks public status changes" below means interpreting those changes as current
semantic status or supersession inside Nyx. It does not prevent a maintainer from
editing/committing an ADR under the existing authority protocol, or recording
separate literal reports once a report-ingestion contract is accepted.

## Accepted constraints and recorded gaps

| Source | Constraint on any eventual answer |
|---|---|
| `decisions/0005-backdated-corrections-fail-loud-pending-semantics.md:28–61,68–84` | Event time versus validity time is unresolved. Backdated corrections fail loudly before commitment and at replay; silent provenance-only handling and guessed override semantics are excluded. Its Implementation line describes the legacy guard and stage-two blanket refusal. |
| `decisions/0018-correction-supersedes-candidates.md:21–38,44–53` | A correction records a fresh candidate and explicit target IDs, validated against the pre-event snapshot. Retain targets, support and verification histories. No verification transfer; empty targets refuse. An additional alternative is an observation. |
| `decisions/0023-stage-two-contract.md:26–58,78–121` | Exact properties, fresh ordinary candidates, no inferred support attachment, semantic retries; section 5 explicitly defers corrections even with targets. Section 4 is amended by ADR 0030. |
| `decisions/0024-no-authoritative-head.md:29–65,70–76` | Recency never selects a head. Named-candidate reads differ from scalar belief reads. Agreement does not coalesce; multiple-candidate scalar and common-value contracts remain constrained/deferred. Same-event diagnostic/restriction policy is separately deferred. |
| `GAPS.md:570–579,597–603` | Backdated corrections and candidate-target eligibility are open. These entries identify blockers, not defaults. |
| `GAPS.md:710–715`; `decisions/0003-genesis-sentinels-and-hash-material-delimiters.md:39–43,57–62`; `decisions/0030-sole-writer-and-positional-fields.md:85–110` | Idempotency omits event_type. Equal keys with differing semantic contents refuse; accepting both kinds with equal source/time/payload requires a decision. Frozen hash formulas cannot be casually changed. |
| `decisions/0013-cross-belief-identity-semantics.md`, sections 1–5; `decisions/0014-cross-belief-reducer-and-hash-lineage.md`, sections 1, 5–10, amended by ADRs 0015/0025 | Recorded identity scopes, applicability, pre-event validation, complete lineage, deterministic cutoffs, atomic publication and replay remain binding. Merge/split implementation is still outside stage two. |
| `decisions/0015-candidate-scoped-verification.md`, sections 1, 3–6; `decisions/0020-multi-user-authority-undecided.md`, Decision | Standing belongs to candidates; support is not invented or pooled into promotion. Attribution supplies no correction privilege, ownership or source independence. Unspecified restriction/restoration transitions stop dependent work. |
| `decisions/0025-incremental-result-commitment.md:28–43,80–108`; `decisions/0032-explicit-stage-two-projector-selection.md`, Decision | Existing event bytes, identities, refusals and projector semantics stay frozen. New behavior needs explicit version/compatibility authority; no automatic upgrade or projector default. |

## S1. Supported stage and version boundary

**Exact open choice:** where a correction-capable contract can run, and which
accepted refusals/formats it explicitly supersedes. Implementing ADR 0018 alone
does not lift ADR 0023 section 5.

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| Keep corrections deferred | ADRs 0023 §5 and 0025 §1 already require this; it does not satisfy a supersession consumer. | Preserve current append/replay refusals; report unsupported current-resolution requests explicitly. | Explicit and absent targets refuse without changing count/tip; ordinary later observations retain all candidates. |
| Introduce an explicitly selected correction-capable projector, number unselected | ADRs 0014 §10, 0025 §1 and 0032 require version isolation; proposed ADR 0027's future version is not available authority. | Ratify full event/payload/read/schema/lineage contract and its version; register reducer, writer, recovery and verifier dispatch. | Old versions retain refusal and goldens; unknown/omitted selection refuses; new incremental/replay equality at every prefix. |
| Explicitly amend existing stage-two versions | Would require narrow, explicit supersession of ADR 0023 §5 and ADR 0025's frozen-semantics/formats guarantees; currently forbidden. | Record compatibility and historical replay treatment before changing dispatch, schemas or fixtures. | Historical bytes and requested-version behavior follow the ratified boundary; no silent reinterpretation or fallback. |

**Blocker:** eTPS supersession_current: Yes. eTPS correction-aware contradiction:
Yes. Public semantic status replacement: Yes. **Resolver:** maintainer authority
change specifying the supported contract and compatibility. **Decision:** Unselected.

## S2. Correction versus change over time versus additional report

**Missing definition:** what assertion the replacement corrects. Later source
text need not make an earlier source-at-revision report false.

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| Rectify an erroneous claim within the same decided claim scope | ADR 0018 requires explicit targets and a fresh candidate, not replacement by recency; ADR 0024 leaves ordinary reports intact. | Define the correction's claim scope and the evidence establishing error; encode explicit relations and targeted validation. | Incorrect C1 corrected by C2; unrelated C3 survives; same value is not implicit targeting; targets retain original report/source spans. |
| Record a real change with temporal applicability | ADR 0005 leaves validity-time meaning open; ADR 0024 supplies no temporal resolution. This is not authorized by naming a correction. | Ratify validity fields/interval rules, overlap and cutoff semantics, and whether this uses correction or a separately decided operation. | 64GB valid yesterday and 128GB today; overlapping/gapped intervals; out-of-order arrival; historical answers remain reproducible. |
| Preserve independent reports without supersession | ADRs 0023 §2 and 0024 authorize alternatives, not a current winner. Proposed ADR 0031 is not yet implementation authority. | Use accepted ordinary observation behavior; any future report importer preserves artifact/revision scope. | Revision R1 says Proposed and R2 says Accepted; both source reports can remain true; same-revision disagreement is shown separately without winner. |

Pure withdrawal without a replacement is not supplied by ADR 0018's fresh-candidate
contract; it would need its own explicit amendment rather than an empty value
standing in for retraction.

**Blocker:** supersession_current: Yes. Contradiction as simultaneous truth:
Yes; displaying differing recorded values alone does not require this choice.
Public semantic status transition: Yes; historical literal status reporting does
not. **Resolver:** maintainer claim-scope/temporal semantics. **Decision:** Unselected.

## S3. Event time, validity time and backdated/equal-time cases

**Exact open choice:** the meaning of occurred_at and which prior timestamps
constrain a targeted correction. A stage-two candidate collection has no single
head timestamp against which to reuse the legacy predicate.

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| Event time only, explicitly refuse unsupported backdating | ADR 0005 supplies the interim refusal, not a multi-target comparison rule. ADR 0006 compares instants, not strings. | Decide whether comparison is with every target, its supporting event or another explicitly recorded reference, including equality and mixed-date targets; validate before append/replay. | Before/equal/after target; two targets straddling occurred_at; timezone-equivalent spellings; refusal leaves log and publication unchanged. |
| Distinguish correction event time from corrected validity time | Requires resolving ADR 0005's open question; ADRs 0025/0030 prohibit implicit format/time overrides. | Specify versioned validity representation and historical evaluation; retain writer-assigned recorded_at separately. | A correction learned today changes a past applicability interval; recording cutoff before learning excludes it; no envelope mutation or source-date substitution. |
| Explicitly authorize a backdated override within a defined scope | Not current authority: supersede the relevant ADR 0005 refusal with exact semantics; ADR 0024 still prevents unrelated recency/head selection. | Define effective supersession timing and any required permission/evidence, with deterministic handling for multi-target dates. | Late-arriving past correction, mixed targets and reverse arrival order under each decided precondition; old cutoffs preserved; no unrelated candidate promotion. |

**Blocker:** all three semantic consumers: Yes for historical/backdated inputs;
a forward-only slice still needs explicit comparison/equality rules and refusal
domain. **Resolver:** maintainer time contract. **Decision:** Unselected.

## S4. Target eligibility, identity and scope

**Missing definition:** which existing candidates a correction may target.
Source lineage, number, equal value or similar path is not eligibility.

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| Restrict to candidates in the named current subject/property belief | ADRs 0018, 0022 and 0023 constrain explicit IDs and exact pair lookup, but do not select this restriction. | Define and validate membership, property, lifecycle and claim applicability at the locked pre-event snapshot. | Missing/noncandidate/wrong-belief/wrong-property target; historical belief; one valid plus one invalid target rejects the whole event. |
| Permit explicitly justified historical predecessor targets | ADRs 0013–0015 preserve history/applicability but do not implement successor resolution; merge/split remain deferred. | Ratify predecessor/current applicability and successor handling; record complete affected set and any necessary associations. | Unique/multiple/no successor; preserved candidate identity across paths; unresolved applicability refuses; unrelated shared evidence stays unaffected. |
| Permit other explicit claim scopes under a decided relationship | Requires additional eligibility and, where permission is involved, ADR 0020 authority resolution. No cross-subject default exists. | Define admissible relationship evidence, exact target scope and all affected beliefs; validate without trusting a caller's subset. | Cross-subject/property request; same ADR number at different paths; same source and value at different scopes; missing relationship proof refuses. |

All options must specify duplicate targets, fresh replacement IDs, whether
multi-claim corrections are supported, and target-set completeness. Empty targets
already refuse under ADR 0018; selecting a subset is permitted only within the
eventual eligibility contract, never inferred from newest support.

**Blocker:** all three semantic consumers: Yes. **Resolver:** complete candidate-
target contract with no-mutation/refusal fixtures. **Decision:** Unselected.

## S5. Chains, branches and already superseded targets

**Missing definition:** repeated correction of a retained candidate and how
successor relationships compose. Retention does not decide target reusability.

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| Only candidates not already superseded are eligible | ADR 0018 preserves targets but does not select this restriction. ADR 0030 protects exact committed retries. | Define supersession membership and atomic checks; distinguish retry from a distinct second event. | C1→C2→C3; distinct C1→C4 after C1 superseded refuses; identical retry succeeds once; concurrent target use validates at actual prefix. |
| Allow multiple explicit successors of a retained target | ADR 0024 forbids choosing one branch by recency; ADR 0018 requires fresh replacements and preserved history. | Represent branching relations and define current applicability without a preferred successor; retain explaining events. | C1→C2 and C1→C3 remain branches; agreeing successors remain distinct; chained branches; duplicate relation handling. |
| Re-correction requires explicitly targeting all intended live descendants | ADR 0018 explicit targeting and ADR 0014 snapshot validation constrain this; automatic expansion is not already decided. | Define descendant discovery, applicability and completeness; record the chosen complete targets without minting IDs at replay. | Missing descendant, unrelated target, mixed branches and stale prepared target list; no implicit fan-out repair. |

Every variant must decide/self-test self-targets and cycles. A fresh replacement
targeting only existing candidates may establish an acyclic construction, but its
exact representation and validation still belong in the ratified contract.

**Blocker:** supersession_current and correction-aware contradiction: Yes.
Public repeated status revisions: Yes. **Resolver:** lifecycle/composition rule.
**Decision:** Unselected.

## S6. Permission and evidence for a correction

**Missing definition:** what, if any, authorization a correction requires.
actor_id and one operator do not settle who can supersede whose claim.

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| Correction eligibility depends only on explicit claim/evidence scope | ADR 0020 requires an explicit decision if implementation depends on a shared acceptance policy; attribution alone is no permission. | Ratify the bounded acceptance model and evidence predicates; do not create implicit owner privileges. | Same/different actor, known source and forged attribution cannot replace scope/evidence validation; permission-neutral cases explicitly enumerated. |
| Producer may correct a defined subset of its own reports | ADR 0020 says source attribution establishes no ownership; ADR 0018 says lineage does not establish target scope. | Decide principal/producer binding, exact permission scope and historical reproducibility separately from evidence of error. | Same actor without authorization; another actor; changed present-day permissions; replay at old prefix reproduces the recorded authorization. |
| Shared correction requires recorded explicit authorization | ADR 0020 leaves this model open; proposed ADR 0027 is not ratified. | Ratify policy/basis and public versus protected representation before implementing authentication/authorization. | Wrong scope/key/principal, withdrawn grant, evidence without permission and permission without relationship evidence; refusal before append. |

**Blocker:** all three consumers when recording authorized supersession: Yes.
Reading/displaying retained reports grants no correction privilege. **Resolver:**
maintainer participation/authority ruling for this operation. **Decision:** Unselected.

## S7. Replacement standing and support-dependent effects

**Already decided:** ADR 0018 prohibits transferring target verification and
requires the replacement to earn its own standing. Supersession is a relation,
not a new verification label or erasure of the target's earlier standing.

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| Bound the first correction slice to an observed supported claim, with dependent transitions refused | ADR 0001 supplies observed standing; ADRs 0015/0018 prohibit promotion by pooled/target evidence. This bounded slice must be explicitly accepted. | Define admissible observed correction support and explicit refusal domain for dependent approvals/restrictions and other origins. | Verified/questioned targets do not lend standing; correction observation counted once across claims; unsupported origins/dependencies refuse. |
| Include dependent corroboration/restriction effects | ADR 0015 §5 requires actual dependency checks and blocks unspecified demotion/restoration destinations. | Ratify each transition/trigger and gate; publish the complete affected delta and lineage while retaining histories. | Necessary support corrected versus unrelated support; surviving justification; removal never promotes; unknown transition halts before append. |

**Blocker:** supersession_current's applicability logic: target verification must
not be its default. Contradiction that changes standing: Yes. Public status
reports: only if such dependent semantics are required; literal observed reports
do not inherit a decision's institutional authority. **Resolver:** supported
origin/dependency domain, then transition rulings where needed. **Decision:** Unselected.

## S8. Current reads and contradiction meaning

**Missing definition:** whether "current" returns a set of unsuperseded claims,
temporal applicability, or a scalar; and whether differing values are comparable.

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| Return all eligible unsuperseded candidates with relation history | ADR 0024 forbids an authoritative head; ADR 0018 retains superseded targets. | Ratify exact set eligibility, freshness, return shape and named historical reads; derive it from recorded relations at a shared prefix. | One/multiple/no live candidates; branching successors; named old candidate still readable; cutoff before correction includes prior state. |
| Return candidates applicable at a chosen validity instant | ADRs 0005/0024 leave temporal applicability unresolved; requires S2/S3. | Define validity selector separately from recording cutoff, overlaps and unknown applicability. | Two claims true in nonoverlapping intervals; simultaneous incompatible scopes; missing interval; later correction does not rewrite an earlier recording cutoff. |
| Supply a scalar/common-value or conflict-resolution contract | No such new contract is accepted under ADR 0024; agreement and recency are insufficient. | Explicitly decide additional scalar reads and any required narrow supersession, without converting verification into authority. | Agreeing distinct candidates; multiple conflicting survivors; one survivor plus retained targets; refusal/winner behavior only as ratified. |

For contradiction, unselected choices are a descriptive list of differing
comparable reports with no state change, a diagnostic restricted to overlapping
active scopes, or a governed restriction. Each needs exact comparability
(subject/property/revision/validity), equality and evidence-count rules. A
restriction additionally needs S7; ADR 0024 §3 specifically defers same-event
diagnostics/restrictions and permits the record. Tests distinguish same-event
incompatibility, different-revision reports, different validity intervals,
superseded targets, agreement, and source-dependent reports without fake
independence. Changing a candidate's report text is not correction of world truth.

**Blocker:** both named eTPS tasks: Yes for current/contradiction semantics beyond
plain retained-value display. Public semantic status consumers: Yes; two literal
status reports need no winner. **Resolver:** exact read/diagnostic contract.
**Decision:** Unselected.

## S9. Idempotency and operation identity

**Recorded edge:** event_type is absent from the accepted idempotency hash. Its
collision is already refused by full semantic comparison; it is not a silent
equivalent retry anymore.

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| Keep the formula and explicit conflicting-key refusal | ADRs 0003/0030 bind the formula and comparison. A future correction payload may differ through its recorded targets, but this is not a guarantee against every equal-key input. | Specify complete correction semantic fields and persist/reuse the request; retain collision refusal without fabricating IDs/times/config to evade it. | Same source/time/payload but different event_type refuses; changed targets/config refuses; identical committed retry returns original pair after later appends. |
| Ratify a versioned operation discriminator/formula change | Requires explicit hash/schema/compatibility decisions under ADRs 0003/0025; event hash, historical keys and retry lookup cannot be implicitly rewritten. | Define old/new key domains and lookup/verification behavior; preserve historical commitments and explicit selection. | Frozen old keys unchanged; cross-kind inputs distinguished only in the accepted new domain; duplicate/new-domain conflicts, crash retries and mixed-history verification. |

Adding an arbitrary payload discriminator solely to dodge the hash boundary is
not a third already authorized choice. The full correction schema must first be
decided. Fresh semantic IDs are created once for a new operation, never on retry.

**Blocker:** both eTPS write/retry tasks and public correction imports: Yes for a
complete collision/retry contract; changing the formula is not inherently required
if refusal is retained explicitly. **Resolver:** maintainer compatibility ruling
only if broader acceptance is desired. **Decision:** Unselected.

## S10. Durable relations, lineage and recovery representation

**Missing mechanics:** exact correction payload/relation representation, schema
and publication/read contract. The logical retention and replay requirements
are already accepted; physical table names are not decisions supplied here.

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| Derive explicit relations from versioned correction events into indexed relation records | ADRs 0018/0014 require recorded targets, complete delta/lineage and atomic progress; ADR 0025 freezes existing payloads/versions. | Ratify exact new event schema and coverage; implement indexed relation reads, publication, full replay and independent verification. | One/all targets, unrelated beliefs unchanged, corruption/missing relation, crash after append/during publication, progress never ahead of rows; complete equality at every prefix. |
| Embed versioned supersession relation content in candidate collections | Same accepted logical requirements; ADR 0025 commits complete candidate contents and does not authorize altering frozen leaves by implication. | Define exact fields and dependency coverage in the selected new contract; update only affected nodes/headers with canonical set treatment. | Target order permutations preserve bytes; relation/support change alters lineage; retained histories and named reads survive; old fixture bytes unchanged. |

Both need a request-retention and backup/restore contract under ADR 0030: retain
complete semantic IDs, targets, associations and timestamps, publish pending
events before dependent acceptance, and return committed pairs on retries. A
derived index cannot become the sole copy of a supersession fact. Restore tests
must reproduce relations, claim scopes, standing, source and prefix progress.

**Blocker:** all three implemented semantic consumers: Yes. **Resolver:** complete
ratified mechanics followed by test-first implementation. **Decision:** Unselected.

## Downstream dependency accounting and finish condition

| Consumer or activity | Blocking choices | Work that does not imply resolution |
|---|---|---|
| eTPS supersession_current | S1–S6, S8–S10; S7 if standing/dependent approval affects eligibility | Inspect retained candidates and explicitly report unsupported correction/current selection. No latest-event fallback. |
| eTPS contradiction | S2/S3/S8 for comparability and temporal meaning; S1/S4–S6/S9/S10 if correction-aware; S7 if changing standing | Show named reports and provenance with their distinct scopes; this is not a ratified contradiction diagnostic or state transition. |
| Public ADR status replacement/current interpretation | S1–S6, S8–S10; S7 for additional verification effects | Maintainer authority edits remain governed by AGENTS.md. Historical literal source reports may coexist once their separate importer contract is accepted; report scope does not prove institutional status. |
| Renamed ADR path or recycled ADR number | S4 plus any separately ratified identity-association mechanism | Retain separate path subjects; supersession cannot substitute for identity merge or silently alias numbers. |

**Resolver:** maintainer records explicit ratification, including a bounded refusal
domain and necessary amendments. The agent stages only authorized authority edits
and waits for the maintainer commit/confirmation, then implements the separate B
change. Successful acceptance must show target validity, no silent winner or
verification transfer, unchanged log count/tip on refusal/retry, preserved history,
independent lineage coverage, and incremental/materialized/replay equality at
shared time, cutoff and explicit version. This worksheet chooses none of them.
