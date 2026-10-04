"""Bundle or restore a public report store, saved requests and frozen policy."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from nyx import report_backup
from nyx.report_policy import ReportDeployment


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest='operation', required=True)
    backup = commands.add_parser('backup', allow_abbrev=False)
    restore = commands.add_parser('restore', allow_abbrev=False)
    for command in (backup, restore):
        command.add_argument('--store', required=True)
        command.add_argument('--bundle', required=True)
        command.add_argument('--repository', required=True)
        command.add_argument('--checkout', required=True)
        command.add_argument('--projector-version', choices=('1', '2'), required=True)
    backup.add_argument('--config', required=True)
    backup.add_argument('--software-revision', required=True)
    backup.add_argument('--policy-revision', required=True)
    args = parser.parse_args(argv)
    try:
        repositories = {args.repository: args.checkout}
        if args.operation == 'backup':
            deployment = ReportDeployment(args.store, args.config, repositories=repositories)
            with closing(deployment.open_writer()) as conn:
                result = report_backup.backup_bundle(conn, args.bundle, projector_version=args.projector_version,
                    software_revision=args.software_revision, policy_revision=args.policy_revision)
            print(json.dumps({'bundle': str(result)}))
        else:
            deployment = report_backup.restore_bundle(args.bundle, args.store, repositories=repositories,
                                                      projector_version=args.projector_version)
            print(json.dumps({'store': str(deployment.store)}))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
