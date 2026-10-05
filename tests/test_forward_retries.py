"""ADR 0034 section 9 keeps semantic retries before target eligibility."""
from contextlib import closing
import pytest
from nyx import events, ingestion, integrity, storage, transition_dependencies, writer
from test_forward_correction import append
from test_forward_expiry import expiry
from test_forward_replacement import replacement, simple_log
from test_reducer_boundary import T1, T2


def request(kind, payload, eid):
    return writer.prepare_event(event_type=kind, payload=payload, event_id=eid,
        origin_type="observed", source={"actor_id": "operator", "config": {}},
        source_class="direct_observation", occurred_at=T1, entity_refs=["s-a"])


def test_retry_after_successor_expired(tmp_path, monkeypatch):
    with closing(storage.init_db(tmp_path / "store.db", create=True)) as conn:
        for pair in simple_log(): append(conn, pair)
        conn.clock = lambda: T2
        first = request(events.CANDIDATE_REPLACED, replacement(["c-a"]), "U1")
        committed = ingestion.submit(conn, first, T2, "3")
        ingestion.submit(conn, request(events.CANDIDATE_EXPIRED, expiry(["c-next"]), "U2"), T2, "3")
        before = tuple(conn.iterdump())
        def unexpected(*args): raise AssertionError("committed retry tested target eligibility")
        monkeypatch.setattr(transition_dependencies, "check_transition_dependencies", unexpected)
        assert ingestion.submit(conn, first, T2, "3") == committed
        assert tuple(conn.iterdump()) == before
        assert storage.read_claim_candidate(conn, "c-next", "3")["live_status"] == "expired"


@pytest.mark.parametrize("first_kind,second_kind,data", [
    (events.CANDIDATE_REPLACED, events.CANDIDATE_EXPIRED, replacement(["c-a"])),
    (events.CANDIDATE_EXPIRED, events.CANDIDATE_REPLACED, expiry(["c-a"]))])
def test_cross_type_key_collision_precedes_payload_or_target_validation(tmp_path, first_kind, second_kind, data):
    with closing(storage.init_db(tmp_path / "store.db", create=True)) as conn:
        for pair in simple_log(): append(conn, pair)
        conn.clock = lambda: T2
        ingestion.submit(conn, request(first_kind, data, "first"), T2, "3")
        before = tuple(conn.iterdump())
        with pytest.raises(integrity.IntegrityError, match="semantic"):
            ingestion.submit(conn, request(second_kind, data, "second"), T2, "3")
        assert tuple(conn.iterdump()) == before
