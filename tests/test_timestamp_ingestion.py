"""Reject ambiguous input before writing; preserve every accepted timestamp byte."""

import json
from contextlib import closing
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from nyx import events, immune, ingestion, skeleton, storage
from test_reducer_boundary import SOURCE, T1, T2, claim, event, mention


RAW = dict(belief_id="b-a", value="64GB", verifiability="externally_checkable",
           source=SOURCE, source_class="direct_observation", occurred_at=T1)


@pytest.mark.parametrize("timestamp", ["2026-07-13", "2026-07-13T00:00:00",
                                       "2026-07-13T00:00:00.123456"])
@pytest.mark.parametrize("writer", [skeleton.record_observation, skeleton.record_correction])
def test_legacy_stage_one_refuses_before_storage_or_allocation(monkeypatch, writer, timestamp):
    raw = {**RAW, "occurred_at": timestamp}
    result = immune.stage1_schema_validate(raw)
    assert not result.accepted and result.stage_reached == 1
    assert "timezone offset" in result.reason

    def forbidden(*args, **kwargs):
        pytest.fail("ambiguous ingestion reached storage or ID allocation")

    monkeypatch.setattr(storage, "init_db", forbidden)
    monkeypatch.setattr(events, "new_event_id", forbidden)
    with pytest.raises(ValueError, match="immune stage 1.*timezone offset"):
        writer("unused.db", raw)


@pytest.mark.parametrize("field", ["occurred_at", "recorded_at"])
def test_event_preparation_refuses_before_hashing_or_allocation(monkeypatch, field):
    def forbidden(*args, **kwargs):
        pytest.fail("ambiguous ingestion reached hashing or ID allocation")

    monkeypatch.setattr(events.hashing, "canonical_json", forbidden)
    monkeypatch.setattr(events, "new_event_id", forbidden)
    arguments = dict(event_type=events.OBSERVATION_RECORDED, origin_type="observed",
                     source=SOURCE, source_class="direct_observation", occurred_at=T1,
                     recorded_at=T2, payload={}, prev_event_hash=None)
    arguments[field] = "2026-07-13T00:00:00"
    with pytest.raises(ValueError, match=f"{field}.*timezone offset"):
        events.build_event(**arguments)


@pytest.mark.parametrize("version", ["1", "2"])
@pytest.mark.parametrize("field", ["occurred_at", "recorded_at"])
def test_stage_two_preparers_refuse_naive_input(tmp_path, monkeypatch, version, field):
    with closing(storage.init_db(tmp_path / "preparation.db", create=True)) as conn:
        before = tuple(conn.iterdump())
        def forbidden(*args, **kwargs):
            pytest.fail("ambiguous preparation reached a writer lookup")

        monkeypatch.setattr(storage, "last_event_hash", forbidden)
        monkeypatch.setattr(storage, "lookup_current_belief_id", forbidden)
        common = dict(source=SOURCE, source_class="direct_observation",
                      occurred_at=T1, recorded_at=T2)
        common[field] = "2026-07-13T00:00:00"
        with pytest.raises(ValueError, match="timezone offset"):
            ingestion.prepare_mention(conn, mention_id="m-a", subject_id="s-a",
                                      text="device", origin_type="observed", **common)
        with pytest.raises(ValueError, match="timezone offset"):
            ingestion.prepare_observation(conn, claims=[claim()], projector_version=version, **common)
        assert tuple(conn.iterdump()) == before


@pytest.mark.parametrize("version", ["1", "2"])
@pytest.mark.parametrize("field", ["occurred_at", "recorded_at"])
@pytest.mark.parametrize("event_type,writer,payload", [
    (events.ENTITY_MENTION_RECORDED, skeleton.record_mention, mention()),
    (events.OBSERVATION_RECORDED, skeleton.record_observation, {"claims": [claim()]}),
])
def test_stage_two_wrappers_refuse_before_storage(monkeypatch, version, field, event_type, writer, payload):
    envelope, body = event(event_type, payload)
    malformed = replace(envelope, **{field: "2026-07-13T00:00:00"})

    def forbidden(*args, **kwargs):
        pytest.fail("ambiguous retained input reached storage")

    monkeypatch.setattr(storage, "init_db", forbidden)
    with pytest.raises(ValueError, match=f"{field}.*timezone offset"):
        writer("unused.db", (malformed, body), version)


@pytest.mark.parametrize("version", ["1", "2"])
@pytest.mark.parametrize("field", ["occurred_at", "recorded_at"])
def test_retained_pair_refuses_before_pending_publication(tmp_path, version, field):
    with closing(storage.init_db(tmp_path / "retained.db", create=True)) as conn:
        first = event(events.ENTITY_MENTION_RECORDED, mention())
        storage.safe_append_event(conn, *first, version)  # Deliberately unpublished.
        envelope, payload = event(events.OBSERVATION_RECORDED, {"claims": [claim()]}, 2, first)
        malformed = replace(envelope, **{field: "2026-07-13T00:00:00"})
        before = tuple(conn.iterdump())
        with pytest.raises(ValueError, match=f"{field}.*timezone offset"):
            ingestion.submit(conn, (malformed, payload), T2, version)
        assert tuple(conn.iterdump()) == before
        assert not conn.in_transaction


@pytest.mark.parametrize("timestamp", ["2026-07-13T00:00:00Z", "2026-07-13T00:00:00+00:00",
    "2026-07-12T19:00:00-05:00", "2026-07-13T05:30:00+05:30", "2026-07-13T00:00:00.123400Z"])
def test_accepted_timestamp_spellings_survive_ingestion_and_retry(tmp_path, timestamp):
    path = tmp_path / "spellings.db"
    storage.init_db(path, create=True).close()
    raw = {**RAW, "occurred_at": timestamp}
    assert immune.stage1_schema_validate(raw).accepted
    skeleton.record_observation(path, raw)
    with closing(storage.init_db(path)) as conn:
        first = storage.read_all_events(conn)
    skeleton.record_observation(path, raw)
    with closing(storage.init_db(path)) as conn:
        assert storage.read_all_events(conn) == first
    assert first[0][0].occurred_at == timestamp
    assert raw["occurred_at"] == timestamp
    envelope, _ = event(events.ENTITY_MENTION_RECORDED, mention(),
                        occurred_at=timestamp, recorded_at=timestamp)
    assert envelope.occurred_at == envelope.recorded_at == timestamp


def test_ingestion_rebuilds_existing_version_zero_golden_envelopes_byte_identically():
    golden = json.loads((Path(__file__).parent / "fixtures/version0_ordinary.json").read_text(encoding="utf-8"))
    for envelope, payload in golden["events"]:
        arguments = {key: value for key, value in envelope.items()
                     if key not in ("event_hash", "payload_hash", "idempotency_key", "schema_version")}
        arguments["source"] = json.loads(arguments["source"])
        arguments["entity_refs"] = (None if arguments["entity_refs"] is None
                                    else json.loads(arguments["entity_refs"]))
        rebuilt, _ = events.build_event(payload=payload, **arguments)
        assert asdict(rebuilt) == envelope
