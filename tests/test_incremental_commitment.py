"""ADR 0025: independent roots, unchanged semantics, indexed atomic publication."""

import hashlib
import itertools
import json
import random
import sqlite3
from contextlib import closing
from copy import deepcopy
from dataclasses import replace

import pytest

from nyx import committed, events, hashing, ingestion, merkle, projection, reducer, skeleton, storage
from test_reducer_boundary import T0, T1, T2, T3, SOURCE, claim, decoded, event, mention


@pytest.fixture
def log():
    result = []
    submissions = [
        (events.ENTITY_MENTION_RECORDED, mention()),
        (events.ENTITY_MENTION_RECORDED, mention("s-b", "m-b")),
        (events.OBSERVATION_RECORDED, {"claims": [claim()]}),
        (events.OBSERVATION_RECORDED, {"claims": [claim("c-a2", value="128GB"),
                                                   claim("c-b", "b-b", "s-b", "m-b")]}),
        (events.OBSERVATION_RECORDED, {"claims": [claim("c-a3"), claim("c-a4")]}),
    ]
    for index, (kind, payload) in enumerate(submissions, 1):
        result.append(event(kind, payload, index, result[-1] if result else None,
                            **({"occurred_at": T0} if index == 5 else {})))
    return result


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "nyx.db"
    with closing(storage.init_db(path, create=True)) as conn:
        yield path, conn


def canonical(value):
    return hashing.canonical_json(value)


def content_only(snapshot):
    records = snapshot.complete()
    for belief in records["beliefs"].values():
        del belief["view_version_hash"]
    return canonical(records)


def independent_root(pairs):
    """Build by partitioning the complete set; never use incremental put/delete."""
    def sha(value):
        return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

    values = [(int(sha(key), 16), key, value) for key, value in pairs]

    def build(rows):
        if not rows:
            return sha({"format": "nyx-map/1", "kind": "empty"})
        if len(rows) == 1:
            _, key, value = rows[0]
            return sha({"format": "nyx-map/1", "kind": "leaf", "key": key, "value": value})
        low, high = min(r[0] for r in rows), max(r[0] for r in rows)
        bit = 256 - (low ^ high).bit_length()
        common = (low >> (256 - bit)) << (256 - bit)
        return sha({"format": "nyx-map/1", "kind": "branch", "bit": bit,
                    "prefix": f"{common:064x}",
                    "left": build([r for r in rows if not (r[0] >> (255-bit)) & 1]),
                    "right": build([r for r in rows if (r[0] >> (255-bit)) & 1])})
    return build(values)


def test_canonical_tree_permutations_replacements_deletions_and_proofs():
    entries = [("é", {"path": ["b", "a"]}), ("雪", [1, None]), ("e\u0301", 3), ("a", False)]
    expected = independent_root(entries)
    for permutation in itertools.permutations(entries):
        tree = merkle.rebuild(permutation)
        assert merkle.digest(tree) == expected
        for key, value in entries:
            proof = merkle.prove(tree, key)
            assert merkle.verify(expected, key, value, proof)
            assert not merkle.verify(expected, key, "wrong", proof)
            assert not merkle.verify(expected, "other-key", value, proof)
            assert not merkle.verify("0" * 64, key, value, proof)
        changed = merkle.put(tree, "a", True)
        assert merkle.get(tree, "a") is False
        assert merkle.digest(changed) == independent_root([*entries[:-1], ("a", True)])
        removed = merkle.delete(changed, "a")
        assert merkle.digest(removed) == independent_root(entries[:-1])
        assert merkle.digest(merkle.put(removed, "a", False)) == expected
        assert merkle.delete(tree, "missing") is tree
    singleton = merkle.rebuild(entries[:1])
    assert merkle.prove(singleton, "é") == []
    assert merkle.digest(merkle.delete(singleton, "é")) == independent_root([])
    with pytest.raises(KeyError):
        merkle.prove(singleton, "absent")


def test_random_tree_updates_against_full_partition_oracle():
    rng = random.Random(25)
    tree, values = None, {}
    for _ in range(200):
        key = f"k-{rng.randrange(50)}"
        if rng.randrange(3) == 0:
            values.pop(key, None)
            tree = merkle.delete(tree, key)
        else:
            values[key] = [rng.randrange(100), {"unicode": "雪"}]
            tree = merkle.put(tree, key, values[key])
        assert merkle.digest(tree) == independent_root(values.items())
        assert dict(merkle.items(tree)) == values


@pytest.mark.parametrize("change", ["order", "prefix", "bit", "child", "extra", "type"])
def test_malformed_proofs_refuse(change):
    entries = [(f"k-{i}", i) for i in range(20)]
    tree = merkle.rebuild(entries)
    proof = merkle.prove(tree, "k-0")
    if change == "order":
        proof.reverse()
    elif change == "prefix":
        proof[0]["prefix"] = "f" * 64
    elif change == "bit":
        proof[0]["bit"] = True
    elif change == "child":
        proof[0]["left"] = "invalid"
    elif change == "extra":
        proof[0]["extra"] = 1
    else:
        proof = {}
    assert not merkle.verify(tree.digest, "k-0", 0, proof)


def test_all_prefixes_replay_storage_independent_roots_and_version_isolation(db, log):
    _, conn = db
    snapshot = committed.Snapshot()
    for position, (env, data) in enumerate(decoded(log), 1):
        previous = canonical(snapshot.complete())
        delta = committed.reduce(snapshot, env, data, T2)
        following = snapshot.apply(delta, position)
        assert canonical(snapshot.complete()) == previous
        assert ingestion.submit(conn, log[position-1], T2, "2")
        live = storage.read_snapshot(conn, "2")
        replay = projection.project_snapshot(decoded(log[:position]), T2, "2")
        assert canonical(live.complete()) == canonical(following.complete()) == canonical(replay.complete())
        assert (live.log_position, live.event_id) == (position, env.event_id)
        old = projection.project_snapshot(decoded(log[:position]), T2, "1")
        assert content_only(old) == content_only(live)
        for bid, belief in live.beliefs().items():
            header = live.header(bid)
            for kind in committed.COLLECTIONS:
                pairs = [(committed.member_key(kind, value), value) for value in belief[kind]]
                assert header["collection_roots"][kind] == independent_root(pairs)
            assert header["collection_roots"] == committed.full_result_roots(belief)
            assert header["result_root"] == committed.result_root(header["collection_roots"])
        snapshot = following
    assert not ingestion.submit(conn, log[-1], T2, "2")
    # The same recorded log remains explicitly replayable under frozen version 1.
    storage.rebuild_projection(conn, T2, "1")
    before = canonical(storage.read_snapshot(conn, "1").complete())
    storage.rebuild_projection(conn, T2, "2")
    assert canonical(storage.read_snapshot(conn, "1").complete()) == before
    assert before == canonical(projection.project_snapshot(decoded(log), T2, "1").complete())


@pytest.mark.parametrize("kind", committed.COLLECTIONS)
def test_result_coverage_changes_with_predecessors_fixed(log, kind):
    snapshot = projection.project_snapshot(decoded(log), T2, "2")
    belief = snapshot.belief("b-a")
    original = committed.full_result_roots(belief)
    altered = deepcopy(belief)
    altered[kind].pop()
    assert committed.full_result_roots(altered)[kind] != original[kind]
    if kind == "claim_candidates":
        for change in ("supporting_events", "provenance_paths", "verification_state"):
            altered = deepcopy(belief)
            altered[kind][0][change] = [] if change != "verification_state" else "questioned"
            assert committed.full_result_roots(altered)[kind] != original[kind]
    elif kind == "event_dependencies":
        altered = deepcopy(belief)
        altered[kind][0]["payload"] = {"different": True}
        assert committed.full_result_roots(altered)[kind] != original[kind]


def test_time_cutoffs_purity_detachment_named_reads_and_proofs(db, log, monkeypatch):
    _, conn = db
    for entry in log:
        ingestion.submit(conn, entry, T2, "2")
    frozen = storage.read_snapshot(conn, "2")
    before = canonical(frozen.complete())
    frozen.belief("b-a")["claim_candidates"].clear()
    frozen.record("claim_candidates", "c-a")["supporting_events"].clear()
    assert canonical(frozen.complete()) == before
    for at in (T0, log[0][0].recorded_at, log[2][0].recorded_at, T2):
        expected = projection.project_snapshot(decoded(log), at, "2")
        assert storage.evaluate_whole_view(conn, at, "2") == expected.beliefs()
    later = projection.project_snapshot(decoded(log), T3, "2")
    for bid, belief in frozen.beliefs().items():
        assert later.belief(bid) == {**belief, "projected_as_of": T3}
    assert storage.read_claim_candidate_value(conn, "c-a", "2") == "64GB"
    assert storage.read_claim_candidate_value(conn, "c-a2", "2") == "128GB"
    with pytest.raises(ValueError, match="multiple"):
        storage.read_belief_scalar(conn, "b-a", "2")
    header = frozen.header("b-a")
    proof = frozen.inclusion_proof("b-a", "claim_candidates", "c-a")
    assert merkle.verify(header["collection_roots"]["claim_candidates"], "c-a",
                         frozen.record("claim_candidates", "c-a"), proof)
    def forbidden(*args, **kwargs):
        pytest.fail("reducer must not allocate IDs or sample the clock")
    monkeypatch.setattr(events, "new_event_id", forbidden)
    monkeypatch.setattr(projection, "_now_iso", forbidden)
    assert projection.project_snapshot(decoded(log), T2, "2").complete() == frozen.complete()


@pytest.mark.parametrize("event_type", ["entity_merge_accepted", "entity_split_asserted",
    "correction_appended", "verification_completed", "entity_link_accepted",
    "dream_reference", "retrieval_exposure", "activation_recorded"])
def test_deferred_and_usage_events_refuse_both_boundaries(db, log, event_type):
    _, conn = db
    for entry in log[:3]:
        ingestion.submit(conn, entry, T2, "2")
    bad = event(event_type, {"claims": [claim("new")]}, 4, log[2])
    before = tuple(conn.iterdump())
    with pytest.raises(NotImplementedError):
        storage.safe_append_event(conn, *bad, "2")
    assert tuple(conn.iterdump()) == before
    with pytest.raises(NotImplementedError):
        projection.project_snapshot(decoded(log[:3] + [bad]), T2, "2")


@pytest.mark.parametrize("field,value", [("claim_candidate_id", "c-a"), ("subject_id", "unknown"),
    ("mention_id", "b-a"), ("belief_id", "new-container"), ("property_id", ""),
    ("verifiability", "guessed")])
def test_invalid_claims_refuse_without_mutation(db, log, field, value):
    _, conn = db
    for entry in log[:3]:
        ingestion.submit(conn, entry, T2, "2")
    bad = event(events.OBSERVATION_RECORDED, {"claims": [{**claim("fresh"), field: value}]}, 4, log[2])
    before = tuple(conn.iterdump())
    with pytest.raises(ValueError):
        storage.safe_append_event(conn, *bad, "2")
    assert tuple(conn.iterdump()) == before
    with pytest.raises(ValueError):
        projection.project_snapshot(decoded(log[:3] + [bad]), T2, "2")


@pytest.mark.parametrize("table", ["committed_nodes", "committed_roots", "projected_beliefs", "derived_progress"])
def test_atomic_publication_retry_and_stale_labels(db, log, table):
    _, conn = db
    for entry in log[:2]:
        ingestion.submit(conn, entry, T2, "2")
    storage.safe_append_event(conn, *log[2], "2")
    assert storage.read_belief_status(conn, "b-a", "2")["stale"]
    before = tuple(conn.iterdump())
    conn.execute(f"CREATE TEMP TRIGGER fail BEFORE INSERT ON {table} BEGIN SELECT RAISE(ABORT,'failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        storage.materialize_pending(conn, T2, "2")
    assert tuple(conn.iterdump()) == before
    with pytest.raises(storage.ProjectionBehindError):
        storage.safe_append_event(conn, *log[3], "2")
    conn.execute("DROP TRIGGER fail")
    assert storage.materialize_pending(conn, T2, "2") == 1
    assert not storage.read_belief_status(conn, "b-a", "2")["stale"]
    assert not storage.safe_append_event(conn, *log[2], "2")
    assert storage.materialize_pending(conn, T2, "2") == 0


@pytest.mark.parametrize("corruption", ["missing", "changed", "roots", "progress"])
def test_recovery_ignores_corruption_and_failure_rolls_back(db, log, monkeypatch, corruption):
    _, conn = db
    for entry in log:
        ingestion.submit(conn, entry, T2, "2")
    detached = storage.read_snapshot(conn, "2")
    expected = canonical(detached.complete())
    with conn:
        if corruption in ("missing", "changed"):
            key = conn.execute("SELECT root_hash FROM committed_roots WHERE kind='beliefs'").fetchone()[0]
            if corruption == "missing":
                conn.execute("DELETE FROM committed_nodes WHERE node_hash=?", (key,))
            else:
                conn.execute("UPDATE committed_nodes SET content='{}' WHERE node_hash=?", (key,))
        elif corruption == "roots":
            conn.execute("DELETE FROM committed_roots WHERE kind='mentions'")
        else:
            conn.execute("UPDATE derived_progress SET log_position=999,event_id='bad' WHERE projector_version='2'")
    with pytest.raises(ValueError):
        storage.read_snapshot(conn, "2")
    assert canonical(detached.complete()) == expected
    before = tuple(conn.iterdump())
    original = committed.reduce
    def fail(snapshot, env, data, at):
        if env.event_id == log[3][0].event_id:
            raise RuntimeError("injected recovery failure")
        return original(snapshot, env, data, at)
    monkeypatch.setattr(committed, "reduce", fail)
    with pytest.raises(RuntimeError):
        storage.rebuild_projection(conn, T2, "2")
    assert tuple(conn.iterdump()) == before
    monkeypatch.setattr(committed, "reduce", original)
    def forbidden(*args):
        pytest.fail("recovery must not consult old materialization")
    monkeypatch.setattr(storage, "_read_snapshot", forbidden)
    storage.rebuild_projection(conn, T2, "2")
    monkeypatch.undo()
    assert canonical(storage.read_snapshot(conn, "2").complete()) == expected


def test_write_path_does_not_enumerate_or_rewrite_accumulated_collections(db, log, monkeypatch):
    _, conn = db
    for entry in log[:3]:
        ingestion.submit(conn, entry, T2, "2")
    before_nodes = dict(conn.execute("SELECT node_hash,content FROM committed_nodes"))
    def forbidden(*args, **kwargs):
        pytest.fail("write path enumerated accumulated content")
    with monkeypatch.context() as patch:
        patch.setattr(merkle, "items", forbidden)
        patch.setattr(committed.Snapshot, "belief", forbidden)
        patch.setattr(committed.Snapshot, "complete", forbidden)
        for entry in log[3:]:
            ingestion.submit(conn, entry, T2, "2")
    after_nodes = dict(conn.execute("SELECT node_hash,content FROM committed_nodes"))
    assert all(after_nodes[key] == value for key, value in before_nodes.items())
    for (raw,) in conn.execute("SELECT content FROM projected_beliefs WHERE projector_version='2'"):
        assert set(committed.COLLECTIONS).isdisjoint(json.loads(raw))
    assert storage.read_snapshot(conn, "2").complete() == projection.project_snapshot(decoded(log), T2, "2").complete()


def test_version_one_probe_bytes_remain_frozen():
    from scripts.probe_lineage_scaling import sample
    size, _, digest = sample(32)
    assert size == 914109
    assert digest == "aac6b0e626261a46069debe46cf450a755ebec601535fab3e1731ec6742f7c6f"


def test_cross_version_freshness_and_reader_isolation(db, log, monkeypatch):
    path, conn = db
    for entry in log[:3]:
        ingestion.submit(conn, entry, T2, "1")
    assert storage.read_belief_status(conn, "b-a", "2")["stale"]
    storage.materialize_pending(conn, T2, "2")
    old = storage.read_snapshot(conn, "2")
    storage.safe_append_event(conn, *log[3], "2")
    assert storage.read_belief_status(conn, "b-a", "1")["stale"]
    original = storage._publish_delta
    with closing(storage.init_db(path)) as reader:
        def fail_publish(*args):
            original(*args)
            assert storage.read_snapshot(reader, "2").complete() == old.complete()
            raise RuntimeError("after roots, before commit")
        monkeypatch.setattr(storage, "_publish_delta", fail_publish)
        before = tuple(conn.iterdump())
        with pytest.raises(RuntimeError):
            storage.materialize_pending(conn, T2, "2")
        assert tuple(conn.iterdump()) == before
        monkeypatch.setattr(storage, "_publish_delta", original)
        storage.materialize_pending(conn, T2, "2")
        assert not storage.read_belief_status(reader, "b-a", "2")["stale"]
        assert storage.read_belief_status(reader, "b-a", "1")["stale"]
        storage.materialize_pending(conn, T2, "1")
        assert not storage.read_belief_status(reader, "b-a", "1")["stale"]


def test_stale_writer_two_connections_and_exact_retained_retry(db, log):
    path, conn = db
    for entry in log[:3]:
        ingestion.submit(conn, entry, T2, "2")
    with closing(storage.init_db(path)) as writer:
        stale = event(events.OBSERVATION_RECORDED, {"claims": [claim("stale")]}, 5, log[2])
        ingestion.submit(conn, log[3], T2, "2")
        before = tuple(conn.iterdump())
        with pytest.raises(ValueError, match="append position"):
            storage.safe_append_event(writer, *stale, "2")
        assert tuple(conn.iterdump()) == before
        altered = replace(log[3][0], event_id="reminted")
        with pytest.raises(ValueError, match="retry differs"):
            storage.safe_append_event(writer, altered, log[3][1], "2")
        assert tuple(conn.iterdump()) == before


def test_writer_helpers_and_snapshot_survives_connection_close(db):
    path, conn = db
    pair = ingestion.prepare_mention(conn, mention_id="m", subject_id="s", text="the device",
                                     source=SOURCE, source_class="direct_observation", origin_type="observed",
                                     occurred_at=T1, recorded_at=T1, event_id="mention")
    assert skeleton.record_mention(path, pair, "2")["subject_id"] == "s"
    observation = ingestion.prepare_observation(conn, claims=[claim("c", "b", "s", "m")],
        source=SOURCE, source_class="direct_observation", occurred_at=T1, recorded_at=T2,
        event_id="observation", projector_version="2")
    assert skeleton.record_observation(path, observation, "2")["b"]["claim_candidates"][0]["value"] == "64GB"
    with closing(storage.init_db(path)) as other:
        detached = storage.read_snapshot(other, "2")
    assert detached.belief("b")["claim_candidates"][0]["claim_candidate_id"] == "c"


def test_changed_path_bound_and_delta_detachment(log):
    snapshot = projection.project_snapshot(decoded(log[:3]), T2, "2")
    before = canonical(snapshot.complete())
    delta = committed.reduce(snapshot, *decoded(log)[3], T2)
    result = snapshot.apply(delta, 4)
    expected = canonical(result.complete())
    delta.claim_candidates["c-a2"]["value"] = "mutated"
    delta.beliefs["b-a"]["collection_roots"].clear()
    delta.nodes.clear()
    delta.roots.clear()
    assert canonical(result.complete()) == expected
    assert canonical(snapshot.complete()) == before
    tree = merkle.rebuild((f"k-{i}", i) for i in range(512))
    path = merkle.prove(tree, "k-0")
    written = {}
    changed = merkle.put(tree, "k-0", "updated", written)
    assert len(written) == len(path) + 1
    assert len(path) <= 256
    assert merkle.get(tree, "k-0") == 0
    assert merkle.get(changed, "k-0") == "updated"
