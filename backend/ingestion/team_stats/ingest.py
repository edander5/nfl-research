"""Guarded development team-stat import/rollback. Dry-run is the default."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import make_engine
from ingestion.team_stats.candidate import StatsRejected, load_candidate, archive_candidate
from ingestion.team_stats.storage import inspect, plan_import, plan_rollback, apply_import, apply_rollback


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--audit', type=Path)
    mode.add_argument('--rollback-batch')
    parser.add_argument('--artifact-dir', type=Path)
    parser.add_argument('--schedule', type=Path)
    parser.add_argument('--identity-map', type=Path)
    parser.add_argument('--references', type=Path)
    parser.add_argument('--archive-dir', type=Path, default=Path('/app/snapshots/team-stats'))
    parser.add_argument('--report-dir', type=Path, default=Path('/app/snapshots/team-stats/reports'))
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--dry-run', action='store_true')
    action.add_argument('--apply', action='store_true')
    parser.add_argument('--approval-stdin', action='store_true', help='Read reviewed token from stdin, not process arguments')
    parser.add_argument('--approve-review', help='Exact token from reviewed dry-run plan')
    args = parser.parse_args(argv)
    if args.approval_stdin:
        if args.approve_review:
            parser.error('choose one approval transport')
        args.approve_review = sys.stdin.readline().strip()
    result, engine, phase = {}, None, 'preparing'
    code = 0
    candidate, archives = None, None
    try:
        if args.approve_review and not args.apply:
            raise StatsRejected('approval_requires_apply')
        candidate, archives = None, None
        if args.audit:
            if not all((args.artifact_dir, args.schedule, args.identity_map, args.references)):
                raise StatsRejected('audit_inputs_required')
            candidate = load_candidate(args.audit, args.artifact_dir, args.schedule, args.identity_map, args.references)
            archives = archive_candidate(candidate, args.archive_dir)
        else:
            from uuid import UUID
            UUID(args.rollback_batch)
        settings = Settings()
        if settings.db_host != 'db' or settings.db_name != 'nfl_research_dev':
            raise StatsRejected('use_compose_development_database')
        if settings.db_purpose != 'runtime':
            raise StatsRejected('restricted_runtime_configuration_required')
        engine = make_engine(settings)
        with Session(engine) as session, session.begin():
            phase = 'transaction'
            if args.apply:
                result = (apply_import(session, candidate, archives, args.approve_review) if candidate
                          else apply_rollback(session, args.rollback_batch, args.approve_review))
            else:
                state = inspect(session)
                plan = plan_import(state, candidate) if candidate else plan_rollback(session, state, args.rollback_batch)
                result = dict(outcome='dry_run', plan=plan)
                if plan['blockers']:
                    result['outcome'], code = 'blocked', 2
            phase = 'committing' if args.apply else 'ending_read_transaction'
        phase = 'complete'
    except StatsRejected as exc:
        result, code = dict(outcome='rejected', error=str(exc)), 2
    except SQLAlchemyError:
        result, code = dict(outcome='database_failure', phase=phase,
                            hint='No automatic retry. If commit acknowledgement was lost, re-run dry-run and inspect batch/selection history.'), 3
    except (ValueError, OSError, KeyError):
        result, code = dict(outcome='input_or_configuration_failure'), 3
    finally:
        if engine is not None:
            engine.dispose()
    if candidate is not None:
        result['candidate_evidence'] = candidate.evidence
        result['archives'] = archives
    result['observed_at'] = datetime.now(timezone.utc).isoformat()
    try:
        args.report_dir.mkdir(parents=True, exist_ok=True)
        path = args.report_dir / ('stats-' + uuid4().hex + '.json')
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(result, stream, indent=2, sort_keys=True, default=str)
            stream.write('\n')
        print(json.dumps(dict(outcome=result.get('outcome'), report=str(path), batch_id=result.get('batch_id'),
                              error=result.get('error'))))
    except OSError:
        print(json.dumps(dict(outcome='report_write_failed', database_outcome=result.get('outcome'))))
        return 3
    return code


if __name__ == '__main__':
    raise SystemExit(main())
