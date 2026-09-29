"""Malformed semantic sources refuse before actor lookup or Layer A mutation."""

from contextlib import closing
from datetime import timedelta

import pytest

from nyx import ingestion, integrity, storage, writer


AT = "2026-07-13T12:00:00Z"
MALFORMED_SOURCES = [
    pytest.param({"config": {}}, "source.actor_id must be a nonempty string", id="missing-actor"),
    pytest.param({"actor_id": 42}, "source.actor_id must be a nonempty string", id="integer-actor"),
    pytest.param({"actor_id": ""}, "source.actor_id must be a nonempty string", id="empty-actor"),
    pytest.param([], "source must be an object", id="list-source"),
    pytest.param({"actor_id": "sensor", "config": []}, "source.config must be an object", id="list-config"),
]


def request(source, event_id, projector_version):
    payload = ({"belief_id": event_id, "value": "64GB", "verifiability": "externally_checkable"}
               if projector_version == "0" else
               {"mention_id": f"m-{event_id}", "subject_id": f"s-{event_id}",
                "text": "device", "link_state": "constitutive"})
    return writer.prepare_event(
        event_type="observation_recorded" if projector_version == "0" else "entity_mention_recorded",
        origin_type="observed", source=source, source_class="direct_observation",
        occurred_at=AT, payload=payload, event_id=event_id,
        entity_refs=None if projector_version == "0" else [f"s-{event_id}"])


@pytest.mark.parametrize("source,message", MALFORMED_SOURCES)
@pytest.mark.parametrize("boundary", ["validate", "assign"])
def test_malformed_source_refuses_before_actor_lookup(source, message, boundary):
    pair = request(source, "bad", "0")
    with pytest.raises(integrity.IntegrityError) as error:
        if boundary == "validate":
            writer.validate_request(pair)
        else:
            writer.assign(pair, AT, None)
    assert str(error.value) == message


@pytest.mark.parametrize("source,message", MALFORMED_SOURCES)
@pytest.mark.parametrize("projector_version", ["0", "1", "2"])
def test_malformed_source_append_preserves_layer_a(tmp_path, source, message, projector_version):
    with closing(storage.init_db(tmp_path / "store.db", create=True, clock=lambda: AT,
                                 threshold=timedelta(seconds=120))) as conn:
        tip = ingestion.submit(conn, request({"actor_id": "sensor", "config": {}}, "good",
                                            projector_version), AT, projector_version)
        before_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        before_hash = storage.last_event_hash(conn)
        assert before_count == 1 and before_hash == tip[0].event_hash
        with pytest.raises(integrity.IntegrityError) as error:
            storage.append_submission(conn, request(source, "bad", projector_version), projector_version)
        assert str(error.value) == message
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == before_count
        assert storage.last_event_hash(conn) == before_hash
