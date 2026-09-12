-- Nyx Layer A + derived-view schema (SQLite, WAL mode).
--
-- SOURCE OF TRUTH: spec/NYX_V0_IMPLEMENTATION.md §4. This file is a mechanical
-- transcription of the DDL decided there. If this file and §4 ever disagree,
-- §4's more-specific mechanical statement wins and THIS file is the bug to fix
-- (two-file provenance rule, spec/NYX_ARCHITECTURE.md §"Document authority").
--
-- Do not "improve" this schema. The spec is complete; build it, don't redesign it.
-- If something here looks wrong, flag it — do not silently change it.

-- Database compatibility metadata (ADR 0011); distinct from event schema_version.
CREATE TABLE schema_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL CHECK (typeof(version) = 'integer' AND version > 0),
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Layer A: Reality Layer. Append-only, ENGINE-enforced (Invariant 1).
-- ENVELOPE / PAYLOAD SPLIT (Invariant 14): the hash chain covers envelopes only,
-- so a destroyed payload never breaks verification. Envelope is PII-free by
-- construction -- no free text, actor is an opaque id.
-- ---------------------------------------------------------------------------
CREATE TABLE events (
    event_id        TEXT PRIMARY KEY,   -- UUIDv7
    idempotency_key TEXT NOT NULL,
    schema_version  TEXT NOT NULL,
    event_type      TEXT NOT NULL,      -- §1 taxonomy
    occurred_at     TEXT NOT NULL,      -- ISO8601, source time
    recorded_at     TEXT NOT NULL,      -- ISO8601, ingest time
    source          TEXT NOT NULL,      -- JSON: {actor_id (opaque), config}
    source_class    TEXT NOT NULL,      -- corroboration counts DISTINCT classes, not
                                        -- raw events -- collapses correlated ingestion
                                        -- (shared model context, re-entrant Dream
                                        -- synthesis, duplicate pasted origin)
    origin_type     TEXT NOT NULL,      -- observed|user_stated|verified_external|derived|personal
    payload_hash    TEXT NOT NULL,      -- content address of the payload row below
    entity_refs     TEXT,               -- JSON array, nullable (§11 soft links);
                                        -- resolves to canonical_entity_id post-merge
    prev_event_hash TEXT,
    event_hash      TEXT NOT NULL UNIQUE  -- covers envelope fields ONLY, not payload
);
CREATE UNIQUE INDEX idx_events_idempotency ON events(idempotency_key);

-- Payload: separately destroyable via key destruction (crypto-shredding).
-- Encrypted at write with a per-canonical-entity key from the keystore
-- (NOT per-mention -- a mention's key has no owner once entities merge/split).
-- A redacted payload is deleted here; the envelope row above is untouched,
-- so replay yields a typed REDACTED sentinel, never a broken chain.
-- KEYED BY event_id, NOT payload_hash. §4's DDL says `payload_hash TEXT PRIMARY KEY`;
-- that is the authoritative document's bug, and this deviates from it deliberately
-- (decisions/0007). Content-keying was wrong for two independent reasons:
--
--   1. It BLOCKS CORROBORATION. Two independent sources reporting the SAME value
--      produce byte-identical payloads -> the same payload_hash -> a PK collision on
--      the second. But that IS corroboration, and §2 makes it the sole promotion path
--      ("2 independent corroborating sources required for unverified -> verified").
--      A table that cannot store the second source makes the gate unreachable.
--   2. It POOLS PAYLOADS ACROSS EVENTS, violating Invariant 14. Payloads are separately
--      destroyable per event by crypto-shredding. Under one shared content-keyed row,
--      redacting one event would destroy another event's payload as collateral —
--      silent erasure of a record nobody asked to erase.
--
-- The table always carried event_id (1:1 with events) while being keyed by content
-- (n:1). Both could not hold. event_id is the identity it always implied.
CREATE TABLE payloads (
    event_id        TEXT PRIMARY KEY REFERENCES events(event_id),
    payload_hash    TEXT NOT NULL,      -- content address; NOT the row identity (see above)
    canonical_entity_id TEXT,           -- key-binding target; nullable pre-resolution
    ciphertext      TEXT,               -- NULL after redaction (key destroyed)
    redacted        INTEGER NOT NULL DEFAULT 0
);

-- Content-addressing survives as an INDEX, and it has a JOB: this is the corroboration
-- lookup key. Identical claim content still yields an identical payload_hash, so
-- "which other events assert this same claim?" is:
--
--     SELECT e.event_id, e.source_class FROM payloads p
--       JOIN events e ON e.event_id = p.event_id
--      WHERE p.payload_hash = ?
--
-- which is what the §2 corroboration gate must run to count DISTINCT source_class
-- (§2 counts distinct CLASSES, not raw events — correlated ingestion must not
-- self-corroborate). Deliberately NON-unique: n events per content is the whole point.
-- The gate itself is not built yet (§8); this is the lookup it will stand on.
CREATE INDEX idx_payloads_corroboration ON payloads(payload_hash);

-- Append-only is a MECHANISM, not a convention (Invariant 1):
CREATE TRIGGER no_update_events BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'Layer A is append-only: updates forbidden'); END;
CREATE TRIGGER no_delete_events BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'Layer A is append-only: deletes forbidden'); END;

-- ---------------------------------------------------------------------------
-- Resolved View: materialized, version-hashed projection
-- (§1, decided: materialized-delta)
-- ---------------------------------------------------------------------------
CREATE TABLE resolved_beliefs (
    belief_id           TEXT PRIMARY KEY,  -- e.g. "entity:legion/property:ram"
    current_value        TEXT,
    value_occurred_at     TEXT,            -- occurred_at of the event that set current_value;
                                           -- the fold's value-recency guard compares against this (§1)
    verification_state     TEXT NOT NULL,   -- §2 two-dimensional state
    verifiability            TEXT NOT NULL,
    display_origin            TEXT,
    supporting_events          TEXT NOT NULL, -- JSON array of event_id
    opposing_events             TEXT NOT NULL, -- JSON array of event_id
    superseding_events           TEXT NOT NULL, -- JSON array of event_id. Invariant 6 names four
                                           -- event classes a belief exposes -- supporting, opposing,
                                           -- SUPERSEDING, gap -- and the §4 DDL carried columns for
                                           -- only two. A correction lands here; the value it
                                           -- superseded STAYS in supporting_events, unmoved and
                                           -- unretagged (Inv. 6: verification adds to the set,
                                           -- never rewrites a member). NOTE this column is an
                                           -- ADDITION to §4's DDL, decided in decisions/0004 -- the
                                           -- only way to record supersession without either
                                           -- retagging a support-set member or parking the LIVE
                                           -- corrected head in verification_state='superseded'.
                                           -- `gap_events` is the remaining Inv. 6 class with no
                                           -- column; unbuilt (no gap_recorded handler yet).
    resolution_basis              TEXT,
    view_version_hash              TEXT NOT NULL,  -- SHA256(prior_hash || latest folded event_hash)
    projected_as_of                 TEXT NOT NULL,  -- Invariant 9, explicit evaluation time
    updated_at                       TEXT NOT NULL
);

-- Stale-read detection: entity -> latest committed event touching it.
-- Updated SYNCHRONOUSLY in the same transaction as the events append (§1) --
-- the one exception to "append is the only sync step." Without this, stale
-- detection races the async projection and reads can be wrong-but-unlabeled.
CREATE TABLE entity_event_index (
    entity_id            TEXT PRIMARY KEY,
    latest_event_id       TEXT NOT NULL,
    latest_event_hash      TEXT NOT NULL,   -- reads compare view_version_hash lineage against this
    updated_at              TEXT NOT NULL
);

-- ADRs 0014/0016: version-isolated ordinary-event materialization. JSON stores
-- the complete logical result using the shared canonical serializer. Version 0
-- continues to use resolved_beliefs above with its original bytes and lineage.
CREATE TABLE projected_beliefs (
    projector_version TEXT NOT NULL,
    belief_id TEXT NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY (projector_version, belief_id)
);

-- ADRs 0017/0022: exact property identity; only current containers participate.
CREATE UNIQUE INDEX idx_current_subject_property ON projected_beliefs (
    projector_version, json_extract(content, '$.subject_id'),
    json_extract(content, '$.property_id')
) WHERE json_extract(content, '$.lifecycle_status') = 'current';

CREATE TABLE projected_entities (
    projector_version TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY (projector_version, subject_id)
);
CREATE TABLE projected_mentions (
    projector_version TEXT NOT NULL,
    mention_id TEXT NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY (projector_version, mention_id)
);
CREATE TABLE projected_entity_links (
    projector_version TEXT NOT NULL,
    mention_id TEXT NOT NULL,
    content TEXT NOT NULL,
    link_state TEXT NOT NULL CHECK (link_state = 'constitutive'),
    entity_link_confidence REAL CHECK (entity_link_confidence IS NULL),
    PRIMARY KEY (projector_version, mention_id)
);
CREATE TABLE projected_claim_candidates (
    projector_version TEXT NOT NULL,
    claim_candidate_id TEXT NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY (projector_version, claim_candidate_id)
);
CREATE TABLE projected_events (
    projector_version TEXT NOT NULL,
    event_id TEXT NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY (projector_version, event_id)
);

-- ADR 0025: version-2 compact headers stay in projected_beliefs; accumulated
-- content and indexes use immutable nodes plus independently published roots.
CREATE TABLE committed_nodes (
    projector_version TEXT NOT NULL CHECK (projector_version = '2'),
    node_hash TEXT NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY (projector_version, node_hash)
);
CREATE TABLE committed_roots (
    projector_version TEXT NOT NULL CHECK (projector_version = '2'),
    kind TEXT NOT NULL,
    root_hash TEXT NOT NULL,
    PRIMARY KEY (projector_version, kind)
);

-- Append-side freshness, separate from derived publication and legacy ID scope.
CREATE TABLE identity_event_index (
    projector_version TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    latest_event_id TEXT NOT NULL,
    PRIMARY KEY (projector_version, subject_id)
);
CREATE TABLE belief_event_index (
    projector_version TEXT NOT NULL,
    belief_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    PRIMARY KEY (projector_version, belief_id)
);

-- Derived publication checkpoint, never written by the append transaction.
-- rowid/log position disambiguates events with the same recorded_at.
CREATE TABLE derived_progress (
    projector_version TEXT PRIMARY KEY,
    log_position INTEGER NOT NULL CHECK (log_position > 0),
    event_id TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Process trace: SEPARATE store. Crash-durable (WAL + fsync) but MUTABLE --
-- explicitly NOT append-only. Grading updates a trace in place (ungraded ->
-- graded), so it cannot carry Layer A's immutability guarantee and has no
-- update-blocking trigger. (Corrects earlier "same guarantees as Layer A"
-- phrasing: immutability IS that guarantee; this table deliberately lacks it.)
-- ---------------------------------------------------------------------------
CREATE TABLE process_traces (
    trace_id            TEXT PRIMARY KEY,
    hypothesis_id        TEXT NOT NULL,
    semantic_hash          TEXT NOT NULL,   -- unified content-addressing, §1
    model                    TEXT NOT NULL,
    evidence_available        TEXT,          -- JSON
    retrieved                   TEXT,          -- JSON
    failure_class                 TEXT,          -- missing_info|overlooked_info|wrong_model|NULL(ungraded)
    graded                          INTEGER NOT NULL DEFAULT 0,
    created_at                       TEXT NOT NULL
);
CREATE INDEX idx_traces_hypothesis ON process_traces(hypothesis_id, semantic_hash);

-- ---------------------------------------------------------------------------
-- Record of absence (§5)
-- ---------------------------------------------------------------------------
CREATE TABLE gaps (
    gap_id                    TEXT PRIMARY KEY,
    search_scope_signature     TEXT NOT NULL,
    methods_tried                 TEXT NOT NULL,  -- JSON array
    searched_at                    TEXT NOT NULL,
    verification_state              TEXT NOT NULL DEFAULT 'unverified',
    event_id                          TEXT NOT NULL  -- FK -> gap_recorded event
);

-- ---------------------------------------------------------------------------
-- Identity v1 minimum (§11) -- soft links only, no canonical graph yet
-- ---------------------------------------------------------------------------
CREATE TABLE entity_links (
    mention_id               TEXT PRIMARY KEY,
    candidate_entity_id       TEXT NOT NULL,
    canonical_entity_id        TEXT,             -- nullable
    entity_link_confidence      REAL NOT NULL,
    link_basis                    TEXT,
    link_state                     TEXT NOT NULL,  -- proposed|accepted|rejected|split
    event_id                        TEXT           -- FK, set once decision becomes a Layer A event
);
