"""The response means artifact A at revision R stated X, with no winner."""
from contextlib import closing
import copy
import json

import pytest

from nyx import integrity, storage
from test_report_admission import AS_OF, deployment
from test_report_importer import OLDER, PATH, REVISION
from test_report_policy import REPOSITORY, policy_files


@pytest.mark.parametrize('projector_version', ['1', '2'])
@pytest.mark.parametrize('reverse', [False, True])
def test_report_scope_shape_contradictions_and_input_order(tmp_path, projector_version, reverse):
    from nyx import report_importer as importer, reports
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        revisions = [OLDER, REVISION]
        if reverse: revisions.reverse()
        artifacts = [a for r in revisions for a in importer.read_artifacts(d.policy, REPOSITORY, r, [PATH])]
        importer.prepare_artifacts(conn, artifacts, 'two', projector_version=projector_version)
        completed = importer.resume_import(conn, 'two', projector_version=projector_version)
        candidates = [storage.read_claim_candidate(conn, c, projector_version) for c in completed['claim_candidate_ids']]
        ids = [c['claim_candidate_id'] for c in candidates if c['property_id'] == 'adr.status.literal'][::-1]
        response = reports.read_report_details(conn, ids, projector_version=projector_version)
        assert set(response) == {'projector_version', 'publication', 'reports'}
        assert response['projector_version'] == projector_version
        assert response['publication'] == {'log_position': 3, 'stale': False}
        assert [r['claim_candidate_id'] for r in response['reports']] == ids
        assert len({r['belief_id'] for r in response['reports']}) == 1
        assert len({r['value'] for r in response['reports']}) == 2
        for report in response['reports']:
            assert set(report) == {'claim_candidate_id', 'belief_id', 'mention_id', 'subject_id',
                'property_id', 'artifact', 'report_scope', 'value', 'verification_state',
                'verifiability', 'projected_as_of', 'provenance'}
            assert report['report_scope'] == {'meaning': 'artifact_at_revision_stated',
                'vocabulary': report['provenance']['source']['config']['report_vocabulary'], 'artifact_scope': 'adr-path'}
            assert report['verification_state'] == 'verified'
            assert report['artifact']['repository'] == REPOSITORY
            assert report['artifact']['path'] == PATH
            assert report['artifact']['revision'] in revisions
            assert set(report['provenance']) == {'observation_event_id', 'occurred_at', 'recorded_at',
                'event_hash', 'payload_hash', 'source', 'source_class', 'origin_type', 'location'}
            blob = next(a for a in artifacts if a.revision == report['artifact']['revision'])
            span = report['provenance']['location']
            assert blob.data[span['start_byte']:span['end_byte']].decode('utf-8') == report['value']
            assert report['projected_as_of'] == storage.read_belief(conn, report['belief_id'], projector_version)['projected_as_of']
        assert not {'winner', 'head', 'current_value', 'as_of'} & set(response)


def test_agreement_staleness_projection_times_and_retirement(tmp_path):
    from nyx import report_importer as importer, reports
    config = policy_files(tmp_path)
    d = deployment(tmp_path, config)
    with closing(d.open_writer(create=True)) as conn:
        importer.prepare_import(conn, REPOSITORY, OLDER, [PATH], 'old', projector_version='2')
        old = importer.resume_import(conn, 'old', projector_version='2')
        another = 'decisions/0032-explicit-stage-two-projector-selection.md'
        importer.prepare_import(conn, REPOSITORY, REVISION, [another], 'another', projector_version='2')
        newer = importer.resume_import(conn, 'another', projector_version='2')
        ids = [old['claim_candidate_ids'][0], newer['claim_candidate_ids'][0]]
        response = reports.read_report_details(conn, ids, projector_version='2')
        assert len({r['projected_as_of'] for r in response['reports']}) == 2
        importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'new', projector_version='2')
        saved = importer.read_manifest(importer.manifest_path(conn, 'new'), projector_version='2')
        pair = importer.requests(saved)[0]
        storage.append_submission(conn, pair, '2')
        assert reports.read_report_details(conn, ids, projector_version='2')['publication']['stale'] is True
        importer.resume_import(conn, 'new', projector_version='2')
        # Two Implementation: None candidates remain separate reports.
        snapshot = storage.read_snapshot(conn, '2')
        same = [c['claim_candidate_id'] for c in snapshot.records('claim_candidates').values()
                if c['property_id'] == 'adr.implementation.literal' and c['source']['config']['report_artifact']['path'] == PATH]
        agreed = reports.read_report_details(conn, same, projector_version='2')
        assert len(agreed['reports']) == 2
        assert len({r['value'] for r in agreed['reports']}) == 1
        for file in config.rglob('*.json'): file.unlink()
        assert reports.read_report_details(conn, same, projector_version='2') == agreed


@pytest.mark.parametrize('bad', ['source', 'scope', 'locations', 'support', 'claim'])
@pytest.mark.parametrize('projector_version', ['1', '2'])
def test_inconsistent_provenance_refuses(tmp_path, monkeypatch, bad, projector_version):
    from nyx import report_importer as importer, reports
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'one', projector_version=projector_version)
        complete = importer.resume_import(conn, 'one', projector_version=projector_version)
        original = storage._read_record
        def corrupt(conn, kind, name, projector_version):
            value = original(conn, kind, name, projector_version)
            if kind == 'claim_candidates' and value is not None:
                value = copy.deepcopy(value)
                if bad == 'source': value['source']['actor_id'] = 'other'
                if bad == 'scope': value['subject_id'] = 'other'
                if bad == 'locations': value['source']['config']['report_locations'] = {}
                if bad == 'support': value['supporting_events'] = []
                if bad == 'claim': value['value'] = 'inconsistent'
            return value
        monkeypatch.setattr(storage, '_read_record', corrupt)
        with pytest.raises(integrity.IntegrityError):
            reports.read_report_details(conn, complete['claim_candidate_ids'], projector_version=projector_version)


def test_reader_requires_distinct_ordered_names_and_explicit_selection(tmp_path):
    from nyx import reports
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        with pytest.raises(TypeError): reports.read_report_details(conn, ['x'])
        with pytest.raises(ValueError): reports.read_report_details(conn, ['x'], projector_version='0')
        for names in ([], 'x', ['x', 'x']):
            with pytest.raises(ValueError): reports.read_report_details(conn, names, projector_version='2')
        with pytest.raises(KeyError): reports.read_report_details(conn, ['absent'], projector_version='2')


def test_ordered_sequence_input_and_named_slot_integrity(tmp_path, monkeypatch):
    from collections import UserList
    from nyx import report_importer as importer, reports
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        artifacts = [a for r in (OLDER, REVISION) for a in importer.read_artifacts(d.policy, REPOSITORY, r, [PATH])]
        importer.prepare_artifacts(conn, artifacts, 'two', projector_version='2')
        complete = importer.resume_import(conn, 'two', projector_version='2')
        ids = complete['claim_candidate_ids']
        assert reports.read_report_details(conn, UserList([ids[0]]), projector_version='2')['reports'][0]['claim_candidate_id'] == ids[0]
        original = storage.read_claim_candidate
        monkeypatch.setattr(storage, 'read_claim_candidate', lambda conn, name, projector_version: original(conn, ids[3], projector_version))
        with pytest.raises(integrity.IntegrityError): reports.read_report_details(conn, [ids[0]], projector_version='2')


@pytest.mark.parametrize('projector_version', ['1', '2'])
@pytest.mark.parametrize('kind,key_field', [
    ('mentions', 'mention_id'), ('entity_links', 'mention_id'),
    ('entities', 'subject_id'), ('beliefs', 'belief_id'),
    ('claim_candidates', 'claim_candidate_id'),
])
def test_stored_record_identity_must_match_lookup_key(tmp_path, projector_version, kind, key_field):
    from nyx import hashing, merkle, report_importer as importer, reports
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'one', projector_version=projector_version)
        completed = importer.resume_import(conn, 'one', projector_version=projector_version)
        candidate_id = completed['claim_candidate_ids'][0]
        candidate = storage.read_claim_candidate(conn, candidate_id, projector_version)
        identifier = candidate[key_field]
        original = storage._read_record(conn, kind, identifier, projector_version)
        log = storage.read_all_events(conn)
        if projector_version == '1':
            record = copy.deepcopy(original)
            record[key_field] = 'different-embedded-id'
            table, column = storage._RECORD_TABLES[kind]
            with conn:
                conn.execute(f'UPDATE {table} SET content=? WHERE projector_version=? AND {column}=?',
                             (hashing.canonical_json(record), projector_version, identifier))
        else:
            snapshot = storage.read_snapshot(conn, projector_version)
            record = snapshot.header(identifier) if kind == 'beliefs' else snapshot.record(kind, identifier)
            record[key_field] = 'different-embedded-id'
            written = {}
            root = merkle.put(snapshot.roots[kind], identifier, record, written)
            # Preserve valid native Merkle hashes so the adapter must reject
            # the identity mismatch rather than relying on a hash failure.
            with conn:
                conn.executemany("INSERT INTO committed_nodes VALUES ('2',?,?)", written.items())
                conn.execute("UPDATE committed_roots SET root_hash=? WHERE projector_version='2' AND kind=?",
                             (merkle.digest(root), kind))
                if kind == 'beliefs':
                    conn.execute("UPDATE projected_beliefs SET content=? WHERE projector_version='2' AND belief_id=?",
                                 (hashing.canonical_json(record), identifier))
        stored = storage._read_record(conn, kind, identifier, projector_version)
        assert stored == {**original, key_field: 'different-embedded-id'}
        assert storage.read_all_events(conn) == log
        with pytest.raises(integrity.IntegrityError):
            reports.read_report_details(conn, [candidate_id], projector_version=projector_version)
