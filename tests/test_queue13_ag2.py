"""A-G2: replay consumes recorded evidence only, ADR 0034 §6/R13."""
from contextlib import closing
import os
import socket
import subprocess
import urllib.request
from nyx import adr_literals, forward, projection, report_importer, report_policy, storage
from queue13_helpers import payload
from test_forward_correction import append
from test_reducer_boundary import T2, claim, decoded, event, mention
from test_verify_store import verifier


def test_ag2_replay_rebuild_and_independent_audit_never_fetch_or_extract(tmp_path, monkeypatch):
    log = [event("entity_mention_recorded", mention())]
    log.append(event("observation_recorded", {"claims": [claim("ordinary"), claim("other")]}, 2, log[-1]))
    log.append(event("observation_recorded", {"claims": [claim("report")]}, 3, log[-1],
                     source={"actor_id": "synthetic-report", "config": {
                         "report_vocabulary": "recorded-v1", "extractor": "nyx.adr-literal/1"}}))
    for kind, target, fresh in [("candidate_replaced", "ordinary", "replacement"),
                                ("correction_appended", "replacement", "correction"),
                                ("candidate_expired", "correction", "unused")]:
        log.append(event(kind, payload(kind, [target], fresh), len(log) + 1, log[-1]))
    path = tmp_path / "offline.db"
    with closing(storage.init_db(path, create=True)) as conn:
        for pair in log:
            append(conn, pair)
        expected = storage.read_snapshot(conn, "3").complete()
        def forbidden(*args, **kwargs):
            raise AssertionError("replay/audit attempted external I/O, policy loading or extraction")
        with monkeypatch.context() as traps:
            for module, name in [(socket, "create_connection"), (socket, "getaddrinfo"),
                                 (socket.socket, "connect"), (socket.socket, "connect_ex"),
                                 (urllib.request, "urlopen"), (subprocess, "Popen"), (os, "system"),
                                 (report_policy, "git"), (report_importer, "git"),
                                 (report_policy, "load_policy"), (report_importer, "read_artifacts"),
                                 (report_importer, "prepare_artifacts"), (adr_literals, "extract_literals")]:
                traps.setattr(module, name, forbidden)
            assert projection.project_snapshot(decoded(log), T2, "3").complete() == expected
            forward.verify_lineage(decoded(log), T2)
            storage.rebuild_projection(conn, T2, "3")
            assert storage.read_snapshot(conn, "3").complete() == expected
            report = verifier["verify_store"](path, "3")
            assert report["ok"], report
