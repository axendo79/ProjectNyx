"""ADR 0033: independent legacy admission and unchanged historical semantics."""

from contextlib import closing
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path
import runpy

import pytest

from nyx import immune, integrity, projection, storage, writer


AT = "2026-07-13T12:00:00+00:00"
KINDS = ("observation_recorded", "correction_appended")
BOUNDARIES = ("stage1", "append_submission", "safe_append_event")
LABELS = ("externally_checkable", "locally_checkable", "subjective",
          "structurally_unverifiable")


def raw(value="64GB", verifiability="externally_checkable", **changes):
    return dict(belief_id="ram", value=value, verifiability=verifiability,
                occurred_at=AT, source={"actor_id": "sensor", "config": {}},
                source_class="direct_observation", **changes)


def request(data, kind="observation_recorded"):
    return writer.prepare_event(
        event_type=kind, origin_type="observed", source=data["source"],
        source_class=data["source_class"], occurred_at=data["occurred_at"],
        payload={key: data[key] for key in ("belief_id", "value", "verifiability")})


def layer_a(conn):
    return (conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            storage.last_event_hash(conn))


@pytest.fixture
def published(tmp_path):
    path = tmp_path / "legacy.db"
    with closing(storage.init_db(path, create=True, clock=lambda: AT,
                                 threshold=timedelta(seconds=120))) as conn:
        first = raw("32GB")
        first["occurred_at"] = "2026-07-13T11:00:00+00:00"
        pair = storage.append_submission(conn, request(first), "0")
        storage.materialize_pending(conn, AT, "0")
        assert layer_a(conn) == (1, pair[0].event_hash)
        yield path, conn


def retained(conn, data, kind):
    pair = writer.assign(request(data, kind), AT, storage.last_event_hash(conn))
    # Prove the only defect is the proposed domain, not hashes or append position.
    decoded = integrity.decode_payload(*pair)
    assert decoded == {key: data[key] for key in ("belief_id", "value", "verifiability")}
    assert pair[0].prev_event_hash == storage.last_event_hash(conn)
    return pair


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("boundary", BOUNDARIES)
@pytest.mark.parametrize("field,bad", [
    pytest.param("value", 42, id="integer"),
    pytest.param("value", 1.5, id="float"),
    pytest.param("value", True, id="true"),
    pytest.param("value", False, id="false"),
    pytest.param("value", None, id="null"),
    pytest.param("value", [], id="list"),
    pytest.param("value", {}, id="object"),
    pytest.param("verifiability", "bogus", id="unknown-label"),
    pytest.param("verifiability", 42, id="non-string-label"),
])
def test_domain_refusal_preserves_layer_a(published, monkeypatch, kind, boundary, field, bad):
    _, conn = published
    data = raw(event_type=kind)
    data[field] = bad
    before = layer_a(conn)
    if boundary == "stage1":
        attempt = lambda: immune.stage1_schema_validate(data)
    elif boundary == "append_submission":
        submission = request(data, kind)

        def forbidden_assignment(*args, **kwargs):
            pytest.fail("legacy domain refusal must precede writer.assign")

        monkeypatch.setattr(writer, "assign", forbidden_assignment)
        attempt = lambda: storage.append_submission(conn, submission, "0")
    else:
        pair = retained(conn, data, kind)
        attempt = lambda: storage.safe_append_event(conn, *pair, "0")
    with pytest.raises(integrity.IntegrityError, match=field):
        attempt()
    assert layer_a(conn) == before


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("boundary", BOUNDARIES)
@pytest.mark.parametrize("value", ["64GB", ""])
@pytest.mark.parametrize("label", LABELS)
def test_strings_and_labels_survive_publication_read_and_replay(
        published, kind, boundary, value, label):
    _, conn = published
    data = raw(value, label, event_type=kind)
    if boundary == "stage1":
        assert immune.stage1_schema_validate(data).accepted
    if boundary == "safe_append_event":
        pair = retained(conn, data, kind)
        assert storage.safe_append_event(conn, *pair, "0")
    else:
        pair = storage.append_submission(conn, request(data, kind), "0")
    assert layer_a(conn) == (2, pair[0].event_hash)
    storage.materialize_pending(conn, AT, "0")
    belief = storage.read_belief(conn, "ram", "0")
    replayed = projection.project(storage.read_all_events(conn), AT, "0")["ram"]
    assert belief == replayed
    assert belief["current_value"] == value
    assert belief["verifiability"] == label


def test_stage1_missing_value_still_returns_missing_field(published):
    _, conn = published
    data = raw()
    del data["value"]
    before = layer_a(conn)
    result = immune.stage1_schema_validate(data)
    assert not result.accepted
    assert result.reason == "missing field: value"
    assert layer_a(conn) == before


@pytest.mark.parametrize("field", ["belief_id", "verifiability", "occurred_at", "source", "source_class"])
@pytest.mark.parametrize("missing", ["absent", "null", "empty"])
def test_other_stage1_missing_field_behavior_unchanged(published, field, missing):
    _, conn = published
    data = raw()
    if missing == "absent":
        del data[field]
    else:
        data[field] = None if missing == "null" else ""
    before = layer_a(conn)
    result = immune.stage1_schema_validate(data)
    assert not result.accepted
    assert result.reason == f"missing field: {field}"
    assert layer_a(conn) == before


@pytest.mark.parametrize("number", [42, 1.5])
def test_historical_numeric_fixture_preserves_replay_and_text_affinity(published, number):
    path, conn = published
    envelope, payload = retained(conn, raw(number), "observation_recorded")
    # No numeric store exists: construct history below the new admission gates.
    with conn:
        for table, record in (("events", envelope), ("payloads", payload)):
            values = asdict(record)
            conn.execute(
                f"INSERT INTO {table} ({','.join(values)}) VALUES ({','.join('?' for _ in values)})",
                tuple(values.values()))
        conn.execute(
            "UPDATE entity_event_index SET latest_event_id=?, latest_event_hash=?, updated_at=? "
            "WHERE entity_id='ram'", (envelope.event_id, envelope.event_hash, AT))
    original_log = storage.read_all_events(conn)
    storage.materialize_pending(conn, AT, "0")
    assert storage.read_all_events(conn) == original_log
    before = tuple(conn.iterdump())
    replayed = projection.project(original_log, AT, "0")["ram"]["current_value"]
    assert type(replayed) is type(number)
    assert replayed == number
    assert storage.read_belief(conn, "ram", "0")["current_value"] == str(number)
    verifier = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/verify_store.py"))
    report = verifier["verify_store"](path, "0")
    assert report["ok"], report["failures"]
    assert report["event_count"] == 2
    assert tuple(conn.iterdump()) == before
