"""Interactive orchestration of existing guarded development workflows; no importer logic."""
import argparse
import json
import signal
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import make_engine
from app.models import TeamStatsAccepted, TeamStatsPair
from app.repositories.schedule import ScheduleRepository
from app.repositories.team_stats import TeamStatsRepository
from ingestion import refresh, scheduler
from ingestion.refresh_state import RefreshState, read_json, write_json
from ingestion.source import SOURCES

ROOT = Path('/app/refresh-state/update-cli')
STATS_REPORTS = Path('/app/snapshots/team-stats/reports')
PIPELINES = scheduler.PIPELINES
METRICS = ('gross_passing_yards', 'original_sack_yards', 'net_passing_yards', 'rushing_yards')


class Unconfirmed(Exception):
    """No automatic retry after a possibly committed operation."""


def emit(value):
    # JSON escaping also prevents untrusted source text from issuing terminal controls.
    print(json.dumps(value, ensure_ascii=True, sort_keys=True, default=str))


LABELS = {'schedule': 'Schedule & Scores', 'team_stats': 'Team Statistics'}
STATES = {'not_checked': 'NOT CHECKED', 'unchanged': 'UP TO DATE',
          'review_required': 'CHANGES AVAILABLE - NOT IMPORTED', 'skipped': 'SKIPPED - NOT IMPORTED',
          'applied': 'UPDATED - VERIFIED', 'blocked': 'VALIDATION BLOCKED', 'failed': 'CHECK OR IMPORT FAILED',
          'failed_verification': 'VERIFICATION FAILED', 'applied_unverified': 'IMPORTED - NOT VERIFIED',
          'indeterminate': 'UNKNOWN APPLY OUTCOME'}
MARKET_FIELDS = {'spread_line', 'total_line', 'home_moneyline', 'away_moneyline',
                 'home_spread_odds', 'away_spread_odds', 'over_odds', 'under_odds'}
REVIEW_FIELDS = MARKET_FIELDS | {'game_id', 'old_game_id', 'espn', 'season', 'week', 'game_type',
                               'home_team', 'away_team', 'gameday', 'gametime', 'home_score', 'away_score'}


def safe(value):
    """Keep external text on one terminal line, without control sequences."""
    if value is None:
        return 'not reported'
    return ''.join(c if c.isprintable() else f'\\x{ord(c):02x}' for c in str(value))


def heading(title):
    print('\n' + title + '\n' + '-' * 30)


def yardage_changed(change):
    before = {v['team_id']: v for v in change.get('before', [])}
    return any(any(before.get(v['team_id'], {}).get(k) != v.get(k) for k in METRICS)
               for v in change.get('after', []))


def counts(report):
    changes = (report.get('plan') or {}).get('changes', [])
    corrections = [c for c in changes if c.get('before_pair_id')]
    return dict(new_scores=sum('newly_reported_scores' in c.get('categories', []) for c in changes),
                corrected_scores=sum('corrected_scores' in c.get('categories', []) for c in changes),
                betting_lines=sum(any(f['field'] in MARKET_FIELDS for f in c.get('fields', [])) for c in changes),
                new_stat_games=sum(c.get('kind') == 'initial_pair' for c in changes),
                corrections=len(corrections), yardage_corrections=sum(yardage_changed(c) for c in corrections),
                source_only_corrections=sum(not yardage_changed(c) for c in corrections),
                changed_games=len(changes))


def change_label(pipeline, change):
    if pipeline == 'schedule':
        names = {'newly_reported_scores': 'new reported scores', 'corrected_scores': 'score correction',
                 'kickoff_change': 'kickoff change', 'identity_change': 'game identity change',
                 'matchup_change': 'matchup change', 'new_game': 'new game',
                 'historical_change': 'historical record change', 'source_record_change': 'source record change'}
        labels = [names.get(v, v.replace('_', ' ')) for v in change.get('categories', [])]
        if any(f['field'] in MARKET_FIELDS for f in change.get('fields', [])):
            labels.append('betting-line reference change')
        return safe(', '.join(labels)) or 'source record change'
    if change.get('kind') == 'initial_pair':
        return 'new two-team statistics game'
    prefix = 'historical correction: ' if change.get('kind') == 'historical_correction' else ''
    if yardage_changed(change):
        return prefix + 'correction to previously accepted yardage'
    fields = [f['field'] for t in change.get('raw_changes', []) for f in t['fields']]
    if any('epa' in field.lower() for field in fields):
        return prefix + 'EPA source values or precision changed; stored yardage unchanged'
    return prefix + 'source details changed; stored yardage unchanged'


def game_label(change):
    identifier = change.get('source_game_id') or change.get('game_id') or 'ID unavailable'
    teams = {f['field']: f.get('after') or f.get('before') for f in change.get('fields', [])
             if f['field'] in ('home_team', 'away_team')}
    matchup = f" ({teams['away_team']} at {teams['home_team']})" if all(teams.get(k) for k in ('home_team', 'away_team')) else ''
    return safe(identifier) + safe(matchup)


def details(pipeline, report):
    """Readable allowlisted values only; never emit tokens or unrelated payloads."""
    for change in (report.get('plan') or {}).get('changes', []):
        print('  ' + game_label(change) + ': ' + change_label(pipeline, change))
        canonical = change.get('canonical_id') or change.get('game_id')
        if canonical:
            print('    Database game ID: ' + safe(canonical))
        if pipeline == 'schedule':
            for field in change.get('fields', []):
                name = safe(field['field'].replace('_', ' '))
                if field['field'] in REVIEW_FIELDS:
                    print(f"    {name}: {safe(field.get('before'))} -> {safe(field.get('after'))}")
                else:
                    print(f"    {name}: source field changed (private values hidden)")
        else:
            before = {v['team_id']: v for v in change.get('before', [])}
            for after in change.get('after', []):
                print('    Team ' + safe(after['team_id']) + ':')
                for metric in METRICS:
                    if metric in after:
                        print(f"      {metric.replace('_', ' ')}: {safe(before.get(after['team_id'], {}).get(metric))} -> {safe(after[metric])}")
            for team in change.get('raw_changes', []):
                print('    Changed source fields: ' + ', '.join(safe(f['field']) for f in team['fields']))
    blockers = (report.get('plan') or {}).get('blockers', [])
    for blocker in blockers:
        print('  Blocker: ' + safe(blocker.get('code', 'validation blocked')).replace('_', ' ') +
              ' ' + safe(blocker.get('source_game_id') or blocker.get('game_id') or ''))


def summary(pipeline, report, state):
    print(f"{LABELS[pipeline]}: {STATES.get(state, 'UNAVAILABLE')}")
    if state == 'review_required':
        c = counts(report)
        items = [('new_scores', 'games with new reported scores'), ('corrected_scores', 'score corrections'),
                 ('betting_lines', 'games with betting-line reference changes')] if pipeline == 'schedule' else [
                     ('new_stat_games', 'new two-team statistics games'), ('corrections', 'corrections to previously accepted games'),
                     ('yardage_corrections', 'yardage corrections'), ('source_only_corrections', 'source-only corrections (stored yardage unchanged)')]
        for key, label in items:
            if c[key]:
                print(f'  {c[key]} {label}')
        print(f"  {c['changed_games']} affected games in total; categories may overlap.")
    if state in ('failed', 'blocked'):
        print('  This pipeline could not complete a valid update. Existing accepted data is retained.')
        if report.get('outcome') in ('source_failed', 'download_failed'):
            print('  NFL source unavailable or download failed. Try a new check after the source issue is resolved.')
        else:
            print('  Resolve the source, validation or database problem before starting a new check.')
        if report.get('error'):
            print('  Diagnostic: ' + safe(report['error']).replace('_', ' '))
        details(pipeline, {'plan': {'blockers': (report.get('plan') or {}).get('blockers', [])}})
    for warning in report.get('warnings', []) + (report.get('plan') or {}).get('warnings', []):
        print('  Note: ' + safe(warning))


def review_state(report):
    if ready(report):
        return 'review_required' if report['plan']['changes'] else 'unchanged'
    if (report.get('plan') or {}).get('blockers') or report.get('outcome') in ('blocked', 'validation_failed', 'rejected'):
        return 'blocked'
    return 'failed'


def ready(report):
    return report.get('outcome') in ('dry_run', 'unchanged') and isinstance(report.get('plan'), dict) and not report['plan'].get('blockers')


class Operations:
    def __init__(self, engine):
        self.engine = engine
        self.config = scheduler.Config.environment()

    def prepare(self):
        runner = scheduler.Scheduler(self.config)
        # Caller holds the original scheduler singleton lock for the entire session.
        # Scheduler worker completion events are JSON. Keep normal interactive
        # output readable; its durable private job records remain unchanged.
        with tempfile.TemporaryFile(mode='w+') as events, redirect_stdout(events), ThreadPoolExecutor(max_workers=2) as pool:
            try:
                runner.tick(scheduler.utcnow(), pool, manual=True)
                jobs = {p: f.result() for p, f in runner.active.items()}
            except BaseException:
                runner.stop.set()
                raise
        reports = {}
        for pipeline, job in jobs.items():
            reports[pipeline] = read_json(Path(job['pipeline_report'])) if job.get('pipeline_report') else dict(outcome=job['outcome'])
            if not job.get('successful_check'):
                if reports[pipeline].get('outcome') in ('dry_run', 'review_required', 'unchanged'):
                    reports[pipeline]['outcome'] = 'failed'
                reports[pipeline].setdefault('error', job['outcome'])
        return reports

    def preview(self, pipeline, prepared):
        if pipeline == 'schedule':
            with RefreshState(Path('/app/refresh-state')).locked():
                return refresh.execute(self.engine, RefreshState(Path('/app/refresh-state')), Path('/app/snapshots'),
                                       SOURCES['nflverse-release'], identifier=prepared['candidate_id'])
        return self.stats(prepared, apply=False)

    def stats(self, prepared, *, apply, token=None):
        handoff = prepared['handoff']
        argv = [sys.executable, '-m', 'ingestion.team_stats.ingest']
        for key in ('audit', 'artifact_dir', 'schedule', 'identity_map', 'references'):
            argv.append('--' + key.replace('_', '-') + '=' + handoff[key])
        argv += ['--apply', '--approval-stdin'] if apply else ['--dry-run']
        # Token travels only over stdin. Raw stdout/stderr never reaches operator logs.
        with tempfile.TemporaryFile() as output:
            process = subprocess.run(argv, input=((token + '\n').encode() if apply else b''),
                                     stdout=output, stderr=subprocess.DEVNULL, check=False)
            output.seek(0)
            result = json.loads(output.read(scheduler.MAX_OUTPUT + 1))
        path = Path(result['report'])
        if path.parent != STATS_REPORTS or not path.name.startswith('stats-') or path.suffix != '.json':
            raise ValueError('unexpected_stats_report')
        report = read_json(path)
        if result['outcome'] != report['outcome']:
            raise ValueError('inconsistent_stats_report')
        report['_report_path'] = str(path)
        if process.returncode != 0 and report['outcome'] not in ('blocked', 'rejected'):
            if apply:
                raise Unconfirmed()
            return dict(outcome='failed')
        return report

    def apply(self, pipeline, prepared, reviewed):
        token = reviewed['plan']['review_token']
        if pipeline == 'team_stats':
            return self.stats(prepared, apply=True, token=token)
        state = RefreshState(Path('/app/refresh-state'))
        with state.locked():
            return refresh.execute(self.engine, state, Path('/app/snapshots'), SOURCES['nflverse-release'],
                                   identifier=prepared['candidate_id'], apply=True, approval=token)

    def verify(self, pipeline, prepared, reviewed):
        with Session(self.engine) as session, session.begin():
            session.execute(text('SET TRANSACTION READ ONLY'))
            if pipeline == 'schedule':
                snapshot, _, _ = refresh.candidate(RefreshState(Path('/app/refresh-state')),
                                                    prepared['candidate_id'], Path('/app/snapshots'))
                expected = {r.values['source_game_id']: r for r in snapshot.rows}
                repo = ScheduleRepository(session)
                actual = {g.source_game_id: g for season in (2024, 2025, 2026) for g in repo.games(season)}
                for change in reviewed['plan']['changes']:
                    identifier = change['source_game_id']
                    game, row = actual.get(identifier), expected[identifier]
                    if (game is None or game.source_record_sha256 != row.sha256
                            or game.source_artifact.sha256 != snapshot.sha256
                            or any(getattr(game, k) != v for k, v in row.values.items())):
                        return False
            else:
                repo = TeamStatsRepository(session)
                for change in reviewed['plan']['changes']:
                    gid = UUID(change['game_id'])
                    rows = {str(r['team_id']): r for r in repo.game(gid)}
                    pair_hash = session.scalar(select(TeamStatsPair.content_sha256).join(
                        TeamStatsAccepted, TeamStatsAccepted.pair_id == TeamStatsPair.id).where(TeamStatsAccepted.game_id == gid))
                    if pair_hash != change['after_sha256'] or len(rows) != 2:
                        return False
                    for expected in change['after']:
                        if any(rows.get(expected['team_id'], {}).get(k) != expected[k] for k in METRICS):
                            return False
        return True


class Interactive:
    def __init__(self, operations, root=ROOT, ask=input):
        self.ops, self.root, self.ask = operations, Path(root), ask
        self.prepared, self.reports = {}, {}
        self.states = {p: 'not_checked' for p in PIPELINES}
        self.audit = dict(run_id=str(uuid4()), phase='review', pipelines=self.states)
        self.verified = set()
        self.imported_counts = {p: {} for p in PIPELINES}

    def save(self):
        self.audit['observed_at'] = scheduler.utcnow().isoformat()
        write_json(self.root/'runs'/(self.audit['run_id']+'.json'), self.audit)
        write_json(self.root/'latest.json', self.audit)

    def show(self):
        for p in PIPELINES:
            summary(p, self.reports.get(p, {}), self.states[p])

    def check(self):
        heading('NFL DATA UPDATE')
        print('Checking NFL sources...')
        self.prepared = self.ops.prepare()
        for p in PIPELINES:
            prepared = self.prepared[p]
            valid = prepared.get('outcome') in (('dry_run',) if p == 'schedule' else ('review_required', 'unchanged'))
            if valid and not (prepared.get('plan') or {}).get('blockers'):
                try:
                    self.reports[p] = self.ops.preview(p, prepared)
                    self.reports[p]['warnings'] = prepared.get('warnings', [])
                    self.states[p] = review_state(self.reports[p])
                except Exception:
                    self.reports[p], self.states[p] = dict(outcome='preview_failed'), 'failed'
            else:
                self.reports[p], self.states[p] = prepared, review_state(prepared) if not valid else 'blocked'
        self.save()

    def approve(self, pipeline):
        if self.states[pipeline] != 'review_required':
            print('Pipeline is not eligible for approval. Start a new check after resolving failures.')
            return
        reviewed = self.reports[pipeline]
        try:
            current = self.ops.preview(pipeline, self.prepared[pipeline])
        except Exception:
            self.reports[pipeline] = dict(outcome='preview_failed')
            self.states[pipeline] = 'failed'
            self.save()
            print(LABELS[pipeline] + ': revalidation failed. No import was attempted; resolve the failure before checking again.')
            return
        if not ready(current) or current['plan']['review_token'] != reviewed['plan']['review_token']:
            self.reports[pipeline] = current
            self.states[pipeline] = review_state(current)
            print('Plan changed or is blocked. Previous approval discarded. Review the new plan before approving again.')
            summary(pipeline, current, self.states[pipeline])
            self.save()
            return 'stale'
        summary(pipeline, reviewed, self.states[pipeline])
        details(pipeline, reviewed)
        if self.ask('Approve import? [y/N] ').strip().lower() not in ('y', 'yes'):
            self.states[pipeline] = 'skipped'
            self.save()
            print('Skipped. These changes were not imported.')
            return
        reviewed_path = reviewed.get('_report_path')
        if pipeline == 'schedule' and reviewed.get('run_id'):
            reviewed_path = str(Path('/app/refresh-state/runs')/(reviewed['run_id']+'.json'))
        self.audit.update(phase='applying', active_pipeline=pipeline,
                          reviewed_report=reviewed_path, candidate_id=self.prepared[pipeline].get('candidate_id'))
        self.save()  # Durable evidence before any possible database write.
        try:
            result = self.ops.apply(pipeline, self.prepared[pipeline], reviewed)
            outcome = result.get('outcome')
            self.audit.update(importer_outcome=outcome,
                              importer_report=result.get('_report_path') or
                              (str(Path('/app/refresh-state/runs')/(result['run_id']+'.json')) if result.get('run_id') else None))
            self.save()
            if outcome not in ('applied', 'unchanged', 'rejected', 'blocked', 'review_required'):
                raise Unconfirmed()
            if outcome in ('applied', 'unchanged'):
                self.states[pipeline] = 'applied_unverified'
                try:
                    verified = self.ops.verify(pipeline, self.prepared[pipeline], reviewed)
                except Exception:
                    verified = False
                if not verified:
                    self.states[pipeline] = 'failed_verification'
                    self.audit['phase'] = 'verification_failed'
                    self.save()
                    print(LABELS[pipeline] + ': importer reported success, but database verification FAILED. Stop for review.')
                    raise Unconfirmed()
                self.states[pipeline] = 'applied' if outcome == 'applied' else 'unchanged'
                self.verified.add(pipeline)
                if outcome == 'applied':
                    self.imported_counts[pipeline] = counts(reviewed)
                    print(LABELS[pipeline] + ': IMPORT SUCCESSFUL - database verification PASSED.')
                else:
                    print(LABELS[pipeline] + ': already accepted; database verification PASSED.')
            else:
                self.states[pipeline] = 'failed'
                print(pipeline + ': guarded importer rejected the apply. No automatic retry.')
            self.audit['phase'] = 'review'
            self.save()
        except BaseException:
            if self.audit['phase'] != 'verification_failed':
                self.audit['phase'] = 'indeterminate'
                self.states[pipeline] = 'indeterminate'
            self.save()
            raise Unconfirmed() from None

    def finish(self):
        heading('NFL DATA UPDATE COMPLETE')
        for p in PIPELINES:
            print(f"{LABELS[p]}: {STATES.get(self.states[p], 'UNAVAILABLE')}")
        total = {k: sum(v.get(k, 0) for v in self.imported_counts.values())
                 for k in ('new_scores', 'corrected_scores', 'betting_lines', 'new_stat_games', 'corrections')}
        if any(self.imported_counts.values()):
            print('Imported and verified in this session:')
            print(f"  New score games: {total['new_scores']}")
            print(f"  Score corrections: {total['corrected_scores']}")
            print(f"  Betting-line reference changes: {total['betting_lines']}")
            print(f"  New statistics games: {total['new_stat_games']}")
            print(f"  Statistics corrections: {total['corrections']}")
        if any(s in ('failed_verification', 'applied_unverified') for s in self.states.values()):
            print('Database verification: FAILED OR INCOMPLETE. Stop and review the accepted state; do not retry blindly.')
        elif 'indeterminate' in self.states.values():
            print('Database verification: UNKNOWN. The import may have committed. Stop for outcome review; do not retry.')
        elif self.verified:
            print('Database verification: PASSED for imports confirmed in this session.')
        else:
            print('Database verification: no imports verified in this session (checks only).')
        if all(s == 'unchanged' for s in self.states.values()):
            print('No new NFL data found in the validated checks. No import was needed.')
            print('The stored accepted data matches the candidates from this check; source coverage may be incomplete.')
        elif all(s in ('applied', 'unchanged') for s in self.states.values()) and self.verified:
            print('Your NFL research website can now read the newly accepted data. Refresh your browser to see the changes.')
            print('This reflects the validated snapshots from this check, not a guarantee of complete or live NFL coverage.')
        else:
            print('PARTIALLY UPDATED.' if self.verified else 'UPDATE NOT COMPLETE.')
            print('Some changes were skipped, blocked, failed or remain unconfirmed. The website is not confirmed up to date.')
            if self.verified:
                print('Verified imports are available to the website; refresh your browser to see those changes.')
            if any(s in ('indeterminate', 'failed_verification', 'applied_unverified') for s in self.states.values()):
                print('Next step: inspect --status and the existing importer journals with the operator runbook before recovery.')
            else:
                print('Next step: resolve any failed checks, then run this command again to review remaining changes.')

    def run(self):
        finished = False
        try:
            self.check()
            self.show()
            if any(s == 'review_required' for s in self.states.values()):
                print('\nNEXT STEP: Review and import updates, one pipeline at a time.')
                print('Scores remain source-reported with UNVERIFIED finality; UNKNOWN statuses are preserved.')
                print('Betting lines are unverified source references, not current sportsbook offers.')
                for p in PIPELINES:
                    changes = (self.reports[p].get('plan') or {}).get('changes', [])
                    if self.states[p] == 'review_required':
                        print('\n' + LABELS[p] + ' - affected games:')
                        for change in changes[:10]:
                            print('  ' + game_label(change) + ': ' + change_label(p, change))
                        if len(changes) > 10:
                            print(f'  ... and {len(changes) - 10} more; review shows all games.')
            for p in PIPELINES:
                while self.states[p] == 'review_required':
                    heading('SCHEDULE UPDATES' if p == 'schedule' else 'TEAM STATISTICS')
                    if self.ask('Review proposed changes? [Y/n] ').strip().lower() not in ('', 'y', 'yes'):
                        self.states[p] = 'skipped'
                        self.save()
                        print('Skipped. These changes were not imported.')
                        break
                    if self.approve(p) != 'stale':
                        break
            self.audit['phase'] = 'complete'
            self.save()
            self.finish()
            finished = True
            self.ask('Press Enter to exit. ')
            return 2 if any(s.startswith('failed') or s == 'blocked' for s in self.states.values()) else 0
        except BaseException:
            for p in PIPELINES:
                if self.states[p] == 'review_required':
                    self.states[p] = 'skipped'
            if not finished:
                self.finish()
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--status', action='store_true', help='Read existing sanitized state only; no downloads or imports')
    args = parser.parse_args(argv)
    engine, cli = None, None
    try:
        if args.status:
            emit(scheduler.status())
            if (ROOT/'latest.json').exists():
                emit(read_json(ROOT/'latest.json'))
            return 0
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            print('Interactive terminal required; use --status.')
            return 3
        settings = Settings()
        if not (settings.db_host == 'db' and settings.db_name == 'nfl_research_dev'
                and settings.db_user == 'nfl_ingest' and settings.db_purpose == 'runtime'):
            raise ValueError('restricted_development_configuration_required')
        engine = make_engine(settings)
        with engine.connect() as connection:
            if connection.scalar(text('select current_database()')) != 'nfl_research_dev':
                raise ValueError('database_guard')
        def interrupted(*_):
            raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM, interrupted)
        with RefreshState(scheduler.ROOT).locked():
            if (ROOT/'latest.json').exists() and read_json(ROOT/'latest.json').get('phase') in ('applying', 'indeterminate', 'verification_failed'):
                print('Prior apply needs outcome review. Inspect --status and original importer journals; no automatic retry or recovery.')
                return 3
            cli = Interactive(Operations(engine))
            return cli.run()
    except (KeyboardInterrupt, EOFError):
        print('Interrupted. No further import will run; retain private reports.')
        return 130
    except Unconfirmed:
        print('STOP: apply outcome or verification is unconfirmed. Inspect private CLI/importer reports; do not retry blindly.')
        return 3
    except BlockingIOError:
        print('Busy: coordinate the recurring scheduler/other updater and retry after it exits. Never delete lock files.')
        return 3
    except BrokenPipeError:
        # Terminal output is gone. No confirmation or further import is possible.
        return 3
    except Exception:
        print('Update stopped: prerequisite, configuration, source, database or report failure. Inspect private reports; no automatic retry.')
        return 3
    finally:
        if cli:
            for pipeline in PIPELINES:
                if cli.states[pipeline] == 'review_required':
                    cli.states[pipeline] = 'skipped'
            # Interactive.run renders the human-readable final summary, including errors.
        if engine is not None:
            engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
