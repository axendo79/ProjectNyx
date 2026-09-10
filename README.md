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

The ADR 0023 scaling hazard is observable: a local in-memory probe with 32, 64,
and 128 agreeing observations on one belief serialized approximately 0.88, 3.38,
and 13.23 MB of cumulative lineage material and took 0.05, 0.18, and 0.70 seconds.
The probe included event construction, reduction, diagnostic lineage serialization,
and snapshot application, not database I/O. This demonstrates quadratic growth in
this workload, not production throughput. Complete lineage coverage is retained;
retention and coalescing remain undecided.

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
runtime is 3.14.2. Package metadata still declares `>=3.11`; that declaration does
not establish a tested compatibility range.

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
| `schema.sql` | SQLite schema and append-only triggers. |
| `spec/` | Architecture and implementation specifications, plus supporting documents. |
| `decisions/` | Numbered ADRs; status distinguishes accepted decisions from recorded blockers. |
| `design/` | Unratified design direction, including temporal/activation material. |
| `GAPS.md` | Verified findings and their resolution or implementation status. |
| `AGENTS.md` | Repository authority and contribution rules. |
| `pyproject.toml` | Packaging, development dependencies, and pytest configuration. |

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
