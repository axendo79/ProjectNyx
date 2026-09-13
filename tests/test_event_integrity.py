"""Integrity failures refuse before publishing or silently shortening a log."""

import json
from contextlib import closing
from dataclasses import asdict, replace

import pytest

from nyx import events, hashing, integrity, projection, skeleton, storage
from test_reducer_boundary import T1, T2, claim, decoded, event, mention


def entries(version):
    if version == "0":
        result = []
        for index in range(1, 4):
            result.append(event(events.OBSERVATION_RECORDED,
                {"belief_id": "b-a", "value": str(index), "verifiability": "externally_checkable"},
                index, result[-1] if result else None))
        return result
    first = event(events.ENTITY_MENTION_RECORDED, mention())
    second = event(events.OBSERVATION_RECORDED, {"claims": [claim()]}, 2, first)
    third = event(events.OBSERVATION_RECORDED, {"claims": [claim("c-next")]}, 3, second)
    return [first, second, third]


def rehash(envelope, data=None, **changes):
    envelope = replace(envelope, **changes)
    if data is not None:
        envelope = replace(envelope,
            payload_hash=hashing._sha256_hex(hashing.canonical_json(data)),
            idempotency_key=hashing.idempotency_key(json.loads(envelope.source)["actor_id"],
                                                   envelope.occurred_at, data))
    material = asdict(envelope)
    del material["event_hash"], material["prev_event_hash"]
    return replace(envelope, event_hash=hashing.event_hash(material, envelope.prev_event_hash))


@pytest.fixture(params=["0", "1", "2"])
def database(tmp_path, request):
    version = request.param
    with closing(storage.init_db(tmp_path / "nyx.db", create=True)) as conn:
        log = entries(version)
        for pair in log:
            storage.safe_append_event(conn, *pair, version)
            storage.materialize_pending(conn, T2, version)
        yield conn, version, log


@pytest.mark.parametrize("damage", ["payload", "payload_hash", "missing", "null",
                                    "event_hash", "predecessor"])
def test_read_and_rebuild_refuse_corruption_without_publication(database, damage):
    conn, version, log = database
    env, payload = log[1]
    with conn:
        if damage == "payload":
            data = json.loads(payload.ciphertext)
            if version == "0":
                data["value"] = "tampered"
            else:
                data["claims"][0]["value"] = "tampered"
            conn.execute("UPDATE payloads SET ciphertext=? WHERE event_id=?",
                         (hashing.canonical_json(data), env.event_id))
        elif damage == "payload_hash":
            conn.execute("UPDATE payloads SET payload_hash=? WHERE event_id=?", ("0"*64, env.event_id))
        elif damage == "missing":
            conn.execute("DELETE FROM payloads WHERE event_id=?", (env.event_id,))
        elif damage == "null":
            conn.execute("UPDATE payloads SET ciphertext=NULL WHERE event_id=?", (env.event_id,))
        else:
            # Simulate external corruption in this disposable database only.
            conn.execute("DROP TRIGGER no_update_events")
            if damage == "event_hash":
                conn.execute("UPDATE events SET event_hash=? WHERE event_id=?", ("0"*64, env.event_id))
            else:
                changed = rehash(env, prev_event_hash="f"*64)
                conn.execute("UPDATE events SET prev_event_hash=?,event_hash=? WHERE event_id=?",
                             (changed.prev_event_hash, changed.event_hash, env.event_id))
    before = tuple(conn.iterdump())
    for read in (lambda: storage.read_all_events(conn),
                 lambda: storage.evaluate_whole_view(conn, T2, version),
                 lambda: storage._pending_events(conn, 1),
                 lambda: storage.find_recorded_event(conn, env.idempotency_key)):
        with pytest.raises(integrity.IntegrityError):
            read()
        assert tuple(conn.iterdump()) == before
        assert not conn.in_transaction
    if version != "0":
        with pytest.raises(integrity.IntegrityError):
            storage.rebuild_projection(conn, T2, version)
        assert tuple(conn.iterdump()) == before


def test_worker_does_not_skip_missing_unpublished_payload(database):
    conn, version, log = database
    if version == "0":
        data = {"belief_id": "b-a", "value": "new", "verifiability": "externally_checkable"}
    else:
        data = {"claims": [claim("c-unpublished")]}
    pair = event(events.OBSERVATION_RECORDED, data, 4, log[-1])
    storage.safe_append_event(conn, *pair, version)
    with conn:
        conn.execute("DELETE FROM payloads WHERE event_id=?", (pair[0].event_id,))
    before = tuple(conn.iterdump())
    with pytest.raises(integrity.IntegrityError, match="missing payload row"):
        storage.materialize_pending(conn, T2, version)
    assert tuple(conn.iterdump()) == before


@pytest.mark.parametrize("damage", ["payload", "envelope", "predecessor", "omission", "order"])
def test_direct_replay_checks_hashes_and_chain(database, damage):
    _, version, log = database
    replay = decoded(log)
    env, data = replay[1]
    if damage == "payload":
        replay[1] = env, {**data, "extra": "tampered"}
    elif damage == "envelope":
        replay[1] = replace(env, source_class="tampered"), data
    elif damage == "predecessor":
        replay[1] = rehash(env, prev_event_hash="f"*64), data
    elif damage == "omission":
        replay.pop(1)
    else:
        replay.reverse()
    with pytest.raises(integrity.IntegrityError):
        projection.project(replay, T2, version)


@pytest.mark.parametrize("field,value", [("schema_version", "999"), ("origin_type", "invented"),
    ("event_type", "invented"), ("event_id", ""), ("source_class", ""),
    ("source", '[]'), ("entity_refs", '{}'),
    ("occurred_at", "2026-09-08T12:00:00"), ("recorded_at", "2026-09-08T12:00:00")])
@pytest.mark.parametrize("version", ["0", "1", "2"])
def test_envelope_schema_refuses_at_append_and_replay(tmp_path, version, field, value):
    with closing(storage.init_db(tmp_path / "schema.db", create=True)) as conn:
        env, payload = entries(version)[0]
        env = rehash(env, **{field: value})
        before = tuple(conn.iterdump())
        for operation in (lambda: storage.safe_append_event(conn, env, payload, version),
                          lambda: projection.project([(env,json.loads(payload.ciphertext))],T2,version)):
            with pytest.raises((ValueError, NotImplementedError)):
                operation()
        assert tuple(conn.iterdump()) == before


@pytest.mark.parametrize("field,value", [("event_hash", "0"*64), ("prev_event_hash", "f"*64),
                                        ("payload_hash", "f"*64)])
def test_append_refuses_integrity_failure_atomically(database, field, value):
    conn, version, log = database
    data = ({"belief_id":"b-a", "value":"four", "verifiability":"externally_checkable"}
            if version == "0" else {"claims":[claim("c-four")]})
    env, payload = event(events.OBSERVATION_RECORDED, data, 4, log[-1])
    env = (rehash(env, **{field:value}) if field == "prev_event_hash"
           else replace(env, **{field:value}))
    before = tuple(conn.iterdump())
    with pytest.raises(integrity.IntegrityError):
        storage.safe_append_event(conn, env, payload, version)
    assert tuple(conn.iterdump()) == before


def test_retained_retry_and_conflicting_ids(database):
    conn, version, log = database
    before = tuple(conn.iterdump())
    assert storage.safe_append_event(conn, *log[0], version) is False  # Tip has advanced.
    env, payload = log[0]
    reminted = rehash(env, event_id="reminted")
    with pytest.raises(integrity.IntegrityError, match="retry differs"):
        storage.safe_append_event(conn, reminted, replace(payload,event_id="reminted"), version)
    different = {**json.loads(payload.ciphertext), "different":"submission"}
    changed = rehash(env, different)
    changed_payload = replace(payload,payload_hash=changed.payload_hash,ciphertext=hashing.canonical_json(different))
    with pytest.raises(integrity.IntegrityError, match="retry differs"):
        storage.safe_append_event(conn, changed, changed_payload, version)
    assert tuple(conn.iterdump()) == before


def test_legacy_wrapper_reuses_recorded_pair_without_allocating_ids(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    storage.init_db(path,create=True).close()
    raw = dict(belief_id="b-a",value="64GB",verifiability="externally_checkable",
               source={"actor_id":"sensor","config":{}},source_class="direct_observation",occurred_at=T1)
    skeleton.record_observation(path, raw)
    def forbidden():
        pytest.fail("a retry must reuse the recorded event ID")
    monkeypatch.setattr(events,"new_event_id",forbidden)
    skeleton.record_observation(path, dict(raw))
    with pytest.raises(ValueError,match="retry differs"):
        skeleton.record_observation(path,{**raw,"source_class":"different"})
    with closing(storage.init_db(path)) as conn:
        assert len(storage.read_all_events(conn)) == 1


@pytest.mark.parametrize("applied,latest,present,valid,expected", [
    (None,None,False,True,False), (None,1,False,True,True), (1,2,True,True,True),
    (2,2,True,True,False), (3,2,True,True,False), (2,2,False,True,True),
    (None,None,True,True,True), (2,2,True,False,True),
])
def test_staleness_uses_positions(applied, latest, present, valid, expected):
    assert projection.is_stale(applied,latest,record_present=present,progress_valid=valid) is expected


def test_staleness_refuses_old_hash_signature():
    with pytest.raises(ValueError,match="positions"):
        projection.is_stale("a"*64,"b"*64)


def test_staleness_from_progress_without_presence_override():
    assert not projection.is_stale(None, None)
    assert projection.is_stale(None, 1)
    assert projection.is_stale(1, 2)
    assert not projection.is_stale(2, 2)


def test_pending_checks_applied_anchor_even_when_caught_up(database):
    conn, version, log = database
    with conn:
        conn.execute("DELETE FROM payloads WHERE event_id=?", (log[-1][0].event_id,))
    before = tuple(conn.iterdump())
    with pytest.raises(integrity.IntegrityError, match="missing payload row"):
        storage.materialize_pending(conn, T2, version)
    assert tuple(conn.iterdump()) == before


@pytest.mark.parametrize("version", ["1", "2"])
def test_identity_status_rejects_false_progress_identity(tmp_path, version):
    with closing(storage.init_db(tmp_path / "progress.db", create=True)) as conn:
        pair = entries(version)[0]
        storage.safe_append_event(conn, *pair, version)
        storage.materialize_pending(conn, T2, version)
        with conn:
            conn.execute("UPDATE derived_progress SET event_id='wrong' WHERE projector_version=?",
                         (version,))
        if version == "2":
            # Version 2 refuses an unproven tree snapshot before serving records.
            with pytest.raises(ValueError, match="derived progress"):
                storage.read_mention_status(conn, "m-a", version)
        else:
            assert storage.read_mention_status(conn, "m-a", version)["stale"]


def test_direct_legacy_fold_refuses_payload_tampering():
    envelope, payload = decoded(entries("0"))[0]
    with pytest.raises(integrity.IntegrityError, match="payload hash"):
        projection.fold(None, envelope, {**payload, "value": "tampered"}, T2)


@pytest.mark.parametrize("version", ["1", "2"])
@pytest.mark.parametrize("read,status,key", [
    (storage.read_entity,storage.read_entity_status,"s-a"),
    (storage.read_mention,storage.read_mention_status,"m-a"),
    (storage.read_entity_link,storage.read_entity_link_status,"m-a"),
])
def test_identity_freshness_discloses_unpublished_absence(tmp_path,version,read,status,key):
    with closing(storage.init_db(tmp_path / "identity.db",create=True)) as conn:
        log = entries(version)
        assert status(conn,key,version)["stale"] is False
        storage.safe_append_event(conn,*log[0],version)
        result = status(conn,key,version)
        assert result["record"] is None and result["stale"] is True
        assert result["derived_progress"] is None
        assert result["append_freshness"]["log_position"] == 1
        with pytest.warns(storage.StaleProjectionWarning) as caught:
            assert read(conn,key,version) is None
        assert caught[0].message.status == result
        storage.materialize_pending(conn,T2,version)
        assert status(conn,key,version)["stale"] is False
        assert read(conn,key,version) == status(conn,key,version)["record"]
        assert status(conn,"absent",version)["stale"] is False
        storage.safe_append_event(conn,*log[1],version)
        with pytest.warns(storage.StaleProjectionWarning):
            assert read(conn,key,version) is not None
        storage.materialize_pending(conn,T2,version)
        assert not status(conn,key,version)["stale"]


@pytest.mark.parametrize("version", ["1", "2"])
def test_snapshot_public_read_parity_and_detachment(version):
    snapshot = projection.project_snapshot(decoded(entries(version)),T2,version)
    assert isinstance(snapshot.events(),list)
    assert snapshot.events() == hashing.canonical_set(list(snapshot.records("events").values()))
    assert snapshot.current_belief("s-a","RAM") == snapshot.belief("b-a")
    assert snapshot.current_belief("unknown","RAM") is None
    returned = snapshot.current_belief("s-a","RAM")
    returned["claim_candidates"].clear()
    snapshot.events()[0]["payload"].clear()
    assert len(snapshot.current_belief("s-a","RAM")["claim_candidates"]) == 2
    assert snapshot.events()[0]["payload"]
