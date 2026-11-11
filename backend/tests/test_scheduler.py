"""No real refreshes: fake children and synthetic private reports for scheduling guarantees."""
import json
import sys
import threading
import time
from concurrent.futures import Future
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from ingestion import scheduler as module
from ingestion.scheduler import Config, Scheduler, local_slot, command, status, execute_child, ChildStopped
from ingestion.refresh_state import RefreshState, read_json, write_json


def utc(value):return datetime.fromisoformat(value.replace('Z','+00:00'))


class ImmediatePool:
    def submit(self,function,*args):
        future=Future()
        try:future.set_result(function(*args))
        except Exception as exc:future.set_exception(exc)
        return future


class BusyPool:
    def __init__(self):self.calls=[]
    def submit(self,function,*args):
        self.calls.append(args)
        return Future()


def child_result(pipeline,root,*,outcome=None):
    identifier=str(uuid4())
    outcome=outcome or ('dry_run' if pipeline=='schedule' else 'review_required')
    report=dict(run_id=identifier,outcome=outcome,completed_at='2026-11-11T13:01:00+00:00',
        plan=dict(changes=[{'synthetic':True}],blockers=[],review_token='PRIVATE_APPROVAL_TOKEN'),
        acquisition=dict(retrieved_at='2026-11-11T13:00:00+00:00',metadata={'asset_updated_at':'2026-11-11T12:00:00+00:00'}),
        freshness=dict(last_successful_validation_at='2026-11-11T13:01:00+00:00'))
    # Redirect only the report reader; filenames/parent validation still uses actual fixed contracts.
    if pipeline=='schedule':
        path=Path('/app/refresh-state/runs')/(identifier+'.json')
        output=dict(outcome=outcome,run_id=identifier,review_token='PRIVATE_APPROVAL_TOKEN')
    else:
        path=Path('/app/snapshots/team-stats-refresh/runs')/(identifier+'.json')
        output=dict(outcome=outcome,report=str(path))
    return output,report,path


@pytest.fixture
def children(tmp_path,monkeypatch):
    real_reader=module.read_json
    reports={}
    calls=[]
    def reader(path):return reports[str(path)] if str(path) in reports else real_reader(path)
    monkeypatch.setattr(module,'read_json',reader)
    def execute(argv,timeout,stop):
        pipeline='schedule' if argv[2]=='ingestion.refresh' else 'team_stats'
        calls.append(argv)
        output,report,path=child_result(pipeline,tmp_path)
        reports[str(path)]=report
        return 0,output
    return execute,calls,reports


@pytest.mark.parametrize('date',['2026-01-05T13:00:10Z','2026-07-05T13:00:10Z','2026-11-11T01:00:59Z'])
def test_phoenix_6am_6pm_in_winter_and_summer(date):
    assert local_slot(utc(date),Config()) is not None
    assert local_slot(utc(date).replace(minute=1),Config()) is None


def test_dst_gap_skipped_and_fold_deduplicated():
    config=Config(times=('01:30','02:30'),zone='America/New_York')
    assert local_slot(utc('2026-11-01T05:30:00Z'),config)==local_slot(utc('2026-11-01T06:30:00Z'),config)
    assert local_slot(utc('2026-03-08T07:30:00Z'),config) is None # local 03:30, no 02:30
    assert local_slot(utc('2026-03-07T07:30:00Z'),config) is not None


@pytest.mark.parametrize('kwargs',[{'times':()},{'times':('6:00',)},{'times':('24:00',)},
    {'times':('06:00','06:00')},{'zone':'not-a-timezone'},{'timeout':0}])
def test_invalid_configuration_is_not_silently_defaulted(kwargs):
    with pytest.raises((ValueError,KeyError)):Config(**kwargs)


def test_fixed_commands_cannot_accept_approval_or_apply_injection():
    config=Config(schedule='/data/raw/--apply',identities='/data/raw/--approve-review',references='/review/docs/r.json')
    for pipeline in module.PIPELINES:
        args=command(pipeline,config)
        assert args[:2]==[sys.executable,'-m'] and '--dry-run' in args
        assert not any(arg in args for arg in ('--apply','--approve-review','--recover','--rollback-batch'))
        assert 'alembic' not in args and 'ingestion.schedule' not in args
    assert '--schedule=/data/raw/--apply' in command('team_stats',config)
    with pytest.raises(ValueError):command('unapproved',config)


def test_due_slot_claims_survive_restart_and_no_catchup(tmp_path,children):
    execute,calls,_=children
    now=utc('2026-11-11T13:00:10Z')
    first=Scheduler(Config(),tmp_path,execute=execute,clock=lambda:now)
    first.tick(now,ImmediatePool())
    assert len(calls)==2
    first.tick(now.replace(second=50),ImmediatePool());assert len(calls)==2
    restarted=Scheduler(Config(),tmp_path,execute=execute,clock=lambda:now)
    restarted.recover_observations();restarted.tick(now,ImmediatePool());assert len(calls)==2
    restarted.tick(now.replace(minute=1),ImmediatePool());assert len(calls)==2
    assert all(job['review_required'] for job in status(tmp_path,now)['pipelines'].values())
    for path in (tmp_path/'jobs').glob('*.json'):
        assert path.stat().st_mode & 0o777==0o600
        assert 'PRIVATE_APPROVAL_TOKEN' not in path.read_text()


def test_busy_pipelines_are_skipped_not_queued(tmp_path):
    scheduler=Scheduler(Config(),tmp_path)
    pool=BusyPool()
    scheduler.tick(utc('2026-11-11T13:00:00Z'),pool)
    scheduler.tick(utc('2026-11-12T01:00:00Z'),pool)
    scheduler.tick(utc('2026-11-12T01:00:30Z'),pool)
    assert len(pool.calls)==2
    assert all(job['outcome']=='skipped_busy' for job in status(tmp_path)['pipelines'].values())


def test_crash_claim_without_completed_job_is_unconfirmed_and_not_replayed(tmp_path):
    now=utc('2026-11-11T13:00:00Z')
    first=Scheduler(Config(),tmp_path,clock=lambda:now)
    first.tick(now,BusyPool())
    restarted=Scheduler(Config(),tmp_path,clock=lambda:now)
    restarted.recover_observations()
    assert all(job['outcome']=='interrupted_unconfirmed' for job in status(tmp_path,now)['pipelines'].values())
    pool=BusyPool();restarted.tick(now,pool);assert not pool.calls


def test_failure_isolation_parallel_manual_once(tmp_path,children):
    execute,calls,_=children
    def fail_schedule(argv,timeout,stop):
        if argv[2]=='ingestion.refresh':raise ValueError('PRIVATE_RAW_OUTPUT')
        return execute(argv,timeout,stop)
    scheduler=Scheduler(Config(),tmp_path,execute=fail_schedule)
    scheduler.run(once=True)
    info=status(tmp_path)
    assert info['pipelines']['schedule']['outcome']=='runner_or_report_failed'
    assert info['pipelines']['team_stats']['successful_check']
    assert 'PRIVATE_RAW_OUTPUT' not in json.dumps(info)
    assert not info['daemon_healthy']


def test_daemon_start_does_not_trigger_immediate_off_schedule_jobs(tmp_path,children):
    execute,calls,_=children
    scheduler=Scheduler(Config(),tmp_path,execute=execute,clock=lambda:utc('2026-11-11T14:00:00Z'))
    # Stop at the first heartbeat wait; no clock sleeps or network execution.
    scheduler.stop.wait=lambda _:scheduler.stop.set()
    scheduler.run()
    assert calls==[] and read_json(tmp_path/'daemon.json')['phase']=='stopped'


def test_singleton_blocks_other_scheduler_manual_once(tmp_path):
    with RefreshState(tmp_path).locked():
        with pytest.raises(BlockingIOError):Scheduler(Config(),tmp_path).run(once=True)


def test_late_old_worker_does_not_hide_newer_skipped_attempt(tmp_path):
    scheduler=Scheduler(Config(),tmp_path)
    latest=dict(job_id=str(uuid4()),pipeline='schedule',started_at='2026-11-12T01:00:00+00:00',outcome='skipped_busy')
    old=dict(job_id=str(uuid4()),pipeline='schedule',started_at='2026-11-11T13:00:00+00:00',outcome='dry_run')
    scheduler.publish(latest);scheduler.publish(old)
    assert read_json(tmp_path/'latest'/'schedule.json')['job_id']==latest['job_id']


def test_report_failure_never_counts_as_a_success(tmp_path,children):
    execute,_,reports=children
    def broken(argv,timeout,stop):
        code,output=execute(argv,timeout,stop)
        if argv[2]=='ingestion.refresh':
            report=reports['/app/refresh-state/runs/'+output['run_id']+'.json']
            report['outcome']='applied' # forbidden unexpected child behavior
        return code,output
    scheduler=Scheduler(Config(),tmp_path,execute=broken);scheduler.run(once=True)
    assert not status(tmp_path)['pipelines']['schedule']['successful_check']
    assert status(tmp_path)['pipelines']['team_stats']['successful_check']


def test_real_subprocess_stdout_is_captured_not_logged(capsys):
    code,result=execute_child([sys.executable,'-c',"import json;print(json.dumps({'review_token':'PRIVATE_TOKEN'}))"],60,threading.Event())
    assert code==0 and result['review_token']=='PRIVATE_TOKEN'
    assert 'PRIVATE_TOKEN' not in capsys.readouterr().out


def test_real_child_shutdown_terminates_and_releases_resources():
    stop=threading.Event();stop.set()
    with pytest.raises(ChildStopped):execute_child([sys.executable,'-c','import time;time.sleep(60)'],60,stop)


def test_real_child_malformed_json_is_not_success():
    with pytest.raises(ValueError):execute_child([sys.executable,'-c',"print('PRIVATE_NOT_JSON')"],60,threading.Event())


def test_health_is_heartbeat_not_pipeline_success(tmp_path):
    now=utc('2026-11-11T13:00:00Z')
    write_json(tmp_path/'daemon.json',dict(phase='running',heartbeat_at=now.isoformat(),private_secret='PRIVATE'))
    assert status(tmp_path,now)['daemon_healthy']
    assert 'PRIVATE' not in json.dumps(status(tmp_path,now))
    assert not status(tmp_path,utc('2026-11-11T13:02:00Z'))['daemon_healthy']


def test_cli_rejects_apply_and_administrator_config(monkeypatch,capsys):
    from app.core import config
    with pytest.raises(SystemExit):module.main(['--apply'])
    monkeypatch.setattr(config,'Settings',lambda:MockSettings())
    assert module.main(['--once'])==3
    assert 'scheduler_stopped' in capsys.readouterr().err


class MockSettings:
    db_host='db';db_name='nfl_research_dev';db_user='admin';db_purpose='migration'


def test_invalid_team_specific_paths_do_not_stop_schedule_pipeline(tmp_path,children):
    execute,_,_=children
    scheduler=Scheduler(Config(schedule='--apply'),tmp_path,execute=execute)
    scheduler.run(once=True)
    info=status(tmp_path)
    assert info['pipelines']['schedule']['successful_check']
    assert not info['pipelines']['team_stats']['successful_check']


def test_slow_failed_schedule_does_not_delay_team_pipeline(tmp_path,children):
    execute,_,_=children
    started=threading.Event();stats_done=threading.Event()
    def parallel(argv,timeout,stop):
        if argv[2]=='ingestion.refresh':
            started.set()
            assert stats_done.wait(timeout=2),'team preparation must run independently'
            raise ChildStopped('timed_out')
        assert started.wait(timeout=2)
        result=execute(argv,timeout,stop);stats_done.set();return result
    scheduler=Scheduler(Config(),tmp_path,execute=parallel)
    scheduler.run(once=True)
    info=status(tmp_path)
    assert info['pipelines']['schedule']['outcome']=='timed_out'
    assert info['pipelines']['team_stats']['successful_check']


def test_real_timeout_terminates_the_child(monkeypatch):
    ticks=iter((0,61))
    with monkeypatch.context() as patch:
        patch.setattr(module.time,'monotonic',lambda:next(ticks,61))
        with pytest.raises(ChildStopped,match='timed_out'):
            execute_child([sys.executable,'-c','import time;time.sleep(60)'],60,threading.Event())


def test_existing_manual_schedule_lock_remains_authoritative(tmp_path,monkeypatch):
    from ingestion import refresh
    monkeypatch.setattr(refresh,'Settings',lambda:GoodSettings())
    class Engine:
        def dispose(self):pass
    monkeypatch.setattr(refresh,'make_engine',lambda _:Engine())
    monkeypatch.setattr(refresh,'execute',lambda *a,**k:pytest.fail('must stop before executing a locked pipeline'))
    with RefreshState(tmp_path).locked():
        assert refresh.main(['--source','nflverse-release','--dry-run','--state-dir',str(tmp_path)])==3


class GoodSettings:
    db_host='db';db_name='nfl_research_dev';db_user='nfl_ingest';db_purpose='runtime'


def test_status_reads_existing_success_times_without_exposing_tokens(tmp_path,monkeypatch):
    original=module.read_json
    checkpoint={'last_successful_check_at':'2026-11-09T13:00:00+00:00','review_token':'PRIVATE_TOKEN',
                'last_successful_ingestion_at':'2026-11-08T13:00:00+00:00'}
    def reader(path):
        if str(path)=='/app/refresh-state/status.json':return checkpoint
        return original(path)
    monkeypatch.setattr(module,'read_json',reader)
    info=status(tmp_path,utc('2026-11-11T13:00:00Z'))
    assert info['pipelines']['schedule']['successful_check_stale'] is True
    assert info['pipelines']['schedule']['checkpoint_observations']['last_successful_ingestion_at']=='2026-11-08T13:00:00+00:00'
    assert 'PRIVATE_TOKEN' not in json.dumps(info)


def test_durable_claim_exists_before_worker_submission(tmp_path):
    class InspectPool:
        def submit(self,function,job):
            assert (tmp_path/'claims'/(job['slot']+'-'+job['pipeline']+'.json')).exists()
            assert read_json(tmp_path/'jobs'/(job['job_id']+'.json'))['phase']=='running'
            return Future()
    Scheduler(Config(),tmp_path).tick(utc('2026-11-11T13:00:00Z'),InspectPool())


def test_singleton_lock_blocks_another_process(tmp_path):
    import os,subprocess
    script='''from pathlib import Path
import sys
from ingestion.refresh_state import RefreshState
try:
    with RefreshState(Path(sys.argv[1])).locked():
        raise SystemExit("unexpected concurrent scheduler")
except BlockingIOError:
    print("busy")
'''
    with RefreshState(tmp_path).locked():
        child=subprocess.run([sys.executable,'-c',script,str(tmp_path)],capture_output=True,text=True,
            timeout=5,env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1])})
    assert child.returncode==0 and child.stdout.strip()=='busy'


def test_concurrent_publication_keeps_latest_attempt(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    scheduler=Scheduler(Config(),tmp_path)
    jobs=[dict(job_id=str(uuid4()),pipeline='schedule',started_at=f'2026-11-11T13:00:{i:02d}+00:00',outcome='synthetic') for i in range(12)]
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(scheduler.publish,reversed(jobs)))
    assert read_json(tmp_path/'latest'/'schedule.json')['job_id']==jobs[-1]['job_id']
