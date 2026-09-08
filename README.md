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
is accepted; its implementation remains pending.

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
