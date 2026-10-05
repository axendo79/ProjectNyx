# Valid-time decision worksheet

**Status:** Non-authoritative decision worksheet. Every option below remains
unselected. This file supplies neither ratification nor implementation authority.
The maintainer resolves contract choices; implementation and acceptance evidence
follow an accepted contract. Recommendations recorded from review appear only in
the final advisory section and are not decisions.

**Source baseline:** `1578e86`, read on 2026-10-05. Companion to
`design/2026-10-04-supersession-worksheet.md`, expanding its S2 option 2 (real
change with temporal applicability), S3 option 2 (correction event time distinct
from corrected validity time) and S8 option 2 (candidates applicable at a chosen
validity instant). ADR Status and Implementation markers, including amendments,
govern over their decision-time body text.

## Two questions kept separate

- **Q-said:** what an identified artifact, at an identified revision or
  observation context, stated. ADR 0031 answers this today for the three ADR
  literal properties.
- **Q-applied:** what applied in the modelled world at valid instant T, using only
  information recorded through knowledge cutoff K. No accepted contract answers it.

Validity fields alone do not convert a Q-said answer into a Q-applied answer.
"File F at revision R2 states Status: Accepted" does not establish when, or
whether, the decision became effective. That needs a defined source/authority rule
(V1). Newest revision, import time, commit date and recording order are not that
rule by default, and no option below may adopt one of them implicitly.

## Scope and completeness accounting

Subject: representing when a claim applies, separately from when Nyx learned it,
while preserving the event log, frozen projector behavior, candidate histories,
fold/replay equivalence and ADR 0024's refusal of an authoritative head.

**What the correction-only slice does not deliver.** Supersession worksheet S2
option 1 (rectifying an erroneous claim within its exact scope) can be specified
without any choice below. It repairs bad records. It does not answer "what applies
now", "what applied then", or "what was learned later about an earlier period",
and it must not be presented as delivering current state.

**eTPS evidence status.** The public eTPS measurement contract
(`docs/v0.2/MEASUREMENT_CONTRACT.md` §3, draft) separates valid time from the order
in which a system learns facts. It specifies benchmark state, system-agnostically;
it does not prescribe Nyx's storage representation. The `supersession_current`
task contents are in the private corpus and were not inspected. Whether run 9
requires native Nyx validity intervals is therefore not established here.

A complete future contract must address V1–V10 below or explicitly keep a case
outside its supported domain with a decided refusal.

## Accepted constraints and recorded gaps

| Source | Constraint on any eventual answer |
|---|---|
| `decisions/0005-backdated-corrections-fail-loud-pending-semantics.md:28–61,86–95,104–107` | Whether occurred_at on a correction is event time or validity time is open. Backdated corrections refuse before append and at replay. Its Consequences anticipate deleting the raise, call sites and test in one change when decided; frozen projector guarantees (below) now constrain that deletion. |
| `decisions/0006-occurred-at-comparison-is-instant-based-not-lexical.md:46–60` | Compare instants, never strings. Stored spellings are never rewritten. Offset-less timestamps refuse rather than being assumed UTC. |
| `decisions/0010-projection-parameters.md:53–80` | as_of bounds recorded_at inclusively. Equal recorded_at values follow sequence/hash-chain order. Bounding on occurred_at was rejected because occurred_at is payload content a later correction may restate. |
| `decisions/0030-sole-writer-and-positional-fields.md:65–74,124–150` | The writer owns recorded_at, assigned monotonically nondecreasing with bounded clamping; equal recorded_at values are possible. occurred_at is a semantic field supplied with the submission. |
| `decisions/0018-correction-supersedes-candidates.md:21–38` | Explicit targets, fresh replacement, retained history, no verification transfer. An additional alternative is an observation, not a correction. |
| `decisions/0023-stage-two-contract.md:112–121`; `decisions/0025-incremental-result-commitment.md:28–43`; `decisions/0032-explicit-stage-two-projector-selection.md`, Decision | Corrections stay refused under "1"/"2". Existing projector bytes and semantics are frozen. New behavior needs an explicitly selected version; no default or automatic upgrade. |
| `decisions/0024-no-authoritative-head.md`, sections 1–3 | Recency never selects a head. Agreement does not coalesce. Scalar and common-value contracts remain deferred. |
| `decisions/0031-source-report-claims.md:33–35,45–73,612–620` | Report claims assert what an artifact stated, not the embedded world claim. For imported reports, occurred_at is the import time; source dates are kept separately in `source.config.source_dates` and are not recorded_at. A later contradictory report is another candidate, not a correction or temporal resolution. |
| `decisions/0031-source-report-claims.md:75–87` | A distinct reported-content origin is the recorded target, with every detail undecided. Option-(a) observations about what an artifact said remain valid. |
| `decisions/0020-multi-user-authority-undecided.md`, Decision; Proposed ADR 0027 | No accepted authority or acceptance model exists. Attribution supplies no privilege. |
| `GAPS.md:657–665` | Backdated-correction semantics are open; the raise is greppable by design. |

**occurred_at has no single existing meaning.** For imported reports it is the
import time (ADR 0031 ratification; `src/nyx/report_importer.py:214`). For ordinary
stage-two observations it is caller-supplied, and ADR 0005 leaves its meaning on a
correction open. "Preserve existing occurred_at semantics" therefore means
preserving each event class's recorded bytes and behavior, not one shared meaning.

### Observed shipped behavior (code facts, not authority)

| Location | Observation relevant to compatibility |
|---|---|
| `src/nyx/projection.py:286–299` | `project_snapshot` skips events after the as_of cutoff but continues iterating the verified log. |
| `src/nyx/integrity.py:60–66,124–139` | `verified_log` validates each event as it is iterated: envelope schema_version must equal the shipped value, and event_type must be in a fixed allowlist. Unknown types raise `NotImplementedError`. |
| `src/nyx/projection.py:120` | The projector-"0" backdating guard refuses only a strictly earlier instant; equal instants pass. |
| ADR 0031 source.config `extractor` (`decisions/0031-source-report-claims.md:336,365`) | Each import event records its extractor identity (`nyx.adr-literal/1`) separately from the vocabulary hash. |

## Worked examples

Examples come before field names. Notation: K is a knowledge cutoff and T a valid
instant. Intervals are written "from start to end" only for readability; the
boundary rule is itself V2. All times are UTC instants.

**E1. Open-ended value, then a later value.** c-A "64 GB", valid from 2026-01-01,
end unstated, recorded at K1 = 2026-02-01. c-B "128 GB", valid from 2026-06-01, end
unstated, recorded at K2 = 2026-07-02.

| Query | Expected answer by option |
|---|---|
| T 2026-03-01, K2 | {c-A} under every option. |
| T 2026-07-01, K1 | {c-A}: c-B was not yet known. |
| T 2026-07-01, K2 | {c-A, c-B} ambiguous if new candidates never alter others (V6a); {c-B} only if an explicit closure of c-A was recorded (V6b); {c-B} by "a later start closes an earlier open interval" is recency selection, excluded by ADR 0024 unless explicitly ratified (V6c). |

**E2. Late-learned fact about an earlier interval.** At K3 = 2026-09-01, c-C "96 GB"
is recorded as valid from 2026-03-01 to 2026-06-01.

| Query | Expected answer by option |
|---|---|
| T 2026-03-15, K2 | {c-A}, reproduced exactly; later knowledge never rewrites an earlier cutoff. |
| T 2026-03-15, K3 | {c-A, c-C} ambiguous unless c-C was recorded as a targeted applicability revision of c-A for that interval (V6b), then {c-C} with c-A retained and readable by name. |

c-C's event happened after c-A's, so event time is not violated; only its valid
interval is earlier. This is the case V8 must distinguish from E3.

**E3. Event-time violation.** A correction with occurred_at 2026-01-15 targets c-B,
whose recording event occurred 2026-07-02. Refused under the supersession
worksheet's recommended S3 rule, whatever validity fields it carries.

**E4. Boundary instant.** c-X valid 2026-01-01 to 2026-06-01; c-Y valid from
2026-06-01. At T = 2026-06-01: half-open gives {c-Y}; closed gives {c-X, c-Y},
ambiguous. `2026-06-01T00:00:00Z` and `2026-05-31T20:00:00-04:00` are the same
instant (ADR 0006) and must give the same answer.

**E5. Gap.** c-X valid 2026-01-01 to 2026-03-01; c-Y valid from 2026-04-01. At
T = 2026-03-15 no candidate applies. That answer must be distinguishable from "no
information about this belief" and from "candidates exist with unknown validity".

**E6. Existing claim with no validity.** A projector-"2" candidate c-U "64 GB"
recorded before any validity contract. At any T: under unknown-validity
disclosure, c-U appears in a separate unknown-validity section, neither applicable
nor discarded. Under valid-from-recorded, c-U appears applicable from its
recorded_at onward.

**E7. Report claims.** Two ADR 0031 reports for one ADR path: revision R1 states
"Proposed", revision R2 states "Accepted —", both imported 2026-10-04.

| Query | Expected answer |
|---|---|
| Q-said: what did R1 state? | "Proposed". Unchanged from today's reader. |
| Q-said: what does R2 state? | "Accepted —". Neither report is erroneous. |
| Q-applied: the decision's status at 2026-10-03T12:00Z | No applicable candidate from these reports alone; reports may be shown as related evidence. A V1 authority rule is required for any other answer. Import time and `source_dates` are not validity. |

A report about an immutable revision does not change over time. Whether such a
claim has "unknown" validity or a distinct "revision-scoped / not applicable"
status is V3.

**E8. Overlapping incompatible claims.** c-P "64" valid from 2026-01-01 (source
s1); c-Q "128" valid from 2026-03-01 (source s2). At T = 2026-04-01: ambiguity
{c-P, c-Q}, no winner, unless an explicit authority rule applies (V5).

**E9. Overlapping agreeing claims.** Two distinct "64" candidates with overlapping
intervals: both returned, not coalesced (ADR 0024).

**E10. Knowledge-cutoff ties.** Two events share a clamped recorded_at (ADR 0030
section 4). An as_of equal to it includes both (ADR 0010); a position cutoff
between them includes only the first. V7 decides which the read contract exposes.

**E11. Mis-extraction correction, no validity involved.** Extractor
`nyx.adr-literal/1` recorded a wrong literal from R1. An admitted later extractor
version reads the correct literal from the same repository, path, revision, blob,
property and source location. A correction targets the wrong candidate within that
exact scope; Q-said for R1 now shows the corrected candidate, with the original
retained by name. A later revision stating something different is E7, not this.

**E12. Store compatibility.** A working copy of the 67-event projector-"2" store
receives a new-contract event at position 68.

| Reader | Expected behavior to be decided and tested |
|---|---|
| Unchanged "2", as_of before event 68 | Works only if event 68 passes frozen validation. A new event_type or envelope schema_version makes the whole read raise, because validation continues past the cutoff. A reused type with new payload fields depends on frozen payload validation and is untested. |
| Unchanged "2", full replay through 68 | Refuses under ADR 0023 section 5 if event 68 is a correction. |
| New projector, positions 1–67 | Reproduces existing candidate, mention and subject identities without reminting. |

**E13. Retry after later events.** Temporal update U1 commits; U2 later changes the
same candidate's applicability. An identical retry of U1 returns U1's committed
pair without re-testing eligibility against the post-U2 state.

## V1. Authority: what turns a report into applied state

**Exact open choice:** whether and how a Q-said answer may contribute to a
Q-applied answer.

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| Report claims never enter Q-applied applicable sets | ADR 0031 section 1 scopes reports to artifact statements; ADR 0024 supplies no head. | Q-applied reads only claims that themselves assert a proposition with validity; reports may be listed as related evidence with no applicability. | E7 returns no applicable candidate; Q-said reads unchanged. |
| A ratified per-vocabulary applicability rule | ADR 0020 leaves the declaring authority open; Proposed ADR 0027 is not authority. | Ratify who may declare the rule, the exact source scope, how validity is derived, and refusal outside the rule. | E7 under the rule; revisions outside the declared scope refuse; changing the rule does not rewrite historical answers at older cutoffs. |
| Attestation recorded as a report, authority decided separately | ADR 0031 section 2: an observation of what an artifact said remains an observation. A human source alone does not require a new origin. | Capture the attestation as an artifact with a report property; decide separately whether any attestation is authority for Q-applied. | "P attested X from T" is answerable as Q-said without changing Q-applied until the authority decision exists. |

**Blocker:** public ADR effective status: Yes. eTPS: only if its tasks require
report-derived state. **Resolver:** maintainer authority ruling. **Decision:** Unselected.

## V2. Interval representation and boundaries

**Exact open choice:** interval shape, open ends and precision.

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| Half-open: start included, end excluded | ADR 0006 instant comparison. | Define open start, open end, and refusal of empty or inverted intervals. | E4; start equals end; end before start; equivalent spellings. |
| Closed: start and end both included | Same. | Define adjacency handling (E4 overlaps at the boundary). | E4 ambiguity; adjacent intervals. |
| Start-only, with ends expressed only by later explicit events | Same; interacts with V6. | Define how an end is recorded and retained. | E1 under each V6 option. |

All options must decide precision. ADR 0006 refuses offset-less timestamps, so
"since June" or date-only values either require full instants or a separately
ratified precision representation. **Blocker:** every Q-applied consumer.
**Decision:** Unselected.

## V3. Unknown and not-applicable validity

**Exact open choice:** how Q-applied treats candidates with no validity, including
all existing events, whose bytes cannot change.

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| Unknown validity, disclosed separately | Frozen bytes; classification only by the new projector's rule. | Return shape with a distinct unknown-validity section; never silently dropped. | E6; E5 versus E6 distinguishable. |
| Valid from recorded_at (or from occurred_at) | ADR 0031 sets report occurred_at to import time, which says nothing about when a condition applied; ADR 0010 separates recording from fact time. | Explicit inference rule per event class. | E6 under the rule; E7 must not acquire import-time validity. |
| Revision-scoped / not applicable for report claims | ADR 0031 section 1. | Separate category for claims about immutable artifacts; Q-applied excludes them except under V1. | E7; mixed belief containing both kinds. |

Also decide whether a later event may assign validity to an existing
unknown-validity candidate, and if so through which V6 operation. **Blocker:** every
Q-applied consumer. **Decision:** Unselected.

## V4. Gaps, open ends and empty answers

**Exact open choice:** which distinct empty or partial answers the read contract
reports. Candidates: no candidate applies at T (E5); candidates exist only with
unknown validity (E6); no information about the belief; T or K before any
recorded knowledge (compare ADR 0010's empty view before genesis). Each must be
distinguishable in the return shape, or explicitly collapsed by decision.
**Decision:** Unselected.

## V5. Overlaps and comparability

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| Overlapping incompatible claims return an ambiguity set | ADR 0024 sections 1 and 3. | Define incompatibility (literal inequality, value shape, units) and same-source versus different-source overlap. | E8; E9; a source overlapping itself. |
| An explicit authority rule resolves defined overlaps | Requires V1-style authority; ADR 0020. | Ratify the rule and its scope; record what it overrode. | E8 under the rule; overlaps outside it remain ambiguous. |

**Decision:** Unselected.

## V6. Correction versus temporal update versus retrospective change

**Missing definition:** three operations that must not be conflated.

- **Correction:** the record was wrong (E11; supersession worksheet S2 option 1).
- **Temporal update:** the world changed; a new candidate with its own interval (E1).
- **Retrospective applicability change:** a late-learned fact about an earlier
  interval (E2).

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| (a) New candidates never alter others' applicability | ADR 0024; ADR 0018 (alternatives are observations). | Overlaps remain ambiguity (V5) permanently. | E1 and E2 ambiguous at K2/K3. |
| (b) Explicit targeted applicability revision | ADR 0018 explicit targets; all of supersession S1–S10 apply if expressed as a correction. | Name targets and the revised interval; retain the original candidate and interval. | E1 and E2 resolved only by explicit events; E13 retry. |
| (c) A later start implicitly closes an earlier open interval | Recency selection; excluded by ADR 0024 without explicit amendment. | Would require that amendment. | E1 at K2 returns {c-B} without any targeting event. |

**Blocker:** eTPS-style "current" and "historical" answers. **Decision:** Unselected.

## V7. Knowledge cutoff

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| as_of over recorded_at, inclusive | ADR 0010 section 1; ADR 0030 clamping. | Reuse existing semantics; ties included together. | E10; E1 at K1 versus K2. |
| Log position | ADR 0014/0025 progress positions. | Expose position cutoffs on Q-applied reads. | E10 split between tied events. |
| Both, with one defined as primary | Both of the above. | Define their relationship and refusal for inconsistent pairs. | Same (T, K) gives the same answer forever. |

**Decision:** Unselected.

## V8. Narrow resolution of ADR 0005

**Exact open choice:** how the new contract treats ADR 0005, distinguishing E2
(late-learned earlier interval) from E3 (event-time violation).

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| For the new projector only, supersede ADR 0005's refusal for events carrying explicit validity; keep the event-time check | ADR 0025/0032 freeze "0"/"1"/"2". ADR 0005's anticipated deletion of all raise sites must be explicitly superseded. | Retain `BackdatedCorrectionError` and its tests for frozen projectors; new projector refuses E3 and accepts E2 per V6. | E2 accepted; E3 refused; projector-"0" fixtures unchanged. |
| Keep ADR 0005's refusal in the new projector, forward validity only | ADR 0005 interim stance. | Define "forward" against event time; refuse earlier valid starts. | E1 and E2 refuse before append, since every valid start in them precedes its recording event (c-A 2026-01-01 vs 2026-02-01; c-B 2026-06-01 vs 2026-07-02); E1 restated with each valid start equal to its recording event is accepted. Any narrower scope for this restriction (particular event classes) needs its own ruling. |
| Resolve ADR 0005's A/B question generally | Changes frozen projector semantics; forbidden by ADR 0025/0032 without explicit amendment. | Would require that amendment and historical replay treatment. | Not available under current authority. |

**Decision:** Unselected.

## V9. Event representation and store compatibility

**Exact open choice:** how validity is carried in events, and how existing stores
transition.

| Unselected option | Accepted constraints | Required implementation | Acceptance tests |
|---|---|---|---|
| New event type(s) | Frozen readers refuse unknown types for the whole log (code fact above). Idempotency omits event_type (supersession worksheet S9). | Register types for the new projector only; decide unchanged-reader behavior explicitly. | E12 rows 1–3; equal source/time/payload collision across types refuses. |
| Existing types with new payload fields | Frozen payload validation behavior is untested; ADR 0025 freezes existing payload contracts. | Prove frozen-reader behavior by test before relying on it. | E12 row 1 under frozen code; old fixtures byte-identical. |
| New envelope schema version | Frozen readers refuse any other schema_version. | Schema/compatibility ADR. | E12 under frozen readers. |

**Store transition**, for any option: whether new-contract events go only into a
working copy; replay equality of the existing prefix under the new projector
before the first new append; tested backup and restore; which copy becomes
authoritative afterward so two writable stores do not diverge; and how projector-"2"
events are interpreted by the new projector without reimport or reminted
identities. **Decision:** Unselected.

## V10. Q-applied read contract

**Exact open choice:** return shape. At minimum, to be decided: the applicable set
at (T, K); the unknown-validity set (V3); distinct empty answers (V4); provenance,
standing and relations per candidate; named reads of retained or superseded
candidates; no scalar or winner unless separately ratified (ADR 0024). Q-said reads
remain available unchanged. **Decision:** Unselected.

## Inputs recorded for the supersession worksheet

These came out of the 2026-10-05 review. They refine supersession worksheet items
and select nothing.

- **Exact report claim scope (S2/S4).** Subject/property alone is insufficient: R1
  and R2 reports share one belief, because the revision lives in source provenance.
  Candidate scope components already recorded per event: repository, exact path,
  revision, blob, property and source location.
- **Correction evidence (S2).** The extractor is deterministic over pinned blob
  bytes, so rerunning the same version is not evidence. An extractor fix can keep
  the vocabulary's meaning and needs only identifiable, reproducible extraction
  evidence plus explicit admission; a change of meaning, scope or value
  constraints is a vocabulary version (ADR 0031 section 4).
- **Human attestation.** Not a new origin merely because a human supplied it
  (ADR 0031 section 2); treating it as authority is a separate decision (V1).
- **S6** remains pending the maintainer's explicit ruling.

## Downstream dependency accounting

| Consumer or activity | Blocking choices | Work that does not imply resolution |
|---|---|---|
| Correction-only slice (bad records) | None here; supersession worksheet S1–S10 | Delivers no current or historical state. |
| eTPS supersession_current / historical | V2–V8, V10 if native Nyx validity is required (not established) | The bridge may continue on projector "0" with its documented limits. |
| Public ADR effective status | V1 first, then V2–V10 | Q-said reports of every revision remain readable with no winner. |
| Existing store D:/nyx-data/adr.sqlite | V9 store transition | The original and its backup remain the projector-"2" reference. |

## Advisory recommendations recorded in review (not decisions)

Positions offered during the 2026-10-05 review, recorded so the maintainer can rule
on them. None is selected.

- Settle valid-time semantics before building the correction-only slice if
  temporal state is the intended deliverable.
- Keep the new explicitly selected projector, frozen old behavior, exact retry
  recognition before eligibility, retained history, and independently verified
  relations.
- V3: explicit unknown validity for existing claims, disclosed separately; do not
  infer valid-from-recorded.
- V5: return ambiguity for overlapping incompatible claims unless an explicit
  authority rule resolves them.
- V8: resolve ADR 0005 narrowly for the new projector, distinguishing E2 from E3,
  keeping frozen guards.
- V9: use a separate working copy first; require prefix replay equality and a tested
  backup/restore before new event kinds; name the authoritative copy afterward.
- V1: keep report history separate from any effective-status interpretation.

**Resolver:** the maintainer records explicit ratification, including a bounded
refusal domain and necessary amendments (at least ADR 0005 for the new projector).
The agent stages only authorized authority edits and waits for the maintainer
commit, then implements the separate (B) change test-first. This worksheet chooses
none of them.
