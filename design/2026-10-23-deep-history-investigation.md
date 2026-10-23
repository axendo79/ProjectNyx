# Deep-history verification and projector-3 append investigation

At 1,000 concentrated events, whole-store verification improved from 293.064 s to 120.271 s (2.44x). At 2,000 events the prototype completed in 631.889 s while the baseline was censored at 1,200 s. Replay alone improved 608.56x at that depth; retained historical-root auditing still dominates the whole operation.

All 11,250 planned replay-prefix comparisons and all 407 mutation reports matched, preserving every one of 331 existing detections. The R9 index prototype reduced the 2,000-event in-memory component median from 24.566 ms to 2.176 ms; a database-index after measurement is not supplied.

Date label: 2026-10-23. Class C evidence only; draft PR, **not for merge**.
No production change or authority ruling is made by this report.

## Scope and provenance

The investigation worktree is `D:\ProjectNyx-wt-deephist-2026-10-22`, branch
`sol/deephist-investigation-2026-10-22`, based on actual `origin/main`
`89e3ca875e2bcb098d5ec7679c9c428dbac1ac41` (the expected commit).
The requested GAPS entry was read with `git show` from
`origin/docs/state-refresh-2026-10-22` at
`2049daf9092622340e3829711f55912bbcb9d559`; it was absent on this main base.
Its supplied cloud measurements are context, not local results.

The pinned Run 11 checkout stayed at
`5acc188a96de60bbed51534b48156214101a13bb` with empty porcelain status before/after setup and after all experiments. Existing worktrees were not operated on. Fetch/worktree
registration used the shared Git administration area as explicitly authorized.
No checkout, pull, reset, stash, commit or source edit occurred in the pinned tree.
No Git configuration or remote was explicitly changed.

Machine: Lenovo 83LY, Intel Core i7-14700HX (20 cores / 28 logical processors),
34,070,192,128 bytes OS-visible physical memory; Python 3.14.2, MSC v.1944 AMD64;
Windows 11 build 26200. Exact environment and setup commands are in
[setup.json](deephist-evidence/setup.json) and
[environment.json](deephist-evidence/environment.json).
The new venv was created with `py -3.14 -m venv .venv` and installed with
`.\.venv\Scripts\python.exe -m pip install -e .`.
Before any test, an assertion confirmed `nyx.__file__` was inside this worktree.

Pytest was reused read-only from the pinned checkout's installed site-packages;
it was not downloaded. Local `src` precedes that directory in `PYTHONPATH`,
and `PYTHONDONTWRITEBYTECODE=1` prevents writes there. Only editable-build
dependencies were downloaded from PyPI. Experiments ran sequentially after the
suites, on a host that was not reserved exclusively for benchmarking. These are
single samples at each depth, with ordinary OS caches, not performance guarantees.

## Workloads and timing boundaries

All fixtures are synthetic, with fixed IDs, UTC timestamps increasing one second
per event from 2026-07-13, fixed source metadata and 200-byte ASCII values.
There are no generated random IDs or sampled event clocks.

- Projector 2 concentrated: exactly one mention and N-1 observations on one belief.
- Projector 2 spread: the same one mention and N-1 observations, with a new property/
  belief after each five observations. This holds the mention/observation mix fixed.
- Projector 3 transitions: one mention, one observation, then a replacement chain.
  There are N-1 retained-or-live candidates and exactly one live candidate.
- The shipped store-scaling probe is a separate control: one mention plus five
  observations per subject, rounding requested event counts to complete groups.
- Seeded equivalence fixtures cover projectors 0/1/2/3, seeds 0/17/902467, 24 events
  each, including Unicode, multi-claim observations, correction, replacement and expiry.

Whole-store verify times include the read-only connection and all audit work,
excluding process startup and fixture construction. Replay times include only
each replay's append calls; comparisons and digest recording are outside the timer.
Database append timings include `safe_append_event` and separate
`materialize_pending` publication, excluding fixture-event construction. They
use the production low-level append path, not the higher-level writer preparer.
Append medians/p95 use the final 64 appends at each depth. The p95 estimator uses
rank floor(0.95*(window-1)) in the sorted window.
Full-belief reads time `storage.read_belief` after opening a fresh read-only
connection, three repetitions; the median is reported. They include complete
collections and freshness labelling, not just header lookup.

Every child run has a 1,200-second wall cap. A censored run is not an exact duration
or a successful full audit. The supervisor total is not a single benchmark run.

## Reproduction

From the new worktree in PowerShell:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH='D:\ProjectNyx-wt-deephist-2026-10-22\src;D:\ProjectNyx-wt-deephist-2026-10-22\design;D:\ProjectNyx\.venv\Lib\site-packages'
.\.venv\Scripts\python.exe -B design/deephist_supervise.py
```

The runner refuses to overwrite fixture databases; use a fresh worktree/fixture
directory for a new campaign. [supervisor.jsonl](deephist-evidence/supervisor.jsonl)
and [jobs.jsonl](deephist-evidence/jobs.jsonl) record exact argument vectors, exit
statuses, times and censoring. They include the full pytest commands, the shipped
`scripts/probe_store_scaling.py`, individual experiment jobs, and the direct
`scripts/verify_store.py --db ... --projector 2 --json` control.

## Verifier prototype and equivalence argument

The shipped `scripts/verify_store.py` is unchanged.
[deephist_prototype.py](deephist_prototype.py) compiles that source with exactly
one asserted expression substitution at `scripts/verify_store.py:474`.
Verifier-owned collection dictionaries remember inserted/replaced members.
At the original root-computation point, dirty members update initially empty
persistent Merkle trees. The logical replay, validation order, lineage assembly,
SQL reads, retained-node checks, stored-root rebuilding and report generation
remain the same source.

Neither stored collection roots, projected headers, committed nodes nor production
snapshots seed these replay trees. They start empty and are changed only by the
verifier's own reconstruction of Layer A. Hashing is delayed until the original
root-computation point to preserve validation/exception ordering. Candidate
transitions already copy changed candidates before replacing collection members.

For every completed synthetic prefix, the harness compares replay verdicts and
all reconstructed records, including every collection root, result root and own
lineage. History and relations are compared as well. The histories are append-only
within replay. The unchanged remainder of `verify_connection` observes only
these equal replay outputs, the same Layer A and the same stored projection.
Consequently it produces the same report for an identical stored prefix.
This is the code argument for prefix verdict equivalence; it is not a claim that
a fresh whole-store audit was executed separately at every large benchmark prefix.

Direct whole-store report comparisons also cover all 300 seeded prefixes
(288 nonempty and 12 empty), completed paired benchmark endpoints and every
existing mutation-matrix case. A timing censored before a baseline report exists
cannot provide a direct endpoint report pair and is labelled accordingly.

## Verifier independence — assessment, not a decision

My assessment is that independence from derived-state authority and from production
semantic reconstruction is preserved by this prototype. The replay consumes the
verifier's own Layer-A decoding and semantics, and never imports a stored root as
its expected root. Existing tests forbidding production reconstruction calls pass.
The stored-root/content audit is retained unchanged.

This is not an independently implemented Merkle algorithm. Both versions already
share canonical hashing and Merkle primitives: `merkle.rebuild` calls
`merkle.put`. The prototype changes their scheduling and shares the incremental
primitive with production. That leaves common-mode algorithm/serialization risk;
finite equivalence and corruption tests cannot close the broader independence
gap or supply a maintainer ruling. Nothing here ratifies a proposed contract.

## R9 interpretation and index prototype

The governing text is ADR 0035 section 2:

> Before any correction, replacement or expiry, at the locked pre-event snapshot,
> the transition refuses before append if either holds:
>
> - any target has a `verification_basis` kind other than `direct_observation`, or a
>   nonempty `predecessors`, `restrictions` or `opposing_events`;
> - any candidate in the snapshot names a target in its `predecessors` or
>   `restrictions`.

It further says: “Replay applies the same check.” ADR 0034 R9 requires an “actual
dependency check, not an assumption that none exist.”

My reading is that this specifies the predicate, its complete snapshot scope and
its timing, rather than requiring enumeration as an algorithm. An exact index is
clearly permitted as a representation of that result; it cannot assume an empty
dependency graph merely because ordinary producers currently create empty fields.
ADR 0025 section 5 also requires indexed lookups for reduction/append validation.

The evidence-only reverse index covers both fields globally across all candidates,
maintained from complete event deltas starting at genesis. Target-local fields
are still checked directly. It retains every referrer, removes obsolete edges and
forks its sparse maps when advancing, preserving earlier snapshots. Non-list field
shapes use a scanner fallback for comparison with forged test records. No
dependent demotion/restoration semantics are implemented.

Ordinary projector-3 observations dispatch to `committed.reduce_ordinary` at
`src/nyx/forward.py:65` and do not invoke R9. The measured R9 attribution is
specific to the transition workload; the supplied cloud fixture was not available.

The index is attached only to experimental in-memory snapshots. The production
database append and storage snapshot paths are unchanged. Before/after index
timings compare the same in-memory reduce-and-apply operation. They are **not**
a measured database-append speedup. A transactional database index, durable
representation, recovery and corrupt-node parity remain follow-up work; caching
only by a stored root without validation is not demonstrated safe here.


## Call paths and remaining work

These locations are on the investigated base; no production file was edited.

| Operation | Exact path | Why depth matters |
| --- | --- | --- |
| Verifier semantic replay | `scripts/verify_store.py:380` `Replay.append` → `:474` full collection rebuilds → `src/nyx/merkle.py:173` `rebuild` → `:119` `put` → `:69` canonical node creation | Each event reserializes/rebuilds the accumulated candidates and event dependencies. Summing growing prefixes repeats history. |
| Retained root audit | `scripts/verify_store.py:563` `check_headers` → `:249` `Trees.root` → `:255` `merkle.rebuild` | Every distinct historical collection root is rebuilt from its full leaf mapping. The prototype deliberately leaves this work intact. |
| Retained content audit | `scripts/verify_store.py:204` `Trees.members`; `:563` header/member/reference checks | Historical subtree mappings are retained/memoized, and historical headers repeatedly enumerate accumulated members and structural event references. Incremental replay does not make this audit linear. |
| Projector-3 append/publication | `src/nyx/storage.py:516` locked append reduction and `:983` publication reduction → `src/nyx/forward.py:119` → `src/nyx/transition_dependencies.py:18` → `src/nyx/committed.py:118` `records` | R9 materializes the complete candidate index twice per submitted transition, once at acceptance and once at publication. |
| Candidate enumeration | `src/nyx/merkle.py:162` `items` → transaction-bound `src/nyx/committed_storage.py:40` `load` | The scan traverses, decodes and validates full candidate nodes. Indexed target lookup is already separate from this global reverse scan. |
| Full-belief read | `src/nyx/storage.py:578` → `:1035` `read_belief_status` → `src/nyx/committed.py:103` `belief` → `src/nyx/merkle.py:162` | All three requested collections are enumerated and canonically sorted. This is complete-content read work, not replay. |

The profiles below distinguish the replay and retained-root callers. Removing
replay rebuilds alone leaves stored historical roots and the growing reference
walks, so a large replay-only speedup cannot be interpreted as the total speedup.
The full-content read boundary remains required by ADR 0025; no content is dropped,
coalesced or replaced by a header-only answer.

## Maintainer yes/no rulings for later work

These questions request future decisions; no answer is assumed by this branch.

1. **Accept the verifier independence assessment for a separate production
   incremental-replay follow-up, while retaining every existing stored-content,
   historical-root and lineage check? Yes / No.**
2. **Confirm that an exact reverse index over every candidate's `predecessors`
   and `restrictions`, checked at the locked pre-event snapshot and on replay,
   satisfies ADR 0035 section 2 without full enumeration on each transition?
   Yes / No.**
3. **Authorize a separate database-index design and corruption/recovery campaign
   before claiming or deploying an append speedup? Yes / No.**

The present index supplies neither a database format nor a recovery default.
No authority file, GAPS status or frozen output is changed to imply otherwise.


## Validation

Both complete runs included the existing `tests/` suite and the 26 explicit
investigation tests in `design/test_deephist.py`:

| Selection | Passed | Skipped | Failed | Time |
| --- | ---: | ---: | ---: | ---: |
| Existing verifier | 2,260 | 9 | 0 | 436.45 s |
| Explicit prototype routing | 2,260 | 9 | 0 | 444.44 s |

The existing suite accounts for 2,234 passed / 9 skipped; the investigation adds
26 passing tests. Logs:
[baseline](deephist-evidence/baseline-pytest.txt),
[prototype](deephist-evidence/prototype-pytest.txt).
The prototype plugin reroutes in-process verifier loads/imports, including campaign
and corruption checks. CLI subprocess tests continue to exercise the unchanged
shipped CLI; the separate mutation matrix explicitly invokes both verifier
implementations on every mutant.

The initial run had 14 failures in the new test harness because its test-only
`reducer.Snapshot` constructors omitted the required empty beliefs argument.
The existing tests passed on that run. The constructor was corrected, all 26
investigation tests passed in 21.29 s, then both full runs above passed.
The initial outcome is retained in setup provenance; its full diagnostic log is
in the local ignored fixture directory. No production fix was involved.


## Bounded profile evidence

The 500-event concentrated profile used 128.063 s total with the existing verifier.
`merkle.rebuild` consumed 119.941 s cumulative (**93.66%**) over 2,501 calls:
1,497 calls / 69.939 s from `Replay.append`, and 1,004 calls / 50.002 s from
`Trees.root`. The prototype profile used 57.811 s total and retained exactly
1,004 rebuild calls, all from stored-root auditing (49.577 s). Thus it removes the
replay rebuilds, rather than replacing the stored-root audit with trust in stored
hashes. In the prototype, `check_headers` still consumed 56.972 s cumulative.

For 64 transition appends starting at depth 1,000, the profile recorded 128 reducer
calls and 128 R9 checks: acceptance and publication each reduced every event.
The 30.036 s profile (including deterministic fixture-envelope generation) spent 28.863 s cumulative (**96.09%**) in
`check_transition_dependencies`, including 28.336 s in candidate enumeration.
The path reached `committed_storage.py:40(load)` 285,932 times, with 266,802
`merkle.py:226(decode)` calls. This is full candidate traversal, decoding,
canonical/hash validation and SQL loading, not merely an indexed target lookup.

Cumulative times include nested callees and must not be added together. Profiling
adds overhead; these profile times are attribution evidence, not the unprofiled
speedup curve.

- [Existing verifier profile](deephist-evidence/verify-concentrated-2-500-False-profile.txt)
- [Incremental replay profile](deephist-evidence/verify-concentrated-2-500-True-profile.txt)
- [Transition append/publication profile](deephist-evidence/append-1000-profile.txt)

The 10 shared mutation non-detections are the existing scope boundaries described
in GAPS: uncommitted payload key-binding metadata (all four versions), legacy
checkpoint absence/relabeling, evaluation-only projected time, and operational
index-clock diagnostics. No policy or independent basis for those fields is
invented, and no gap is marked resolved.

## Measurements

Raw numeric results, report counts, prefix digests and commands: [results.json](deephist-evidence/results.json). Censoring is wall time including process startup; successful operation timers exclude startup.

### Whole-store verification (projector 2)

| Events | Concentrated existing s | Incremental s | Speedup | Spread existing s | Incremental s | Speedup |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 250 | 12.711 | 4.147 | 3.06x | 0.348 | 0.310 | 1.12x |
| 500 | 72.372 | 30.465 | 2.38x | 0.717 | 0.659 | 1.09x |
| 1000 | 293.064 | 120.271 | 2.44x | 1.625 | 1.348 | 1.21x |
| 2000 | censored / unavailable | 631.889 | no exact paired ratio | 3.783 | 3.162 | 1.20x |

The 2,000-event concentrated baseline was censored at 1,200 seconds. Its prototype report is successful, but there is no completed baseline whole-store report at that endpoint. No exact speedup or empirical full-report pair is claimed there.

### Replay-only verifier curve and prefix equivalence

| Events | Concentrated existing s | Incremental s | Speedup | Spread speedup | Transition replay speedup |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 250 | 5.779 | 0.073 | 78.91x | 2.05x | 48.08x |
| 500 | 36.796 | 0.219 | 167.76x | 2.14x | 95.27x |
| 1000 | 170.968 | 0.521 | 328.06x | 2.14x | 153.04x |
| 2000 | 818.912 | 1.346 | 608.56x | 2.15x | 233.08x |

Completed large-workload prefix comparisons: 11,250. They compare records, recomputed roots, history and relations; every completed comparison matched. The seeded tests add 300 direct complete-report prefix pairs. Censored jobs/checkpoints are recorded separately, rather than counted as completed workloads.

### Append and index component measurements

| Events | P2 concentrated append+publish median ms | P3 transition append+publish median ms | P3 p95 ms | In-memory scan median ms | Index median ms |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 250 | 4.850 | 37.058 | 78.808 | 2.064 | 0.808 |
| 500 | 5.244 | 97.302 | 136.307 | 3.495 | 0.890 |
| 1000 | 5.364 | 267.795 | 313.979 | 13.246 | 2.027 |
| 2000 | 5.782 | 553.125 | 598.090 | 24.566 | 2.176 |

These are different timing boundaries: the two database columns contain real append and publication; the final two columns compare one in-memory reduction plus snapshot application. No database-index after measurement exists. All completed index runs compare every prefix's index roots and the final complete logical snapshot. The mixed index campaign also compares all output node bytes and complete snapshots at 72 prefixes across three seeds.

### Full-belief reads (median of three, seconds)

| Events | P2 concentrated | P3 transition history | P2 spread first belief (5 candidates) |
| ---: | ---: | ---: | ---: |
| 250 | 0.034 | 0.033 | 0.001 |
| 500 | 0.064 | 0.069 | 0.001 |
| 1000 | 0.132 | 0.138 | 0.001 |
| 2000 | 0.301 | 0.291 | 0.001 |

### Existing mutation/corruption matrix

407 cases; 66 unchanged controls; 331 changed cases detected by both; 10 changed cases not detected by either. Every complete report matched exactly, including failures and unchecked findings. Every existing detection therefore still fires; existing non-detections remain limitations.

[Every case and detection category](deephist-evidence/mutations.json). The campaign uses all cases returned by the shipped mutation harness, seed 17 and 12 events, for all four projectors. Self-consistently rehashed Merkle/relation mutants are included.

Existing non-detection IDs (no scope change is claimed):

- Projector 0: `payloads/canonical_entity_id/flip`, `derived_progress/projector_version/flip`, `derived_progress/projector_version/delete`, `resolved_beliefs/projected_as_of/flip`, `resolved_beliefs/projected_as_of/swap`, `entity_event_index/updated_at/flip`, `entity_event_index/updated_at/swap`.
- Projector 1: `payloads/canonical_entity_id/flip`.
- Projector 2: `payloads/canonical_entity_id/flip`.
- Projector 3: `payloads/canonical_entity_id/flip`.

### Censored runs

- verify --shape concentrated --count 2000 --version 2: censored at 1200 s; observed wall 1200.010 s.
- build --shape transitions --count 10000 --version 3: censored at 1200 s; observed wall 1200.022 s.

The 10,000-event append attempt saved verified progress windows before any censoring:

| Completed events | Accumulated append+publish s | Final-window median ms |
| ---: | ---: | ---: |
| 250 | 5.868 | 34.233 |
| 500 | 25.994 | 101.419 |
| 750 | 61.335 | 164.909 |
| 1000 | 120.543 | 269.703 |
| 1250 | 194.016 | 345.765 |
| 1500 | 289.209 | 392.946 |
| 1750 | 397.651 | 476.021 |
| 2000 | 520.945 | 513.536 |
| 2250 | 671.957 | 654.239 |
| 2500 | 838.452 | 720.442 |
| 2750 | 1019.604 | 760.455 |

These are completed prefixes of an attempt, not a completed 10,000-event result. No 10,000-event full verify, RSS/virtual-address limit experiment, 100k or 500k run is claimed.

### Shipped probe control

[Store-scaling control data](deephist-evidence/store-scaling.json) and [stdout](deephist-evidence/store-scaling.txt) preserve actual rounded counts. Projector 1 was explicitly skipped for this control; it was still covered by both full test suites.

Raw per-job stdout duplicates the consolidated JSON and remains in the local ignored fixture directory; failed/censored job logs are retained in this evidence folder. No experimental phase was skipped for a missing permission. Delivery status is recorded in the final summary.
