"""Consistent public-report backup bundles. No protected restoration guarantee."""
from contextlib import closing
import hashlib
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3

from . import hashing, integrity, report_importer, storage, writer
from .report_policy import ReportDeployment, fields, strict_json

FORMAT = 'nyx.report-backup/1'


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _revision(value, name):
    if not isinstance(value, str) or not value:
        raise ValueError(f'{name} must name the exact release revision')


def backup_bundle(conn, destination, *, projector_version, software_revision, policy_revision):
    """Quiesce the owning writer; capture SQLite, retained requests and loaded policy.

    The caller supplies release revision labels. Exact file digests and historical
    vocabulary bindings also describe the captured bytes, including policy edits.
    """
    report_importer.selected(projector_version)
    _revision(software_revision, 'software_revision'); _revision(policy_revision, 'policy_revision')
    if not isinstance(conn, writer.WriterConnection) or conn.owner_lock is None or conn.report_policy is None:
        raise ValueError('backup requires the owning trusted report writer')
    target = Path(destination).resolve()
    if target.exists(): raise FileExistsError(target)
    with conn.append_lock:
        if conn.in_transaction: raise RuntimeError('backup requires no active writer transaction')
        target.mkdir(parents=True)
        with closing(sqlite3.connect(target / 'store.sqlite3')) as backup:
            conn.backup(backup)
        policy = target / 'policy'; policy.mkdir()
        for name, data in conn.report_policy.original_files.items():
            file = policy / name; file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(data)
        imports = report_importer.imports_dir(conn)
        if imports.exists(): shutil.copytree(imports, target / 'imports')
        else: (target / 'imports').mkdir()
        captured = {p.relative_to(target).as_posix(): _digest(p) for p in sorted(target.rglob('*')) if p.is_file()}
        bindings = [dict(zip(('identity', 'version', 'digest_algorithm', 'canonicalization_profile', 'definition_digest'), key))
                    for key in conn.report_policy.definitions]
        status = storage.read_projection_status(conn, projector_version)
        metadata = {'format': FORMAT, 'projector_version': projector_version,
                    'software_revision': software_revision, 'policy_revision': policy_revision,
                    'vocabulary_bindings': hashing.canonical_set(bindings),
                    'tip_hash': storage.last_event_hash(conn), 'progress': status['derived_progress'], 'files': captured}
        (target / 'bundle.json').write_bytes((hashing.canonical_json(metadata) + '\n').encode('utf-8'))
    return target


def _bundle(bundle, projector_version):
    root = Path(bundle).resolve()
    metadata = strict_json((root / 'bundle.json').read_bytes(), root / 'bundle.json')
    fields(metadata, ('format', 'projector_version', 'software_revision', 'policy_revision',
                      'vocabulary_bindings', 'tip_hash', 'progress', 'files'), root)
    if metadata['format'] != FORMAT or metadata['projector_version'] != projector_version:
        raise integrity.IntegrityError('backup format/projector mismatch; no implicit upgrade')
    _revision(metadata['software_revision'], 'software_revision'); _revision(metadata['policy_revision'], 'policy_revision')
    if not isinstance(metadata['files'], dict): raise integrity.IntegrityError('missing bundle file manifest')
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != root / 'bundle.json'}
    if actual != set(metadata['files']): raise integrity.IntegrityError('backup file inventory mismatch')
    for name, digest in metadata['files'].items():
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name:
            raise integrity.IntegrityError('unsafe backup member path')
        member = (root / name).resolve()
        if not member.is_relative_to(root) or not re.fullmatch('[0-9a-f]{64}', digest) or _digest(member) != digest:
            raise integrity.IntegrityError(f'backup member hash mismatch: {name}')
    if 'store.sqlite3' not in actual: raise integrity.IntegrityError('missing backup store')
    return root, metadata


def restore_bundle(bundle, store, *, repositories, projector_version):
    """Restore only to a fresh destination, after bundle and full policy validation."""
    report_importer.selected(projector_version)
    destination = Path(store).resolve()
    if destination.exists() or Path(str(destination) + '.imports').exists() or Path(str(destination) + '.policy').exists():
        raise FileExistsError(destination)
    root, metadata = _bundle(bundle, projector_version)
    snapshot = ReportDeployment(root / 'store.sqlite3', root / 'policy', repositories=repositories).policy
    expected_bindings = hashing.canonical_set([dict(zip(
        ('identity', 'version', 'digest_algorithm', 'canonicalization_profile', 'definition_digest'), key))
        for key in snapshot.definitions])
    if metadata['vocabulary_bindings'] != expected_bindings:
        raise integrity.IntegrityError('backup historical vocabulary bindings differ from preserved definitions')
    with closing(storage.open_readonly(root / 'store.sqlite3')) as source:
        storage.read_all_events(source)
        if storage.last_event_hash(source) != metadata['tip_hash']:
            raise integrity.IntegrityError('backup tip mismatch')
        if storage.read_projection_status(source, projector_version)['derived_progress'] != metadata['progress']:
            raise integrity.IntegrityError('backup progress mismatch')
        # Validate every retained request before exposing a restored writer.
        for file in (root / 'imports').glob('*/requests.json'):
            raw = strict_json(file.read_bytes(), file)
            report_importer.read_manifest(file, projector_version=raw['projector_version'])
        destination.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(destination)) as restored:
            source.backup(restored)
    shutil.copytree(root / 'imports', Path(str(destination) + '.imports'))
    restored_policy = Path(str(destination) + '.policy')
    shutil.copytree(root / 'policy', restored_policy)
    # Retain the captured software/policy revision and digest inventory beside
    # the restored operational data, too; do not rewrite saved request JSON.
    (Path(str(destination) + '.imports') / 'bundle.json').write_bytes((root / 'bundle.json').read_bytes())
    return ReportDeployment(destination, restored_policy, repositories=repositories)
