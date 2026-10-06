"""B13: retained remote dependencies refuse, ADR 0035 §2 / 0015 §5."""
from contextlib import closing
import json
import pytest
from nyx import forward, merkle, storage
from queue13_helpers import contents, payload
from test_forward_correction import append
from test_reducer_boundary import T2, claim, event, mention


@pytest.mark.parametrize("kind", ["correction_appended", "candidate_replaced", "candidate_expired"])
@pytest.mark.parametrize("field", ["predecessors", "restrictions"])
def test_b13_retained_other_belief_dependency_refuses(tmp_path, monkeypatch, kind, field):
    log = [event("entity_mention_recorded", mention())]
    log.append(event("observation_recorded", {"claims": [claim("target"), claim("remote", "b-q", prop="Q")]},
                     2, log[-1]))
    log.append(event("candidate_expired", payload("candidate_expired", ["remote"], bid="b-q"), 3, log[-1]))
    with closing(storage.init_db(tmp_path / "remote.db", create=True)) as conn:
        for pair in log:
            append(conn, pair)
        snapshot = storage.read_snapshot(conn, "3")
        remote = snapshot.record("claim_candidates", "remote")
        assert remote["belief_id"] != "b-a" and remote["live_status"] == "expired"
        # Supplied recorded dependency fixture: producer/demotion semantics remain
        # undecided; the closed check must inspect even retained foreign candidates.
        remote[field] = ["target"]
        roots = dict(snapshot.roots)
        roots["claim_candidates"] = merkle.put(roots["claim_candidates"], "remote", remote)
        supplied = forward.Snapshot(roots, snapshot.log_position, snapshot.event_id)
        pair = event(kind, payload(kind, ["target"]), 4, log[-1])
        with pytest.raises(NotImplementedError, match="ADR 0015 section 5"):
            forward.Projector().reduce(supplied, pair[0], json.loads(pair[1].ciphertext), T2)
        monkeypatch.setattr(storage, "_read_snapshot", lambda *args: supplied)
        before = contents(conn)
        with pytest.raises(NotImplementedError, match="ADR 0015 section 5"):
            storage.safe_append_event(conn, *pair, "3")
        assert contents(conn) == before
