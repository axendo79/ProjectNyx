"""RV2: unsupported origin semantics must refuse before the Layer A commit."""

from contextlib import closing

import pytest

from nyx import integrity, projection, storage, writer


AT = "2026-07-13T12:00:00Z"


def request(origin, event_type, event_id):
    return writer.prepare_event(
        event_type=event_type, origin_type=origin,
        source={"actor_id": "origin-test", "config": {}},
        source_class="direct_observation", occurred_at=AT, event_id=event_id,
        payload={"belief_id": "ram", "value": event_id, "verifiability": "externally_checkable"})


def layer_a(conn):
    return conn.execute("SELECT count(*) FROM events").fetchone()[0], storage.last_event_hash(conn)


def append(conn, submission, boundary):
    if boundary == "append_submission":
        return storage.append_submission(conn, submission, "0")
    pair = writer.assign(submission, AT, storage.last_event_hash(conn))
    integrity.decode_payload(*pair)  # Hashes/schema are valid; origin semantics are the defect.
    assert storage.safe_append_event(conn, *pair, "0")
    return pair


@pytest.mark.parametrize("boundary", ["append_submission", "safe_append_event"])
@pytest.mark.parametrize("prior_belief", [False, True])
@pytest.mark.parametrize("event_type", ["observation_recorded", "correction_appended"])
@pytest.mark.parametrize("origin", ["user_stated", "verified_external", "derived", "personal"])
def test_unmapped_origin_refuses_without_poisoning_replay(
        tmp_path, boundary, prior_belief, event_type, origin):
    with closing(storage.init_db(tmp_path / "origin.db", create=True, clock=lambda: AT)) as conn:
        if prior_belief:
            storage.append_submission(conn, request("observed", "observation_recorded", "e-prior"), "0")
            storage.materialize_pending(conn, AT, "0")
        before = layer_a(conn)
        before_store = tuple(conn.iterdump())
        with pytest.raises(NotImplementedError, match="origin -> verification_state mapping"):
            append(conn, request(origin, event_type, "e-refused"), boundary)
        assert layer_a(conn) == before
        assert tuple(conn.iterdump()) == before_store
        assert projection.project(storage.read_all_events(conn), AT, "0") == (
            {} if not prior_belief else {"ram": storage.read_belief(conn, "ram", "0")})
        # Refusal must not prevent a subsequent supported append/publication/replay.
        pair = append(conn, request("observed", event_type, "e-observed"), boundary)
        assert layer_a(conn) == (before[0] + 1, pair[0].event_hash)
        storage.materialize_pending(conn, AT, "0")
        assert storage.read_belief(conn, "ram", "0") == projection.project(
            storage.read_all_events(conn), AT, "0")["ram"]
