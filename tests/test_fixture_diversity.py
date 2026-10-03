"""Large values and SQLite journal modes preserve admitted content (Queue 3 B).

ADRs 0011/0012: supported connections and whole-view equality; ADR 0025:
complete candidate/dependency content; ADR 0033: legacy string value domain.
"""

from contextlib import closing
from pathlib import Path
import runpy
import sqlite3

import pytest

from nyx import ingestion, projection, storage, writer


AT = "2026-07-13T12:00:00Z"
SOURCE = {"actor_id": "fixture-diversity", "config": {}}
VERIFY = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/verify_store.py"))["verify_store"]


def populate(path, version, value, mode="wal"):
    with closing(storage.init_db(path, create=True, clock=lambda: AT)) as conn:
        assert conn.execute(f"PRAGMA journal_mode={mode}").fetchone() == (mode,)
        if version != "0":
            mention = ingestion.prepare_mention(
                conn, mention_id="m", subject_id="s", text="artifact", source=SOURCE,
                source_class="direct_observation", occurred_at=AT,
                origin_type="observed", event_id="mention")
            ingestion.submit(conn, mention, AT, version)
        payload = {"belief_id": "b", "value": value, "verifiability": "externally_checkable"}
        if version != "0":
            payload = {"claims": [{**payload, "mention_id": "m", "subject_id": "s",
                                   "property_id": "P", "claim_candidate_id": "c"}]}
        request = writer.prepare_event(
            event_type="observation_recorded", origin_type="observed", source=SOURCE,
            source_class="direct_observation", occurred_at=AT, event_id="observation",
            payload=payload)
        pair = ingestion.submit(conn, request, AT, version)
        assert ingestion.submit(conn, request, AT, version) == pair
        live = storage.read_belief(conn, "b", version)
        replay = projection.project(storage.read_all_events(conn), AT, version)["b"]
        assert live == (replay if version == "0" else {**replay, "stale": False})
        observed = live["current_value"] if version == "0" else live["claim_candidates"][0]["value"]
        assert observed == value
        return live


@pytest.mark.parametrize("version", ["0", "1", "2"])
@pytest.mark.parametrize("size", [1, 262144])
def test_large_strings_survive_append_retry_read_replay_and_verifier(tmp_path, version, size):
    path = tmp_path / "large.sqlite"
    expected = populate(path, version, "\u96ea" * size)
    with closing(storage.open_readonly(path)) as conn:
        assert storage.read_belief(conn, "b", version) == expected
    report = VERIFY(path, version)
    assert report["ok"], report["failures"]


@pytest.mark.parametrize("version", ["1", "2"])
def test_large_compound_values_preserve_exact_content(tmp_path, version):
    value = {"integer": 2**256, "items": list(range(4096)), "text": "\u96ea" * 4096}
    path = tmp_path / "compound.sqlite"
    populate(path, version, value)
    report = VERIFY(path, version)
    assert report["ok"], report["failures"]


@pytest.mark.parametrize("version", ["0", "1", "2"])
@pytest.mark.parametrize("mode", ["wal", "delete"])
def test_journal_modes_preserve_publication_and_readonly_audit(tmp_path, version, mode):
    path = tmp_path / "journal.sqlite"
    expected = populate(path, version, "journal-mode-value", mode)
    with closing(sqlite3.connect(path)) as conn:
        before = tuple(conn.iterdump())
        assert conn.execute("PRAGMA journal_mode").fetchone() == (mode,)
    with closing(storage.open_readonly(path)) as conn:
        assert storage.read_belief(conn, "b", version) == expected
    report = VERIFY(path, version)
    assert report["ok"], report["failures"]
    # Supported existing-store writer reopen must neither repair nor switch mode.
    with closing(storage.init_db(path)) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone() == (mode,)
        assert tuple(conn.iterdump()) == before
        assert storage.read_belief(conn, "b", version) == expected
