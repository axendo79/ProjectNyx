# ProjectNyx review and next-steps architecture

**Status:** Non-authoritative. Intended for `design/`. Supplies no decisions,
defaults or implementation authority; every choice below marked **R#** needs a
maintainer ruling and, where it changes a contract, an ADR.

**Baseline:** `5a37b1e` (2026-09-14, no commits since). Reviewed 2026-09-22.

**Verified at baseline:** 589 passed, 8 skipped on CPython 3.14.4 (skips are
deliberate representation/legacy cases in `test_verify_store.py`).
`scripts/check_docs.py`: 0 failures, 78 unchecked baseline, 96 unchecked in
`design/`. Measurements below come from reproducible probes described in
section 5. These are supplied reviewer evidence, not measurements performed by
the implementation agent. They were run on a Linux container, so absolute times will differ on
the Windows workstation while the growth shapes should hold.

## 1. Summary

The substrate is in better shape than its own status line says. Layer A, the
hash chain, payload verification on read, the snapshot reducer seam, projector
"2"'s incremental commitments and the independent verifier all work, and the
test suite is honest about what it covers. The findings that matter are not in
the kernel's correctness. They are in three places:

1. **Scale was measured along one axis only.** Per-belief lineage was profiled
   thoroughly. Whole-store behaviour was not, and two components are quadratic
   in total event count: projector "1" ingestion and the standalone verifier.
2. **The first real-data slice is blocked by decisions nobody has asked for yet,
   not by 0027/0028.** Every stage-two ClaimCandidate is born `verified`, and
   the only writable origin is `observed`. So ingesting any external document or
   model output today records it as verified world truth. The writer also has no
   concurrency model, which an MCP server immediately needs.
3. **Effort has moved away from the stated priority order.** Stage-three
   authority and crypto-shredding are priority 4 in the Sep 13 ordering. Since
   `abffdcf` they have received 3,220 lines of design text against 59 lines of
   test code. ADR 0027, 0028 and their briefs now total 4,766 lines, exceeding
   all of `src/` at 3,253. The project is not parked because it is blocked. It
   is parked behind a gate it placed in front of a path it does not need to
   take yet.

## 2. Findings

Severity: **High** means it silently produces a wrong result or will block the
next slice. **Medium** means it will bite at realistic scale or under a second
writer. **Low** means hygiene.

### 2.1 Errors

**E1. The standalone verifier has quadratic copying in total events. (Medium, trivial fix)**

`scripts/verify_store.py:497` deep-copies the entire replay record set after
every event inside the published prefix:

```python
if p <= position:
    expected = deepcopy(replay.records)
```

Measured on projector "2" stores:

| Events | Verify time |
|---:|---:|
| 600 | 7.2 s |
| 1,200 | 28.3 s |

Doubling the events quadruples the time. Profiling puts 65% of runtime in
`copy.deepcopy` (24.6M calls at 1,200 events). Extrapolated, 10k events take
about half an hour, and the verifier is supposed to be the routine audit tool.

The fix copies once, at the published position:

```python
if p == position:
    expected = deepcopy(replay.records)
```

This needs a regression test that asserts linear growth, following the pattern
of `probe_lineage_scaling.py`.

**E2. Stage-two defaults point at the quadratic projector. (Medium)**

Several stage-two functions default `projector_version="1"`:
`ingestion.prepare_observation`, `ingestion.submit`,
`storage.materialize_pending`, `storage.rebuild_projection`,
`storage.read_snapshot` and the `read_*` helpers. Under "1", `_read_snapshot`
loads every projected record of every kind on each append and on each
single-event publication step.

Measured ingestion (200 subjects  1 mention + 5 observations, 200-byte values):

| Events | Projector "1" | Projector "2" |
|---:|---:|---:|
| 300 | 15.1 s | 1.8 s |
| 600 | 60.5 s | 4.0 s |
| 900 | 135.5 s | 6.4 s |
| 1,200 | 240.8 s | 8.9 s |

Projector "1" is frozen and correct; it is simply not usable as a real store.
Any caller that omits the argument gets it.

This is **R1**: make `projector_version` required on stage-two entry points
(refuse when absent), or change the default to "2". Requiring it is the safer
reading of the gap protocol, since it picks nothing on the caller's behalf.

**E3. A retained `recorded_at` can make a retry permanently unappendable. (High for any second writer)**

ADR 0023 4 says retries use the writer's retained recorded IDs and submitted
contents. The `ingestion.py` docstring is stricter: it says to retain the
complete Envelope/Payload pair. Both break under a lost race:

- `prev_event_hash` is bound at prepare time, so the retained pair refuses as
  `IntegrityError: event was built against a different append position`.
- If the caller retained a supplied `recorded_at` and the winning writer
  committed a later one, every ADR-compliant retry refuses as
  `BackdatedRecordingError`, forever.

Reproduced at baseline. Two connections prepare observations against the same
tip. The winner commits with `recorded_at` `00:00:02`. The loser's retained pair
carries `00:00:01` and can never append. Re-preparing with the same IDs and
a fresh `recorded_at` succeeds.

ADR 0023 does not say which envelope fields may change when an uncommitted
event is retried. See O1 and **R2**.

**E4. `CLAUDE.md` is stale and states a conflicting authority rule. (Low, but it steers agents)**

- It says the three spec files are "the finished, adversarially-hardened build
  spec", yet ADRs 00270029 are Proposed and 20+ accepted ADRs supersede spec
  text.
- Its build order still marks "Commit 1  scaffold" as "this baseline" and
  "Commit 2  walking skeleton" as next.
- Its conflict rule ("the more specific mechanical statement wins") contradicts
  `AGENTS.md`, where accepted ADRs supersede the spec.

`AGENTS.md` tells agents to ignore `CLAUDE.md`, but an agent that loads
`CLAUDE.md` first may never reach that sentence. The fix is to replace
`CLAUDE.md` with a pointer to `AGENTS.md` plus the one standing rule. The doc
checker could then flag any future authority statement in it.

### 2.2 Omissions

**O1. No writer concurrency model. (High for the next slice)**

Nothing in `spec/`, `decisions/`, `README.md` or `GAPS.md` states whether Nyx
has one writer or many. The code serializes appends with `BEGIN IMMEDIATE`,
but prepare runs outside that lock and stamps `prev_event_hash` and
`recorded_at`. An MCP server running beside a CLI or an ingester is a second
writer.

`recorded_at` also defaults to wall-clock time at prepare. A backwards clock
step makes every append refuse until wall time passes the tip again, with no
diagnostic beyond `BackdatedRecordingError`.

This is **R2**, and it needs an ADR (proposed 0030).

**O2. The source-report / world-fact split is not shipped, and ingestion collapses it. (High)**

`reducer.py:220` and `committed.py` resolve every ClaimCandidate's state
through `projection._state_for_origin`. That maps `observed` to `verified` and
refuses every other origin. `source_class` is an unchecked non-empty string.

The consequence: the only way to write a stage-two claim is as a verified
observation. An ingested ADR saying "status: Accepted", a web page, or an LLM's
answer written through MCP would each be recorded as a verified world claim.
That contradicts rule 2 of the untrusted-source contract (a source's report
establishes what the source reported, not the reported fact) and is the silent
promotion Invariant 3 exists to prevent.

This also answers the open question from Sep 14 ("is rule 2 partly
shipped?"). It is not. Ordinary observations collapse the two.

This is **R3**, and it needs an ADR (proposed 0031) before any non-fixture write.

**O3. No read surface beyond lookup by ID. (High for the next slice)**

The public read contract has no way to list subjects, mentions, properties or
beliefs, and no way to search. An MCP server built on today's surface
would require the model to already know opaque IDs, which makes it unusable.

Any listing or search index is derived state. Under Invariant 8 it must be
rebuildable from Layer A. Under ADR 0028's persistence-closure inventory, a
plaintext index (FTS, embeddings) is a copy of payload content that would
survive a crypto-shred. It must appear in that inventory before the index holds
anything private.

**O4. Store growth under projector "2" is unquantified at store scale. (Medium)**

ADR 0025 acknowledges node retention and defers garbage collection. Measured at
600 events: 21,381 `committed_nodes` rows (about 36 per event), 6.8 MB of node
content, and a 12 MB database file  about 20 KB per event with 200-byte
values.

Linear extrapolation gives about 200 MB at 10k events and about 2 GB at 100k.
That is fine for dogfooding, but it should be a measured, published number with
a threshold, as the lineage deferral was.

**O5. No deletion path exists for anything ingested. (High as a data-handling rule)**

Payloads are plaintext (ADR 0002), and redaction would brick replay (GAPS.md).
Anything private that enters Layer A is permanent and readable by anyone with
the file until 0028 ships and passes Gate 3.

This is not a reason to wait for 0028. It is a reason to restrict the dogfood
corpus to material that is already public, such as the repo itself.

**O6. `idempotency_key` omits `event_type` (known, in GAPS.md "Noted, not acted on").**

It becomes live the moment projector "1"/"2" corrections land: an observation
and a correction with identical actor, `occurred_at` and payload collide. Carry
it into the correction-eligibility ADR rather than fixing it alone.

### 2.3 Wrong or weakened assumptions

**W1. "Everything remaining is decision-blocked."**

This is true only of stage three: merge/split, corrections under "1"/"2",
authority and redaction. The stage-two dogfood path (sections 34) is blocked
only on R1R3. Those are single-user decisions the maintainer can rule on
without a cryptographer, and none of them depend on 0027 or 0028.

**W2. "0027/0028 are on the critical path."**

- ADR 0020 deliberately leaves multi-user authority undecided.
- A single-user, local store of public material needs neither custody schemas
  nor crypto-shredding.
- The Sep 13 priority order ranks authority and forgetting fourth, below
  substrate, consolidation and monitoring.

The standing rule in `CLAUDE.md` already names the pattern: more
specification passes are avoidance, not progress. 0027/0028 should proceed in
parallel as an asynchronous track that waits on reviewer engagement, not as the
gate for all other work.

**W3. "Dream is the highest-leverage next piece."**

Dream needs things that do not exist yet:

- real content;
- retrieval, since "Dream searches questions; retrieval searches information";
- a temporal layer;
- an acquisition path;
- a ratified 0029.

The proposed generative-flux metric also needs embeddings. Run on synthetic
fixtures, Dream would produce numbers that measure nothing. Dream is the
highest-leverage piece once the store holds real material and can be queried by
something other than ID. Until then, the dogfood slice is.

**W4. "Lineage growth can be deferred because 512 observations on one belief is beyond personal use."**

This holds for projector "2" and for per-belief lineage. It does not hold for
projector "1", whose cost is quadratic in total store size however the
observations are distributed (E2). The deferral stands. Projector "1" should be
labelled as not intended for persistent stores.

**W5. "ADRs are structured enough to ingest without extraction."**

Structure is not the obstacle; semantics are.

- An ADR's status changes over time (Proposed  Accepted). Under ADR 0024 each
  observation adds a candidate with no head.
- Corrections under "1"/"2" are deferred, so disagreement accumulates, and a
  scalar read of "status" refuses.
- Without R3, each recorded status is a verified world claim rather than "file
  F at commit C states S".

That behaviour is correct and honest, but the read contract has to present
candidate sets with their provenance (section 4.4), and the ingester has to
model what the source said rather than what is true.

## 3. Plan

Four steps, each with an exit criterion that can be checked mechanically. Steps
0 and 1 can run in the same week; step 2 depends on R2 and R3.

### Step 0  Hygiene batch (one Codex prompt, no new decisions except R1)

1. Fix E1 and add a linear-scaling regression test for the verifier.
2. Add `scripts/probe_store_scaling.py`, a whole-store companion to the lineage
   probe. It reports ingestion time, verifier time, node count and bytes per
   event at 300/600/1,200/2,400 events for "1" and "2", so the tables in E2 and
   O4 become reproducible rather than asserted.
3. Apply the R1 ruling to the stage-two defaults.
4. Replace `CLAUDE.md` with a pointer to `AGENTS.md` (E4).
5. Record E2, O1, O2, O3 and O4 in GAPS.md.

**Exit:** suite green; verifier at 2,400 events runs within about 2.2 of its
1,200-event time; `check_docs.py` at 0 failures.

### Step 1  Two small ADRs (maintainer rulings)

**ADR 0030, writer model (R2).** Recommended shape:

- One writer process owns Layer A appends. Other processes submit to it and
  never open the store for writing. This matches SQLite's model and keeps
  `BEGIN IMMEDIATE` as a backstop rather than the mechanism.
- Split the submission into two parts. The semantic part is fixed by the
  caller: `event_id`, IDs in the payload, payload, `occurred_at`, source,
  origin. The positional part (`prev_event_hash`, `recorded_at`) is assigned by
  the writer under the append lock.
- A retry is the same semantic submission. The writer re-derives the positional
  fields if the event never committed, and returns the committed pair if it
  did. This keeps ADR 0023 4 ("retained recorded IDs and submitted
  contents"), and the stricter docstring is corrected to match it.
- **Withdrawn (2026-09-22, maintainer resolution 2):** the proposal to assign
  `recorded_at` as the maximum of wall-clock time and the tip plus the smallest
  representable increment was written without checking accepted ADR 0010.
  ADR 0030 must preserve ADR 0010 section 1a's refusal behavior as its baseline.
  Clamping is only an unresolved option requiring explicit supersession of that
  section and its backward-clock acceptance case; equal timestamps remain allowed.

**ADR 0031, source reports (R3).** Choose between:

- **(a) Report-scoped properties by convention, ratified.** The subject is the
  source artifact's mention (for example, a specific ADR file). Properties name
  what the source states: `adr.status_as_stated`, `adr.title_as_stated`,
  `adr.body_sha256`. The commit SHA goes in `source`, and `occurred_at` is the
  commit time. `verified` then means exactly what was observed  that the
  artifact said it.
  - Needs no projector change.
  - Risk: convention is not enforcement. The ADR should require that every
    ingester declares its property vocabulary as report-scoped, and a check
    should refuse ingested writes whose properties are not in a registered
    report vocabulary.
- **(b) A new origin mapping** (for example `document_reported` or
  `user_stated`  an unverified reported state). This is the principled end
  state and generalises to LLM output, but it changes `_state_for_origin` and
  therefore needs a new projector version.

Recommended: **(a) now, (b) recorded as the target** in the same ADR. Option
(a) unblocks dogfooding in days, and every event it writes stays valid under
(b), since a report about an artifact is still true after (b) exists.

**Exit:** both ADRs accepted and committed through the usual `--no-verify` path
after diff review, with the file-count check.

### Step 2  Dogfood slice: public-corpus ingester plus read-only MCP

The architecture is in section 4.

**Exit:** each of the following must be true:

- The ingester loads the full ADR history of this repo into a persistent store
  under projector "2".
- A second run appends nothing, which is the idempotency proof.
- `verify_store.py` passes.
- Through MCP, a model can answer "what did ADR 0027's status line say as of
  2026-09-13, and from which commit?" with the candidate set and provenance,
  without being given any ID.
- A deliberately contradictory status (two commits disagreeing) is shown as two
  candidates, never as one resolved value.

### Step 3  Retrieval by meaning (spec first)

This is the first genuinely unspecified problem; it gets an ADR before code. It
must decide:

- **Index as derived state.** It is rebuildable from Layer A, versioned, and
  listed in 0028's persistence inventory.
- **Embedding model identity.** The model and version are recorded, and a model
  change means a rebuild, never an in-place mutation.
- **Exposure recording under 0026.** Retrieval exposures are usage, never
  evidence, and never enter `event_dependencies`.
- **The generated / exposed / referenced vocabulary** already adopted for the
  feedback loop.
- **Nondeterminism.** Retrieval may be nondeterministic. Invariant 9 governs
  the Resolved View, not ranking, but nothing ranked may enter Layer A without a
  new event.

**Exit:** the recalibration milestone from Sep 13. A piece of real information
enters without a fixture, becomes retrievable by meaning, and carries temporal
context.

### Later, in order

The temporal/activation layer, then Dream (ratify 0029 first) once the store
has had weeks of real content.

0027/0028 continue as a parallel track whose next action is engaging the
reviewer, not further drafting. Stage-three corrections come after that, and
their ADR should absorb O6.

## 4. Architecture of the dogfood slice

### 4.1 Components and boundaries

```text
                   git history (public repo)
                             read-only


  nyx-ingest-adr  (script, single run)
   - walks commits touching decisions/*.md
   - parses Status / Implementation / title
   - builds SEMANTIC submissions only

                         semantic submissions


  writer  (sole Layer A writer, ADR 0030)
   - assigns prev_event_hash, recorded_at
   - append (BEGIN IMMEDIATE) + publish "2"



               SQLite store        Layer A + projector "2"
               (schema v4)         + listing index (derived)

                         open_readonly only


  nyx-mcp  (separate package, read-only)
   tools: status, list_subjects, find_mention,
   belief_candidates, subject_events, verify

```

**Package boundary.** `nyx-mcp` is a separate distribution that depends on
`nyx`. The kernel keeps `dependencies = []`. The MCP SDK, and later any
embedding library, stays outside the kernel, where it cannot enter replay.

**Write boundary.** In this slice MCP has no write tools. The first write tool
is the untrusted-source channel and waits for ADR 0031 option (b), because a
model's statement cannot be a report-scoped observation of an artifact.

### 4.2 Event model for ingested ADRs (under ADR 0031 option a)

| Element | Value |
|---|---|
| Mention | one per ADR file path, `entity_mention_recorded`, constitutive link |
| Subject | "the referent of this mention" (ADR 0019): the file, not the decision |
| Observation | one per (commit, ADR file) where content changed |
| Claims | `adr.title_as_stated`, `adr.status_as_stated`, `adr.implementation_as_stated`, `adr.body_sha256` |
| `source` | `{"actor_id": "nyx-ingest-adr", "config": {"repo": , "commit": <sha>, "path": }}` |
| `occurred_at` | commit time, recorded under ADR 0006's existing timestamp rules (offset-bearing; accepted spelling preserved) |
| IDs | derived deterministically from (repo, path, commit, property) so a re-run is an exact retry |

Bodies are recorded by hash, not text. Full text stays in git, which is already
the durable, public record. This keeps Nyx from becoming a second copy of the
repo, and keeps O4 growth small.

### 4.3 Listing index

A derived table maintained by the writer after publication and rebuildable by
full replay. It holds (`subject_id`, `mention_text`, `property_id`,
`belief_id`, latest applied position). It supports `list_subjects` and
`find_mention` by exact and prefix text match.

The table carries no ranking and no plaintext beyond mention text. Mention text
is listed in the persistence inventory as a known copy; for a public corpus that
is acceptable, and it is recorded so the private-corpus case cannot slip in
unnoticed. Staleness uses the existing progress/freshness contract; a read
behind progress says so rather than guessing.

### 4.4 Read contract for disagreement

`belief_candidates` returns every ClaimCandidate on the belief. Each carries its
value, origin, verification state and basis, `source` (including the commit),
`occurred_at`, `recorded_at` and the event ID. Candidates are ordered by
`occurred_at`, then event ID, **for display only**. The response always
includes the explicit statement from ADR 0024: no authoritative value is
selected.

The client or model may say "the most recent commit states X". Nyx never says
"the status is X". This is the line that keeps W5 honest, and it should be
tested as a response-shape property, not left as a docstring.

### 4.5 Invariant check for the slice

| Invariant | How the slice respects it |
|---|---|
| 1, 8 Append-only / commit point | Only the writer appends; the index is derived and rebuildable. |
| 3 No silent promotion | ADR 0031: claims are about what an artifact stated, which was actually observed. |
| 9 Determinism | IDs derived from (repo, path, commit, property); the ingester is re-runnable byte-identically. |
| 10 Behavioural invariance | MCP returns candidate sets, never a synthesized answer. |
| 14 Erasure boundary | Public corpus only (O5); the index copy is declared in the inventory. |
| 0026 Usage  evidence | MCP reads are not recorded as anything in this slice; exposure recording is a step-3 decision. |

### 4.6 Failure modes to test

- A crash between append and publish: the next run publishes the pending event
  and appends nothing new.
- The ingester re-runs after a partial run: each event is an exact retry or a
  new append, never a duplicate candidate.
- A second writer process attempts to append: it refuses, per ADR 0030.
- The MCP server is pointed at a store behind progress: freshness is reported,
  and no data is fabricated.
- A malformed ADR (missing Status line): nothing is recorded for that property,
  and the absence is not converted into a claim.
- A clock step backwards during ingestion: the behaviour is whatever ADR 0030
  rules, and a test pins it.

## 5. Reproduction notes

- **Suite:** `uv python install 3.14`, `uv venv -p 3.14`, `pip install -e .[dev]`,
  `pytest -q`.
- **Ingestion probe:** 200 subjects, each with one mention and five
  single-claim observations of 200-byte values. `ingestion.submit` per event,
  with `recorded_at` spaced one second apart.
- **Verifier probe:** `scripts/verify_store.py --projector 2 --json` on the
  600- and 1,200-event stores from the ingestion probe, profiled with
  `cProfile`.
- **Concurrency reproduction:** two connections prepare observations against the
  same tip. The first submits; the second's retained pair refuses with
  `BackdatedRecordingError`; re-preparing with the same IDs and a fresh
  `recorded_at` succeeds.

## 6. Rulings needed

- **R1.** Stage-two entry points: require `projector_version`, or default to "2".
- **R2.** The writer model (ADR 0030): sole writer, the semantic/positional
  split of submissions, and the `recorded_at` rule under clock steps.
- **R3.** Source reports (ADR 0031): option (a) now with (b) as the recorded
  target, or (b) directly with a new projector version.
- **R4.** Corpus policy until 0028 passes Gate 3: public material only, or an
  explicit acceptance that anything ingested is permanent.
- **R5.** Whether mention text in the listing index is an acceptable declared
  copy for public corpora.

## Rulings (2026-09-22)

R1  Stage-two entry points require an explicit projector_version. No default.
    This is a proposed change awaiting ADR 0032's acceptance; it is not
    implemented by this task. Accepted ADR 0025 section 1 preserves existing
    API defaults until explicitly superseded.
R2  A sole writer owns Layer A appends and all positional fields
    (prev_event_hash, recorded_at). Callers own semantic identity (event_id,
    payload IDs, payload, occurred_at, source, origin). Skew detection runs
    before any clamping. If the persisted tip is beyond the allowed threshold
    relative to the writer clock, writes halt; alert and recovery semantics
    must be defined. Historical imports need a separate, explicit path.
R3  Ingested external content is recorded as report-scoped claims (option a)
    now; a new origin mapping (option b) is the recorded target. Report-scoped
    vocabularies are enforced at the writer trust boundary. Each event records
    an immutable vocabulary identity, version and hash.
R4  public corpus only until the erasure requirements (Gate 3 of proposed ADR 0027 together with proposed ADR 0028 9 and 11) are accepted, implemented and passed.
R5  Mention text is allowed in a derived listing index for public corpora,
    provided it is inventoried as a derived copy and rebuildable by replay.
Renames: under current ADRs a renamed file remains a separate subject. Git's
    rename/similarity is recorded only as a report-scoped claim. An ADR number
    is metadata/searchable text, never identity.

These rulings govern the requested work only where consistent with accepted
ADRs. They do not ratify the forthcoming ADR drafts or implement Step 2.
R2 preserves ADR 0010's backward-clock refusal baseline, with equal timestamps
allowed. Threshold, alert channel, recovery procedure and timestamp assignment
within the threshold remain explicit maintainer choices in proposed ADR 0030;
clamping would require the supersession stated above.
R3's vocabulary enforcement is an ingestion-time writer restriction only.
Property IDs remain exact opaque strings under ADR 0023 section 1; no property
registry or replay-time vocabulary check is introduced. Vocabulary-identity
location remains a maintainer choice in proposed ADR 0031.
