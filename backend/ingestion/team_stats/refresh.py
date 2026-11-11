"""Manual development team-stat refresh preparation. No apply, scheduler or database writes."""
import argparse
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import make_engine
from app.models import TeamStatsBatch
from ingestion.refresh_state import RefreshState, read_json, write_json
from ingestion.team_stats import source
from ingestion.team_stats.candidate import (StatsRejected, archive_candidate, digest, load_candidate,
                                           require, validate_receipt)
from ingestion.team_stats.storage import inspect, plan_import
from ingestion.team_stats.validation import audit, canonical_map, reference_list
from ingestion.validation import ValidationFailure, validate_bytes

DATASET = 'nflverse_weekly_team_stats'
STALE_SECONDS = 36 * 3600


def initial_status(root):
    path = root / 'status.json'
    if not path.exists():
        # A lost checkpoint after prior runs must not silently erase the last-good history.
        require(not any((root / 'runs').glob('*.json')), 'missing_refresh_checkpoint')
        return dict(version=1, dataset=DATASET, last_successful_validation_at=None,
                    last_successfully_applied_import_at=None, observed_hashes={})
    try:
        state = read_json(path)
        require(type(state.get('version')) is int and state.get('version') == 1 and state.get('dataset') == DATASET, 'invalid_refresh_checkpoint')
        require(isinstance(state.get('observed_hashes'), dict), 'invalid_refresh_checkpoint')
        stamp = state.get('last_successful_validation_at')
        if stamp is not None:
            require(datetime.fromisoformat(stamp).utcoffset() is not None, 'invalid_refresh_checkpoint')
        return state
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        if isinstance(exc, StatsRejected):
            raise
        raise StatsRejected('invalid_refresh_checkpoint') from None


def validate_inputs(inputs):
    """Fail before network access on invalid supplied schedule/identity/reference evidence."""
    schedule_bytes = source.read_input(inputs['schedule'])
    identity_bytes = source.read_input(inputs['identities'])
    references_bytes = source.read_input(inputs['references'])
    schedule = [row.raw for row in validate_bytes(schedule_bytes).rows]
    try:
        identities = canonical_map(json.loads(identity_bytes), schedule)
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise StatsRejected('identity_input_invalid') from None
    try:
        references = reference_list(json.loads(references_bytes))
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise StatsRejected('reference_input_invalid') from None
    return schedule_bytes, identity_bytes, references_bytes, schedule, identities, references


def build_audit(context, captures):
    """Adapt existing pure validators to the unchanged version-1 candidate admission schema."""
    schedule_bytes, identity_bytes, references_bytes, schedule, identities, references = context
    report = dict(version=1, created_at=source.now(), mode='refresh_audit', seasons={}, errors=[],
                  rankings_published=False, database_access=False, independent_origin_authenticated=False,
                  completion_eligibility='unverified', identity_scope='canonical_export_and_schedule',
                  schedule=dict(sha256=digest(schedule_bytes), selected_games=len(schedule)),
                  identity_map=dict(sha256=digest(identity_bytes), origin='operator_supplied'),
                  references=dict(sha256=digest(references_bytes), origin='operator_supplied'))
    failed = False
    for year in source.SEASONS:
        data, receipt = captures[year]
        result = audit(data, year, schedule, identities, references)
        result.update(receipt=receipt, state='audited')
        report['seasons'][str(year)] = result
        if (result['errors'] or result['sack_convention'] != 'negative_validated_against_reviewed_reference'
                or any(stage['missing_reported_score_games'] for stage in result.get('coverage',{}).values())):
            failed = True
    report['audit_exit_code'] = 2 if failed else 0
    return report


def diagnostic_missing(state, report):
    """Absent or unusable pairs are diagnostics, not a claim of confirmed upstream withdrawal."""
    found = {game['canonical_game_id'] for result in report['seasons'].values()
             for game in result['matched_games']}
    return [dict(game_id=gid, source_game_id=state['games'][gid].source_game_id,
                 reason='absent_or_rejected_by_validator_not_confirmed_withdrawal')
            for gid in sorted(set(state['selections']) - found)]


def describe_plan(plan, state):
    incoming_changes = plan['changes']
    by_kind = dict(
        newly_available_pairs=[change for change in incoming_changes if change['before_pair_id'] is None],
        historical_corrections=[change for change in incoming_changes if change['before_pair_id'] is not None],
        missing_previously_accepted=[dict(game_id=b['game_id'], source_game_id=state['games'][b['game_id']].source_game_id)
            for b in plan['blockers'] if b['code'] == 'missing_accepted_game'],
        unchanged_pairs=plan['unchanged_pairs'], invalid_or_ambiguous_records=[])
    return by_kind


def inspect_import_time(session):
    batch = session.execute(select(TeamStatsBatch.id, TeamStatsBatch.recorded_at).where(
        TeamStatsBatch.kind == 'IMPORT').order_by(TeamStatsBatch.recorded_at.desc(), TeamStatsBatch.id.desc()).limit(1)).one_or_none()
    return batch.recorded_at.isoformat() if batch else None


def prepare_refresh(session_factory, root, schedule, identities, references, *, acquire=None, clock=None):
    """Reusable prepare-only workflow. Session factory must provide caller-owned transactions."""
    root = Path(root).resolve()
    acquire = acquire or source.acquire
    clock = clock or source.now
    for path in (schedule,identities,references):
        require(Path(path).resolve() not in (root/'status.json', root/'runner.lock'), 'input_state_path_collision')
    with RefreshState(root).locked():
        status = initial_status(root)
        run = dict(version=1, dataset=DATASET, run_id=str(uuid4()), started_at=clock(),
                   outcome='in_progress', automatic_acceptance_enabled=False, database_writes=False,
                   acquisitions={}, warnings=[], counts=None)
        previous_hashes = dict(status['observed_hashes'])
        if status.get('last_outcome') == 'in_progress':
            run['warnings'].append('previous_preparation_interrupted_no_apply_path_exists')
        status.update(last_attempt_at=run['started_at'], last_run_id=run['run_id'], last_outcome='in_progress')
        write_json(root / 'status.json', status)
        captures = {}
        observed = {}
        try:
            # Capture and use stable copies; never reread mutable operator inputs during this run.
            inputs = {}
            run['phase'] = 'inputs'
            for name,path in (('schedule',schedule),('identities',identities),('references',references)):
                run['input_label'] = name
                inputs[name] = Path(source.capture(root/'snapshots', source.read_input(path))).resolve()
            run['phase'] = 'input_validation'
            context = validate_inputs(inputs)
            for year in source.SEASONS:
                run.update(phase='source_acquisition', source_season=year)
                data, receipt = acquire(year)
                path = source.capture(root/'snapshots', data)
                receipt = dict(receipt, archive=path)
                measured = digest(data)
                run['acquisitions'][str(year)] = dict(receipt=receipt, measured_sha256=measured,
                    changed_since_previous_check=(previous_hashes.get(str(year)) != measured
                                                 if str(year) in previous_hashes else None))
                write_json(root/'acquisitions'/f"{run['run_id']}-{year}.json", run['acquisitions'][str(year)], replace=False)
                # Independently recompute receipt/hash/size/source/metadata claims before any admission.
                require(receipt.get('method') == 'official_download', 'refresh_requires_official_acquisition')
                validate_receipt(receipt, data, year)
                observed[str(year)] = measured
                captures[year] = data, receipt
                if receipt.get('publisher_metadata') is None:
                    run['warnings'].append(f'publisher_metadata_unavailable_{year}')
            run['source_check_passed_at'] = clock()
            run['phase'] = 'audit'
            report = build_audit(context, captures)
            audit_path = root/'audits'/f"{run['run_id']}.json"
            write_json(audit_path, report, replace=False)
            run['audit_path'] = str(audit_path)
            run['invalid_or_ambiguous_records'] = {year: result['errors'] for year,result in report['seasons'].items() if result['errors']}
            run['coverage'] = {year: result.get('coverage',{}) for year,result in report['seasons'].items()}
            if any(stage['missing_schedule_games'] for stage in report['seasons']['2026'].get('coverage',{}).values()):
                run['warnings'].append('partial_2026_schedule_coverage_not_completion_evidence')
            # Even invalid audits get read-only missing/withdrawn diagnostics when the baseline is sound.
            run['phase'] = 'live_comparison'
            with session_factory() as session, session.begin():
                state = inspect(session)
                run['last_successfully_applied_import_at'] = inspect_import_time(session)
                run['import_timestamp_observed_at'] = clock()
                run['missing_previously_accepted'] = diagnostic_missing(state, report)
                run['diagnostic_counts'] = dict(missing_or_unusable_accepted_pairs=len(run['missing_previously_accepted']),
                    invalid_or_ambiguous_records=sum(len(items) for items in run['invalid_or_ambiguous_records'].values()),
                    locally_matched_pairs=sum(len(result['matched_games']) for result in report['seasons'].values()))
                accepted_hashes = {str(year): sorted({state['artifacts'][str(state['pairs'][str(sel.pair_id)].source_artifact_id)].sha256
                    for gid,sel in state['selections'].items() if state['games'][gid].season == year}) for year in source.SEASONS}
                run['accepted_source_hashes'] = accepted_hashes
                if report['audit_exit_code'] != 0:
                    run['outcome'] = 'validation_failed'
                else:
                    candidate = load_candidate(audit_path, root/'snapshots', inputs['schedule'], inputs['identities'], inputs['references'])
                    archives = archive_candidate(candidate, root/'snapshots')
                    plan = plan_import(state, candidate)
                    run.update(plan=plan, classifications=describe_plan(plan,state), archives=archives,
                        candidate_sha256=candidate.sha256,
                        counts=dict(new_pairs=plan['inserted_pairs'], corrected_pairs=plan['corrected_pairs'],
                                    unchanged_pairs=plan['unchanged_pairs'], missing_pairs=len(run['missing_previously_accepted']),
                                    selected_pairs=plan['selected_pairs'], team_rows=2*plan['selected_pairs']))
                    run['outcome'] = ('blocked' if plan['blockers'] else
                                      'review_required' if plan['changes'] else 'unchanged')
                    if not plan['blockers']:
                        run['handoff'] = dict(audit=archives['audit.json'], artifact_dir=str(root/'snapshots'),
                            schedule=archives['schedule.csv'], identity_map=archives['identities.json'], references=archives['references.json'])
                        run['validation_passed_at'] = clock()
            # No database DML: transactions only hold/release reconciliation locks.
        except source.AcquisitionError as exc:
            run.update(outcome='source_failed', error=str(exc), failed_source_season=run.get('source_season'))
        except StatsRejected as exc:
            run.update(outcome='validation_failed', error=str(exc))
        except ValidationFailure as exc:
            run.update(outcome='validation_failed', error='schedule_contract_failed',
                       schedule_problem_codes=sorted({p.code for p in exc.problems}))
        except SQLAlchemyError:
            run.update(outcome='database_failed', error='database_unavailable')
        except PermissionError:
            run.update(outcome='failed', error='input_or_archive_unreadable')
        except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
            run.update(outcome='failed', error='input_or_state_failure')
        if run['outcome'] not in ('review_required', 'unchanged', 'blocked'):
            # A failed transaction/report preparation must never publish a ready handoff or success time.
            run.pop('handoff', None)
            run.pop('validation_passed_at', None)
            if run['counts'] is not None:
                run['unconfirmed_counts'] = run['counts']
                run['counts'] = None
        run['completed_at'] = clock()
        run['warnings'].append('source_original_publication_and_game_completion_times_not_established')
        if run['outcome'] not in ('review_required', 'unchanged'):
            run['warnings'].append(run['outcome'] + ('_' + str(run['failed_source_season']) if run.get('failed_source_season') else ''))
        status.update(last_outcome=run['outcome'], last_refresh_check_at=run['completed_at'], latest_error=run.get('error'),
                      last_import_timestamp_rechecked=('last_successfully_applied_import_at' in run),
                      latest_counts=run['counts'], latest_warnings=run['warnings'])
        if run.get('source_check_passed_at'):
            status.update(last_successful_source_check_at=run['source_check_passed_at'], observed_hashes=observed,
                          source_observations={year:dict(measured_sha256=item['measured_sha256'],
                              source_url=item['receipt']['source_url'], retrieved_at=item['receipt']['retrieved_at'],
                              publisher_asset_updated_at=(item['receipt'].get('publisher_metadata') or {}).get('updated_at'))
                              for year,item in run['acquisitions'].items()})
        if run.get('validation_passed_at'):
            status.update(last_successful_validation_at=run['validation_passed_at'], last_validated_hashes=observed,
                          last_validated_counts=run['counts'], last_validated_run_id=run['run_id'])
        if 'last_successfully_applied_import_at' in run:
            status['last_successfully_applied_import_at'] = run['last_successfully_applied_import_at']
            status['import_timestamp_observed_at'] = run['import_timestamp_observed_at']
        status['applied_timestamp_basis'] = 'Latest visible immutable IMPORT batch recorded_at; not exact commit, completion or source-publication time.'
        stamp = status.get('last_successful_validation_at')
        age = max(0, (datetime.fromisoformat(run['completed_at'])-datetime.fromisoformat(stamp)).total_seconds()) if stamp else None
        status.update(validation_age_seconds=age, validation_stale=age>STALE_SECONDS if age is not None else None,
                      stale_after_seconds=STALE_SECONDS)
        if age is None or age > STALE_SECONDS:
            status['latest_warnings'] = [*run['warnings'], 'no_recent_successful_validation']
        run['freshness'] = dict(status)
        path = root/'runs'/f"{run['run_id']}.json"
        write_json(path,run,replace=False)
        write_json(root/'status.json',status)
        return run,path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=['nflverse-weekly'], required=True)
    parser.add_argument('--schedule', type=Path, required=True)
    parser.add_argument('--identity-map', type=Path, required=True)
    parser.add_argument('--references', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, default=Path('/app/snapshots/team-stats-refresh'))
    parser.add_argument('--dry-run', action='store_true', help='Default and only mode; application is a separate guarded command')
    args=parser.parse_args(argv)
    engine=None
    try:
        settings=Settings()
        require(settings.db_host=='db' and settings.db_name=='nfl_research_dev'
                and settings.db_user=='nfl_ingest' and settings.db_purpose=='runtime','restricted_development_configuration_required')
        engine=make_engine(settings)
        run,path=prepare_refresh(lambda:Session(engine),args.state_dir,args.schedule,args.identity_map,args.references)
        print(json.dumps(dict(outcome=run['outcome'],report=str(path),counts=run['counts'])))
        return 0 if run['outcome'] in ('review_required','unchanged') else 2
    except (StatsRejected, OSError, ValueError, KeyError, BlockingIOError):
        print(json.dumps(dict(outcome='failed',error='configuration_checkpoint_or_lock_failure')))
        return 3
    finally:
        if engine is not None:engine.dispose()


if __name__=='__main__':
    raise SystemExit(main())
