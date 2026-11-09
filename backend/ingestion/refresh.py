"""Manually invoked development refresh. Dry-run by default; no scheduler or API trigger."""
import argparse
import csv
import io
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import make_engine
from app.models import Game, SourceArtifact
from ingestion.refresh_policy import ReviewRejected, guarded_apply, inspect_database
from ingestion.refresh_state import RefreshState, write_json
from ingestion.service import SOURCE_URL, capture
from ingestion.source import SOURCES, SourceFailure, retrieve, utcnow
from ingestion.validation import Snapshot, ValidationFailure, validate_bytes


def candidate(state, identifier, snapshot_dir):
    receipt = state.load('candidates', identifier)
    evidence = receipt['acquisition']
    if evidence.get('integrity_error'):
        raise SourceFailure(evidence['integrity_error'])
    if evidence['source_url'] != SOURCE_URL or evidence['source'] != 'nflverse-release':
        raise ValueError('candidate_source_mismatch')
    stamp = datetime.fromisoformat(evidence['retrieved_at'])
    if stamp.utcoffset() is None:
        raise ValueError('candidate_retrieval_time_invalid')
    digest = evidence['sha256']
    if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('candidate_hash_invalid')
    path = snapshot_dir/f'{digest}.csv'
    if path.is_symlink():
        raise ValueError('candidate_archive_symlink')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest or len(data) != evidence['byte_size']:
        raise ValueError('candidate_archive_changed')
    metadata = evidence.get('metadata') or {}
    if metadata and (metadata['byte_size'] != len(data) or metadata.get('publisher_sha256') not in (None,digest)):
        raise ValueError('candidate_publisher_mismatch')
    return validate_bytes(data), evidence, path


def recover(session, state, identifier):
    database = session.execute(text('select current_database()')).scalar_one()
    if database not in ('nfl_research_dev','nfl_research_test'):
        raise ValueError('database_guard')
    session.execute(text("SET LOCAL lock_timeout = '5s'"))
    session.execute(text('select pg_advisory_xact_lock(202426, 1)'))
    run = state.load('runs', identifier)
    if run.get('phase') != 'commit_pending':
        raise ValueError('run_not_indeterminate')
    artifact = session.get(SourceArtifact, UUID(run['result']['artifact_id']))
    if artifact is None:
        run['prepared_result'] = run.pop('result')
        run.update(outcome='not_applied',phase='complete',completed_at=utcnow(),recovered=True)
        state.finish(run)
        return run
    receipt = json.loads(artifact.provenance_notes)
    if (not artifact or artifact.provider != 'nflverse' or artifact.sha256 != run['sha256']
            or receipt.get('acquisition',{}).get('run_id') != identifier):
        raise ValueError('commit_not_confirmed_stop_for_review')
    run.update(outcome='applied', phase='complete', completed_at=utcnow(), recovered=True)
    state.finish(run)
    return run


def execute(engine, state, snapshot_dir, config, *, identifier=None, apply=False, approval=None,
            recover_id=None, download=retrieve):
    """The state lock is held by the CLI. Commit evidence is durable before attempting commit."""
    if recover_id:
        with Session(engine) as session:
            return recover(session,state,recover_id)
    if state.pending():
        raise ValueError('indeterminate_run_requires_recovery')
    if apply and identifier is None:
        raise ValueError('apply_requires_saved_candidate')
    run = dict(run_id=str(uuid4()), started_at=utcnow(), outcome='running', phase='download', mode='apply' if apply else 'dry_run')
    state.save_run(run)
    committed_changes = False
    try:
        if identifier is None:
            data,evidence = download(config)
            # Capture exact bytes even if complete CSV validation later fails.
            archive = capture(Snapshot(data,evidence['sha256'],0,(),()),snapshot_dir)
            identifier = run['run_id']
            write_json(state.path('candidates',identifier),dict(acquisition=evidence),replace=False)
        run['candidate_id'] = identifier
        saved = state.load('candidates',identifier)['acquisition']
        run.update(sha256=saved['sha256'],acquisition=saved,phase='validate')
        state.save_run(run)
        snapshot,evidence,archive = candidate(state,identifier,snapshot_dir)
        run.update(sha256=snapshot.sha256, acquisition=evidence, phase='compare', validated_at=utcnow())
        state.save_run(run)
        with Session(engine) as session:
            with session.begin():
                plan = inspect_database(session,snapshot,evidence)
                status = state.status()
                previous_stamp = status.get('accepted_asset_updated_at')
                current_stamp = (evidence.get('metadata') or {}).get('asset_updated_at')
                if previous_stamp and (not current_stamp or datetime.fromisoformat(current_stamp.replace('Z','+00:00')) < datetime.fromisoformat(previous_stamp.replace('Z','+00:00'))):
                    plan['blockers'].append(dict(code='older_or_missing_source_revision'))
                if snapshot.sha256 in status.get('accepted_hashes',[]) and snapshot.sha256 != status.get('accepted_sha256'):
                    plan['blockers'].append(dict(code='superseded_snapshot_replay'))
                run['plan'] = plan
                if not apply:
                    run['outcome'] = 'rejected' if plan['blockers'] else 'dry_run'
                else:
                    result = guarded_apply(session,snapshot,evidence,archive,plan,approval,run['run_id'],identifier)
                    run['result'] = result
                    if result['inserted'] or result['updated']:
                        run['phase'] = 'commit_pending'
                        state.save_run(run)
                    run['outcome'] = 'applied' if result['inserted'] or result['updated'] else 'unchanged'
        committed_changes = run['outcome'] == 'applied'
        run.update(phase='complete',completed_at=utcnow())
        state.finish(run)
        return run
    except Exception as exc:
        # SQL parameters, URLs with redirect signatures and credential-bearing errors stay private.
        if committed_changes or run.get('phase') == 'commit_pending':
            # Never overwrite the prepared receipt: COMMIT may have succeeded without acknowledgement.
            raise ValueError(f"indeterminate_commit_recover_run_{run['run_id']}") from None
        if isinstance(exc, SourceFailure) and exc.data is not None:
            capture(Snapshot(exc.data,exc.evidence['sha256'],0,(),()),snapshot_dir)
            identifier = run['run_id']
            write_json(state.path('candidates',identifier),dict(acquisition=exc.evidence),replace=False)
            run.update(candidate_id=identifier,sha256=exc.evidence['sha256'],acquisition=exc.evidence)
        if isinstance(exc, ReviewRejected):
            code,outcome = str(exc),'review_required' if 'review_required' in str(exc) else 'rejected'
        elif isinstance(exc, SourceFailure):
            code,outcome = exc.code,'download_failed'
        elif isinstance(exc, ValidationFailure):
            code,outcome = 'invalid_schedule','validation_failed'
            run['validation'] = [dict(code=p.code,line=p.line,field=p.field,message=p.message) for p in exc.problems[:100]]
            run['validation_problem_count'] = len(exc.problems)
            run['missing_record_diagnostic'] = missing_diagnostic(engine,(snapshot_dir/f"{run['sha256']}.csv").read_bytes())
        else:
            code,outcome = 'database_or_state_failure','failed'
        run.update(outcome=outcome,error=code,error_class=type(exc).__name__,phase='failed',completed_at=utcnow())
        state.finish(run)
        return run


def readable_ids(data):
    """Diagnostics only: never creates an importable partial Snapshot."""
    try:
        reader = csv.reader(io.StringIO(data.decode('utf-8-sig'),newline=''),strict=True)
        header = next(reader)
        if len(set(header)) != len(header) or not {'season','game_id'} <= set(header):
            return None
        ids = set()
        for cells in reader:
            if len(cells) != len(header):
                return None
            row = dict(zip(header,cells))
            year = int(row['season'])
            if year in (2024,2025,2026):
                ids.add(row['game_id'])
        return ids
    except (ValueError,UnicodeError,csv.Error,StopIteration):
        return None


def missing_diagnostic(engine, data):
    ids = readable_ids(data)
    if ids is None or engine is None:
        return {'diagnostic_only':True,'available':False}
    try:
        with Session(engine) as session:
            if session.scalar(text('select current_database()')) not in ('nfl_research_dev','nfl_research_test'):
                return {'diagnostic_only':True,'available':False}
            previous = session.scalars(select(Game.source_game_id).where(Game.provider=='nflverse')).all()
        return dict(diagnostic_only=True,available=True,absent_source_ids=sorted(set(previous)-ids))
    except SQLAlchemyError:
        return {'diagnostic_only':True,'available':False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=SOURCES, required=True)
    parser.add_argument('--state-dir',type=Path,default=Path('/app/refresh-state'))
    parser.add_argument('--snapshot-dir',type=Path,default=Path('/app/snapshots'))
    parser.add_argument('--candidate',type=lambda s:str(UUID(s)))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run',action='store_true')
    mode.add_argument('--apply',action='store_true')
    mode.add_argument('--recover',type=lambda s:str(UUID(s)))
    parser.add_argument('--approve-review',help='Exact review_token from the candidate dry-run report; never overrides blockers')
    args = parser.parse_args(argv)
    if args.apply and not args.candidate:
        parser.error('--apply requires --candidate from a previous dry-run; fresh downloads cannot apply in one step')
    if args.approve_review and not args.apply:
        parser.error('--approve-review requires --apply')
    engine = None
    state = None
    try:
        settings = Settings()
        if settings.db_name != 'nfl_research_dev' or settings.db_host != 'db':
            raise ValueError('database_guard')
        state = RefreshState(args.state_dir)
        engine = make_engine(settings)
        with state.locked():
            run = execute(engine,state,args.snapshot_dir,SOURCES[args.source],identifier=args.candidate,
                          apply=args.apply,approval=args.approve_review,recover_id=args.recover)
        # Full diff is durable; terminal output is bounded and safe to review.
        print(json.dumps({k:v for k,v in run.items() if k not in ('plan','acquisition')} | {
            'report_path':str(state.path('runs',run['run_id'])),
            'review_token':run.get('plan',{}).get('review_token'),
            'summary':run.get('plan',{}).get('summary'),
            'blockers':run.get('plan',{}).get('blockers',[])[:100]},sort_keys=True))
        return 0 if run['outcome'] in ('dry_run','applied','unchanged','not_applied') else 2
    except (ValueError,OSError,ValidationError,SQLAlchemyError,KeyError,TypeError) as exc:
        pending = []
        if state is not None:
            try:
                pending = [run['run_id'] for run in state.pending()]
            except (ValueError,OSError,KeyError,TypeError):
                pass
        print(json.dumps(dict(pending_run_ids=pending,error_class=type(exc).__name__,error='refresh_stopped',hint='Check isolated Compose configuration, state/lock and pending run receipts; no automatic override. For commit_pending use --recover RUN_ID.')),file=sys.stderr)
        return 3
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
