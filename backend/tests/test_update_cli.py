"""Synthetic operator sessions only: no external downloads or development writes."""
import copy
import json
import os
import subprocess
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from ingestion import update_cli as module
from ingestion.refresh_state import RefreshState, read_json


TOKEN = 'PRIVATE_REVIEW_TOKEN_DO_NOT_PRINT'


def report(pipeline, changes=True):
    change = (dict(source_game_id='2026_10_A_B', canonical_id='synthetic-game',
                   categories=['newly_reported_scores', 'source_record_change'],
                   fields=[dict(field='home_score', before=None, after=21),
                           dict(field='spread_line', before='3', after='4'),
                           dict(field='private_payload', before=None, after='PRIVATE_PAYLOAD')])
              if pipeline == 'schedule' else
              dict(source_game_id='2024_01_A_B', game_id='synthetic-game', kind='historical_correction',
                   before_pair_id='old', after_sha256='hash',
                   before=[dict(team_id='a', net_passing_yards=200)],
                   after=[dict(team_id='a', net_passing_yards=201)],
                   raw_changes=[dict(team_id='a', fields=[dict(field='passing_yards', before=200, after=201),
                                                        dict(field='private_payload', after='PRIVATE_PAYLOAD')])]))
    return dict(outcome='dry_run', candidate_id='synthetic-candidate', handoff={'synthetic': True},
                plan=dict(review_token=TOKEN, changes=[change] if changes else [], blockers=[],
                          summary={'newly_reported_scores': int(changes)}, inserted_pairs=0,
                          corrected_pairs=int(changes), unchanged_pairs=int(not changes)))


class FakeOperations:
    def __init__(self, changes=True):
        self.reports = {p: report(p, changes) for p in module.PIPELINES}
        self.applies, self.previews, self.verifications = [], [], []
        self.result = {'outcome': 'applied'}
        self.verified = True

    def prepare(self):
        result = copy.deepcopy(self.reports)
        if result['team_stats']['outcome'] == 'dry_run':
            result['team_stats']['outcome'] = 'review_required'
        return result

    def preview(self, pipeline, prepared):
        self.previews.append(pipeline)
        return copy.deepcopy(self.reports[pipeline])

    def apply(self, pipeline, prepared, reviewed):
        assert reviewed['plan']['review_token'] == self.reports[pipeline]['plan']['review_token']
        self.applies.append(pipeline)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result

    def verify(self, pipeline, prepared, reviewed):
        self.verifications.append(pipeline)
        return self.verified


def session(tmp_path, answers, ops=None):
    ops = ops or FakeOperations()
    answers = iter(answers)
    cli = module.Interactive(ops, tmp_path, ask=lambda _: next(answers))
    return cli, ops


def test_both_separately_reviewed_applied_and_verified(tmp_path, capsys):
    cli, ops = session(tmp_path, ['', 'yes', '', 'y', ''])
    assert cli.run() == 0
    assert ops.applies == ops.verifications == ['schedule', 'team_stats']
    assert cli.states == dict(schedule='applied', team_stats='applied')
    output = capsys.readouterr().out
    assert TOKEN not in output and 'PRIVATE_PAYLOAD' not in output
    assert 'spread line' in output and 'yardage correction' in output
    assert 'previously accepted' in output
    assert 'IMPORT SUCCESSFUL' in output and 'Refresh your browser' in output
    assert not any(line.startswith('{') for line in output.splitlines())
    assert TOKEN not in json.dumps(read_json(tmp_path/'latest.json'))
    assert (tmp_path/'latest.json').stat().st_mode & 0o777 == 0o600


def test_unchanged_repeat_does_not_call_apply(tmp_path):
    for _ in range(2):
        cli, ops = session(tmp_path, [''], FakeOperations(changes=False))
        assert cli.run() == 0
        assert not ops.applies and not ops.verifications
        assert set(cli.states.values()) == {'unchanged'}


@pytest.mark.parametrize('answers', [['n', 'n', ''], ['', '', '', '', ''],
                                    ['', 'n', '', 'no', ''], ['', 'unexpected', 'n', '']])
def test_no_implicit_approval_and_skips(tmp_path, answers):
    cli, ops = session(tmp_path, answers)
    assert cli.run() == 0
    assert not ops.applies
    assert set(cli.states.values()) == {'skipped'}


@pytest.mark.parametrize('outcome', ['source_failed', 'download_failed', 'validation_failed', 'failed'])
def test_failed_check_is_not_unchanged_and_other_pipeline_available(tmp_path, outcome):
    ops = FakeOperations()
    ops.reports['schedule'] = dict(outcome=outcome, error='missing_sources')
    cli, _ = session(tmp_path, ['n', ''], ops)
    assert cli.run() == 2
    assert cli.states == dict(schedule='blocked' if outcome == 'validation_failed' else 'failed', team_stats='skipped')
    assert not ops.applies


def test_blockers_cannot_be_approved(tmp_path):
    ops = FakeOperations()
    ops.reports['team_stats']['plan']['blockers'] = [{'code': 'missing_accepted_game'}]
    cli, _ = session(tmp_path, ['n', ''], ops)
    assert cli.run() == 2 and not ops.applies


def test_stale_plan_requires_another_review_and_new_approval(tmp_path, capsys):
    cli, ops = session(tmp_path, [])
    cli.check()
    ops.reports['schedule']['plan']['review_token'] = 'NEW_PRIVATE_TOKEN'
    cli.approve('schedule')  # Must not even prompt on this attempt.
    assert not ops.applies
    assert cli.reports['schedule']['plan']['review_token'] == 'NEW_PRIVATE_TOKEN'
    assert 'Plan changed' in capsys.readouterr().out


@pytest.mark.parametrize('outcome', ['rejected', 'blocked', 'review_required'])
def test_importer_token_mismatch_rejection_not_retried(tmp_path, outcome):
    ops = FakeOperations()
    ops.result = dict(outcome=outcome, error='review_required_or_stale')
    cli, _ = session(tmp_path, ['', 'y', 'n', ''], ops)
    assert cli.run() == 2
    assert ops.applies == ['schedule'] and not ops.verifications


@pytest.mark.parametrize('failure', [module.Unconfirmed(), KeyboardInterrupt(), ValueError('PRIVATE_EXCEPTION')])
def test_apply_interrupt_and_unexpected_failure_stop_with_private_journal(tmp_path, capsys, failure):
    ops = FakeOperations()
    ops.result = failure
    cli, _ = session(tmp_path, ['', 'y'], ops)
    with pytest.raises(module.Unconfirmed):
        cli.run()
    assert ops.applies == ['schedule']
    assert read_json(tmp_path/'latest.json')['phase'] == 'indeterminate'
    assert 'PRIVATE_EXCEPTION' not in capsys.readouterr().out


def test_verification_failure_stops_second_pipeline_and_retains_applied_uncertainty(tmp_path):
    ops = FakeOperations()
    ops.verified = False
    cli, _ = session(tmp_path, ['', 'y'], ops)
    with pytest.raises(module.Unconfirmed):
        cli.run()
    assert cli.states['schedule'] == 'failed_verification'
    assert read_json(tmp_path/'latest.json')['phase'] == 'verification_failed'
    assert ops.applies == ['schedule']


@pytest.mark.parametrize('outcome', ['database_failure', 'report_write_failed', 'unknown'])
def test_indeterminate_structured_outcome_stops(tmp_path, outcome):
    ops = FakeOperations()
    ops.result = dict(outcome=outcome)
    cli, _ = session(tmp_path, ['n', '', 'y'], ops)
    with pytest.raises(module.Unconfirmed):
        cli.run()
    assert ops.applies == ['team_stats'] and not ops.verifications


def test_ctrl_c_during_prompt_never_applies(tmp_path):
    ops = FakeOperations()
    def interrupt(_):
        raise KeyboardInterrupt()
    cli = module.Interactive(ops, tmp_path, ask=interrupt)
    with pytest.raises(KeyboardInterrupt):
        cli.run()
    assert not ops.applies and read_json(tmp_path/'latest.json')['phase'] == 'review'


def test_stats_adapter_uses_stdin_never_token_arguments(tmp_path, monkeypatch):
    path = tmp_path/'stats-synthetic.json'
    path.write_text(json.dumps(dict(outcome='applied', plan={'review_token': TOKEN})))
    monkeypatch.setattr(module, 'STATS_REPORTS', tmp_path)
    calls = []
    def run(argv, **kwargs):
        calls.append((argv, kwargs['input']))
        kwargs['stdout'].write(json.dumps(dict(outcome='applied', report=str(path))).encode())
        return type('Result', (), {'returncode': 0})()
    monkeypatch.setattr(module.subprocess, 'run', run)
    ops = module.Operations(None)
    handoff = {k: '/app/snapshots/synthetic' for k in ('audit', 'artifact_dir', 'schedule', 'identity_map', 'references')}
    assert ops.stats({'handoff': handoff}, apply=True, token=TOKEN)['outcome'] == 'applied'
    argv, stdin = calls[0]
    assert TOKEN not in ' '.join(argv)
    assert '--apply' in argv and '--approval-stdin' in argv and stdin == (TOKEN+'\n').encode()


def test_schedule_adapter_uses_original_lock_and_exact_candidate(tmp_path, monkeypatch):
    # Exercise the adapter while redirecting only its fixed state location.
    original = module.RefreshState
    monkeypatch.setattr(module, 'RefreshState', lambda _: original(tmp_path))
    calls = []
    def execute(*args, **kwargs):
        calls.append(kwargs)
        return dict(outcome='applied')
    monkeypatch.setattr(module.refresh, 'execute', execute)
    ops = module.Operations(None)
    with original(tmp_path).locked():
        with pytest.raises(BlockingIOError):
            ops.apply('schedule', {'candidate_id': 'reviewed'}, report('schedule'))
    assert not calls
    ops.apply('schedule', {'candidate_id': 'reviewed'}, report('schedule'))
    assert calls[0] == dict(identifier='reviewed', apply=True, approval=TOKEN)


def test_noninteractive_cannot_check_or_import(monkeypatch):
    monkeypatch.setattr(module.sys.stdin, 'isatty', lambda: False)
    monkeypatch.setattr(module, 'make_engine', lambda _: pytest.fail('no DB access'))
    assert module.main([]) == 3


def test_status_does_not_prepare_or_connect(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module.scheduler, 'status', lambda: {'prepare_only': True})
    monkeypatch.setattr(module, 'make_engine', lambda _: pytest.fail('no DB access'))
    assert module.main(['--status']) == 0
    assert 'prepare_only' in capsys.readouterr().out


def test_new_pairs_and_source_only_corrections_are_distinct(capsys):
    data = report('team_stats')
    correction = data['plan']['changes'][0]
    correction['after'] = copy.deepcopy(correction['before'])
    initial = copy.deepcopy(correction)
    initial.update(kind='initial_pair', before_pair_id=None, before=[], raw_changes=[])
    data['plan']['changes'].append(initial)
    module.summary('team_stats', data, 'review_required')
    output = capsys.readouterr().out
    assert '1 source-only corrections' in output
    assert 'yardage corrections' not in output
    module.details('team_stats', data)
    output = capsys.readouterr().out
    assert 'new two-team statistics game' in output and 'stored yardage unchanged' in output


class ReadSession:
    def __init__(self, pair_hash='hash'):
        self.statements, self.pair_hash = [], pair_hash
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def begin(self): return nullcontext()
    def execute(self, statement): self.statements.append(str(statement))
    def scalar(self, statement): return self.pair_hash


@pytest.mark.parametrize('mismatch', [None, 'score', 'source_record', 'artifact', 'missing_game'])
def test_schedule_verification_checks_scores_and_provenance(monkeypatch, mismatch):
    s = ReadSession()
    monkeypatch.setattr(module, 'Session', lambda _: s)
    expected = SimpleNamespace(sha256='row-hash', values=dict(source_game_id='synthetic', reported_home_score=21, reported_away_score=0))
    snapshot = SimpleNamespace(rows=[expected], sha256='artifact-hash')
    monkeypatch.setattr(module.refresh, 'candidate', lambda *a: (snapshot, None, None))
    game = SimpleNamespace(**expected.values, source_record_sha256=expected.sha256,
                           source_artifact=SimpleNamespace(sha256=snapshot.sha256))
    if mismatch == 'score': game.reported_home_score = None
    if mismatch == 'source_record': game.source_record_sha256 = 'wrong'
    if mismatch == 'artifact': game.source_artifact.sha256 = 'wrong'
    monkeypatch.setattr(module.ScheduleRepository, 'games', lambda _, season: [] if mismatch == 'missing_game' or season != 2026 else [game])
    reviewed = dict(plan=dict(changes=[dict(source_game_id='synthetic')]))
    result = module.Operations(None).verify('schedule', {'candidate_id': 'synthetic'}, reviewed)
    assert result == (mismatch is None)
    assert s.statements == ['SET TRANSACTION READ ONLY']


@pytest.mark.parametrize('mismatch', [None, 'yards', 'missing_side', 'pair'])
def test_statistics_verification_checks_complete_pair_and_metrics(monkeypatch, mismatch):
    s = ReadSession('wrong' if mismatch == 'pair' else 'hash')
    monkeypatch.setattr(module, 'Session', lambda _: s)
    after = [dict(team_id=str(uuid4()), **{k: 0 for k in module.METRICS}) for _ in range(2)]
    actual = copy.deepcopy(after)
    if mismatch == 'yards': actual[0]['net_passing_yards'] = 1
    if mismatch == 'missing_side': actual.pop()
    monkeypatch.setattr(module.TeamStatsRepository, 'game', lambda *a: actual)
    reviewed = dict(plan=dict(changes=[dict(game_id=str(uuid4()), after_sha256='hash', after=after)]))
    assert module.Operations(None).verify('team_stats', {}, reviewed) == (mismatch is None)
    assert s.statements == ['SET TRANSACTION READ ONLY']


@pytest.mark.parametrize('phase', ['applying', 'indeterminate', 'verification_failed'])
def test_prior_unconfirmed_apply_blocks_repeated_execution(tmp_path, monkeypatch, phase):
    from ingestion.refresh_state import write_json
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module.scheduler, 'ROOT', tmp_path/'scheduler')
    monkeypatch.setattr(module.sys.stdin, 'isatty', lambda: True)
    monkeypatch.setattr(module.sys.stdout, 'isatty', lambda: True)
    monkeypatch.setattr(module, 'Settings', lambda: SimpleNamespace(db_host='db', db_name='nfl_research_dev', db_user='nfl_ingest', db_purpose='runtime'))
    class Engine:
        def connect(self): return ReadSession('nfl_research_dev')
        def dispose(self): pass
    monkeypatch.setattr(module, 'make_engine', lambda _: Engine())
    monkeypatch.setattr(module, 'Operations', lambda _: pytest.fail('must not prepare/retry'))
    write_json(tmp_path/'latest.json', dict(phase=phase))
    assert module.main([]) == 3


def test_launcher_status_and_prerequisites(tmp_path):
    docker = tmp_path/'docker'
    docker.write_text('''#!/usr/bin/env bash
case "$*" in
  'compose version'|'info'|*'config --quiet') exit 0 ;;
  'compose ps -q db') printf '%s' "${FAKE_DB:-db-container}" ;;
  'compose ps -q api') printf '%s' api-container ;;
  inspect*) printf '%s' "${FAKE_HEALTH:-healthy}" ;;
  *'run -T --rm --no-deps scheduler python -m ingestion.update_cli --status') printf '%s' status-only ;;
  *) exit 9 ;;
esac
''')
    docker.chmod(0o755)
    launcher = Path(__file__).resolve().parents[2]/'scripts/update-nfl-data.sh'
    env = {**os.environ, 'PATH': str(tmp_path)+':'+os.environ['PATH']}
    result = subprocess.run([str(launcher), '--status'], cwd='/tmp', env=env, capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout == 'status-only'
    result = subprocess.run([str(launcher), '--status'], env={**env, 'FAKE_HEALTH': 'unhealthy'}, capture_output=True, text=True)
    assert result.returncode == 3 and 'not healthy' in result.stderr


def test_preparation_preserves_failed_exit_even_with_valid_looking_report(tmp_path, monkeypatch, capsys):
    from concurrent.futures import Future
    from ingestion.refresh_state import write_json
    paths = {}
    for p in module.PIPELINES:
        paths[p] = tmp_path/(p+'.json')
        write_json(paths[p], report(p))
    class Runner:
        def __init__(self, _): self.active = {}
        def tick(self, now, pool, manual):
            assert manual is True
            print('{"synthetic_scheduler_event": true}')
            for p in module.PIPELINES:
                future = Future()
                future.set_result(dict(pipeline_report=str(paths[p]), successful_check=p != 'schedule', outcome='pipeline_failed'))
                self.active[p] = future
    monkeypatch.setattr(module.scheduler, 'Scheduler', Runner)
    result = module.Operations(None).prepare()
    assert result['schedule']['outcome'] == 'failed'
    assert result['team_stats']['outcome'] == 'dry_run'
    assert capsys.readouterr().out == ''


def test_main_respects_existing_scheduler_singleton(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'ROOT', tmp_path/'cli')
    monkeypatch.setattr(module.scheduler, 'ROOT', tmp_path/'scheduler')
    monkeypatch.setattr(module.sys.stdin, 'isatty', lambda: True)
    monkeypatch.setattr(module.sys.stdout, 'isatty', lambda: True)
    monkeypatch.setattr(module, 'Settings', lambda: SimpleNamespace(db_host='db', db_name='nfl_research_dev', db_user='nfl_ingest', db_purpose='runtime'))
    class Engine:
        def connect(self): return ReadSession('nfl_research_dev')
        def dispose(self): pass
    monkeypatch.setattr(module, 'make_engine', lambda _: Engine())
    monkeypatch.setattr(module, 'Operations', lambda _: pytest.fail('must not prepare when busy'))
    with RefreshState(tmp_path/'scheduler').locked():
        assert module.main([]) == 3


def test_no_change_is_plain_text_and_never_requests_approval(tmp_path, capsys):
    prompts = []
    ops = FakeOperations(changes=False)
    cli = module.Interactive(ops, tmp_path, ask=lambda prompt: prompts.append(prompt) or '')
    assert cli.run() == 0
    assert prompts == ['Press Enter to exit. ']
    output = capsys.readouterr().out
    assert output.count('UP TO DATE') == 4
    assert 'No new NFL data found' in output
    assert 'No import was needed' in output
    assert 'IMPORT SUCCESSFUL' not in output and 'newly accepted data' not in output
    assert not any(line.startswith('{') for line in output.splitlines())


@pytest.mark.parametrize('pipeline', module.PIPELINES)
def test_only_changing_pipeline_requests_review_and_import(tmp_path, capsys, pipeline):
    ops = FakeOperations(changes=False)
    ops.reports[pipeline] = report(pipeline)
    if pipeline == 'schedule':
        ops.reports[pipeline]['plan']['changes'][0]['fields'] = [{'field': 'home_score', 'before': None, 'after': 21}]
    else:
        ops.reports[pipeline]['plan']['changes'][0].update(kind='initial_pair', before_pair_id=None, before=[], raw_changes=[])
    prompts, answers = [], iter(['', 'y', ''])
    def ask(prompt):
        prompts.append(prompt)
        return next(answers)
    cli = module.Interactive(ops, tmp_path, ask=ask)
    assert cli.run() == 0
    assert ops.applies == ops.verifications == [pipeline]
    assert len([p for p in prompts if p == 'Approve import? [y/N] ']) == 1
    output = capsys.readouterr().out
    assert 'IMPORT SUCCESSFUL' in output and 'database verification PASSED' in output
    assert 'Refresh your browser' in output
    assert ('New score games: 1' if pipeline == 'schedule' else 'New statistics games: 1') in output


def test_skipped_schedule_and_accepted_stats_explain_partial_update(tmp_path, capsys):
    cli, ops = session(tmp_path, ['n', '', 'y', ''])
    assert cli.run() == 0
    assert ops.applies == ['team_stats']
    output = capsys.readouterr().out
    assert 'PARTIALLY UPDATED' in output and 'SKIPPED - NOT IMPORTED' in output
    assert 'website is not confirmed up to date' in output
    assert 'Your NFL research website can now read the newly accepted data' not in output


def test_epa_source_only_correction_explained_without_private_values(capsys):
    data = report('team_stats')
    change = data['plan']['changes'][0]
    change['after'] = copy.deepcopy(change['before'])
    change['raw_changes'] = [{'team_id': 'a', 'fields': [{'field': 'passing_epa', 'before': 'PRIVATE_PAYLOAD', 'after': TOKEN}]}]
    module.details('team_stats', data)
    output = capsys.readouterr().out
    assert 'EPA source values or precision changed; stored yardage unchanged' in output
    assert TOKEN not in output and 'PRIVATE_PAYLOAD' not in output


def test_guided_stale_candidate_is_reviewed_again_before_confirmation(tmp_path, capsys):
    ops = FakeOperations()
    original = ops.preview
    def preview(pipeline, prepared):
        if pipeline == 'schedule' and ops.previews.count('schedule') == 1:
            ops.reports[pipeline]['plan']['review_token'] = 'NEW_PRIVATE_TOKEN'
        return original(pipeline, prepared)
    ops.preview = preview
    prompts, answers = [], iter(['', '', 'y', 'n', ''])
    def ask(prompt):
        prompts.append(prompt)
        return next(answers)
    cli = module.Interactive(ops, tmp_path, ask=ask)
    assert cli.run() == 0
    assert ops.applies == ['schedule']
    assert prompts[:3] == ['Review proposed changes? [Y/n] ', 'Review proposed changes? [Y/n] ', 'Approve import? [y/N] ']
    output = capsys.readouterr().out
    assert 'Plan changed' in output and 'NEW_PRIVATE_TOKEN' not in output


def test_verification_exception_never_claims_website_updated(tmp_path, capsys):
    ops = FakeOperations()
    def verify(*_):
        raise ValueError('PRIVATE_DATABASE_EXCEPTION')
    ops.verify = verify
    cli, _ = session(tmp_path, ['', 'y'], ops)
    with pytest.raises(module.Unconfirmed):
        cli.run()
    assert cli.states['schedule'] == 'failed_verification'
    output = capsys.readouterr().out
    assert 'VERIFICATION FAILED' in output and 'IMPORT SUCCESSFUL' not in output
    assert 'PRIVATE_DATABASE_EXCEPTION' not in output


def test_terminal_error_during_confirmation_cannot_approve(tmp_path):
    ops = FakeOperations()
    def ask(prompt):
        if prompt == 'Approve import? [y/N] ':
            raise OSError('synthetic terminal disconnected')
        return ''
    cli = module.Interactive(ops, tmp_path, ask=ask)
    with pytest.raises(OSError):
        cli.run()
    assert not ops.applies


def test_status_json_contract_with_cli_record(tmp_path, monkeypatch, capsys):
    from ingestion.refresh_state import write_json
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module.scheduler, 'status', lambda: {'prepare_only': True, 'pipelines': {}})
    write_json(tmp_path/'latest.json', dict(phase='complete', pipelines={'schedule': 'applied', 'team_stats': 'blocked'}))
    assert module.main(['--status']) == 0
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert lines[0]['prepare_only'] is True
    assert lines[1]['pipelines'] == {'schedule': 'applied', 'team_stats': 'blocked'}


def test_external_terminal_control_characters_are_escaped(capsys):
    data = report('schedule')
    data['plan']['changes'][0]['fields'][0]['after'] = '\x1b[31m\nunsafe'
    module.details('schedule', data)
    output = capsys.readouterr().out
    assert '\x1b' not in output and '\\x1b[31m\\x0aunsafe' in output


def test_failed_revalidation_leaves_other_pipeline_reviewable(tmp_path, capsys):
    ops = FakeOperations()
    original = ops.preview
    def preview(pipeline, prepared):
        if pipeline == 'schedule' and ops.previews.count('schedule') == 1:
            raise ValueError('PRIVATE_SOURCE_FAILURE')
        return original(pipeline, prepared)
    ops.preview = preview
    cli, _ = session(tmp_path, ['', '', 'y', ''], ops)
    assert cli.run() == 2
    assert ops.applies == ['team_stats']
    assert cli.states == dict(schedule='failed', team_stats='applied')
    output = capsys.readouterr().out
    assert 'revalidation failed' in output and 'PARTIALLY UPDATED' in output
    assert 'PRIVATE_SOURCE_FAILURE' not in output


@pytest.mark.parametrize('pipeline', module.PIPELINES)
@pytest.mark.parametrize('answer', ['', 'n', 'no', 'import schedule', 'import team stats', 'unexpected', 'y', ' Y ', 'yes', ' YES '])
def test_exact_default_no_confirmation_for_each_pipeline(tmp_path, pipeline, answer):
    ops = FakeOperations(changes=False)
    ops.reports[pipeline] = report(pipeline)
    prompts, answers = [], iter(['', answer, ''])
    def ask(prompt):
        prompts.append(prompt)
        return next(answers)
    cli = module.Interactive(ops, tmp_path, ask=ask)
    assert cli.run() == 0
    assert prompts == ['Review proposed changes? [Y/n] ', 'Approve import? [y/N] ', 'Press Enter to exit. ']
    approved = answer.strip().lower() in ('y', 'yes')
    assert ops.applies == ops.verifications == ([pipeline] if approved else [])
    assert cli.states[pipeline] == ('applied' if approved else 'skipped')


def test_schedule_approval_does_not_approve_statistics(tmp_path, capsys):
    cli, ops = session(tmp_path, ['', 'y', '', '', ''])
    assert cli.run() == 0
    assert ops.applies == ops.verifications == ['schedule']
    assert cli.states == dict(schedule='applied', team_stats='skipped')
    output = capsys.readouterr().out
    assert 'PARTIALLY UPDATED' in output
    assert 'Team Statistics: SKIPPED - NOT IMPORTED' in output
