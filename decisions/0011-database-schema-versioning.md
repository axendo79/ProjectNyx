# ADR 0011: Database Schema Versioning

Status: Accepted

Date: 2026-09-08

## Context

Schema compatibility is a deterministic storage invariant, not something the model, memory system, or an initialization routine should infer or repair. The epistemic system can reason about uncertainty; the database contract should not.

The contract distinguishes **at most one row** from **exactly one valid row**. Checking every `init_db()` call is necessary, but it is not sufficient to detect every database swap during a running process.

## 1. Exact schema: include the diagnostics

`created_at` and `created_by` are retained. Their storage cost is negligible, and they are useful when diagnosing an unexplained database. They are initialization diagnostics, not evidence of authorship, identity, or an audit trail.

```sql
CREATE TABLE schema_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL CHECK (typeof(version) = 'integer' AND version > 0),
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL
);
```

The initial row is inserted explicitly during fresh initialization:

```sql
INSERT INTO schema_meta (id, version, created_at, created_by)
VALUES (1, 1, :created_at, :created_by);
```

`created_at` is a UTC RFC 3339 timestamp supplied by the initialization code. `created_by` is a stable software identifier, such as `nyx-core/<actual-build>`, not a guessed human identity. Neither field is used for compatibility decisions.

No `CHECK (version = 1)` is added. The table remains capable of representing future versions; the runtime enforces which version it supports. The positive-integer check rejects zero as an invalid new value, while validation still distinguishes an existing explicit-zero value from missing metadata.

**SQLite type-affinity requirement:** Validation checks the actual storage type of `version` using `typeof(version) = 'integer'`, not whether the value can be coerced to an integer. The same requirement applies to the diagnostic fields: validation checks `typeof(created_at) = 'text'` and `typeof(created_by) = 'text'`, not whether their values can be coerced to text.

**Structural validation requirement:** Validation compares CHECK constraints as well as column names and declared types. Metadata must contain both required CHECK constraints, `CHECK (id = 1)` and `CHECK (typeof(version) = 'integer' AND version > 0)`, and must not contain the prohibited `CHECK (version = 1)`. Generated or extra columns are rejected.

### The single-row invariant

`id INTEGER PRIMARY KEY CHECK (id = 1)` guarantees **at most one row**, not exactly one. A table with zero rows satisfies that constraint.

The complete invariant is:

> `schema_meta` contains exactly one row, with `id = 1`, a valid integer version, and the required diagnostic fields. Any violation is an initialization error. The system must not insert, repair, or replace metadata in an existing database.

The validator reads the actual row count and validates the row. Validation does not rely on `LIMIT 1`, because that can conceal extra rows in a malformed legacy table. No delete-prevention triggers are added by this ADR; the explicit refusal policy and operator-controlled recovery are clearer than introducing another mechanism that must later be bypassed.

## 2. Check every `init_db()` call, with a defined scope

> Every `init_db()` invocation validates schema compatibility before performing any initialization, write, migration, or projection operation. A successful earlier invocation does not exempt a later invocation from validation.

That catches a database that has been replaced between calls. However, it does **not** guarantee detection of a swap after `init_db()` returns, or while an existing connection remains open. On some operating systems, replacing a pathname does not change the database file already held by an open connection.

A file-watcher or continuous identity-monitoring subsystem is outside the current scope. **Each newly opened connection, or each connection checkout if pooling is introduced, must validate compatibility before use.** If Nyx later needs to detect replacement of a same-version database, that is a separate database-identity problem; a schema version cannot solve it.

## Fresh initialization authorization

Fresh initialization is authorized explicitly by an `init_db(path, create=False)` parameter. `create` defaults to `False`: ordinary calls validate an existing database and never create one. `create=True` permits initialization only when the database contains no user-defined schema objects — that is, when `SELECT count(*) FROM sqlite_master WHERE type IN ('table','index','view','trigger') AND name NOT LIKE 'sqlite\_%' ESCAPE '\'` returns zero. A `create=True` call against a database that is not empty by that test refuses; it does not fall back to validation and does not stamp metadata. File existence and file size are not used as emptiness tests.

The underscore in `sqlite\_%` must be escaped so it is matched literally. An unescaped underscore is a single-character wildcard in `LIKE` and would incorrectly exclude user tables such as `sqliteX_existing` from the emptiness test.

## Initialization decision tree

The critical distinction is between a genuinely fresh database and an existing database that lacks metadata.

1. **Open the requested database**

   Determine whether this is an explicitly authorized fresh initialization or an existing database. File existence alone is not a sufficient test for an empty database.

2. **Fresh, explicitly authorized**

   Begin a transaction, create the schema, insert version `1` and diagnostics, validate, then commit. On failure, roll back the entire operation.

3. **Existing database**

   Inspect and validate metadata without modification. Only exact supported version `1` proceeds; missing, zero, older, newer, malformed, or structurally invalid metadata refuses.

The general reopening path does not use `CREATE TABLE IF NOT EXISTS schema_meta` followed by an insert. That can silently convert an unversioned database into a versioned one, which is precisely what this ADR prohibits. Fresh creation and existing-database validation need distinct branches.

## Acceptance tests

- **Fresh initialization:** schema and metadata commit atomically; version is `1`; diagnostics are populated.
- **Supported reopen:** succeeds without changing any database bytes or logical contents.
- **Unversioned existing database:** refuses, including an existing database with otherwise recognizable Nyx tables.
- **Missing versus zero:** separate rejection cases, with distinct error classifications.
- **Malformed metadata:** empty table, multiple rows where structurally possible, wrong ID, null fields, wrong types, and invalid version values all refuse.
- **Older and newer versions:** refuse without mutation; no migration or auto-stamping.
- **Failed fresh initialization:** leaves no partial schema or metadata.
- **Repeated `init_db()`:** validates again and detects an incompatible database substituted between invocations.
- **Fold-versus-replay equality:** remains unchanged by the introduction of schema metadata.
- **Non-empty creation refusal:** `create=True` against a non-empty database refuses without mutation.
- **Escaped-prefix creation refusal:** `create=True` refuses without mutation a database containing a user table such as `sqliteX_existing`, whose name matches the unescaped pattern.
- **Missing CHECK constraints:** metadata missing `CHECK (id = 1)` or `CHECK (typeof(version) = 'integer' AND version > 0)` refuses without mutation; each missing constraint is tested separately.
- **Prohibited version CHECK:** metadata carrying `CHECK (version = 1)` refuses without mutation.
- **Extra or generated columns:** metadata with a fifth column or a generated column refuses without mutation.

For the no-mutation tests, compare database content before and after, not only whether an exception was raised. SQLite may create auxiliary journal or WAL files as part of normal connection behavior, so define the assertion around the database's logical state rather than requiring the filesystem directory to be byte-for-byte identical.

The four-field schema is accepted. Schema constraints plus validation enforce the exactly-one-row invariant, and validation runs on every `init_db()` call and every new connection boundary. Automatic migration, repair, deletion, and database-identity monitoring are outside this ADR. This defines a narrow, testable storage contract.