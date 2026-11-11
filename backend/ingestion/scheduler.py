"""Opt-in local daily scheduler: fixed prepare-only commands, no queue or publication path."""
import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from ingestion.refresh_state import RefreshState, read_json, write_json

ROOT = Path('/app/refresh-state/scheduler')
PIPELINES = ('schedule', 'team_stats')
POLL_SECONDS = 15
HEALTH_SECONDS = 90
MAX_OUTPUT = 2 * 1024 * 1024


def utcnow():
    return datetime.now(timezone.utc)


def stamp(value):
    """Accept timestamps only; never echo arbitrary child strings into operator logs."""
    try:
        if isinstance(value,str) and len(value)<=64 and datetime.fromisoformat(value.replace('Z','+00:00')).utcoffset() is not None:
            return value
    except ValueError:
        pass
    return None


@dataclass(frozen=True)
class Config:
    times: tuple[str,...] = ('06:00','18:00')
    zone: str = 'America/Phoenix'
    schedule: str = '/data/raw/games.csv'
    identities: str = '/data/raw/team-stats-identities.json'
    references: str = '/review/docs/team-stats-gamebook-references.json'
    timeout: int = 1200

    def __post_init__(self):
        if (not self.times or len(set(self.times))!=len(self.times)
                or any(not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', t) for t in self.times)):
            raise ValueError('invalid_daily_times')
        ZoneInfo(self.zone)  # Never silently use UTC when the requested IANA database is missing.
        if not 60 <= self.timeout <= 7200:
            raise ValueError('invalid_job_timeout')

    @classmethod
    def environment(cls):
        return cls(times=tuple(s.strip() for s in os.getenv('SCHEDULER_TIMES','06:00,18:00').split(',')),
                   zone=os.getenv('SCHEDULER_TIMEZONE','America/Phoenix'),
                   schedule=os.getenv('SCHEDULER_STATS_SCHEDULE','/data/raw/games.csv'),
                   identities=os.getenv('SCHEDULER_STATS_IDENTITIES','/data/raw/team-stats-identities.json'),
                   references=os.getenv('SCHEDULER_STATS_REFERENCES','/review/docs/team-stats-gamebook-references.json'),
                   timeout=int(os.getenv('SCHEDULER_JOB_TIMEOUT_SECONDS','1200')))


def local_slot(now, config):
    if now.utcoffset() is None:
        raise ValueError('aware_clock_required')
    local = now.astimezone(ZoneInfo(config.zone))
    clock = local.strftime('%H:%M')
    if clock not in config.times:
        return None
    zone_key=hashlib.sha256(config.zone.encode()).hexdigest()[:12]
    # Same key in both folds: at most one occurrence per configured local day/time.
    return f'{local:%Y%m%d}-{clock.replace(":","")}-{zone_key}'


def command(pipeline, config):
    if pipeline == 'schedule':
        return [sys.executable,'-m','ingestion.refresh','--source','nflverse-release','--dry-run']
    if pipeline == 'team_stats':
        if any(not Path(p).is_absolute() for p in (config.schedule,config.identities,config.references)):
            raise ValueError('absolute_input_paths_required')
        return [sys.executable,'-m','ingestion.team_stats.refresh','--source','nflverse-weekly',
                '--schedule='+config.schedule,'--identity-map='+config.identities,
                '--references='+config.references,'--dry-run']
    raise ValueError('unknown_pipeline')


class ChildStopped(Exception):
    pass


def execute_child(argv, timeout, stop):
    """Discard raw stderr; capture stdout privately and boundedly, never stream review tokens."""
    with tempfile.TemporaryFile() as output:
        process=subprocess.Popen(argv,stdout=output,stderr=subprocess.DEVNULL,start_new_session=True,
                                 stdin=subprocess.DEVNULL,close_fds=True)
        started=time.monotonic()
        reason=None
        try:
            while process.poll() is None:
                if stop.is_set():
                    reason='interrupted'
                    break
                if time.monotonic()-started >= timeout:
                    reason='timed_out'
                    break
                stop.wait(.2)
        finally:
            if process.poll() is None:
                try:os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    process.wait()
        if reason:
            raise ChildStopped(reason)
        output.seek(0)
        data=output.read(MAX_OUTPUT+1)
        if len(data)>MAX_OUTPUT:
            raise ValueError('child_output_too_large')
        return process.returncode,json.loads(data)


def checkpoint_observations(pipeline):
    path=Path('/app/refresh-state/status.json') if pipeline=='schedule' else Path('/app/snapshots/team-stats-refresh/status.json')
    try:
        checkpoint=read_json(path)
        keys=('last_successful_check_at','last_successful_ingestion_at','last_data_change_observed_at') if pipeline=='schedule' else (
            'last_successful_source_check_at','last_successful_validation_at','last_successfully_applied_import_at','import_timestamp_observed_at')
        return dict(metadata_state='available',**{key:stamp(checkpoint.get(key)) for key in keys})
    except (OSError,ValueError,TypeError,RecursionError):
        return {'metadata_state':'unavailable'}


def summarize_child(pipeline, code, output):
    """Read only the expected private pipeline report; never copy its token/evidence into logs."""
    if not isinstance(output,dict):
        raise ValueError('invalid_child_output')
    success = ('dry_run',) if pipeline=='schedule' else ('review_required','unchanged')
    outcome=output.get('outcome')
    allowed=success+('rejected','validation_failed','download_failed','source_failed','database_failed','blocked','failed')
    if outcome not in allowed:
        raise ValueError('unexpected_child_outcome')
    if pipeline=='schedule':
        identifier=str(UUID(output['run_id']))
        report_path=Path('/app/refresh-state/runs')/(identifier+'.json')
    else:
        supplied=Path(output['report'])
        identifier=str(UUID(supplied.stem))
        report_path=Path('/app/snapshots/team-stats-refresh/runs')/(identifier+'.json')
        if supplied!=report_path:
            raise ValueError('unexpected_report_path')
    report=read_json(report_path)
    if report.get('run_id')!=identifier or report.get('outcome')!=outcome:
        raise ValueError('inconsistent_pipeline_report')
    completed=stamp(report.get('completed_at'))
    if completed is None:
        raise ValueError('incomplete_pipeline_report')
    plan=report.get('plan') or {}
    blockers=plan.get('blockers',[])
    ok=code==0 and outcome in success and not blockers
    result=dict(outcome=outcome if ok else 'pipeline_failed', pipeline_outcome=outcome,
                successful_check=ok, review_required=ok and bool(plan.get('changes')),
                blocker_count=len(blockers), pipeline_report=str(report_path),
                pipeline_completed_at=completed)
    # These observations come from the actual runner, never the scheduler clock.
    if pipeline=='schedule':
        acquisition=report.get('acquisition') or {}
        result['source_observations']={'schedule':dict(retrieved_at=stamp(acquisition.get('retrieved_at')),
            publisher_asset_updated_at=stamp((acquisition.get('metadata') or {}).get('asset_updated_at')))}
    else:
        result['source_observations']={year:dict(retrieved_at=stamp((item.get('receipt') or {}).get('retrieved_at')),
            publisher_asset_updated_at=stamp(((item.get('receipt') or {}).get('publisher_metadata') or {}).get('updated_at')))
            for year,item in report.get('acquisitions',{}).items() if year in ('2024','2025','2026')}
        result['last_successful_validation_at']=stamp((report.get('freshness') or {}).get('last_successful_validation_at'))
    result['checkpoint_observations']=checkpoint_observations(pipeline)
    return result


class Scheduler:
    def __init__(self, config, root=ROOT, *, execute=execute_child, clock=utcnow):
        self.config=config
        self.root=Path(root)
        self.execute=execute
        self.clock=clock
        self.stop=threading.Event()
        self.active={}
        self._publish_lock=threading.Lock()

    def publish(self, job):
        with self._publish_lock:
            write_json(self.root/'jobs'/(job['job_id']+'.json'),job)
            latest=self.root/'latest'/(job['pipeline']+'.json')
            previous=read_json(latest) if latest.exists() else None
            if previous is None or previous.get('job_id')==job['job_id'] or previous['started_at']<=job['started_at']:
                write_json(latest,job)

    def recover_observations(self):
        """Claims are at-most-once, not a replay queue. Lost workers remain unconfirmed."""
        for path in sorted((self.root/'claims').glob('*.json')):
            claim=read_json(path)
            identifier=str(UUID(claim['job_id']))
            pipeline=claim['pipeline']
            if pipeline not in PIPELINES:
                raise ValueError('invalid_claim')
            job_path=self.root/'jobs'/(identifier+'.json')
            job=read_json(job_path) if job_path.exists() else dict(claim,phase='running')
            if job.get('phase')!='complete':
                job.update(phase='complete',outcome='interrupted_unconfirmed',successful_check=False,
                           review_required=False,finished_at=self.clock().isoformat())
                self.publish(job)

    def work(self, job):
        try:
            code,output=self.execute(command(job['pipeline'],self.config),self.config.timeout,self.stop)
            job['exit_code']=code
            job.update(**summarize_child(job['pipeline'],code,output))
        except ChildStopped as exc:
            job.update(outcome='timed_out' if str(exc)=='timed_out' else 'interrupted_unconfirmed',
                       successful_check=False,review_required=False)
        except Exception:
            # Never persist exception repr, stderr, child stdout, environment or approval secrets.
            job.update(outcome='runner_or_report_failed',successful_check=False,review_required=False)
        job.update(phase='complete',finished_at=self.clock().isoformat())
        self.publish(job)
        print(json.dumps({k:job[k] for k in ('pipeline','outcome','finished_at','review_required')}),flush=True)
        return job

    def tick(self, now, pool, *, manual=False):
        for pipeline,future in list(self.active.items()):
            if future.done():
                future.result()  # Persistence failure must stop heartbeat, not silently claim completion.
                del self.active[pipeline]
        slot='manual-'+str(uuid4()) if manual else local_slot(now,self.config)
        if slot is None:return
        for pipeline in PIPELINES:
            claim_path=self.root/'claims'/(slot+'-'+pipeline+'.json')
            if claim_path.exists():continue
            job=dict(job_id=str(uuid4()),pipeline=pipeline,slot=slot,phase='running',
                     started_at=now.isoformat(),successful_check=False,review_required=False)
            write_json(claim_path,job,replace=False)
            if pipeline in self.active:
                job.update(phase='complete',finished_at=now.isoformat(),outcome='skipped_busy')
                self.publish(job)
                continue
            self.publish(job)
            self.active[pipeline]=pool.submit(self.work,job)

    def run(self, *, once=False):
        # This singleton lock is separate from, and never replaces, the child runner/manual locks.
        with RefreshState(self.root).locked():
            self.recover_observations()
            pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='nfl-prepare')
            try:
                if once:
                    self.tick(self.clock(),pool,manual=True)
                    for future in self.active.values():future.result()
                else:
                    while not self.stop.is_set():
                        self.tick(self.clock(),pool)
                        write_json(self.root/'daemon.json',dict(phase='running',heartbeat_at=self.clock().isoformat(),
                            timezone=self.config.zone,times=list(self.config.times),prepare_only=True))
                        self.stop.wait(POLL_SECONDS)
            finally:
                self.stop.set()
                pool.shutdown(wait=True,cancel_futures=False)
                write_json(self.root/'daemon.json',dict(phase='stopped',heartbeat_at=self.clock().isoformat(),prepare_only=True))


def status(root=ROOT, now=None):
    root=Path(root);now=now or utcnow()
    result=dict(prepare_only=True,daemon=None,pipelines={})
    if (root/'daemon.json').exists():
        daemon=read_json(root/'daemon.json')
        result['daemon']={key:daemon[key] for key in ('phase','heartbeat_at','timezone','times','prepare_only') if key in daemon}
    for pipeline in PIPELINES:
        path=root/'latest'/(pipeline+'.json')
        job=read_json(path) if path.exists() else None
        # Explicit projection: unexpected future fields must not become operator log output.
        keys=('job_id','phase','outcome','pipeline_outcome','exit_code','started_at','finished_at','review_required',
              'successful_check','blocker_count','pipeline_report','source_observations','last_successful_validation_at','checkpoint_observations')
        projected={key:job[key] for key in keys if key in job} if job else {'outcome':'not_run'}
        observations=checkpoint_observations(pipeline)
        projected['checkpoint_observations']=observations
        check_key='last_successful_check_at' if pipeline=='schedule' else 'last_successful_validation_at'
        check=observations.get(check_key)
        check_age=(now-datetime.fromisoformat(check.replace('Z','+00:00'))).total_seconds() if check else None
        projected['successful_check_age_seconds']=check_age if check_age is not None and check_age>=0 else None
        projected['successful_check_stale']=check_age>36*3600 if check_age is not None and check_age>=0 else None
        result['pipelines'][pipeline]=projected
    heartbeat=stamp((result['daemon'] or {}).get('heartbeat_at'))
    age=(now-datetime.fromisoformat(heartbeat.replace('Z','+00:00'))).total_seconds() if heartbeat else None
    result['daemon_healthy']=bool((result['daemon'] or {}).get('phase')=='running' and age is not None and 0<=age<=HEALTH_SECONDS)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--once',action='store_true',help='One manual preparation per pipeline; no queued retries')
    modes.add_argument('--status',action='store_true',help='Read sanitized operational state without running jobs')
    modes.add_argument('--health',action='store_true',help='Check daemon heartbeat, not source/data health')
    args=parser.parse_args(argv)
    try:
        if args.status or args.health:
            info=status()
            if args.status:print(json.dumps(info,sort_keys=True))
            return 0 if args.status or info['daemon_healthy'] else 1
        # Same existing restricted development credentials; no admin or DB state changes at startup.
        from app.core.config import Settings
        settings=Settings()
        if not(settings.db_host=='db' and settings.db_name=='nfl_research_dev'
               and settings.db_user=='nfl_ingest' and settings.db_purpose=='runtime'):
            raise ValueError('restricted_development_configuration_required')
        scheduler=Scheduler(Config.environment())
        for signum in (signal.SIGTERM,signal.SIGINT):
            signal.signal(signum,lambda *_:scheduler.stop.set())
        scheduler.run(once=args.once)
        if args.once:
            jobs=[future.result() for future in scheduler.active.values()]
            return 0 if all(job.get('successful_check') for job in jobs) else 2
        return 0
    except Exception:
        print(json.dumps({'error':'scheduler_stopped','hint':'Inspect private scheduler/runner state, configuration and locks; no automatic safety override.'}),file=sys.stderr)
        return 3


if __name__=='__main__':
    raise SystemExit(main())
