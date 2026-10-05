#!/usr/bin/env python3
"""Create and prove a projector-3 working copy; never write the source store.

ADR 0034 section 10 steps 1-3 only. No transition event is appended and this
tool does not designate an authoritative store. All output paths must be new.
"""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nyx import forward, projection, storage
from verify_store import verify_store


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def imports_of(store):
    # ADR 0031: retained import request manifests live beside the store.
    return store.with_name(store.name + '.imports')


def tree_hashes(root):
    if not root.exists():
        return {}
    return {path.relative_to(root).as_posix(): file_hash(path)
            for path in sorted(root.rglob('*')) if path.is_file()}


def report_bundle_record(bundle, log, tip, imports, repositories):
    """ADR 0031 BACKUP BUNDLE: a report store's backup is a restorable bundle.

    Restorability is proven, not inferred from file hashes: a trial
    report_backup.restore_bundle runs from a temporary copy of the bundle
    (restoring in place could leave SQLite side files that break its exact
    inventory). The restored store must hold this source's Layer A log and tip,
    and its import manifests must equal the source's.
    """
    from nyx import report_backup
    root = Path(bundle).resolve()
    if not isinstance(repositories, dict) or not repositories:
        raise ValueError('report bundle validation requires the public repository mapping')
    try:
        metadata = json.loads((root / 'bundle.json').read_bytes())
        version = metadata.get('projector_version')
        if version not in ('1', '2'):
            raise ValueError(f'unsupported bundle projector_version {version!r}')
        with tempfile.TemporaryDirectory() as scratch:
            copy = Path(scratch) / 'bundle'
            shutil.copytree(root, copy)
            trial = Path(scratch) / 'trial.db'
            report_backup.restore_bundle(copy, trial, repositories=repositories, projector_version=version)
            with closing(storage.open_readonly(trial)) as conn:
                restored_log = storage.read_all_events(conn)
                restored_tip = storage.last_event_hash(conn)
            restored_imports = tree_hashes(imports_of(trial))
            # restore_bundle retains its bundle.json beside the restored requests.
            restored_imports.pop('bundle.json', None)
    except (OSError, ValueError) as error:
        raise ValueError(f'report bundle is not restorable: {error}') from error
    if restored_tip != tip or restored_log != log or restored_imports != imports:
        raise ValueError('report bundle does not match the source store (tip, log or import manifests)')
    return dict(path=str(root), bundle_sha256=file_hash(root / 'bundle.json'),
                projector_version=version, software_revision=metadata['software_revision'],
                policy_revision=metadata['policy_revision'], tip_hash=tip)


def logical_image(source):
    # iterdump performs PRAGMAs denied by the source's read-only authorizer.
    # Dump an isolated backup instead, leaving that authorizer intact.
    with closing(sqlite3.connect(':memory:')) as image:
        source.backup(image)
        return tuple(image.iterdump())


def transition_store(source_path, working_path, projector_version, report_bundle=None,
                     repositories=None):
    if projector_version != '3':
        raise ValueError('store transition requires explicitly selected projector 3')
    source_path, working_path = Path(source_path).resolve(), Path(working_path).resolve()
    backup_path = working_path.with_name(working_path.name + '.source-backup.db')
    manifest_path = working_path.with_name(working_path.name + '.transition.json')
    outputs = (working_path, backup_path, manifest_path,
               imports_of(working_path), imports_of(backup_path))
    if source_path in outputs or imports_of(source_path) in outputs or len(set(outputs)) != 5:
        raise ValueError('source and new output paths must be distinct')
    if any(path.exists() for path in outputs):
        raise ValueError('all output paths must be new; an output already exists')
    source_digest = file_hash(source_path)
    source_imports = imports_of(source_path)
    imports = tree_hashes(source_imports)
    with closing(storage.open_readonly(source_path)) as source:
        source.execute('BEGIN')
        version, created_at = source.execute('SELECT version,created_at FROM schema_meta').fetchone()
        reference = logical_image(source)
        log = storage.read_all_events(source)
        has_reports = any('report_vocabulary' in json.loads(envelope.source).get('config', {})
                          for envelope, _ in log)
        # Saved import requests are report material even before any append.
        if (has_reports or imports) and report_bundle is None:
            raise ValueError('source holds report events or import requests; supply its ADR 0031 report bundle')
        bundle_record = (None if report_bundle is None else report_bundle_record(
            report_bundle, log, storage.last_event_hash(source), imports, repositories))
        at = log[-1][0].recorded_at if log else created_at
        # SQLite backup captures WAL-resident committed data too; no file copy
        # can silently omit it. Both outputs use this same pinned read snapshot.
        for path in (backup_path, working_path):
            with path.open('xb'):
                pass
            with closing(sqlite3.connect(path)) as destination:
                source.backup(destination)
    if source_imports.exists():
        for copy in (backup_path, working_path):
            shutil.copytree(source_imports, imports_of(copy))
            if tree_hashes(imports_of(copy)) != imports:
                raise ValueError('copied import manifests differ from the source')
    if version == 4:
        storage.migrate_working_copy(backup_path, working_path)
    with closing(storage.init_db(working_path)) as working:
        storage.require_projector_schema(working, projector_version)
        copied_log = storage.read_all_events(working)
        if copied_log != log:
            raise ValueError('copied log differs from the pinned source')
        for position in range(len(log) + 1):
            old = projection.project_snapshot(log[:position], at, '2')
            new = projection.project_snapshot(copied_log[:position], at, projector_version)
            forward.assert_semantically_equivalent(old, new)
            if old.log_position != position or new.log_position != position:
                raise ValueError('prefix proof omitted a recorded position')
        forward.verify_lineage(copied_log, at)
        storage.rebuild_projection(working, at, projector_version)
        working.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    audit = verify_store(working_path, projector_version)
    if not audit['ok']:
        raise ValueError('independent working-copy verification failed: ' + json.dumps(audit['failures']))
    with closing(storage.open_readonly(source_path)) as source:
        if (logical_image(source) != reference or file_hash(source_path) != source_digest
                or tree_hashes(source_imports) != imports):
            raise ValueError('source changed during transition proof')
    result = dict(format='nyx-store-transition/1', projector_version=projector_version,
        source=str(source_path), source_schema=version, source_sha256=source_digest,
        backup=str(backup_path), backup_sha256=file_hash(backup_path),
        working=str(working_path), working_sha256=file_hash(working_path),
        imports=imports, report_bundle=bundle_record, as_of=at, positions_verified=len(log), identities_unchanged=True,
        independent_verification=audit['checked'])
    with manifest_path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--working', required=True, type=Path)
    parser.add_argument('--projector-version', required=True, choices=['3'])
    parser.add_argument('--report-bundle', type=Path, default=None,
                        help='ADR 0031 backup bundle; required when the source holds report events or import requests')
    parser.add_argument('--repository', action='append', default=[], metavar='URL=PATH',
                        help='public repository mapping used to validate the report bundle (repeatable)')
    args = parser.parse_args(argv)
    try:
        repositories = dict(item.split('=', 1) for item in args.repository)
        result = transition_store(args.source, args.working, args.projector_version, args.report_bundle,
                                  {url: Path(path) for url, path in repositories.items()} or None)
    except (OSError, sqlite3.Error, ValueError, NotImplementedError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
