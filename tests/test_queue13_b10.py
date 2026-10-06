"""B10: real death after first relation insert / publication, ADR 0034 §§8–9."""
from contextlib import closing
from dataclasses import asdict
import json
import os
from pathlib import Path
from queue import Queue
import subprocess
import sys
from threading import Thread
import pytest
from nyx import ingestion, storage
from queue13_helpers import assert_prefix, payload, request
from test_forward_correction import append
from test_reducer_boundary import T2, claim, event, mention


CHILD = '''
import json, os, sys
from nyx import storage, writer
saved=json.loads(open(sys.argv[2], encoding="utf-8").read())
request=writer.EventRequest(**saved[0]), writer.PayloadRequest(**saved[1])
conn=storage.init_db(sys.argv[1], clock=lambda: "2026-07-14T00:00:00Z")
storage.append_submission(conn, request, "3")
count=0
def pause():
    print(json.dumps({"pid":os.getpid(), "transaction":conn.in_transaction}), flush=True)
    sys.stdin.read()
    raise AssertionError("child resumed")
def trace(sql):
    global count
    if sql.upper().startswith("INSERT INTO CANDIDATE_RELATIONS"):
        count += 1
        if count == 2: pause()  # First insert executed, second has not.
if sys.argv[3] == "first-relation": conn.set_trace_callback(trace)
storage.materialize_pending(conn, "2026-07-14T00:00:00Z", "3")
if sys.argv[3] == "after-publication": pause()
raise AssertionError("pause not reached")
'''


@pytest.mark.parametrize("point", ["first-relation", "after-publication"])
def test_b10_three_target_batch_survives_process_death(tmp_path, point):
    path = tmp_path / "batch.db"
    log = [event("entity_mention_recorded", mention())]
    log.append(event("observation_recorded", {"claims": [claim(cid) for cid in ["A", "B", "C"]]}, 2, log[-1]))
    log.append(event("candidate_replaced", payload("candidate_replaced", ["A"], "D"), 3, log[-1]))
    recorded = request("correction_appended", ["B", "C", "D"], "E")
    with closing(storage.init_db(path, create=True)) as conn:
        for pair in log:
            append(conn, pair)
        old = storage.read_snapshot(conn, "3").complete()
    manifest = tmp_path / "request.json"
    manifest.write_text(json.dumps([asdict(p) for p in recorded]), encoding="utf-8")
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                   "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    proc = subprocess.Popen([sys._base_executable, "-B", "-c", CHILD, str(path), str(manifest), point],
                            env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    ready = Queue()
    thread = Thread(target=lambda: ready.put(proc.stdout.readline()), daemon=True)
    thread.start()
    try:
        line = ready.get(timeout=15)
        assert line, proc.communicate(timeout=15)
        message = json.loads(line)
        assert message == {"pid": proc.pid, "transaction": point == "first-relation"}
        with closing(storage.open_readonly(path)) as reader:
            assert len(storage.read_all_events(reader)) == 4
            snapshot = storage.read_snapshot(reader, "3")
            if point == "first-relation":
                assert snapshot.complete() == old
                assert len(snapshot.relations()) == 1
            else:
                assert snapshot.log_position == 4
                assert len(snapshot.relations()) == 4
        proc.kill()
        proc.wait(timeout=15)
    finally:
        if proc.poll() is None:
            proc.kill()
        _, stderr = proc.communicate(timeout=15)
        thread.join(timeout=1)
    assert not stderr, stderr
    with closing(storage.init_db(path, clock=lambda: T2)) as conn:
        storage.materialize_pending(conn, T2, "3")
        committed = ingestion.submit(conn, recorded, T2, "3")
        assert ingestion.submit(conn, recorded, T2, "3") == committed
        assert len(storage.read_all_events(conn)) == 4
        assert_prefix(conn, path, log + [committed])
        assert conn.execute("SELECT count(*) FROM candidate_relations WHERE event_id=?", (committed[0].event_id,)).fetchone() == (3,)
