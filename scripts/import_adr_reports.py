"""Import pinned reviewed public ADR literals, or resume beside-store requests."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from nyx import report_importer
from nyx.report_policy import ReportDeployment


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--store', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--checkout', required=True)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--revision')
    parser.add_argument('--path', action='append', dest='paths')
    parser.add_argument('--projector-version', choices=('1', '2'), required=True)
    parser.add_argument('--create', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args(argv)
    if not args.resume and (args.revision is None or not args.paths):
        parser.error('--revision and --path are required unless --resume is selected')
    try:
        deployment = ReportDeployment(args.store, args.config, repositories={args.repository: args.checkout})
        with closing(deployment.open_writer(create=args.create)) as conn:
            if not args.resume:
                report_importer.prepare_import(conn, args.repository, args.revision, args.paths,
                                               args.run_id, projector_version=args.projector_version)
            result = report_importer.resume_import(conn, args.run_id, projector_version=args.projector_version)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        # ClockSkewError's complete structured fields/units and policy context
        # are rendered by their existing exception text. Refusal is not success.
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
