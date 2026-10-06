"""A-G10: candidate APIs use live, not current, ADR 0034 §3/R4."""
from contextlib import closing
import inspect
import json
from nyx import cli, forward, projection, storage
from test_forward_correction import append
from test_forward_reads import transition_log
from test_reducer_boundary import T2, decoded


def candidate_labels(value):
    if isinstance(value, dict):
        if "claim_candidate_id" in value and "verification_basis" in value:
            assert not any("current" in key.split("_") for key in value)
            assert value["live_status"] in {"live", "corrected", "replaced", "expired"}
            assert value["verification_state"] != "current"
            assert value["verification_basis"]["kind"] != "current"
        # Set labels, distinct from opaque record IDs and user claim values.
        if "live" in value and "retained" in value:
            assert "current" not in value
        for member in value.values():
            candidate_labels(member)
    elif isinstance(value, list):
        for member in value:
            candidate_labels(member)


def test_ag10_all_candidate_read_shapes_and_cli_labels(tmp_path, capsys):
    path = tmp_path / "names.db"
    log = transition_log()
    with closing(storage.init_db(path, create=True)) as conn:
        for position, pair in enumerate(log, 1):
            append(conn, pair)
            snapshot = storage.read_snapshot(conn, "3")
            replay = projection.project_snapshot(decoded(log[:position]), T2, "3")
            for selected in (snapshot, replay):
                for value in (selected.complete(), selected.records("claim_candidates"), selected.beliefs(),
                              selected.belief("b-a"), selected.current_belief("s-a", "RAM"),
                              selected.candidate_sets("b-a")):
                    candidate_labels(value)
                for cid in selected.records("claim_candidates"):
                    candidate_labels(selected.record("claim_candidates", cid))
                    candidate_labels(selected.inclusion_proof("b-a", "claim_candidates", cid))
            for value in (storage.read_belief(conn, "b-a", "3"), storage.read_belief_status(conn, "b-a", "3"),
                          storage.evaluate_whole_view(conn, T2, "3"), storage.read_candidate_sets(conn, "b-a", "3")):
                candidate_labels(value)
            for cid in snapshot.records("claim_candidates"):
                candidate_labels(storage.read_claim_candidate(conn, cid, "3"))
                candidate_labels(storage.read_claim_candidate_details(conn, cid, "3"))
                assert storage.read_claim_candidate_value(conn, cid, "3") == snapshot.record("claim_candidates", cid)["value"]
            if position >= 2:
                assert snapshot.belief("b-a")["lifecycle_status"] == "current"  # Explicit exemption.
            for args in [["belief", "b-a"], ["belief", "b-a", "--as-of", T2],
                         ["subject", "s-a"], ["replay", "--as-of", T2]]:
                assert cli.main(args + ["--db", str(path), "--projector", "3", "--json"]) == 0
                candidate_labels(json.loads(capsys.readouterr().out))
    for surface in (storage, forward.Snapshot, forward.Projector):
        for name, member in inspect.getmembers(surface, callable):
            if "candidate" in name:
                assert "current" not in name.split("_"), name


def test_ag10_current_is_allowed_as_opaque_user_value():
    # A literal claim value is data; it cannot be banned by a naming guard.
    candidate_labels({"claim_candidate_id": "literal", "value": "current", "live_status": "live",
                      "verification_state": "verified", "verification_basis": {"kind": "direct_observation"}})
