# Projector-3 public read hardening: test evidence

Validated test commit: `3a042bbc9327e045f535a85c376d0310d7f296ef`.
Baseline `origin/main`: `31f93bb93b6748e4e3f619c0fb0f70d7599f6929`.
Branch: `sol/read-hardening-2026-10-15`.
Worktree: `D:\ProjectNyx-wt-read-hardening`.
Test file SHA-256: `4ce4f8d998408bb6f700ad3f7d4eeef9d4e6e6234222febc338ab20a3a9c0d19`.

This evidence is committed separately after the test commit so that its exact
commit hash can be recorded without a self-referential hash. The full-suite run
validated the identical test-file bytes before that commit. No test or source
changes occurred between that successful run and the test commit.

## Results and coverage

- Full suite: 2234 passed, 9 skipped in 284.04s (0:04:44).
- Targeted initial run: 84 passed in 154.37s (0:02:34). Two independent completeness assertions
  (all recorded candidate IDs and belief IDs) were added during that run; the
  subsequent full suite validates the final file, including those assertions.
- Documentation checker: zero failures; 83 unchecked baseline references plus
  103 unchecked references in design/ (186 total), pre-existing on this baseline.
- Findings: no failing contract properties; no xfail markers were needed.
- Twelve distinct seeded histories, 48 events each: 576 distinct events.
  Every seed covers mentions, observations, all three transition types, multiple
  targets, successor chains, agreement, disagreement, an empty live set, new
  observations after expiry, and tied recording instants.
- Each full run generates 24 sequences: 12 primary histories and 12 independent
  same-seed regenerations. Seven parameterized cases per seed yield 84 new cases.
  Eight fresh-store executions per seed yield 96 executions / 4,608 publications.
  Historical reconstruction checks 50 cutoffs per seed, 600 in total.
- Seed list (decimal): 0, 1, 2, 3, 7, 17, 42, 73, 99, 31337, 12648430, 20261015.
  The decimal seed 12648430 is written as `0xC0FFEE` in the test module.

## Contract interpretation and limits

Every test docstring cites the accepted ADR clause it exercises. The public
read inventory in `D:\ProjectNyx\scratch\nyx-devuse-inspection.md` and the
required README / ADR / GAPS / architecture / implementation reading order were
followed. This is a class-C test audit of existing accepted behavior, not a new
ADR implementation. Proposed ADRs 0036/0037 supply no test expectations.

Candidate membership and ending relations are checked against a small test-only
oracle reading recorded claim payloads and targets, not nyx.forward's relation
mapping. Replay compares all six complete snapshot maps and their canonical UTF-8
bytes at every prefix. Publication uses the final generated log tip as one shared
evaluation time for all prefixes, as ADR 0012 / ADR 0014 section 7 require.
Unrelated raw live rows evaluated at different times are not relabeled or claimed
to be a shared-time snapshot.

As-of checks use the entire verified log at and one microsecond before every
distinct recording instant, including genesis and tied instants. Scalar refusals
cover agreeing and disagreeing live candidates and beliefs retaining candidates
after expiry. No zero/one-candidate scalar result is invented.

Read-only tests compare the main database and durable WAL bytes both while the
reader is open and after it closes, with a closed writer and an active WAL writer.
SQLite SHM reader bookkeeping is outside that durable-byte comparison; an absent
and an empty WAL both contribute zero durable bytes. Directory-sidecar immutability
is not claimed. All stores are disposable fixtures under `scratch/pytest-tmp`.

No src/, decisions/, spec/, schema or dependency declaration changed. No authority
completion marker is appropriate for this audit of already completed ADRs. The
original checkout's working files were not edited. Worktree creation necessarily
updated shared Git worktree/branch metadata. No push or hook bypass occurred.

## Setup commands

Observed setup commands (exit 0):

```powershell
git -C D:\ProjectNyx worktree add D:\ProjectNyx-wt-read-hardening -b sol/read-hardening-2026-10-15 origin/main
python scripts/check_docs.py --status
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Only the existing declared development extra was installed. Runtime and package
versions, editable source resolution and per-seed event totals are preserved in
the raw environment log below. No dependency declaration was added.

Local logging-helper setup encountered WinError 2 before launching pytest; using
the absolute venv interpreter fixed it. A later console-print UnicodeEncodeError
occurred after docs-status had already exited 0 and its complete UTF-8 log and
exit-code record were saved. Configuring the helper's console as UTF-8 fixed
printing. These were evidence-helper issues, not test or Nyx contract failures.

## Captured command results

Each record contains the actual argv, working directory, UTC start, duration,
exit status and raw combined stdout/stderr. The untracked local capture helper
runs subprocesses with no shell or command rewriting beyond resolving an existing
relative executable path. The full suite uses the required basetemp.

### environment

```json
{
  "label": "environment",
  "cwd": "D:\\ProjectNyx-wt-read-hardening",
  "command": [
    "D:\\ProjectNyx-wt-read-hardening\\.venv\\Scripts\\python.exe",
    "scratch/report_environment.py"
  ],
  "started_utc": "2026-10-15T23:47:53.128948+00:00",
  "elapsed_seconds": 0.573596299997007,
  "exit_code": 0,
  "log": "environment.log"
}
```

```text
{
  "python": "3.14.2 (tags/v3.14.2:df79316, Dec  5 2025, 17:18:21) [MSC v.1944 64 bit (AMD64)]",
  "executable": "D:\\ProjectNyx-wt-read-hardening\\.venv\\Scripts\\python.exe",
  "base_prefix": "C:\\Users\\axend\\AppData\\Local\\Python\\pythoncore-3.14-64",
  "platform": "Windows-11-10.0.26200-SP0",
  "sqlite": "3.50.4",
  "nyx_import": "D:\\ProjectNyx-wt-read-hardening\\src\\nyx\\__init__.py",
  "packages": {
    "nyx": "0.0.0",
    "pytest": "9.1.1",
    "pip": "25.3"
  },
  "nyx_direct_url": "{\"dir_info\": {\"editable\": true}, \"url\": \"file:///D:/ProjectNyx-wt-read-hardening\"}",
  "head": "31f93bb93b6748e4e3f619c0fb0f70d7599f6929",
  "origin_main": "31f93bb93b6748e4e3f619c0fb0f70d7599f6929",
  "coverage": [
    {
      "seed": 0,
      "events": 48,
      "event_types": {
        "entity_mention_recorded": 5,
        "observation_recorded": 24,
        "candidate_replaced": 11,
        "correction_appended": 5,
        "candidate_expired": 3
      },
      "multi_target_transitions": 4,
      "unique_recording_instants": 25,
      "historical_cutoffs": 50
    },
    {
      "seed": 1,
      "events": 48,
      "event_types": {
        "entity_mention_recorded": 5,
        "observation_recorded": 21,
        "candidate_replaced": 8,
        "correction_appended": 3,
        "candidate_expired": 11
      },
      "multi_target_transitions": 7,
      "unique_recording_instants": 25,
      "historical_cutoffs": 50
    },
    {
      "seed": 2,
      "events": 48,
      "event_types": {
        "entity_mention_recorded": 5,
        "observation_recorded": 26,
        "candidate_replaced": 4,
        "correction_appended": 7,
        "candidate_expired": 6
      },
      "multi_target_transitions": 8,
      "unique_recording_instants": 25,
      "historical_cutoffs": 50
    },
    {
      "seed": 3,
      "events": 48,
      "event_types": {
        "entity_mention_recorded": 5,
        "observation_recorded": 24,
        "candidate_replaced": 6,
        "correction_appended": 5,
        "candidate_expired": 8
      },
      "multi_target_transitions": 8,
      "unique_recording_instants": 25,
      "historical_cutoffs": 50
    },
    {
      "seed": 7,
      "events": 48,
      "event_types": {
        "entity_mention_recorded": 5,
        "observation_recorded": 18,
        "candidate_replaced": 5,
        "correction_appended": 8,
        "candidate_expired": 12
      },
      "multi_target_transitions": 4,
      "unique_recording_instants": 25,
      "historical_cutoffs": 50
    },
    {
      "seed": 17,
      "events": 48,
      "event_types": {
        "entity_mention_recorded": 5,
        "observation_recorded": 15,
        "candidate_replaced": 10,
        "correction_appended": 7,
        "candidate_expired": 11
      },
      "multi_target_transitions": 6,
      "unique_recording_instants": 25,
      "historical_cutoffs": 50
    },
    {
      "seed": 42,
      "events": 48,
      "event_types": {
        "entity_mention_recorded": 5,
        "observation_recorded": 19,
        "candidate_replaced": 10,
        "correction_appended": 3,
        "candidate_expired": 11
      },
      "multi_target_transitions": 4,
      "unique_recording_instants": 25,
      "historical_cutoffs": 50
    },
    {
      "seed": 73,
      "events": 48,
      "event_types": {
        "entity_mention_recorded": 5,
        "observation_recorded": 22,
        "candidate_replaced": 6,
        "correction_appended": 7,
        "candidate_expired": 8
      },
      "multi_target_transitions": 8,
      "unique_recording_instants": 25,
      "historical_cutoffs": 50
    },
    {
      "seed": 99,
      "events": 48,
      "event_types": {
        "entity_mention_recorded": 5,
        "observation_recorded": 23,
        "candidate_replaced": 5,
        "correction_appended": 8,
        "candidate_expired": 7
      },
      "multi_target_transitions": 8,
      "unique_recording_instants": 25,
      "historical_cutoffs": 50
    },
    {
      "seed": 31337,
      "events": 48,
      "event_types": {
        "entity_mention_recorded": 5,
        "observation_recorded": 26,
        "candidate_replaced": 4,
        "correction_appended": 5,
        "candidate_expired": 8
      },
      "multi_target_transitions": 3,
      "unique_recording_instants": 25,
      "historical_cutoffs": 50
    },
    {
      "seed": 12648430,
      "events": 48,
      "event_types": {
        "entity_mention_recorded": 5,
        "observation_recorded": 25,
        "candidate_replaced": 7,
        "correction_appended": 7,
        "candidate_expired": 4
      },
      "multi_target_transitions": 6,
      "unique_recording_instants": 25,
      "historical_cutoffs": 50
    },
    {
      "seed": 20261015,
      "events": 48,
      "event_types": {
        "entity_mention_recorded": 5,
        "observation_recorded": 21,
        "candidate_replaced": 6,
        "correction_appended": 6,
        "candidate_expired": 10
      },
      "multi_target_transitions": 7,
      "unique_recording_instants": 25,
      "historical_cutoffs": 50
    }
  ],
  "unique_seeded_histories": 12,
  "events_per_history": 48,
  "unique_events_total": 576,
  "new_test_cases": 84,
  "generated_sequences_in_test_run": 24,
  "fresh_store_executions_in_test_run": 96,
  "published_prefixes_in_test_run": 4608,
  "historical_cutoffs_total": 600
}

```

### docs-status

```json
{
  "label": "docs-status",
  "cwd": "D:\\ProjectNyx-wt-read-hardening",
  "command": [
    "D:\\ProjectNyx-wt-read-hardening\\.venv\\Scripts\\python.exe",
    "-B",
    "scripts/check_docs.py",
    "--status"
  ],
  "started_utc": "2026-10-15T23:48:57.094584+00:00",
  "elapsed_seconds": 0.13625350000074832,
  "exit_code": 0,
  "log": "docs-status.log"
}
```

```text
ACCEPTED ADRS
0001 | 0001 — An `observation_recorded` event resolves its belief to `verified` | Accepted — ratified by Josh, 2026-07-12 | Implemented in `src/nyx/projection.py`: `_state_for_origin` maps `observed` to `verified`, and `fold...
0002 | 0002 — Payloads are stored as plaintext in v0; at-rest encryption is Phase 3 | Accepted — 2026-07-12 | `src/nyx/events.py` `build_event` emits plaintext canonical JSON in `Payload.ciphertext` with `redac...
0003 | 0003 — Genesis sentinels and hash-material delimiters | Accepted — 2026-07-12 | `src/nyx/hashing.py` implements the unit separator in `idempotency_key` and the empty predecessor co...
0004 | 0004 — `correction_appended` supersedes via a `superseding_events` column; the belief head is never marked `superseded` | Accepted — ratified by Josh, 2026-07-13; superseded in part by [ADR 0018](0018-correction-supersedes-candidates.md) for projector "1" correction payloads and supersession representation. | Legacy projector "0" corrections ship through `skeleton.record_correction`, `projection.fold` and `s...
0005 | 0005 — Backdated corrections fail loud (interim), pending a decision on their semantics | Accepted as an **INTERIM STANCE** — ratified by Josh, 2026-07-13. | For projector "0", `skeleton._record` calls `projection.assert_not_backdated` before building/append...
0006 | 0006 — `occurred_at` comparison is instant-based, never lexical | Accepted — ratified by Josh, 2026-07-13 | `projection._instant` implements instant-based comparison for the legacy value-recency and correctio...
0007 | 0007 — `payloads` is keyed by `event_id`, not `payload_hash` (§4's DDL is the bug) | Accepted — ratified by Josh, 2026-07-13 | `schema.sql` keys `payloads` by `event_id` and retains a non-unique `idx_payloads_corroboration` on ...
0009 | 0009 — Python 3.14 re-adopted as the target (the downgrade P0 was never enforced) | Accepted — ratified by Josh, 2026-07-15 | `pyproject.toml` declares `requires-python = ">=3.14"`; the repository's `.venv` and full pytest sui...
0010 | ADR 0010: Projection Parameters — as_of, projector_version, projected_as_of | Accepted; superseded in part by [ADR 0030](0030-sole-writer-and-positional-fields.md), only section 1a's ordinary writer timestamp assignment and its backward-clock refusal acceptance case. | `projection.project` and `project_snapshot` apply inclusive `recorded_at` cutoffs and dispatch the r...
0011 | ADR 0011: Database Schema Versioning | Accepted; superseded in part by [ADR 0016](0016-schema-version-2.md) and then [ADR 0017](0017-schema-version-3.md), only the supported database schema version. | `storage.init_db` explicitly authorizes fresh creation and atomically creates schema/metadata; exist...
0012 | ADR 0012: Whole-View Equality | Accepted | Implemented in `storage.evaluate_whole_view`, with acceptance coverage in `tests/test_whole_view_equ...
0013 | ADR 0013: Cross-Belief Identity Semantics | Accepted | Partial under projector "1": distinct recorded identity scopes, candidate evidence/provenance, and s...
0014 | ADR 0014: Cross-Belief Reducer Shape and Hash Lineage | Accepted; superseded in part by [ADR 0015](0015-candidate-scoped-verification.md), section 4's differing-state refusal, its corresponding acceptance case, and references to that verification boundary as unresolved. | The snapshot/delta seam, structured lineage, append freshness, derived progress, atomic publication,...
0015 | ADR 0015: Candidate-Scoped Verification | Accepted | Partial under projector "1": ClaimCandidates retain individual support and verification, with candid...
0016 | ADR 0016: Database Schema Version 2 | Accepted; superseded in part by [ADR 0017](0017-schema-version-3.md), only the selection of supported database schema version 2. | The derived-progress record is implemented in `schema.sql` and `src/nyx/storage.py`. The current sup...
0017 | ADR 0017: Database Schema Version 3 | Accepted | Implemented in `schema.sql` and `src/nyx/storage.py`, including older-version refusal and schema-val...
0018 | ADR 0018: Corrections Supersede Explicit Candidates | Accepted | Deferred under [ADR 0023 section 5](0023-stage-two-contract.md#5-corrections-are-deferred-under-vers...
0019 | ADR 0019: Identity Bootstrap | Accepted; superseded in part by [ADR 0021](0021-bootstrap-link-treatment.md) for section 5's bootstrap link treatment, and by [ADR 0023 section 3](0023-stage-two-contract.md#3-existing-mentions-and-the-bootstrap-cost) for the unconditional two-appends-per-fact consequence. | Scoped mention/subject bootstrap, separate observations, recorded identities, and retries ship under...
0020 | ADR 0020: Multi-User Authority Remains Undecided | Accepted | Dependent implementation is blocked pending later decisions.
0021 | ADR 0021: Bootstrap Link Treatment | Accepted | Constitutive bootstrap links and their no-confidence treatment ship under projector "1" in `src/nyx/...
0022 | ADR 0022: Belief Container Uniqueness | Accepted | Implemented for stage two in writer lookup, append/replay validation, and the current-only partial u...
0023 | ADR 0023: Stage Two Contract | Accepted; section 4's undifferentiated submitted-contents retry rule is superseded in part by [ADR 0030](0030-sole-writer-and-positional-fields.md), which separates caller-owned semantic contents from writer-assigned positional fields. | The original stage-two contract is implemented under projector "1" in `src/nyx/ingestion.py`, `src/n...
0024 | ADR 0024: No Authoritative Head | Accepted | Implemented under projector "1" in `src/nyx/reducer.py` and the candidate/scalar read APIs in `src/n...
0025 | ADR 0025: Incremental Result Commitment | Accepted; section 1's API-default guarantee is superseded in part by [ADR 0032](0032-explicit-stage-two-projector-selection.md), and its single supported database schema version by [ADR 0035](0035-adr-0034-implementation-boundaries.md) section 1. | Implemented under projector "2" in `src/nyx/merkle.py`, `src/nyx/committed.py`, `src/nyx/committed_s...
0026 | ADR 0026: Usage Is Not Evidence | Accepted | Binding boundary; no usage-log or activation subsystem is implemented by this decision.
0030 | ADR 0030: Sole Writer and Positional Event Assignment | Accepted — maintainer acceptance 2026-09-23 | Complete in commit `30a4e5d5ee9ee56c0670ec6e50788e5cc523eda5`: sole-writer exclusion, semantic/posit...
0031 | ADR 0031: Report-Scoped External Content | Accepted — ratified by the maintainer, 2026-10-04 | Slice 1 complete in (B) commits `3e52ac2e359b61e36a74e69df36e518605870538`, `b5319a76643cf8e3bacd40a...
0032 | ADR 0032: Explicit Stage-Two Projector Selection | Accepted — maintainer acceptance 2026-09-23 | Complete in commit `55b5af0e8fefbf71a55adcf4a89f4e6464094584`: explicit stage-two parameters, requir...
0033 | ADR 0033: Projector 0 value and verifiability domain | Accepted — ratified by the maintainer, 2026-09-28 | Complete in (B) commit `9565f56ffb26434a96b5fcf864762b406af1a3a9`; shared legacy admission checks an...
0034 | ADR 0034: Forward State Transitions Under Projector "3" | Accepted — ratified by the maintainer, 2026-10-05; implementation boundaries for the schema version, the R9 dependency check and section 6 report corrections are set by [ADR 0035](0035-adr-0034-implementation-boundaries.md). | Complete under projector "3" in (B) commits `d85bd970af17035e4ab477c2d3565d0ad3eedd2c`, `82c3aa67a13...
0035 | ADR 0035: ADR 0034 Implementation Boundaries — Schema, Dependencies, Report Corrections | Accepted — ratified by the maintainer, 2026-10-05; section 1 amended the same day for schema-5 committed-table constraints | Complete in (B) commits `82c3aa67a1327a1d9720afa973a2fa68a9c79c51`, `55f8ec295804be160ff987bccd16fff...

PROPOSED ADRS (DO NOT IMPLEMENT)
0027 | ADR 0027: Stage Three Authority and Acceptance | Proposed — draft for review; not ratified and does not authorize implementation. | None. This file proposes one shared acceptance contract for merge, split and corroboration, includin...
0028 | ADR 0028: Redaction and Crypto-Shredding | Proposed — draft for review; not ratified and does not authorize implementation. | None. Encryption, key custody, authorization, typed sentinel, erasure sweep, proof plumbing and reco...
0029 | ADR 0029: Dream Emission Semantics | Proposed — draft for review; not ratified and does not authorize implementation. | None. This draft records the settled Dream boundaries for ratification review and identifies the dec...
0036 | ADR 0036: Strict Payload Keys Under a New Explicit Projector | Proposed - draft for review; not ratified and does not authorize implementation | None. Proposed ADR only; no parser, projector, schema, diagnostic or migration is implemented by thi...
0037 | ADR 0037: O3 Public Mention Discovery in a Same-Database Derived Index | Proposed - draft for review; not ratified and does not authorize implementation | None. No listing API, search index, schema migration, test or usage recorder is implemented by this ...

SUPERSEDED
0008 | 0008 — The `fold` signature structurally cannot express a cross-belief event (Phase 2 blocker) | Superseded by ADR 0014 (accepted 2026-09-08). | This superseded blocker has no separate handler. ADR 0014's `Snapshot`/`EventDelta` reducer seam shi...

OPEN GAPS
Correctness gaps
  Redaction breaks the write path and replay
  Whole-view equality across live materialized beliefs and replay
Schema / operational gaps
  Listing and search surface — O3, unbuilt
  Whole-store growth — O4, measurement available; retention deferred
  Corpus restriction — R4, policy in force; erasure unbuilt
  Rename identity — scoped subjects retained
  Queue 6 mutation campaign: verifier scope and remaining escapes
  Queue 6 crash campaign: legacy rebuild API boundary
  Duplicate-key payload text is accepted outside canonical writer preparation
  Cross-language canonicalization and verifier independence remain unproven
  Timestamp canonicalization belongs at the ingestion boundary
Undecided semantics (fail loud, on purpose)
  Backdated corrections
  Origin → verification_state beyond `observed`
  Candidate corrections and target eligibility
  Existing-subject association and multi-user authority
  Mention correction
  Support attachment to an existing ClaimCandidate
  Retention, coalescing, and temporal resolution
  Usage recording
  Dream emission semantics and operational contracts
  Additional scalar belief reads
  Later link treatment and support-dependent verification transitions

RESOLVED OR PARTLY RESOLVED (headings only)
Cross-belief reducer — seam implemented; merge/split handlers pending
  The legacy `fold` signature cannot express a cross-belief event — resolved for projector "1"
Correctness gaps
  Live stage-two publication cutoff — RV1, resolved
  Read/replay integrity and append parity — resolved
  Typed identity freshness and `is_stale` — resolved for stage two
  Version-2 snapshot read parity — resolved
  `project()` event dispatch — resolved for supported stages
  `as_of` / `projector_version` — resolved
Schema / operational gaps
  Stage-two projector defaults — E2, resolved by ADR 0032
  Writer concurrency and positional retries — E3/O1, resolved by ADR 0030
  External source-report scope — O2, slice 1 resolved
  Standalone replay verifier — resolved for shipped contracts
  Stage 1 verifiability null/empty refusal — resolved
  Database schema versioning — resolved
Undecided semantics (fail loud, on purpose)
  Projector 3 committed storage constraint — resolved

```

### docs-initial

```json
{
  "label": "docs-initial",
  "cwd": "D:\\ProjectNyx-wt-read-hardening",
  "command": [
    "D:\\ProjectNyx-wt-read-hardening\\.venv\\Scripts\\python.exe",
    "-B",
    "scripts/check_docs.py",
    "--fix-none"
  ],
  "started_utc": "2026-10-15T23:47:53.141496+00:00",
  "elapsed_seconds": 0.7979429999977583,
  "exit_code": 0,
  "log": "docs-initial.log"
}
```

```text
Baseline unchecked (outside design/): 83
UNCHECKED GAPS.md:191 [proposed_references] ADR 0036 reference requires human authority/context review
UNCHECKED GAPS.md:498 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED GAPS.md:577 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED GAPS.md:596 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED GAPS.md:622 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED GAPS.md:657 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED GAPS.md:847 [proposed_references] ADR 0029 reference requires human authority/context review
UNCHECKED GAPS.md:854 [proposed_references] ADR 0029 reference requires human authority/context review
UNCHECKED README.md:668 [proposed_references] ADR 0029 reference requires human authority/context review
UNCHECKED decisions/0027-stage-three-authority-and-acceptance.md:1 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0027-stage-three-authority-and-acceptance.md:219 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0027-stage-three-authority-and-acceptance.md:358 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0027-stage-three-authority-and-acceptance.md:547 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0027-stage-three-authority-and-acceptance.md:672 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0027-stage-three-authority-and-acceptance.md:683 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0027-stage-three-authority-and-acceptance.md:690 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0027-stage-three-authority-and-acceptance.md:703 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0027-stage-three-authority-and-acceptance.md:797 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0027-stage-three-authority-and-acceptance.md:859 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0027-stage-three-authority-and-acceptance.md:868 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0027-stage-three-authority-and-acceptance.md:902 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0027-stage-three-authority-and-acceptance.md:921 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:1 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:39 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:42 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:79 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:82 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:99 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:108 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:133 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:134 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:189 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:207 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:235 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:376 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:404 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:445 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:557 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:565 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:569 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:616 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:718 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:817 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:820 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:822 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:828 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:834 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:836 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:863 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:910 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:966 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0028-redaction-and-crypto-shredding.md:974 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0029-dream-emission-semantics.md:1 [proposed_references] ADR 0029 reference requires human authority/context review
UNCHECKED decisions/0029-dream-emission-semantics.md:9 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0029-dream-emission-semantics.md:75 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0029-dream-emission-semantics.md:157 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0029-dream-emission-semantics.md:163 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0031-source-report-claims.md:290 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED decisions/0031-source-report-claims.md:696 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED decisions/0036-strict-payload-keys.md:1 [proposed_references] ADR 0036 reference requires human authority/context review
UNCHECKED decisions/0037-o3-mention-discovery.md:1 [proposed_references] ADR 0037 reference requires human authority/context review
UNCHECKED spec/:1 [hash_formulas] Hash/serialization prose and formulas outside the supported SHA256 expression syntax require semantic review
UNCHECKED spec/NYX_ARCHITECTURE.md:7 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED spec/NYX_ARCHITECTURE.md:7 [proposed_references] ADR 0029 reference requires human authority/context review
UNCHECKED spec/NYX_ARCHITECTURE.md:15 [proposed_references] ADR 0029 reference requires human authority/context review
UNCHECKED spec/NYX_ARCHITECTURE.md:26 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED spec/NYX_ARCHITECTURE.md:29 [proposed_references] ADR 0029 reference requires human authority/context review
UNCHECKED spec/NYX_ARCHITECTURE.md:32 [proposed_references] ADR 0029 reference requires human authority/context review
UNCHECKED spec/NYX_ARCHITECTURE.md:35 [proposed_references] ADR 0029 reference requires human authority/context review
UNCHECKED spec/NYX_ARCHITECTURE.md:39 [proposed_references] ADR 0029 reference requires human authority/context review
UNCHECKED spec/NYX_ARCHITECTURE.md:40 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED spec/NYX_ARCHITECTURE.md:48 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED spec/NYX_ARCHITECTURE.md:63 [proposed_references] ADR 0029 reference requires human authority/context review
UNCHECKED spec/NYX_ARCHITECTURE.md:127 [proposed_references] ADR 0029 reference requires human authority/context review
UNCHECKED spec/NYX_ARCHITECTURE.md:171 [proposed_references] ADR 0029 reference requires human authority/context review
UNCHECKED spec/NYX_ARCHITECTURE.md:219 [proposed_references] ADR 0029 reference requires human authority/context review
UNCHECKED spec/NYX_ARCHITECTURE.md:243 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED spec/NYX_ARCHITECTURE.md:282 [proposed_references] ADR 0029 reference requires human authority/context review
UNCHECKED spec/NYX_ARCHITECTURE.md:421 [proposed_references] ADR 0029 reference requires human authority/context review
UNCHECKED spec/NYX_V0_IMPLEMENTATION.md:186 [hash_formulas] Unchecked formula SHA256(prior_hash || latest folded event_hash): invalid syntax (<unknown>, line 1)
UNCHECKED spec/NYX_V0_IMPLEMENTATION.md:315 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED spec/NYX_V0_IMPLEMENTATION.md:315 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED src/nyx/hashing.py:1 [serialization] Finite compatibility samples only; no Proposed wire/parser/crypto conformance or exhaustive number-format proof
Design unchecked (in design/): 103
UNCHECKED design/0027-b2-private-value-codec-ruling-brief.md:1 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b2-private-value-codec-ruling-brief.md:9 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b2-private-value-codec-ruling-brief.md:15 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b2-private-value-codec-ruling-brief.md:30 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b2-private-value-codec-ruling-brief.md:214 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b2-private-value-codec-ruling-brief.md:294 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED design/0027-b2-private-value-codec-ruling-brief.md:300 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b2-private-value-codec-ruling-brief.md:507 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:1 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:8 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:8 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:13 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:27 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:28 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:29 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:30 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:34 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:57 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:63 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:67 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:82 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:91 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:93 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:101 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:115 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:140 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:148 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:172 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:186 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:201 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:217 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:231 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:239 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:246 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:260 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:284 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:301 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:314 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:329 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:345 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:361 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:378 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:392 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:402 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:414 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:431 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:445 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:453 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:459 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:478 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:487 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:495 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:507 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:515 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:547 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:552 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:564 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:581 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:635 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:650 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:673 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:763 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:793 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:797 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:799 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:810 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:910 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-b3-compound-custody-ruling-brief.md:959 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:1 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:8 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:9 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:15 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:16 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:21 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:38 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:42 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:50 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:52 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:72 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:92 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:94 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:102 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:109 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:150 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:172 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:181 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:212 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:229 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:273 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:290 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:299 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:338 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:364 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:409 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:423 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/0027-gate1-worksheet.md:487 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/2026-09-22-review-and-next-steps.md:36 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/2026-09-22-review-and-next-steps.md:181 [proposed_references] ADR 0028 reference requires human authority/context review
UNCHECKED design/2026-09-22-review-and-next-steps.md:347 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/2026-10-03-adr-0031-worksheet.md:12 [proposed_references] ADR 0027 reference requires human authority/context review
UNCHECKED design/2026-10-14-adr-0036-0037-implementation-plan.md:6 [proposed_references] ADR 0036 reference requires human authority/context review
UNCHECKED design/2026-10-14-adr-0036-0037-implementation-plan.md:7 [proposed_references] ADR 0037 reference requires human authority/context review
UNCHECKED design/2026-10-14-adr-0036-0037-implementation-plan.md:10 [proposed_references] ADR 0036 reference requires human authority/context review
0 failures; 83 unchecked baseline; 103 unchecked in design/ (186 total)
Checked: links=1050, adr_markers=74, proposed_references=110, invariants=15, hash_formulas=4, legacy_schema=1, fences=36, readme_map=187, serialization=5

```

### targeted-initial

```json
{
  "label": "targeted-initial",
  "cwd": "D:\\ProjectNyx-wt-read-hardening",
  "command": [
    "D:\\ProjectNyx-wt-read-hardening\\.venv\\Scripts\\python.exe",
    "-m",
    "pytest",
    "tests/test_projector3_read_properties.py",
    "-q",
    "--basetemp=scratch/pytest-tmp"
  ],
  "started_utc": "2026-10-15T23:47:29.919663+00:00",
  "elapsed_seconds": 154.80311139999685,
  "exit_code": 0,
  "log": "targeted-initial.log"
}
```

```text
........................................................................ [ 85%]
............                                                             [100%]
84 passed in 154.37s (0:02:34)

```

### full-suite

```json
{
  "label": "full-suite",
  "cwd": "D:\\ProjectNyx-wt-read-hardening",
  "command": [
    "D:\\ProjectNyx-wt-read-hardening\\.venv\\Scripts\\python.exe",
    "-m",
    "pytest",
    "-q",
    "--basetemp=scratch/pytest-tmp"
  ],
  "started_utc": "2026-10-15T23:50:11.899866+00:00",
  "elapsed_seconds": 284.52397329999803,
  "exit_code": 0,
  "log": "full-suite.log"
}
```

```text
........................................................................ [  3%]
........................................................................ [  6%]
...............................................s........................ [  9%]
........................................................................ [ 12%]
........................................................................ [ 16%]
........................................................................ [ 19%]
........................................................................ [ 22%]
........................................................................ [ 25%]
........................................................................ [ 28%]
........................................................................ [ 32%]
........................................................................ [ 35%]
........................................................................ [ 38%]
........................................................................ [ 41%]
........................................................................ [ 44%]
........................................................................ [ 48%]
........................................................................ [ 51%]
........................................................................ [ 54%]
........................................................................ [ 57%]
........................................................................ [ 60%]
........................................................................ [ 64%]
........................................................................ [ 67%]
........................................................................ [ 70%]
........................................................................ [ 73%]
........................................................................ [ 77%]
........................................................................ [ 80%]
........................................................................ [ 83%]
........................................................................ [ 86%]
........................................................................ [ 89%]
........................................................................ [ 93%]
.........................................ss.ss.ss....................... [ 96%]
.ss..................................................................... [ 99%]
...........                                                              [100%]
2234 passed, 9 skipped in 284.04s (0:04:44)

```

### docs-final

```json
{
  "label": "docs-final",
  "cwd": "D:\\ProjectNyx-wt-read-hardening",
  "command": [
    "D:\\ProjectNyx-wt-read-hardening\\.venv\\Scripts\\python.exe",
    "-B",
    "scripts/check_docs.py",
    "--fix-none",
    "--quiet"
  ],
  "started_utc": "2026-10-15T23:50:22.094706+00:00",
  "elapsed_seconds": 0.7025689999936731,
  "exit_code": 0,
  "log": "docs-final.log"
}
```

```text
0 failures; 83 unchecked baseline; 103 unchecked in design/ (186 total)

```

### scope

```json
{
  "label": "scope",
  "cwd": "D:\\ProjectNyx-wt-read-hardening",
  "command": [
    "D:\\ProjectNyx-wt-read-hardening\\.venv\\Scripts\\python.exe",
    "scratch/check_scope.py"
  ],
  "started_utc": "2026-10-15T23:55:04.261053+00:00",
  "elapsed_seconds": 0.16798520000156714,
  "exit_code": 0,
  "log": "scope.log"
}
```

```text
$ git status --short
A  tests/test_projector3_read_properties.py
exit=0
$ git diff --cached --stat
 tests/test_projector3_read_properties.py | 370 +++++++++++++++++++++++++++++++
 1 file changed, 370 insertions(+)
exit=0
$ git diff --cached --check
exit=0
$ git diff --exit-code origin/main -- src decisions spec schema.sql pyproject.toml
exit=0
$ git config --get core.hooksPath
.githooks
exit=0
test_file_sha256=4ce4f8d998408bb6f700ad3f7d4eeef9d4e6e6234222febc338ab20a3a9c0d19
Only the requested test file is staged; protected source, authority, schema and dependency files equal origin/main.

```

### commit-tests

```json
{
  "label": "commit-tests",
  "cwd": "D:\\ProjectNyx-wt-read-hardening",
  "command": [
    "git",
    "commit",
    "-m",
    "test: harden projector 3 public reads with seeded histories"
  ],
  "started_utc": "2026-10-15T23:55:05.295392+00:00",
  "elapsed_seconds": 0.7642981999961194,
  "exit_code": 0,
  "log": "commit-tests.log"
}
```

```text
0 failures; 83 unchecked baseline; 103 unchecked in design/ (186 total)
[sol/read-hardening-2026-10-15 3a042bb] test: harden projector 3 public reads with seeded histories
 1 file changed, 370 insertions(+)
 create mode 100644 tests/test_projector3_read_properties.py

```
