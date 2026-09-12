"""Transaction-bound indexed materialization for projector 2 (ADR 0025)."""

import json
from dataclasses import replace
from types import MappingProxyType

from . import committed, hashing, merkle


def read_snapshot(conn):
    if not conn.in_transaction:
        raise RuntimeError("snapshot reads require a transaction")
    progress = conn.execute(
        "SELECT log_position,event_id FROM derived_progress WHERE projector_version='2'"
    ).fetchone()
    roots = dict(conn.execute("SELECT kind,root_hash FROM committed_roots WHERE projector_version='2'"))
    if progress is None:
        if (roots or conn.execute("SELECT 1 FROM committed_nodes WHERE projector_version='2' LIMIT 1").fetchone()
                or conn.execute("SELECT 1 FROM projected_beliefs WHERE projector_version='2' LIMIT 1").fetchone()):
            raise ValueError("unproven version-2 materialization; recover by full replay")
        return committed.Snapshot()
    if set(roots) != set(committed.INDEX_KINDS):
        raise ValueError("incomplete committed root inventory; recover by full replay")
    if conn.execute("SELECT event_id FROM events WHERE rowid=?", (progress[0],)).fetchone() != (progress[1],):
        raise ValueError("derived progress does not identify a log prefix")
    cache = {}

    def reference(digest):
        if not merkle.valid_hash(digest):
            raise ValueError("invalid stored root hash")
        return None if digest == merkle.EMPTY else merkle.Reference(digest, load)

    def load(digest):
        if not conn.in_transaction:
            raise RuntimeError("lazy snapshot escaped its read transaction")
        if digest in cache:
            return cache[digest]
        row = conn.execute(
            "SELECT content FROM committed_nodes WHERE projector_version='2' AND node_hash=?", (digest,)
        ).fetchone()
        if row is None:
            raise ValueError("missing committed node; recover by full replay")
        node = merkle.decode(row[0], digest, load)
        if node.bit < 0:
            value = json.loads(node.value)
            if isinstance(value, dict) and "collection_roots" in value:
                if (set(value["collection_roots"]) != set(committed.COLLECTIONS)
                        or committed.result_root(value["collection_roots"]) != value.get("result_root")):
                    raise ValueError("invalid committed belief header")
                node = replace(node, links=MappingProxyType(
                    {k: reference(v) for k, v in value["collection_roots"].items()}))
        cache[digest] = node
        return node

    return committed.Snapshot({k: reference(v) for k, v in roots.items()}, *progress)


def publication_material(delta):
    """Serialized content written, excluding SQL framing, indexes and progress."""
    yield from delta.nodes.values()
    for header in delta.beliefs.values():
        yield hashing.canonical_json(header)
    for kind, root in delta.root_changes.items():
        yield hashing.canonical_json({"kind": kind, "root": merkle.digest(root)})


def publish(conn, delta):
    if not conn.in_transaction:
        raise RuntimeError("delta publication requires a transaction")
    for node_hash, raw in delta.nodes.items():
        if hashing._sha256_hex(raw) != node_hash:
            raise ValueError("publication node hash mismatch")
        inserted = conn.execute(
            "INSERT INTO committed_nodes VALUES ('2',?,?) ON CONFLICT DO NOTHING", (node_hash, raw))
        if inserted.rowcount == 0 and conn.execute(
            "SELECT content FROM committed_nodes WHERE projector_version='2' AND node_hash=?", (node_hash,)
        ).fetchone() != (raw,):
            raise ValueError("existing committed node is corrupt")
    for belief_id, header in delta.beliefs.items():
        conn.execute(
            "INSERT INTO projected_beliefs VALUES ('2',?,?) "
            "ON CONFLICT(projector_version,belief_id) DO UPDATE SET content=excluded.content",
            (belief_id, hashing.canonical_json(header)))
    for kind, root in delta.root_changes.items():
        conn.execute(
            "INSERT INTO committed_roots VALUES ('2',?,?) "
            "ON CONFLICT(projector_version,kind) DO UPDATE SET root_hash=excluded.root_hash",
            (kind, merkle.digest(root)))
