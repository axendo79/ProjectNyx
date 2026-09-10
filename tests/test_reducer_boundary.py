"""Stage-two acceptance and version-zero byte isolation, ADRs 0013–0024."""

import json
import sqlite3
from contextlib import closing
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from nyx import events, hashing, ingestion, projection, reducer, skeleton, storage

T0 = "2026-07-12T00:00:00Z"
T1 = "2026-07-13T00:00:00Z"
T2 = "2026-07-14T00:00:00Z"
T3 = "2026-07-15T00:00:00Z"
SOURCE = {"actor_id": "sensor", "config": {}}


def canonical(value):
    return hashing.canonical_json(value).encode("utf-8")


def event(kind, payload, index=1, previous=None, **changes):
    args = dict(event_type=kind, origin_type="observed", source=SOURCE,
                source_class="direct_observation", occurred_at=T1,
                recorded_at=f"2026-07-13T00:00:{index:02d}Z", event_id=f"e-{index}",
                prev_event_hash=None if previous is None else previous[0].event_hash,
                payload=payload)
    args.update(changes)
    return events.build_event(**args)


def mention(subject="s-a", mid="m-a"):
    return dict(mention_id=mid, subject_id=subject, text="the device", link_state="constitutive")


def claim(cid="c-a", bid="b-a", subject="s-a", mid="m-a", prop="RAM", value="64GB"):
    return dict(mention_id=mid, subject_id=subject, property_id=prop, belief_id=bid,
                claim_candidate_id=cid, value=value, verifiability="externally_checkable")


def decoded(log):
    return [(env, json.loads(payload.ciphertext)) for env, payload in log]


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "nyx.db"
    with closing(storage.init_db(path, create=True)) as conn:
        yield path, conn


@pytest.fixture
def log():
    a = event(events.ENTITY_MENTION_RECORDED, mention())
    b = event(events.ENTITY_MENTION_RECORDED, mention("s-b", "m-b"), 2, a)
    c = event(events.OBSERVATION_RECORDED, {"claims": [claim()]}, 3, b)
    d = event(events.OBSERVATION_RECORDED, {"claims": [claim("c-a2", value="128GB"),
              claim("c-b", "b-b", "s-b", "m-b")]}, 4, c)
    e = event(events.OBSERVATION_RECORDED, {"claims": [claim("c-a3")]}, 5, d, occurred_at=T0)
    return [a, b, c, d, e]


def ingest(conn, entries, at=T2):
    for entry in entries:
        assert storage.safe_append_event(conn, *entry, "1")
        storage.materialize_pending(conn, at, "1")


def dump(conn):
    return tuple(conn.iterdump())


def test_version_zero_golden_bytes_and_no_retrofit(db):
    _, conn = db
    golden = json.loads((Path(__file__).parent / "fixtures/version0_ordinary.json").read_text(encoding="utf-8"))
    legacy = [(events.Envelope(**env), data) for env, data in golden["events"]]
    expected = golden["expected_canonical"].encode("utf-8")
    assert canonical(projection.project(legacy, T2, "0")) == expected
    for env, payload in legacy:
        storage.safe_append_event(conn, env, events.Payload(env.payload_hash, env.event_id,
                                  None, hashing.canonical_json(payload)))
        storage.upsert_belief(conn, projection.fold(storage.read_belief(conn, payload["belief_id"]), env, payload, T2))
    assert canonical({key: storage.read_belief(conn, key) for key in ("a", "b")}) == expected
    before = dump(conn)
    with pytest.raises(ValueError):
        storage.materialize_pending(conn, T2, "1")  # Legacy events lack recorded identity.
    assert dump(conn) == before
    assert canonical(storage.evaluate_whole_view(conn, T2, "0")) == expected


def test_complete_incremental_replay_every_prefix_and_recovery(db, log):
    _, conn = db
    for index, entry in enumerate(log, 1):
        ingest(conn, [entry])
        live = storage.read_snapshot(conn)
        replay = projection.project_snapshot(decoded(log[:index]), T2)
        assert canonical(live.complete()) == canonical(replay.complete())
        assert (live.log_position, live.event_id) == (index, entry[0].event_id)
        assert storage.evaluate_whole_view(conn, T2, "1") == replay.beliefs()
    before = dump(conn)
    storage.rebuild_projection(conn, T2)
    assert dump(conn) == before


def test_bootstrap_mention_only_and_confidence(db, log):
    _, conn = db
    ingest(conn, log[:1])
    snap = storage.read_snapshot(conn)
    assert snap.beliefs() == {}
    assert snap.records("claim_candidates") == {}
    assert storage.read_entity(conn, "s-a")["constituting_mention_id"] == "m-a"
    link = storage.read_entity_link(conn, "m-a")
    assert link["link_state"] == "constitutive"
    assert link["entity_link_confidence"] is None
    assert reducer.identity_confidence_ceiling([link, link]) is None
    assert conn.execute("SELECT link_state,entity_link_confidence FROM projected_entity_links").fetchone() == ("constitutive", None)
    for state in ("accepted", "proposed", "rejected", "split"):
        with pytest.raises(NotImplementedError):
            reducer.identity_confidence_ceiling([link, {**link, "link_state": state}])
    with pytest.raises(ValueError):
        reducer.identity_confidence_ceiling([{**link, "entity_link_confidence": 1.0}])
    assert "owner" not in canonical(snap.complete()).decode()


def test_no_head_named_candidate_and_event_evidence_scope(db, log):
    _, conn = db
    ingest(conn, log)
    belief = storage.read_belief(conn, "b-a", "1")
    assert "current_value" not in belief and "verification_state" not in belief
    assert {c["claim_candidate_id"] for c in belief["claim_candidates"]} == {"c-a", "c-a2", "c-a3"}
    assert {c["verification_state"] for c in belief["claim_candidates"]} == {"verified"}
    assert storage.read_claim_candidate_value(conn, "c-a") == "64GB"
    assert storage.read_claim_candidate_value(conn, "c-a2") == "128GB"
    with pytest.raises(ValueError, match="multiple ClaimCandidates"):
        storage.read_belief_scalar(conn, "b-a")
    candidates = list(storage.read_snapshot(conn).records("claim_candidates").values())
    assert reducer.evidence_event_ids(candidates) == ["e-3", "e-4", "e-5"]
    assert storage.read_claim_candidate(conn, "c-b")["supporting_events"] == ["e-4"]
    assert "e-1" not in reducer.evidence_event_ids(candidates)
    assert all("confidence" not in c for c in candidates)


@pytest.mark.parametrize("values", [("64GB", "128GB"), ("64GB", "64GB")])
def test_one_event_same_belief_multiple_claims(db, log, values):
    _, conn = db
    ingest(conn, log[:1])
    entry = event(events.OBSERVATION_RECORDED, {"claims": [claim("c1", value=values[0]),
                  claim("c2", value=values[1])]}, 2, log[0])
    ingest(conn, [entry])
    belief = storage.read_belief(conn, "b-a", "1")
    assert len(belief["claim_candidates"]) == 2
    assert reducer.evidence_event_ids(belief["claim_candidates"]) == ["e-2"]
    assert all(c["source"] == SOURCE and c["verification_state"] == "verified" for c in belief["claim_candidates"])
    with pytest.raises(ValueError):
        storage.read_belief_scalar(conn, "b-a")


def assert_refused(conn, prefix, invalid, error=ValueError):
    before = dump(conn)
    with pytest.raises(error):
        storage.safe_append_event(conn, *invalid, "1")
    assert dump(conn) == before
    with pytest.raises(error):
        projection.project_snapshot(decoded(prefix + [invalid]), T2)


@pytest.mark.parametrize("field,bad", [
    ("mention_id", "s-a"), ("mention_id", "b-a"), ("mention_id", "c-a"), ("mention_id", "e-3"),
    ("subject_id", "m-a"), ("subject_id", "b-a"), ("subject_id", "c-a"), ("subject_id", "e-3"),
    ("belief_id", "s-a"), ("belief_id", "m-a"), ("belief_id", "c-a"), ("belief_id", "e-3"),
    ("subject_id", "s-b"), ("mention_id", "m-b"), ("belief_id", "fresh-wrong-container"),
    ("claim_candidate_id", "c-a"), ("property_id", ""), ("property_id", None),
    ("mention_id", ""), ("subject_id", 1), ("belief_id", None), ("claim_candidate_id", ""),
])
def test_scope_substitution_and_invalid_association_refuse_before_append_and_replay(db, log, field, bad):
    _, conn = db
    prefix = log[:3]
    ingest(conn, prefix)
    invalid = event(events.OBSERVATION_RECORDED, {"claims": [{**claim("fresh"), field: bad}]}, 4, prefix[-1])
    assert_refused(conn, prefix, invalid)


@pytest.mark.parametrize("field", list(claim()))
def test_missing_explicit_claim_contents_refuse(db, log, field):
    _, conn = db
    ingest(conn, log[:1])
    bad = claim()
    del bad[field]
    assert_refused(conn, log[:1], event(events.OBSERVATION_RECORDED, {"claims": [bad]}, 2, log[0]))


@pytest.mark.parametrize("field,value", [("supporting_events", ["m-a"]), ("verification_state", "verified"),
    ("confidence", 1.0), ("candidate_entity_id", "s-a"), ("hypothesis_id", "c-a")])
def test_no_implicit_support_authority_or_other_candidate_roles(db, log, field, value):
    _, conn = db
    ingest(conn, log[:1])
    assert_refused(conn, log[:1], event(events.OBSERVATION_RECORDED,
                   {"claims": [{**claim(), field: value}]}, 2, log[0]))


@pytest.mark.parametrize("field,value", [("subject_id", "s-a"), ("mention_id", "m-a"),
    ("link_state", "accepted"), ("entity_link_confidence", 1.0), ("owner", "sensor")])
def test_new_mention_cannot_reuse_identity_or_invent_defaults(db, log, field, value):
    _, conn = db
    ingest(conn, log[:1])
    assert_refused(conn, log[:1], event(events.ENTITY_MENTION_RECORDED,
                   {**mention("s-new", "m-new"), field: value}, 2, log[0]))


def test_same_spelling_in_distinct_id_scopes_never_aliases(db):
    _, conn = db
    # IDs are opaque and fresh within their scopes (ADR 0014), not prefixes.
    m = event(events.ENTITY_MENTION_RECORDED, mention("opaque", "opaque"), event_id="opaque")
    ingest(conn, [m])
    o = event(events.OBSERVATION_RECORDED, {"claims": [claim("opaque", "opaque", "opaque", "opaque")]}, 2, m)
    ingest(conn, [o])
    snap = storage.read_snapshot(conn)
    assert snap.event("opaque")["envelope"]["event_type"] == events.ENTITY_MENTION_RECORDED
    assert snap.belief("opaque")["property_id"] == "RAM"
    assert storage.read_claim_candidate_value(conn, "opaque") == "64GB"
    assert storage.read_entity(conn, "opaque")["constituting_mention_id"] == "opaque"


def test_typed_reads_never_search_other_id_scopes(db, log):
    _, conn = db
    ingest(conn, log)
    readers = {"s-a": storage.read_entity, "m-a": storage.read_mention,
               "b-a": lambda c, k: storage.read_belief(c, k, "1"), "c-a": storage.read_claim_candidate}
    for own, reader in readers.items():
        assert reader(conn, own) is not None
        for other in set(readers) | {"e-3"}:
            if other != own:
                assert reader(conn, other) is None
    with pytest.raises(KeyError):
        storage.read_claim_candidate_value(conn, "b-a")


def test_exact_properties_and_current_only_uniqueness(db, log):
    _, conn = db
    ingest(conn, log[:1])
    props = ["RAM", "ram", "é", "e\u0301"]
    claims = [claim(f"c{i}", f"b{i}", prop=p) for i, p in enumerate(props)]
    ingest(conn, [event(events.OBSERVATION_RECORDED, {"claims": claims}, 2, log[0])])
    assert [storage.lookup_current_belief_id(conn, "s-a", p) for p in props] == [f"b{i}" for i in range(4)]
    # Constraint-only post-merge fixture (ADR 0022): no invented merge operation.
    historic = {"subject_id": "s-a", "property_id": "RAM", "lifecycle_status": "historical"}
    with conn:
        conn.execute("INSERT INTO projected_beliefs VALUES ('1','historical',?)", (hashing.canonical_json(historic),))
    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            conn.execute("INSERT INTO projected_beliefs VALUES ('1','duplicate',?)",
                         (hashing.canonical_json({**historic, "lifecycle_status": "current"}),))


@pytest.mark.parametrize("kind", [events.CORRECTION_APPENDED, events.ENTITY_MERGE_ACCEPTED,
    events.ENTITY_SPLIT_ASSERTED, events.VERIFICATION_COMPLETED, events.ENTITY_LINK_ACCEPTED,
    events.ENTITY_LINK_PROPOSED, events.CLAIM_QUARANTINED, events.CLAIM_RESTORED])
def test_deferred_events_refuse_both_boundaries(db, log, kind):
    _, conn = db
    ingest(conn, log[:3])
    assert_refused(conn, log[:3], event(kind, {"targets": ["c-a"], "claims": [claim("fresh")]},
                   4, log[2]), NotImplementedError)


def test_unworked_origin_still_refuses(db, log):
    _, conn = db
    ingest(conn, log[:1])
    assert_refused(conn, log[:1], event(events.OBSERVATION_RECORDED, {"claims": [claim()]},
                   2, log[0], origin_type="user_stated"), NotImplementedError)


def test_snapshot_detached_pure_and_no_clock_or_allocation(db, log, monkeypatch):
    _, conn = db
    ingest(conn, log[:3])
    snap = storage.read_snapshot(conn)
    before = canonical(snap.complete())
    copied = snap.complete()
    copied["claim_candidates"]["c-a"]["supporting_events"].clear()
    assert canonical(snap.complete()) == before
    with pytest.raises(TypeError):
        snap._records["entities"]["s-a"] = "{}"
    def forbidden(*args, **kwargs):
        pytest.fail("reducer must not read clock, allocate IDs, or access storage")
    monkeypatch.setattr(events, "new_event_id", forbidden)
    monkeypatch.setattr(projection, "_now_iso", forbidden)
    monkeypatch.setattr(storage, "read_all_events", forbidden)
    assert projection.project_snapshot(decoded(log), T2).beliefs()
    assert storage.read_claim_candidate_value(conn, "c-a") == "64GB"
    with pytest.raises(ValueError, match="snapshot projector version"):
        reducer.reduce(reducer.Snapshot({}, projector_version="0"), *decoded(log)[0], T2)


def test_cutoffs_time_only_lineage_and_unrelated_beliefs(db, log):
    _, conn = db
    ingest(conn, log[:4])
    before = storage.read_belief(conn, "b-b", "1")
    ingest(conn, log[4:])
    assert storage.read_belief(conn, "b-b", "1") == before
    assert projection.project_snapshot(decoded(log), T0).complete() == reducer.Snapshot({}).complete()
    at_mention = projection.project_snapshot(decoded(log), log[0][0].recorded_at)
    assert at_mention.records("mentions") and not at_mention.beliefs()
    for cutoff_index in range(1, len(log) + 1):
        at = log[cutoff_index - 1][0].recorded_at
        assert projection.project_snapshot(decoded(log), at).complete() == projection.project_snapshot(decoded(log[:cutoff_index]), at).complete()
    early = projection.project(decoded(log), T2, "1")
    later = projection.project(decoded(log), T3, "1")
    assert later == {key: {**value, "projected_as_of": T3} for key, value in early.items()}


def test_lineage_complete_result_and_pre_event_dependencies(log):
    snap = reducer.Snapshot({})
    for index, (env, payload) in enumerate(decoded(log), 1):
        delta = reducer.reduce(snap, env, payload, T2)
        for key, belief in delta.beliefs.items():
            prior = snap.belief(key)
            predecessors = [] if prior is None else [{"belief_id": key, "view_version_hash": prior["view_version_hash"]}]
            expected = hashing.belief_lineage("1", env.event_id, env.event_hash, predecessors, belief)
            assert belief["view_version_hash"] == hashing._sha256_hex(hashing.canonical_json(expected))
            for field in ("subject_id", "property_id", "lifecycle_status", "claim_candidates",
                          "identity_records", "event_dependencies", "predecessors", "resolution_status", "updated_at"):
                altered = {**belief, field: "changed"}
                assert hashing.belief_lineage("1", env.event_id, env.event_hash, predecessors, altered) != expected
        snap = snap.apply(delta, index)


def test_canonical_collections_and_source_coverage(log):
    snap = projection.project_snapshot(decoded(log[:3]), T2)
    env, payload = decoded(log)[3]
    one = reducer.reduce(snap, env, payload, T2)
    two = reducer.reduce(snap, env, {"claims": payload["claims"][::-1]}, T2)
    # Recorded payload sequences remain dependencies; holding those fixed,
    # enumeration of snapshot sets cannot affect the computed result.
    records = snap.complete()
    records["beliefs"]["b-a"]["identity_records"] *= 2
    records["beliefs"]["b-a"]["event_dependencies"].reverse()
    three = reducer.reduce(reducer.Snapshot(**records), env, payload, T2)
    assert canonical(asdict(one)) == canonical(asdict(three))
    assert {c["claim_candidate_id"] for c in one.beliefs["b-a"]["claim_candidates"]} == {c["claim_candidate_id"] for c in two.beliefs["b-a"]["claim_candidates"]}
    modified = replace(env, source_class="different")  # Hold global event hash fixed.
    changed = reducer.reduce(snap, modified, payload, T2)
    assert changed.beliefs["b-a"]["view_version_hash"] != one.beliefs["b-a"]["view_version_hash"]


def test_append_progress_freshness_uses_entity_not_belief_spelling(db, log):
    _, conn = db
    ingest(conn, log[:2])
    storage.safe_append_event(conn, *log[2], "1")
    status = storage.read_belief_status(conn, "b-a")
    assert status["stale"] and status["belief"] is None
    assert status["append_freshness"]["event_id"] == "e-3"
    assert status["derived_progress"]["event_id"] == "e-2"
    assert storage.read_belief_status(conn, "s-a")["append_freshness"] is None
    storage.materialize_pending(conn, T2)
    assert not storage.read_belief_status(conn, "b-a")["stale"]
    storage.safe_append_event(conn, *log[3], "1")
    assert storage.read_belief_status(conn, "b-a")["stale"]
    assert storage.read_belief_status(conn, "b-b")["stale"]
    assert conn.execute("SELECT count(*) FROM entity_event_index").fetchone() == (0,)


def test_prefix_and_stale_chain_refuse_without_mutation(db, log):
    _, conn = db
    storage.safe_append_event(conn, *log[0], "1")
    before = dump(conn)
    with pytest.raises(storage.ProjectionBehindError):
        storage.safe_append_event(conn, *log[1], "1")
    assert dump(conn) == before
    storage.materialize_pending(conn, T2)
    ingest(conn, log[1:2])
    invalid = event(events.OBSERVATION_RECORDED, {"claims": [claim()]}, 3, log[0])
    before = dump(conn)
    with pytest.raises(ValueError, match="different append position"):
        storage.safe_append_event(conn, *invalid, "1")
    assert dump(conn) == before


@pytest.mark.parametrize("table", ["projected_entities", "projected_mentions", "projected_entity_links",
    "projected_claim_candidates", "projected_beliefs", "projected_events", "derived_progress"])
def test_atomic_publication_at_every_record_kind(db, log, table):
    path, conn = db
    entries = log[:1] if table in ("projected_entities", "projected_mentions", "projected_entity_links") else log[2:3]
    if entries == log[2:3]:
        ingest(conn, log[:2])
    storage.safe_append_event(conn, *entries[0], "1")
    before = dump(conn)
    conn.execute(f"CREATE TEMP TRIGGER fail BEFORE INSERT ON {table} BEGIN SELECT RAISE(ABORT,'publication failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        storage.materialize_pending(conn, T2)
    assert dump(conn) == before
    conn.execute("DROP TRIGGER fail")
    assert storage.materialize_pending(conn, T2) == 1
    assert storage.read_snapshot(conn).complete() == projection.project_snapshot(storage.read_all_events(conn), T2).complete()


def test_append_failure_and_publication_reader_isolation(db, log, monkeypatch):
    path, conn = db
    before = dump(conn)
    original = reducer.reduce
    with closing(storage.init_db(path)) as reader:
        def fail(snapshot, envelope, payload, as_of):
            original(snapshot, envelope, payload, as_of)
            assert reader.execute("SELECT count(*) FROM events").fetchone() == (0,)
            raise RuntimeError("acceptance failure")
        monkeypatch.setattr(reducer, "reduce", fail)
        with pytest.raises(RuntimeError):
            storage.safe_append_event(conn, *log[0], "1")
        assert dump(conn) == before
        monkeypatch.setattr(reducer, "reduce", original)
        storage.safe_append_event(conn, *log[0], "1")
        publish = storage._publish_delta
        def fail_publish(*args):
            publish(*args)
            assert storage.read_snapshot(reader).complete() == reducer.Snapshot({}).complete()
            raise RuntimeError("publication failure")
        monkeypatch.setattr(storage, "_publish_delta", fail_publish)
        with pytest.raises(RuntimeError):
            storage.materialize_pending(conn, T2)
        assert storage.read_snapshot(conn).complete() == reducer.Snapshot({}).complete()


def test_recovery_ignores_corrupt_snapshot_and_rolls_back_failure(db, log, monkeypatch):
    _, conn = db
    ingest(conn, log)
    expected = storage.read_snapshot(conn).complete()
    before = dump(conn)
    original = reducer.reduce
    def fail(snap, env, payload, at):
        if env.event_id == "e-4":
            raise RuntimeError("recovery failure")
        return original(snap, env, payload, at)
    monkeypatch.setattr(reducer, "reduce", fail)
    with pytest.raises(RuntimeError):
        storage.rebuild_projection(conn, T2)
    assert dump(conn) == before
    monkeypatch.setattr(reducer, "reduce", original)
    with conn:
        conn.execute("DELETE FROM projected_mentions")
        conn.execute("UPDATE derived_progress SET log_position=999,event_id='bogus'")
    def forbidden(*args):
        pytest.fail("recovery must not read derived snapshot")
    monkeypatch.setattr(storage, "_read_snapshot", forbidden)
    storage.rebuild_projection(conn, T2)
    monkeypatch.undo()
    assert storage.read_snapshot(conn).complete() == expected


def test_retained_retry_mention_survives_and_no_remint(db, log, monkeypatch):
    _, conn = db
    ingest(conn, log[:1])
    assert storage.read_mention(conn, "m-a")
    assert not storage.read_snapshot(conn).beliefs()
    entry = ingestion.prepare_observation(conn, claims=[claim()], source=SOURCE,
              source_class="direct_observation", occurred_at=T1, recorded_at=T2)
    storage.safe_append_event(conn, *entry, "1")  # Crash before publication.
    storage.materialize_pending(conn, T2)
    before = dump(conn)
    def forbidden(*args, **kwargs):
        pytest.fail("exact retry must not reduce, allocate, or match")
    monkeypatch.setattr(reducer, "reduce", forbidden)
    monkeypatch.setattr(events, "new_event_id", forbidden)
    assert storage.safe_append_event(conn, *entry, "1") is False
    assert storage.materialize_pending(conn, T3) == 0
    assert dump(conn) == before
    with pytest.raises(ValueError, match="retry differs"):
        storage.safe_append_event(conn, replace(entry[0], event_id="reminted"), entry[1], "1")


def test_writer_lookup_and_skeleton_two_then_one_events(db):
    path, conn = db
    m = ingestion.prepare_mention(conn, mention_id="m", subject_id="s", text="device",
          source=SOURCE, source_class="direct_observation", occurred_at=T1, origin_type="observed")
    skeleton.record_mention(path, m)
    o = ingestion.prepare_observation(conn, claims=[claim("c1", "b", "s", "m")],
          source=SOURCE, source_class="direct_observation", occurred_at=T1)
    first = skeleton.record_observation(path, o, "1")
    assert list(first) == ["b"]
    assert skeleton.record_observation(path, o, "1") == first
    next_claim = claim("c2", "b", "s", "m")
    del next_claim["belief_id"]
    p = ingestion.prepare_observation(conn, claims=[next_claim], source=SOURCE,
          source_class="direct_observation", occurred_at=T2)
    assert json.loads(p[1].ciphertext)["claims"][0]["belief_id"] == "b"
    skeleton.record_observation(path, p, "1")
    assert conn.execute("SELECT count(*) FROM events").fetchone() == (3,)
    with pytest.raises(ValueError):
        ingestion.prepare_observation(conn, claims=[claim("c3", "wrong", "s", "m")],
            source=SOURCE, source_class="direct_observation", occurred_at=T2)
    with pytest.raises(NotImplementedError):
        skeleton.record_correction(path, {}, "1")
    with pytest.raises(NotImplementedError):
        storage.materialize_pending(conn, p[0].recorded_at, "0")


def test_same_value_different_standing_and_identity_paths_survive(log):
    # ADR 0015/0023 explicitly allow standing/history as fixture preconditions.
    # This is not a production claim_questioned handler or an origin mapping.
    prefix = projection.project_snapshot(decoded(log[:3]), T2)
    records = prefix.complete()
    restricted = records["claim_candidates"]["c-a"]
    q = event(events.CLAIM_QUESTIONED, {"claim_candidate_id": "c-a", "reason": "fixture restriction"},
              4, log[2])
    qenv, qpayload = decoded([q])[0]
    qrecord = {"event_id": qenv.event_id, "event_hash": qenv.event_hash,
               "envelope": asdict(qenv), "payload": qpayload}
    restricted["verification_state"] = "questioned"
    restricted["restrictions"] = [{"event_id": qenv.event_id, "kind": "questioned"}]
    records["events"][qenv.event_id] = qrecord
    records["beliefs"]["b-a"]["claim_candidates"] = [restricted]
    records["beliefs"]["b-a"]["event_dependencies"].append(qrecord)
    snap = reducer.Snapshot(**records, log_position=4, event_id=qenv.event_id)
    fresh = event(events.OBSERVATION_RECORDED, {"claims": [claim("c-new")]}, 5, q)
    delta = reducer.reduce(snap, *decoded([fresh])[0], T2)
    cs = {c["claim_candidate_id"]: c for c in delta.beliefs["b-a"]["claim_candidates"]}
    assert cs["c-a"] == restricted
    assert cs["c-a"]["value"] == cs["c-new"]["value"]
    assert cs["c-a"]["verification_state"] == "questioned"
    assert cs["c-new"]["verification_state"] == "verified"
    # Distinct established paths to an unchanged claim are input preconditions,
    # not execution of a deferred merge/split.
    other_path = {**restricted, "provenance_paths": [[{"event_id": "fixture-path-2"}]]}
    union = reducer.canonical_claim_candidates([restricted, other_path, restricted, cs["c-new"]])
    assert len(union) == 2
    old = next(c for c in union if c["claim_candidate_id"] == "c-a")
    assert len(old["provenance_paths"]) == 2
    assert reducer.evidence_event_ids(union) == ["e-3", "e-5"]
    assert reducer.canonical_claim_candidates(list(reversed([restricted, other_path, cs["c-new"]]))) == union


@pytest.mark.parametrize("case", ["candidate-duplicate", "belief-duplicate", "historical-belief", "historical-candidate"])
def test_freshness_across_event_and_history(db, log, case):
    _, conn = db
    ingest(conn, log[:3])
    cs = [claim("new")]
    if case == "candidate-duplicate":
        cs.append(claim("new", "b-new", prop="disk"))
    elif case == "belief-duplicate":
        cs = [claim("new", "b-new1", prop="disk"), claim("new2", "b-new2", prop="disk")]
    else:
        records = storage.read_snapshot(conn).complete()
        if case == "historical-belief":
            records["beliefs"]["b-a"]["lifecycle_status"] = "historical"
        else:
            records["claim_candidates"]["c-a"]["verification_state"] = "superseded"
            cs[0]["claim_candidate_id"] = "c-a"
        invalid = event(events.OBSERVATION_RECORDED, {"claims": cs}, 4, log[2])
        with pytest.raises(ValueError):
            reducer.reduce(reducer.Snapshot(**records), *decoded([invalid])[0], T2)
        return
    assert_refused(conn, log[:3], event(events.OBSERVATION_RECORDED, {"claims": cs}, 4, log[2]))


def test_new_mentions_with_identical_text_and_different_actors_are_isolated(db, log):
    _, conn = db
    ingest(conn, log[:1])
    b = event(events.ENTITY_MENTION_RECORDED, mention("s-other", "m-other"), 2, log[0],
              source={"actor_id": "another-speaker", "config": {}}, origin_type="user_stated")
    ingest(conn, [b])
    assert storage.read_mention(conn, "m-a")["text"] == storage.read_mention(conn, "m-other")["text"]
    assert storage.read_entity_link(conn, "m-a")["subject_id"] == "s-a"
    assert storage.read_entity_link(conn, "m-other")["subject_id"] == "s-other"


def test_stale_lookup_duplicate_pair_and_reused_event_id(db, log):
    _, conn = db
    ingest(conn, log[:2])
    assert storage.lookup_current_belief_id(conn, "s-a", "RAM") is None
    ingest(conn, log[2:3])
    # Validate the obsolete lookup against the actual, now-current prefix.
    bad = event(events.OBSERVATION_RECORDED, {"claims": [claim("new", "new-container")]}, 4, log[2])
    assert_refused(conn, log[:3], bad)
    reused = event(events.OBSERVATION_RECORDED, {"claims": [claim("new")]}, 4, log[2], event_id="e-1")
    assert_refused(conn, log[:3], reused)


def test_backward_recording_refuses_without_mutation(db, log):
    _, conn = db
    ingest(conn, log[:1])
    bad = event(events.OBSERVATION_RECORDED, {"claims": [claim()]}, 2, log[0], recorded_at=T0)
    before = dump(conn)
    with pytest.raises(storage.BackdatedRecordingError):
        storage.safe_append_event(conn, *bad, "1")
    assert dump(conn) == before


def test_canonical_sets_preserve_unicode_and_ordered_path_edges():
    members = [{"id": "é", "path": ["b", "a"]}, {"id": "😀", "path": ["a", "b"]}]
    assert hashing.canonical_set(members[::-1] + members) == sorted(members, key=canonical)
    assert b'"path":["b","a"]' in canonical(hashing.canonical_set(members))


@pytest.mark.parametrize("refs", [["m-a"], ["b-a"], ["c-a"], ["e-3"], ["s-b"], ["s-a", "s-b"]])
def test_envelope_entity_refs_cannot_substitute_other_scopes(db, log, refs):
    _, conn = db
    ingest(conn, log[:3])
    bad = event(events.OBSERVATION_RECORDED, {"claims": [claim("new")]}, 4, log[2], entity_refs=refs)
    assert_refused(conn, log[:3], bad)


@pytest.mark.parametrize("table", ["events", "payloads", "identity_event_index", "belief_event_index"])
def test_failure_inside_append_rolls_back_every_record_and_index(db, log, table):
    _, conn = db
    ingest(conn, log[:2])
    before = dump(conn)
    operation = "UPDATE" if table == "identity_event_index" else "INSERT"
    conn.execute(f"CREATE TEMP TRIGGER fail_append AFTER {operation} ON {table} BEGIN SELECT RAISE(ABORT,'append failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        storage.safe_append_event(conn, *log[2], "1")
    assert dump(conn) == before
    conn.execute("DROP TRIGGER fail_append")
    assert storage.safe_append_event(conn, *log[2], "1")


def test_incremental_and_replay_receive_same_complete_pre_event_snapshot(db, log, monkeypatch):
    _, conn = db
    original = reducer.reduce
    seen = []
    def capture(snapshot, env, payload, at):
        seen.append((snapshot.log_position, snapshot.event_id, snapshot.complete()))
        return original(snapshot, env, payload, at)
    monkeypatch.setattr(reducer, "reduce", capture)
    ingest(conn, log)
    # Append validation and publication each see the same complete prefix.
    assert seen[::2] == seen[1::2]
    live = seen[1::2]
    seen.clear()
    projection.project_snapshot(decoded(log), T2)
    assert seen == live


def test_two_connections_cannot_authorize_against_old_append_position(db, log):
    path, conn = db
    ingest(conn, log[:1])
    stale = event(events.OBSERVATION_RECORDED, {"claims": [claim()]}, 3, log[0])
    with closing(storage.init_db(path)) as second:
        ingest(second, log[1:2])
    before = dump(conn)
    with pytest.raises(ValueError, match="different append position"):
        storage.safe_append_event(conn, *stale, "1")
    assert dump(conn) == before


def test_unrelated_subject_stays_fresh_while_another_is_pending(db, log):
    _, conn = db
    ingest(conn, log[:4])
    storage.safe_append_event(conn, *log[4], "1")
    assert storage.read_belief_status(conn, "b-a")["stale"]
    assert not storage.read_belief_status(conn, "b-b")["stale"]


@pytest.mark.parametrize("field", ["supporting_events", "verification_state", "verification_basis",
    "restrictions", "provenance_paths", "source", "occurred_at", "claim_candidate_id"])
def test_lineage_covers_candidate_contents_with_predecessors_fixed(log, field):
    belief = projection.project(decoded(log), T2, "1")["b-a"]
    altered = deepcopy(belief)
    altered["claim_candidates"][0][field] = "changed"
    assert hashing.belief_lineage("1", "e", "hash", [], altered) != hashing.belief_lineage("1", "e", "hash", [], belief)


def test_version_two_existing_database_refuses_byte_unchanged(db, log):
    path, conn = db
    ingest(conn, log[:1])
    with conn:
        conn.execute("UPDATE schema_meta SET version=2")
    before = dump(conn)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    bytes_before = path.read_bytes()
    with pytest.raises(storage.SchemaCompatibilityError, match="unsupported_version"):
        storage.init_db(path)
    assert path.read_bytes() == bytes_before
    assert dump(conn) == before
