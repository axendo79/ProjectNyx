"""ADR 0030: ownership, semantic retries and clock checks at the actual append."""

from contextlib import closing
from dataclasses import fields, replace
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from queue import Queue
import subprocess
import sys
from threading import Thread

import pytest

from nyx import events, hashing, ingestion, integrity, projection, reducer, committed, storage, writer

AT = "2026-07-13T12:00:00Z"
THRESHOLD = timedelta(seconds=120)  # Explicit fixture, not the production default.


def shifted(seconds):
    return (datetime.fromisoformat(AT) + timedelta(seconds=seconds)).isoformat()


def samples(conn, *values):
    source = iter(values)

    def clock():
        assert conn.in_transaction, "writer sample must be under the append lock"
        return next(source)

    conn.clock = clock


def mention(conn, name="a"):
    return ingestion.prepare_mention(
        conn, mention_id=f"m-{name}", subject_id=f"s-{name}", text=name,
        source={"actor_id": "test", "config": {}}, source_class="direct_observation",
        occurred_at=AT, origin_type="observed", event_id=f"e-{name}")


@pytest.fixture(params=["1", "2"])
def db(tmp_path, request):
    path = tmp_path / "store.db"
    with closing(storage.init_db(path, create=True, clock=lambda: AT, threshold=THRESHOLD)) as conn:
        yield path, conn, request.param


def submit(conn, request, projector_version):
    return ingestion.submit(conn, request, shifted(86400), projector_version)


def test_production_constant_and_semantic_field_classification():
    assert writer.MAX_CLOCK_SKEW == timedelta(seconds=120)
    # ADR 0030 section 3's enumerated caller-owned fields. Any new field must be
    # explicitly classified; comparison itself uses the complement, not this list.
    caller_envelope = {"event_id", "schema_version", "event_type", "occurred_at",
                       "source", "source_class", "origin_type", "entity_refs"}
    caller_payload = {"event_id", "canonical_entity_id", "ciphertext", "redacted"}
    assert {f.name for f in fields(events.Envelope)} - writer.POSITIONAL_DERIVED == caller_envelope
    assert {f.name for f in fields(events.Payload)} - writer.POSITIONAL_DERIVED == caller_payload
    assert {f.name for f in fields(writer.EventRequest)} == caller_envelope
    assert {f.name for f in fields(writer.PayloadRequest)} == caller_payload
    assert writer.POSITIONAL_DERIVED == {
        "recorded_at", "prev_event_hash", "event_hash", "payload_hash", "idempotency_key"}


@pytest.mark.parametrize("behind,refuses", [(120, False), (120.000001, True), (0, False), (-1, False)])
def test_sample_one_boundary_clamping_and_equal_timestamps(db, behind, refuses):
    _, conn, version = db
    first = submit(conn, mention(conn), version)
    before = tuple(conn.iterdump())
    observed = shifted(-behind)
    samples(conn, observed, observed)
    if refuses:
        with pytest.raises(writer.ClockSkewError) as raised:
            submit(conn, mention(conn, "b"), version)
        assert raised.value.details() == {
            "reason_code": "tip_ahead_of_clock", "tip_event_id": "e-a",
            "tip_recorded_at": AT, "observed_writer_clock": observed, "threshold": "120 s"}
        assert tuple(conn.iterdump()) == before
    else:
        result = submit(conn, mention(conn, "b"), version)
        assert datetime.fromisoformat(result[0].recorded_at) == max(
            datetime.fromisoformat(AT), datetime.fromisoformat(observed))
        assert result[0].prev_event_hash == first[0].event_hash
        assert result[0].event_hash != first[0].event_hash


@pytest.mark.parametrize("genesis", [False, True])
@pytest.mark.parametrize("behind,refuses", [(120, False), (120.000001, True)])
def test_sample_two_validates_without_reassignment(db, genesis, behind, refuses):
    _, conn, version = db
    if not genesis:
        submit(conn, mention(conn), version)
    before = tuple(conn.iterdump())
    samples(conn, AT, shifted(-behind))
    if refuses:
        with pytest.raises(writer.ClockSkewError) as raised:
            submit(conn, mention(conn, "b"), version)
        assert raised.value.reason_code == "assignment_ahead_of_clock"
        assert raised.value.tip_event_id == (None if genesis else "e-a")
        assert raised.value.tip_recorded_at == (None if genesis else AT)
        assert raised.value.observed_writer_clock == shifted(-behind)
        assert raised.value.threshold == "120 s"
        assert tuple(conn.iterdump()) == before
    else:
        assert submit(conn, mention(conn, "b"), version)[0].recorded_at == AT


def test_sample_two_forward_step_does_not_advance_assignment(db):
    _, conn, version = db
    samples(conn, AT, shifted(200))
    assert submit(conn, mention(conn), version)[0].recorded_at == AT


def test_restart_rechecks_and_recovers_without_acknowledgment(db):
    path, conn, version = db
    original_request = mention(conn)
    original = submit(conn, original_request, version)
    request = mention(conn, "b")
    conn.close()
    with closing(storage.init_db(path, clock=lambda: shifted(-121), threshold=THRESHOLD)) as restarted:
        before = tuple(restarted.iterdump())
        for _ in range(2):  # A lost refusal has no effect on the next attempt.
            with pytest.raises(writer.ClockSkewError):
                submit(restarted, request, version)
            assert tuple(restarted.iterdump()) == before
        # An already committed retry neither samples the clock nor clears a latch.
        samples(restarted)
        assert submit(restarted, original_request, version) == original
        samples(restarted, shifted(-120), shifted(-120))
        assert submit(restarted, request, version)[0].recorded_at == AT


def test_injected_threshold_and_first_wrong_clock_limit(db):
    _, conn, version = db
    conn.threshold = timedelta(seconds=3)
    samples(conn, shifted(100000), shifted(100000))
    assert submit(conn, mention(conn), version)[0].recorded_at == shifted(100000)
    samples(conn, AT)
    with pytest.raises(writer.ClockSkewError, match="threshold: 3 s"):
        submit(conn, mention(conn, "b"), version)


def test_preparation_does_not_assign_positions_and_retry_never_remints(db, monkeypatch):
    _, conn, version = db
    request = mention(conn)
    other = mention(conn, "b")
    assert not hasattr(request[0], "recorded_at")
    preceding = submit(conn, other, version)
    result = submit(conn, request, version)
    assert result[0].prev_event_hash == preceding[0].event_hash
    assert writer.semantic_contents(*result) == writer.semantic_contents(*request)
    submit(conn, mention(conn, "c"), version)
    before = tuple(conn.iterdump())
    def forbidden(*args, **kwargs):
        pytest.fail("committed retry must not remint, reduce or resample")
    monkeypatch.setattr(writer, "new_event_id", forbidden)
    monkeypatch.setattr(reducer if version == "1" else committed, "reduce", forbidden)
    conn.clock = forbidden
    assert submit(conn, request, version) == result
    assert tuple(conn.iterdump()) == before


@pytest.mark.parametrize("field,value", [
    ("source", hashing.canonical_json({"actor_id": "test", "config": {"vocabulary": "different"}})),
    ("event_id", "reminted"), ("schema_version", "other"),
    ("event_type", "observation_recorded"), ("origin_type", "user_stated"),
    ("source_class", "different"), ("entity_refs", '["other"]'),
    ("occurred_at", shifted(1)),
])
def test_all_semantic_envelope_changes_refuse(db, field, value):
    _, conn, version = db
    request = mention(conn)
    submit(conn, request, version)
    before = tuple(conn.iterdump())
    changed = (replace(request[0], **{field: value}), request[1])
    if field == "event_id":
        changed = (changed[0], replace(changed[1], event_id=value))
    with pytest.raises(integrity.IntegrityError, match="semantic contents"):
        submit(conn, changed, version)
    assert tuple(conn.iterdump()) == before


def test_payload_change_refuses_and_pair_override_is_not_an_import(db):
    _, conn, version = db
    request = mention(conn)
    committed = submit(conn, request, version)
    before = tuple(conn.iterdump())
    altered = (request[0], replace(request[1], ciphertext='{"different":true}'))
    with pytest.raises(integrity.IntegrityError, match="semantic contents"):
        submit(conn, altered, version)
    with pytest.raises(ValueError, match="recorded_at.*belong to the writer"):
        submit(conn, committed, version)
    with pytest.raises(TypeError, match="recorded_at"):
        ingestion.prepare_mention(conn, recorded_at=AT)
    assert tuple(conn.iterdump()) == before


def test_mention_survives_failed_observation_and_replay_never_samples(db, monkeypatch):
    _, conn, version = db
    m = submit(conn, mention(conn), version)
    request = ingestion.prepare_observation(conn, claims=[dict(
        mention_id="m-a", subject_id="s-a", belief_id="b-a", property_id="RAM",
        claim_candidate_id="c-a", value="64GB", verifiability="externally_checkable")],
        source={"actor_id": "test", "config": {}}, source_class="direct_observation",
        occurred_at=AT, event_id="observation", projector_version=version)
    samples(conn, shifted(-121))
    with pytest.raises(writer.ClockSkewError):
        submit(conn, request, version)
    assert storage.read_mention(conn, "m-a", version)["subject_id"] == "s-a"
    assert not storage.read_snapshot(conn, version).beliefs()
    samples(conn, AT, AT)
    result = submit(conn, request, version)
    assert result[0].prev_event_hash == m[0].event_hash
    def forbidden(*args):
        pytest.fail("replay must not sample the writer clock")
    conn.clock = forbidden
    monkeypatch.setattr(writer, "clock_now", forbidden)
    assert submit(conn, request, version) == result
    storage.rebuild_projection(conn, shifted(86400), version)
    replay = projection.project_snapshot(storage.read_all_events(conn), shifted(86400), version)
    assert replay.complete() == storage.read_snapshot(conn, version).complete()
    assert len(storage.read_all_events(conn)) == 2


@pytest.mark.parametrize("surface", ["cli", "seed"])
def test_structured_refusal_surfaces_full_fields_on_stderr(tmp_path, monkeypatch, capsys, surface):
    # CLI currently has only read commands. Exercise its refusal handler without
    # inventing a CLI write operation; the fixture ingester uses ordinary submit.
    from nyx import cli
    from scripts import seed_store
    error = writer.ClockSkewError("tip_ahead_of_clock", ("tip-id", "hash", AT), shifted(-121), THRESHOLD)
    def fail(*args, **kwargs):
        raise error
    path = tmp_path / "store.db"
    storage.init_db(path, create=True, clock=lambda: AT, threshold=THRESHOLD).close()
    if surface == "cli":
        monkeypatch.setattr(cli, "_run", fail)
        code = cli.main(["status", "--db", str(path)])
    else:
        monkeypatch.setattr(seed_store, "seed_store", fail)
        code = seed_store.main(["--db", str(path)])
    out = capsys.readouterr()
    assert code != 0 and not out.out
    for field, value in error.details().items():
        assert f"{field}: {value}" in out.err


def test_failure_before_append_and_during_publication_preserves_retry(db, monkeypatch):
    _, conn, version = db
    request = mention(conn)
    samples(conn, AT, shifted(-121))
    with pytest.raises(writer.ClockSkewError):
        submit(conn, request, version)
    assert storage.read_all_events(conn) == []
    samples(conn, AT, AT)
    original = storage._publish_delta
    def fail(*args):
        original(*args)
        raise RuntimeError("publication failure")
    monkeypatch.setattr(storage, "_publish_delta", fail)
    with pytest.raises(RuntimeError, match="publication failure"):
        submit(conn, request, version)
    committed = storage._recorded_pair(conn, request[0].event_id)
    assert committed is not None
    assert storage.read_projection_status(conn, version)["stale"]
    monkeypatch.setattr(storage, "_publish_delta", original)
    samples(conn)  # Lost acknowledgment/recovery does not assign another time.
    assert submit(conn, request, version) == committed
    assert len(storage.read_all_events(conn)) == 1
    assert not storage.read_projection_status(conn, version)["stale"]


def test_reader_is_independent_and_second_writer_refuses_before_writes(db, monkeypatch):
    path, conn, version = db
    submit(conn, mention(conn), version)
    before = tuple(conn.iterdump())
    lockfile = writer.lock_path(path)
    lock_before = lockfile.stat()
    with pytest.raises(writer.WriterBusyError):
        storage.init_db(path, clock=lambda: AT, threshold=THRESHOLD)
    def forbidden(*args):
        pytest.fail("read-only opener must not acquire or create a lockfile")
    monkeypatch.setattr(writer, "acquire", forbidden)
    with closing(storage.open_readonly(path)) as reader:
        assert len(storage.read_all_events(reader)) == 1
    assert lockfile.stat().st_size == lock_before.st_size
    assert lockfile.stat().st_mtime_ns == lock_before.st_mtime_ns
    assert tuple(conn.iterdump()) == before


def test_readonly_does_not_create_missing_lockfile(tmp_path, monkeypatch):
    path = tmp_path / "store.db"
    storage.init_db(path, create=True, clock=lambda: AT, threshold=THRESHOLD).close()
    lockfile = writer.lock_path(path)
    lockfile.unlink()  # No owner; model an existing store without a lockfile.
    def forbidden(*args):
        pytest.fail("read-only opener must not acquire or create a lockfile")
    monkeypatch.setattr(writer, "acquire", forbidden)
    with closing(storage.open_readonly(path)) as conn:
        assert storage.read_all_events(conn) == []
    assert not lockfile.exists()


def test_killed_subprocess_releases_lock_for_new_writer(tmp_path):
    path = tmp_path / "store.db"
    script = '''
import sys, os
from datetime import timedelta
from nyx import storage
conn = storage.init_db(sys.argv[1], create=True,
    clock=lambda: "2026-07-13T12:00:00Z", threshold=timedelta(seconds=120))
print(os.getpid(), flush=True)
sys.stdin.read()
'''
    # Windows venv python.exe is a redirector: killing it can leave its child
    # alive. Launch the actual interpreter and assert it is the lock owner.
    environment = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    proc = subprocess.Popen([sys._base_executable, "-c", script, str(path)], env=environment,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    ready = Queue()
    Thread(target=lambda: ready.put(proc.stdout.readline()), daemon=True).start()
    try:
        assert int(ready.get(timeout=15).strip()) == proc.pid
        with pytest.raises(writer.WriterBusyError):
            storage.init_db(path, clock=lambda: AT, threshold=THRESHOLD)
        with closing(storage.open_readonly(path)) as reader:
            assert storage.read_all_events(reader) == []
        proc.kill()
        proc.wait(timeout=15)
        assert proc.returncode != 0
        with closing(storage.init_db(path, clock=lambda: AT, threshold=THRESHOLD)) as conn:
            assert submit(conn, mention(conn), "2")[0].recorded_at == AT
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.communicate(timeout=15)
