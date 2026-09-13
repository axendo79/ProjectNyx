"""The inspection CLI wraps shipped reads without publishing or repairing."""

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tomllib

import pytest

from nyx import cli, events, integrity, projection, storage
from test_event_integrity import entries
from test_reducer_boundary import T0, T2, event, mention


@pytest.fixture(params=["0", "1", "2"])
def store(tmp_path, request):
    version = request.param
    path = tmp_path / "nyx.db"
    with closing(storage.init_db(path, create=True)) as conn:
        log = entries(version)
        for pair in log[:2]:
            storage.safe_append_event(conn, *pair, version)
            storage.materialize_pending(conn, T2, version)
        yield path, conn, version, log


def invoke(capsys, store, command, *arguments):
    path, _, version, _ = store
    args = [command, "--db", str(path), "--json", *arguments]
    if command not in ("status", "events"):
        args.extend(["--projector", version])
    code = cli.main(args)
    return code, json.loads(capsys.readouterr().out)


@pytest.mark.parametrize("command", ["belief", "replay", "verify", "status", "events"])
def test_commands_read_fixture_without_mutation(store, capsys, command):
    _, conn, version, _ = store
    before = tuple(conn.iterdump())
    args = ["b-a"] if command == "belief" else []
    if command == "replay":
        args += ["--as-of", T2]
    code, output = invoke(capsys, store, command, *args)
    assert code == 0
    if command == "belief":
        assert output["belief"] == storage.read_belief_status(conn, "b-a", version)["belief"]
        assert output["stale"] is False
    elif command == "replay":
        assert output["view"]["beliefs"] == storage.evaluate_whole_view(conn, T2, version)
        assert output["materialized_status"]["stale"] is False
    elif command == "verify":
        assert output["result"] == "PASS" and output["event_count"] == 2
    elif command == "status":
        assert output["schema_version"] == 4 and output["event_count"] == 2
        assert output["freshness"][version]["stale"] is False
    else:
        assert output["returned_count"] == 2
        assert all("payload" not in row and "ciphertext" not in row for row in output["events"])
        assert "64GB" not in json.dumps(output)
    assert tuple(conn.iterdump()) == before


@pytest.mark.parametrize("command,identifier", [("subject", "s-a"), ("mention", "m-a")])
def test_identity_reads_and_unsupported_version(store, capsys, command, identifier):
    code, result = invoke(capsys, store, command, identifier)
    if store[2] == "0":
        assert code == 2 and result["result"] == "unimplemented"
        assert "projector '0'" in result["reason"]
    else:
        assert code == 0 and result["record"]["subject_id"] == "s-a"
        assert result["stale"] is False
        if command == "subject":
            assert set(result["beliefs"]) == {"b-a"}


def test_stale_belief_replay_and_status_disclose_unpublished_state(store, capsys):
    _, conn, version, log = store
    storage.safe_append_event(conn, *log[2], version)
    before = tuple(conn.iterdump())
    _, materialized = invoke(capsys, store, "belief", "b-a")
    assert materialized["stale"] is True
    assert materialized["derived_progress"]["log_position"] == 2
    _, replay = invoke(capsys, store, "replay", "--as-of", T2)
    assert replay["materialized_status"]["stale"] is True
    assert replay["view"]["beliefs"] == storage.evaluate_whole_view(conn, T2, version)
    _, status = invoke(capsys, store, "status")
    assert status["freshness"][version]["stale"] is True
    assert tuple(conn.iterdump()) == before


@pytest.mark.parametrize("store", ["1", "2"], indirect=True)
def test_unpublished_mention_is_not_bare_absence(store, capsys):
    _, conn, version, log = store
    pair = event(events.ENTITY_MENTION_RECORDED, mention("s-new", "m-new"), 3, log[1])
    storage.safe_append_event(conn, *pair, version)
    _, result = invoke(capsys, store, "mention", "m-new")
    assert result["record"] is None and result["stale"] is True
    assert result["freshness_scope"] == "log"
    assert result["append_freshness"]["event_id"] == pair[0].event_id


def test_historical_and_property_filters(store, capsys):
    _, result = invoke(capsys, store, "belief", "b-a", "--as-of", T0)
    assert result["belief"] is None and result["read_mode"] == "replay"
    assert "belief" not in result["materialized_status"]
    assert "64GB" not in json.dumps(result)
    if store[2] != "0":
        _, result = invoke(capsys, store, "subject", "s-a", "--property", "other")
        assert result["beliefs"] == {} and result["record"] is not None
        _, result = invoke(capsys, store, "subject", "s-a", "--as-of", T0)
        assert result["record"] is None and result["beliefs"] == {}
        assert "record" not in result["materialized_status"]
        _, result = invoke(capsys, store, "subject", "s-a", "--property", "RAM", "--as-of", T2)
        assert set(result["beliefs"]) == {"b-a"}


def test_event_filter_is_recorded_time_inclusive(store, capsys):
    _, result = invoke(capsys, store, "events", "--since", "2026-07-12T19:00:02-05:00", "--limit", "1")
    assert [row["event_id"] for row in result["events"]] == ["e-2"]
    _, result = invoke(capsys, store, "events", "--limit", "0")
    assert result["events"] == []


@pytest.mark.parametrize("command,args", [("verify", []), ("replay", ["--as-of", T0]),
    ("events", ["--limit", "0"]), ("belief", ["b-a", "--as-of", T0])])
def test_corruption_propagates_specific_integrity_error_before_filtering(store, capsys, command, args):
    _, conn, _, _ = store
    with conn:
        conn.execute("UPDATE payloads SET ciphertext='{}' WHERE event_id='e-2'")
    before = tuple(conn.iterdump())
    with pytest.raises(integrity.IntegrityError, match="payload hash mismatch"):
        invoke(capsys, store, command, *args)
    assert capsys.readouterr().out == ""
    assert tuple(conn.iterdump()) == before


def test_plain_output_and_unimplemented_exception(store, capsys, monkeypatch):
    path, _, version, _ = store
    assert cli.main(["belief", "b-a", "--db", str(path), "--projector", version]) == 0
    assert "stale: false" in capsys.readouterr().out

    def unavailable(*args, **kwargs):
        raise NotImplementedError("requested read is unimplemented")

    monkeypatch.setattr(storage, "read_belief_status", unavailable)
    assert cli.main(["belief", "b-a", "--db", str(path)]) == 2
    output = capsys.readouterr().out
    assert "unimplemented" in output and "Traceback" not in output


def test_accidental_mutation_fails_loudly(store, monkeypatch):
    path, conn, _, _ = store
    before = tuple(conn.iterdump())

    def bad_read(reader):
        reader.execute("DELETE FROM payloads")

    monkeypatch.setattr(storage, "read_store_metadata", bad_read)
    with pytest.raises(sqlite3.DatabaseError):
        cli.main(["status", "--db", str(path)])
    assert tuple(conn.iterdump()) == before


@pytest.mark.parametrize("command,tail", [("belief", ["b-a"]), ("subject", ["s-a"]),
    ("mention", ["m-a"]), ("replay", []), ("verify", []), ("status", []), ("events", [])])
def test_database_path_is_required(command, tail, capsys):
    with pytest.raises(SystemExit) as error:
        cli.main([command, *tail])
    assert error.value.code == 2
    assert "--db" in capsys.readouterr().err


def test_console_entry_and_module_invocation(store):
    path, _, _, _ = store
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as file:
        assert tomllib.load(file)["project"]["scripts"]["nyx"] == "nyx.cli:main"
    result = subprocess.run([sys.executable, "-B", "-m", "nyx.cli", "status", "--db", str(path), "--json"],
                            capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["event_count"] == 2


@pytest.mark.parametrize("store", ["0"], indirect=True)
def test_legacy_unknown_freshness_in_cli(store, capsys):
    _, conn, _, _ = store
    with conn:
        conn.execute("DELETE FROM derived_progress WHERE projector_version='0'")
    _, result = invoke(capsys, store, "belief", "b-a")
    assert result["stale"] is None and result["freshness_state"] == "unknown"
    _, result = invoke(capsys, store, "status")
    assert result["freshness"]["0"]["freshness_state"] == "unknown"


def test_verify_process_exit_preserves_integrity_failure(store):
    path, conn, version, _ = store
    with conn:
        conn.execute("DELETE FROM payloads WHERE event_id='e-1'")
    result = subprocess.run([sys.executable, "-B", "-m", "nyx.cli", "verify", "--db", str(path),
                             "--projector", version], capture_output=True, text=True)
    assert result.returncode != 0
    assert "IntegrityError: missing payload row for 'e-1'" in result.stderr
    assert result.stdout == ""
