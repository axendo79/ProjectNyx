# Nyx

Nyx is an epistemic kernel: a core for recording assertions, preserving their
provenance, and deriving what a system currently believes. This repository
contains a Python/SQLite Phase 1 walking skeleton, exercised through Python APIs
and tests.

## Model and current implementation

**Layer A** is the durable event log. SQLite triggers prevent updates and deletes
of event rows. Event envelopes are hash-chained, with payloads stored separately.
Corrections append new events rather than rewriting earlier observations.

**Layer B** is derived synthesis: it may read Layer A but cannot turn its own output
into world evidence or mutate the log. The current code implements deterministic
belief projection and a materialized Resolved View; it does not implement the
broader synthesis subsystems described in the architecture.

The implemented path validates observations through Immune Stage 1, appends them
with idempotency protection, updates the entity-event index, folds the event into
a belief, and reads the result. It also handles corrections, late-arriving
observations, historical recording-time cutoffs, and projector-version dispatch.
Database creation requires explicit authorization, and each connection validates
schema metadata. Append refuses backward recording timestamps.

The governing invariants are append-only provenance, reconstructible derived
state, deterministic projection for a fixed log/time/version, and no silent
promotion of derived claims into world truth. Current event handling supports
observed-origin value-setting events; unsupported semantics fail loudly. See
[GAPS.md](GAPS.md) for concrete limitations, including redaction and cross-belief
handling. The [shared-time whole-view equality contract](decisions/0012-whole-view-equality.md)
is implemented by `nyx.storage.evaluate_whole_view(conn, as_of, projector_version="0")`.
This explicit operation reconstructs from the log; ordinary materialized reads
are unchanged.

[Stage two](decisions/0023-stage-two-contract.md) is available as projector version
`"1"`. A separate `entity_mention_recorded` event creates a mention, its scoped
subject, and a `constitutive` link with no numeric confidence. Observations name
that mention and subject, an exact opaque `property_id`, the current `belief_id`,
and fresh `claim_candidate_id` values. Each ClaimCandidate retains its own support
and verification. Version `"0"` remains the default with its original fold,
correction behavior, lineage, and byte fixtures.

Version `"1"` exposes candidate collections with
[no authoritative head](decisions/0024-no-authoritative-head.md). Later observations
do not select a value by recency. Scalar belief requests with multiple candidates
refuse even when the values agree. Use `storage.read_claim_candidate_value` for a
named candidate. Single-candidate scalar belief requests also remain outside the
implemented read contract; naming the candidate is available. Corrections, merges,
splits, verification approvals, and associations with existing subjects refuse at
both append and replay in this stage.

The new reducer reads a consistent pre-event snapshot and returns one complete
event delta. Its structured lineage covers predecessor hashes, resulting belief
content, candidate support and verification, and the observation and identity
records explaining the result. Set collections use canonical UTF-8 ordering.
`projection.project_snapshot(log, as_of)` returns the complete version `"1"`
snapshot, including mention-only prefixes; `project` and `evaluate_whole_view`
retain their belief-mapping return shape. `storage.read_snapshot` reads the complete
materialization without replay.

The version `"1"` writer uses `ingestion.prepare_mention` and
`ingestion.prepare_observation`, then submits the returned `(Envelope, Payload)`
pair through `ingestion.submit(conn, pair, as_of)` or the skeleton wrappers
`record_mention(path, pair)` and `record_observation(path, pair, "1")`. Retain the
complete pair before append and reuse it on retry; preparation is performed once,
not again on retry. The observation preparer looks up existing belief IDs and
refuses a conflicting supplied ID. For a new pair, supply a fresh belief ID.
Every claim supplies its fresh candidate ID, mention, subject, property, value,
and verifiability. The claim's containing observation is its explicit support.
Bootstrap takes two appends; later observations through an existing mention take
one. A committed mention remains valid if its observation never commits.

The [standalone lineage-scaling probe](scripts/probe_lineage_scaling.py) measures
the ADR 0023 implementation hazard. Run it from the checkout root, outside pytest:

```powershell
.\.venv\Scripts\python.exe -B scripts/probe_lineage_scaling.py
```

Each sample starts empty, creates one mention, then records N agreeing observations
on one belief. The script fixes IDs, timestamps, source metadata, and payloads and
uses the checkout's production reducer and canonical serializer. It counts each
changed belief's lineage record once as UTF-8 bytes and verifies that record
against the reducer's hash. Three independent runs per size must agree on byte
counts and final lineage; elapsed time is reported as their median. Use `--sizes`
and `--repeat` to vary the workload, for example `--sizes 16 32 --repeat 5`.

Recorded on Python 3.14.2 / Windows 11 on 2026-09-11 with the default arguments:

| Observations | Cumulative lineage bytes | MB (1,000,000 bytes) | Median seconds |
|---:|---:|---:|---:|
| 32 | 914,109 | 0.914109 | 0.055314 |
| 64 | 3,500,237 | 3.500237 | 0.199777 |
| 128 | 13,692,578 | 13.692578 | 0.754273 |

These replace the earlier undocumented probe measurements. Byte counts are
reproducible for this fixed workload and implementation; timings vary with the
machine and run. Timing includes event construction, reduction, diagnostic lineage
serialization/hash verification, and snapshot application. It excludes database
I/O. The byte metric is cumulative lineage material, not peak memory or database
size. Doubling observations approaches four times the lineage bytes in this
workload; these timings are not production throughput. For the governing scope
and unresolved work, see [ADR 0023](decisions/0023-stage-two-contract.md).

`storage.materialize_pending(conn, as_of, projector_version="1")` publishes each
pending event and its progress atomically after append. `read_belief(...,
projector_version="1")` includes a `stale` label; `read_belief_status` exposes the
belief, append freshness, and derived progress separately, including an appended
belief that has no materialization yet. These reads do not replay. After a crash,
use `storage.rebuild_projection(conn, as_of, projector_version="1")` for full
replay from Layer A; it replaces the selected new-version materialization in one
transaction. The walking-skeleton calls drive publication synchronously after
the separate append commit; they do not start a background worker.

Database schema version `3` is required under
[ADR 0017](decisions/0017-schema-version-3.md). Version-1 and version-2 databases are refused
unchanged; there is no migration, and recreation is an operator action.

## Install and run the suite

Use Python 3.14, the accepted target in
[ADR 0009](decisions/0009-python-314-re-adopted-as-target.md). The recorded development
runtime is 3.14.2. Package metadata declares `>=3.14`; the suite has been run on
3.14.2, not a matrix of later Python versions.

From a repository checkout, in PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

Runtime code uses the Python standard library; the development extra installs
pytest. Run from a checkout: storage currently locates `schema.sql` at the
repository root. The tests create temporary databases and need no model service.
All tests must pass; the suite size is not a fixed acceptance threshold.

For a fresh database, call `nyx.storage.init_db(path, create=True)` and close the
returned connection. Ordinary `init_db(path)` calls validate an existing database;
they never create or auto-stamp one. `nyx.skeleton.record_observation` and
`record_correction` operate on an initialized database. There is no application
CLI, `/audit`, or `/selftest` interface in the current repository.

## Repository layout

| Path | Contents |
|---|---|
| `src/nyx/` | Event types, storage, projection, hashing, validation, and the walking-skeleton APIs. Some broader interfaces remain stubs. |
| `tests/` | Storage, event, projection, correction, and invariant regression tests. |
| `scripts/` | Standalone diagnostic probes, outside pytest discovery. |
| `schema.sql` | SQLite schema and append-only triggers. |
| `spec/` | Architecture and implementation specifications, plus supporting documents. |
| `decisions/` | Numbered ADRs; status distinguishes accepted decisions from recorded blockers. |
| `design/` | Unratified design direction, including temporal/activation material. |
| `GAPS.md` | Verified findings and their resolution or implementation status. |
| `AGENTS.md` | Repository authority and contribution rules. |
| `pyproject.toml` | Packaging, development dependencies, and pytest configuration. |

## Decision-to-code map

This is the single navigation map, kept beside the shipped-state overview so code
and test pointers can be updated together. ADRs remain the authority; this table
does not reproduce their decisions or replace their Status/Implementation lines.
Update the relevant row when moving a handler or changing its acceptance coverage.
Pointers use file and symbol names rather than line numbers that shift on edits.

| ADR | Implementation locations | Executable coverage |
|---|---|---|
| [0001](decisions/0001-observation-recorded-resolves-to-verified.md) | [projection.py] `_state_for_origin`, `fold`; [reducer.py] `reduce` | [test_walking_skeleton.py](tests/test_walking_skeleton.py), `test_resolved_belief_fields`; stage-two `test_unworked_origin_still_refuses` |
| [0002](decisions/0002-payload-stored-plaintext-in-v0.md) | [events.py](src/nyx/events.py) `build_event`; [storage.py] `read_all_events` | [test_walking_skeleton.py](tests/test_walking_skeleton.py) exercises payload round trips; no dedicated plaintext-storage assertion |
| [0003](decisions/0003-genesis-sentinels-and-hash-material-delimiters.md) | [hashing.py] `_SEP`, `idempotency_key`, `event_hash`; [projection.py] `_GENESIS_VIEW_HASH`, `fold` | [test_walking_skeleton.py](tests/test_walking_skeleton.py); stage-two `test_version_zero_golden_bytes_and_no_retrofit` and [version0_ordinary.json](tests/fixtures/version0_ordinary.json) |
| [0004](decisions/0004-correction-appended-supersedes-via-superseding-events.md) | [projection.py] `fold`; [skeleton.py] `record_correction`; [storage.py] `_upsert_legacy_belief` | [test_correction_appended.py](tests/test_correction_appended.py) |
| [0005](decisions/0005-backdated-corrections-fail-loud-pending-semantics.md) | [projection.py] `assert_not_backdated`; [skeleton.py] `_record` | [test_correction_appended.py](tests/test_correction_appended.py), `test_backdated_correction_raises`, `test_backdated_correction_does_not_poison_layer_a` |
| [0006](decisions/0006-occurred-at-comparison-is-instant-based-not-lexical.md) | [projection.py] `_instant`, `fold`, `assert_not_backdated` | [test_occurred_at_ordering.py](tests/test_occurred_at_ordering.py) |
| [0007](decisions/0007-payloads-keyed-by-event-id-not-payload-hash.md) | [schema.sql](schema.sql) `payloads`, `idx_payloads_corroboration`; [storage.py] `safe_append_event` | [test_corroboration_payload_identity.py](tests/test_corroboration_payload_identity.py) |
| [0008](decisions/0008-fold-signature-cannot-express-cross-belief-events.md) | Historical blocker; implementation navigation is in row 0014 | No separate handler or test suite for this superseded blocker |
| [0009](decisions/0009-python-314-re-adopted-as-target.md) | [pyproject.toml](pyproject.toml) `requires-python` | Full suite on the documented runtime; no interpreter-version matrix |
| [0010](decisions/0010-projection-parameters.md) | [projection.py] `PROJECTORS`, `project`, `project_snapshot`; [storage.py] `safe_append_event` | [test_projection_parameters.py](tests/test_projection_parameters.py), [test_recorded_at_monotonicity.py](tests/test_recorded_at_monotonicity.py) |
| [0011](decisions/0011-database-schema-versioning.md) | [storage.py] `init_db`, `_validate_schema`; [schema.sql](schema.sql) `schema_meta` | [test_database_schema_versioning.py](tests/test_database_schema_versioning.py) |
| [0012](decisions/0012-whole-view-equality.md) | [storage.py] `evaluate_whole_view`; [projection.py] `project` | [test_whole_view_equality.py](tests/test_whole_view_equality.py); stage-two `test_complete_incremental_replay_every_prefix_and_recovery` |

In the remaining rows, all named tests are in
[test_reducer_boundary.py](tests/test_reducer_boundary.py), unless another file is
linked. Despite its name, that file covers **bootstrap, candidates, property
identity, refusals, retries, publication, and recovery**, as well as reducer purity
and lineage. Use a named case directly with
`python -m pytest tests/test_reducer_boundary.py::test_bootstrap_mention_only_and_confidence -q`.
These are navigation examples, not a claim that every ADR acceptance case is
implemented; refusal tests and supplied-state fixtures do not establish working
merge, split, approval, or authority handlers.

| ADR | Handler or related implementation | Tests to start with |
|---|---|---|
| [0013](decisions/0013-cross-belief-identity-semantics.md) | [reducer.py] `reduce`, `evidence_event_ids`; [storage.py] typed read functions. Merge/split and successor-resolution handlers are absent. | `test_same_spelling_in_distinct_id_scopes_never_aliases`, `test_typed_reads_never_search_other_id_scopes`, `test_no_head_named_candidate_and_event_evidence_scope`, `test_deferred_events_refuse_both_boundaries` |
| [0014](decisions/0014-cross-belief-reducer-and-hash-lineage.md) | [reducer.py] `Snapshot`, `EventDelta`, `reduce`; [hashing.py] `belief_lineage`, `canonical_set`; [storage.py] `_append_stage_two`, `_publish_delta`, `materialize_pending`, `read_belief_status`, `rebuild_projection` | `test_snapshot_detached_pure_and_no_clock_or_allocation`, `test_lineage_complete_result_and_pre_event_dependencies`, `test_append_progress_freshness_uses_entity_not_belief_spelling`, `test_atomic_publication_at_every_record_kind`, `test_recovery_ignores_corrupt_snapshot_and_rolls_back_failure`, `test_two_connections_cannot_authorize_against_old_append_position` |
| [0015](decisions/0015-candidate-scoped-verification.md) | [reducer.py] `canonical_claim_candidates`, `evidence_event_ids`, `reduce`. Later standing/approval handlers are absent. | `test_same_value_different_standing_and_identity_paths_survive` (supplied-state fixture), `test_no_head_named_candidate_and_event_evidence_scope`, `test_lineage_covers_candidate_contents_with_predecessors_fixed` |
| [0016](decisions/0016-schema-version-2.md) | [schema.sql](schema.sql) `derived_progress`; [storage.py] `_publish_delta`, `_read_snapshot`; current schema selection is in row 0017 | `test_append_progress_freshness_uses_entity_not_belief_spelling`, `test_atomic_publication_at_every_record_kind`; [test_database_schema_versioning.py](tests/test_database_schema_versioning.py) |
| [0017](decisions/0017-schema-version-3.md) | [storage.py] `DATABASE_SCHEMA_VERSION`, `_validate_schema`; [schema.sql](schema.sql) `projected_*` tables | `test_version_two_existing_database_refuses_byte_unchanged`; [test_database_schema_versioning.py](tests/test_database_schema_versioning.py) |
| [0018](decisions/0018-correction-supersedes-candidates.md) | No version-"1" correction handler; refusal boundaries in [storage.py] `_append_stage_two` and [reducer.py] `reduce` | `test_deferred_events_refuse_both_boundaries`; successful candidate-correction coverage is absent |
| [0019](decisions/0019-identity-bootstrap.md) | [ingestion.py] `prepare_mention`, `prepare_observation`, `submit`; [reducer.py] `reduce`; [skeleton.py] `record_mention`, `_record_stage_two` | `test_bootstrap_mention_only_and_confidence`, `test_new_mentions_with_identical_text_and_different_actors_are_isolated`, `test_retained_retry_mention_survives_and_no_remint`, `test_writer_lookup_and_skeleton_two_then_one_events` |
| [0020](decisions/0020-multi-user-authority-undecided.md) | No authority-policy handler; [reducer.py] `_fields`, `reduce` and [storage.py] `_append_stage_two` provide current rejection boundaries | `test_no_implicit_support_authority_or_other_candidate_roles`, `test_deferred_events_refuse_both_boundaries`; no authority-model acceptance suite |
| [0021](decisions/0021-bootstrap-link-treatment.md) | [reducer.py] `identity_confidence_ceiling`, `reduce`; [schema.sql](schema.sql) `projected_entity_links` | `test_bootstrap_mention_only_and_confidence`, `test_new_mention_cannot_reuse_identity_or_invent_defaults` |
| [0022](decisions/0022-belief-container-uniqueness.md) | [ingestion.py] `prepare_observation`; [storage.py] `lookup_current_belief_id`; [reducer.py] `Snapshot.current_belief`, `reduce`; [schema.sql](schema.sql) `idx_current_subject_property` | `test_exact_properties_and_current_only_uniqueness`, `test_stale_lookup_duplicate_pair_and_reused_event_id`, `test_writer_lookup_and_skeleton_two_then_one_events` |
| [0023](decisions/0023-stage-two-contract.md) | [ingestion.py] preparation/submission functions; [reducer.py] `reduce`; [storage.py] `_append_stage_two`; [lineage probe](scripts/probe_lineage_scaling.py) | `test_exact_properties_and_current_only_uniqueness`, `test_missing_explicit_claim_contents_refuse`, `test_one_event_same_belief_multiple_claims`, `test_retained_retry_mention_survives_and_no_remint`, `test_deferred_events_refuse_both_boundaries`. The probe is outside the suite. |
| [0024](decisions/0024-no-authoritative-head.md) | [reducer.py] `scalar_belief_value`, `reduce`; [storage.py] `read_belief_scalar`, `read_claim_candidate_value` | `test_no_head_named_candidate_and_event_evidence_scope`, `test_one_event_same_belief_multiple_claims`, `test_cutoffs_time_only_lineage_and_unrelated_beliefs` |

[projection.py]: src/nyx/projection.py
[reducer.py]: src/nyx/reducer.py
[hashing.py]: src/nyx/hashing.py
[storage.py]: src/nyx/storage.py
[skeleton.py]: src/nyx/skeleton.py
[ingestion.py]: src/nyx/ingestion.py

## Authority and contribution rules

[AGENTS.md](AGENTS.md) defines the authority order:

1. Accepted numbered ADRs supersede the specifications where they conflict.
2. [NYX_ARCHITECTURE.md](spec/NYX_ARCHITECTURE.md) governs what and why;
   [NYX_V0_IMPLEMENTATION.md](spec/NYX_V0_IMPLEMENTATION.md) governs mechanics,
   including schema, algorithms, defaults, and tests.
3. `GAPS.md` records findings; it does not authorize out-of-scope fixes.
4. `design/` is non-authoritative. It does not authorize implementation, supply
   missing defaults, or supersede accepted decisions.

`CLAUDE.md` was written for a different agent and is explicitly excluded by
AGENTS.md. Implementation must stop at unresolved required decisions rather than
inventing semantics. This README is an entry point, not an additional authority.
