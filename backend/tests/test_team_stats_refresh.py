"""Synthetic prepare-only refresh checks. No real downloads or development writes."""
import json
from contextlib import nullcontext
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import select,func,text
from sqlalchemy.orm import Session

from ingestion.team_stats import refresh as runner
from ingestion.team_stats.candidate import load_candidate,StatsRejected
from ingestion.team_stats.source import describe,AcquisitionError
from ingestion.refresh_state import RefreshState,read_json
from test_team_stats_ingestion import files,make_files,fake_state,db_candidate,approved_import
from test_ingestion import source_rows


def provider(files):
    report=json.loads(files['audit_path'].read_bytes())
    def acquire(year):
        data=(files['artifact_dir']/(report['seasons'][str(year)]['sha256']+'.csv')).read_bytes()
        # Synthetic bytes presented through the real official-download receipt contract.
        receipt=describe(data,year,'official_download')
        receipt['retrieved_at']=receipt['captured_at']
        return data,receipt
    return acquire


class FakeSession:
    def __init__(self):self.execute=Mock()
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def begin(self):return nullcontext()


@pytest.fixture
def offline(files,monkeypatch):
    candidate=load_candidate(**files)
    state=fake_state(candidate)
    state.update(artifacts={})
    monkeypatch.setattr(runner,'inspect',lambda _:state)
    monkeypatch.setattr(runner,'inspect_import_time',lambda _ : None)
    return state,files,candidate


def run(files,root,acquire=None,session_factory=FakeSession,clock=None):
    return runner.prepare_refresh(session_factory,root,files['schedule_path'],files['identity_path'],
        files['references_path'],acquire=acquire or provider(files),clock=clock)


def test_new_arrivals_prepare_real_admission_no_apply(offline,tmp_path):
    state,files,candidate=offline
    report,path=run(files,tmp_path/'refresh')
    assert report['outcome']=='review_required' and report['database_writes'] is False
    assert report['counts']==dict(new_pairs=842,corrected_pairs=0,unchanged_pairs=0,missing_pairs=0,selected_pairs=842,team_rows=1684)
    assert len(report['classifications']['newly_available_pairs'])==842
    assert report['plan']['review_token'] not in json.dumps(read_json(path.parent.parent/'status.json'))
    assert path.stat().st_mode & 0o777 == 0o600
    actual=load_candidate(Path(report['handoff']['audit']),Path(report['handoff']['artifact_dir']),
        Path(report['handoff']['schedule']),Path(report['handoff']['identity_map']),Path(report['handoff']['references']))
    assert len(actual.pairs)==842 and actual.evidence['receipts']['2024']['method']=='official_download'
    assert actual.evidence['receipts']['2024']['independently_authenticated'] is False
    assert actual.evidence['definition']=='net_pass_negative_sacks_v1'


def test_unchanged_refresh_revalidates_and_is_idempotent(offline,tmp_path,monkeypatch):
    state,files,c=offline
    # plan classification is real; synthetic acceptance baseline mimics matching immutable hashes.
    for pair in c.pairs:
        identifier=str(uuid4());artifact_id=uuid4()
        state['selections'][pair['game_id']]=SimpleNamespace(pair_id=identifier)
        state['pairs'][identifier]=SimpleNamespace(id=identifier,content_sha256=pair['content_sha256'],source_artifact_id=artifact_id)
        state['artifacts'][str(artifact_id)]=SimpleNamespace(sha256='a'*64)
    root=tmp_path/'refresh'
    first,_=run(files,root);second,_=run(files,root)
    assert first['outcome']==second['outcome']=='unchanged'
    assert second['counts']['new_pairs']==second['counts']['corrected_pairs']==0
    assert second['counts']['unchanged_pairs']==842
    assert all(not item['changed_since_previous_check'] for item in second['acquisitions'].values())
    assert len(list((root/'runs').glob('*.json')))==2
    assert read_json(root/'status.json')['last_successfully_applied_import_at'] is None


def test_network_failure_stops_remaining_sources_preserves_last_validation(offline,tmp_path):
    _,files,_=offline;root=tmp_path/'refresh';run(files,root)
    before=read_json(root/'status.json')
    calls=[]
    def fail(year):calls.append(year);raise AcquisitionError('network_failure')
    report,_=run(files,root,fail)
    assert report['outcome']=='source_failed' and calls==[2024]
    assert report['counts'] is None and report['failed_source_season']==2024
    after=read_json(root/'status.json')
    assert after['last_successful_validation_at']==before['last_successful_validation_at']
    assert after['observed_hashes']==before['observed_hashes']


@pytest.mark.parametrize('bad',['digest','receipt','partial','headers','sign'])
def test_bad_source_cannot_produce_handoff(offline,tmp_path,bad):
    _,files,_=offline;original=provider(files)
    def acquire(year):
        data,receipt=original(year)
        if year==2026:
            if bad=='digest':receipt['sha256']='0'*64
            elif bad=='receipt':receipt['source_url']='https://unapproved.invalid'
            elif bad=='partial':data=b'game_id,season\n';receipt=describe(data,year,'official_download');receipt['retrieved_at']=receipt['captured_at']
            elif bad=='headers':data=b'invalid,headers\n1,2\n';receipt=describe(data,year,'official_download');receipt['retrieved_at']=receipt['captured_at']
            else:data=data.replace(b',-10,',b',10,');receipt=describe(data,year,'official_download');receipt['retrieved_at']=receipt['captured_at']
        return data,receipt
    report,_=run(files,tmp_path/bad,acquire)
    assert report['outcome']=='validation_failed'
    assert 'handoff' not in report and report['database_writes'] is False


def test_invalid_input_and_checkpoint_fail_closed(offline,tmp_path):
    _,files,_=offline;root=tmp_path/'refresh'
    root.mkdir();(root/'status.json').write_text('{}')
    with pytest.raises(StatsRejected,match='invalid_refresh_checkpoint'):run(files,root)
    assert (root/'status.json').read_text()=='{}'


def test_single_runner_lock(offline,tmp_path):
    _,files,_=offline;root=tmp_path/'refresh'
    with RefreshState(root).locked():
        with pytest.raises(BlockingIOError):run(files,root)


def test_no_apply_flag_and_restricted_cli_guard(tmp_path,monkeypatch,capsys):
    from ingestion.team_stats.refresh import main
    args=['--source','nflverse-weekly','--schedule','s','--identity-map','i','--references','r']
    with pytest.raises(SystemExit):main([*args,'--apply'])
    monkeypatch.setattr(runner,'Settings',lambda:SimpleNamespace(db_host='db',db_name='nfl_research_dev',db_user='admin',db_purpose='migration'))
    monkeypatch.setattr(runner,'make_engine',lambda _:pytest.fail('must not connect'))
    assert main(args)==3
    assert 'configuration_checkpoint_or_lock_failure' in capsys.readouterr().out


@pytest.mark.database
def test_postgresql_refresh_never_changes_accepted_statistics_or_schedule(db_candidate,tmp_path):
    from app.models import Game,TeamStatsAccepted,TeamStatsPair,TeamGameStatRevision,TeamStatsBatch
    s,c,a,files,rows,identities=db_candidate
    assert s.scalar(text('SELECT session_user'))=='nfl_ingest'
    approved_import(db_candidate)
    before={model.__tablename__:s.scalar(select(func.count()).select_from(model)) for model in
        (Game,TeamStatsAccepted,TeamStatsPair,TeamGameStatRevision,TeamStatsBatch)}
    from app.repositories.team_rankings import TeamRankingsRepository
    from app.services.team_rankings import TeamRankingsService
    from app.schemas.team_rankings import RankingFilters
    rankings_before=TeamRankingsService(TeamRankingsRepository(s)).rankings(RankingFilters(season=2024)).model_dump()
    scores=list(s.execute(select(Game.id,Game.status,Game.reported_home_score,Game.reported_away_score).order_by(Game.id)))
    factory=lambda:Session(bind=s.connection(),join_transaction_mode='create_savepoint')
    first,_=run(files,tmp_path/'refresh',session_factory=factory)
    second,_=run(files,tmp_path/'refresh',session_factory=factory)
    assert first['outcome']==second['outcome']=='unchanged'
    assert second['last_successfully_applied_import_at'] is not None
    assert before=={model.__tablename__:s.scalar(select(func.count()).select_from(model)) for model in
        (Game,TeamStatsAccepted,TeamStatsPair,TeamGameStatRevision,TeamStatsBatch)}
    assert scores==list(s.execute(select(Game.id,Game.status,Game.reported_home_score,Game.reported_away_score).order_by(Game.id)))
    # A correction is only prepared; existing selection remains unchanged.
    def correction(year,records):
        if year==2024:records[4]['passing_yards']='201'
    changed=make_files(tmp_path/'changed',rows,identities,correction)
    result,_=run(changed,tmp_path/'correction',session_factory=factory)
    assert result['outcome']=='review_required' and result['counts']['corrected_pairs']==1
    assert len(result['classifications']['historical_corrections'])==1
    assert s.scalar(select(func.count()).select_from(TeamStatsPair))==before['team_stats_pairs']
    handoff=result['handoff']
    c=load_candidate(Path(handoff['audit']),Path(handoff['artifact_dir']),Path(handoff['schedule']),Path(handoff['identity_map']),Path(handoff['references']))
    from ingestion.team_stats.storage import apply_import
    with pytest.raises(StatsRejected,match='review_required_or_stale'),s.begin_nested():
        apply_import(s,c,result['archives'],'not-an-approved-token')
    assert TeamRankingsService(TeamRankingsRepository(s)).rankings(RankingFilters(season=2024)).model_dump()==rankings_before


def accept_fake(state,candidate,excluded=()):
    for pair in candidate.pairs:
        if pair['game_id'] in excluded:continue
        identifier=str(uuid4());artifact=uuid4()
        state['selections'][pair['game_id']]=SimpleNamespace(pair_id=identifier)
        state['pairs'][identifier]=SimpleNamespace(id=identifier,content_sha256=pair['content_sha256'],source_artifact_id=artifact)
        state['artifacts'][str(artifact)]=SimpleNamespace(sha256=candidate.evidence['receipts'][str(pair['season'])]['sha256'])
        state['rows'][identifier]=[SimpleNamespace(team_id=team['team_id'],raw_source_record=team['raw'],**team['values']) for team in pair['teams']]


def test_single_new_pair_among_existing_pairs_needs_review(offline,tmp_path):
    state,files,c=offline
    accept_fake(state,c,excluded=[c.pairs[-1]['game_id']])
    report,_=run(files,tmp_path/'refresh')
    assert report['outcome']=='review_required'
    assert report['counts']['new_pairs']==1 and report['counts']['unchanged_pairs']==841
    assert not report['automatic_acceptance_enabled']


def changed_provider(files,callback):
    import csv,io
    from test_ingestion import encode
    original=provider(files)
    def acquire(year):
        data,_=original(year)
        rows=list(csv.DictReader(io.StringIO(data.decode())))
        rows=callback(year,rows)
        data=encode(rows)
        receipt=describe(data,year,'official_download');receipt['retrieved_at']=receipt['captured_at']
        return data,receipt
    return acquire


def test_historical_correction_retains_full_before_after_and_requires_review(offline,tmp_path):
    state,files,c=offline;accept_fake(state,c)
    original={path.name:path.read_bytes() for path in files['artifact_dir'].glob('*.csv')}
    def change(year,rows):
        if year==2024:rows[4]['passing_yards']='201'
        return rows
    report,_=run(files,tmp_path/'refresh',changed_provider(files,change))
    assert report['outcome']=='review_required' and report['counts']['corrected_pairs']==1
    correction=report['classifications']['historical_corrections'][0]
    assert correction['before'][0]['net_passing_yards'] in (190,191)
    assert any(row['net_passing_yards']==191 for row in correction['after'])
    assert correction['raw_changes'] and correction['before_pair_id']
    assert all(path.read_bytes()==original[path.name] for path in files['artifact_dir'].glob('*.csv'))


@pytest.mark.parametrize('year',[2024,2026])
def test_missing_accepted_games_rejects_without_publication(offline,tmp_path,year):
    state,files,c=offline;accept_fake(state,c)
    target=next(pair for pair in reversed(c.pairs) if pair['season']==year)
    def remove(season,rows):
        return [row for row in rows if not(season==year and row['game_id']==target['source_game_id'])]
    report,_=run(files,tmp_path/'refresh',changed_provider(files,remove))
    assert report['outcome']==('validation_failed' if year==2024 else 'blocked')
    assert any(item['game_id']==target['game_id'] for item in report['missing_previously_accepted'])
    assert 'handoff' not in report
    assert report['diagnostic_counts']['missing_or_unusable_accepted_pairs']==1
    assert read_json(tmp_path/'refresh'/'status.json')['last_successful_validation_at'] is None


def test_stale_metadata_and_last_import_are_observations_not_check_time(offline,tmp_path,monkeypatch):
    _,files,_=offline;root=tmp_path/'refresh'
    old='2026-01-01T00:00:00+00:00';new='2026-01-03T00:00:00+00:00'
    monkeypatch.setattr(runner,'inspect_import_time',lambda _:old)
    run(files,root,clock=lambda:old)
    def fail(year):raise AcquisitionError('http_503')
    report,_=run(files,root,fail,clock=lambda:new)
    state=read_json(root/'status.json')
    assert state['last_successful_validation_at']==state['last_successfully_applied_import_at']==old
    assert state['last_refresh_check_at']==new and state['validation_stale']
    assert state['latest_counts'] is None and 'no_recent_successful_validation' in state['latest_warnings']


def test_admitted_handoff_retains_existing_approval_and_archive_checks(offline,tmp_path):
    from ingestion.team_stats.storage import apply_import
    _,files,_=offline;report,_=run(files,tmp_path/'refresh')
    handoff=report['handoff']
    c=load_candidate(Path(handoff['audit']),Path(handoff['artifact_dir']),Path(handoff['schedule']),
                     Path(handoff['identity_map']),Path(handoff['references']))
    Path(report['archives']['2026.csv']).write_bytes(b'synthetic alteration')
    session=SimpleNamespace(new=(),dirty=(),deleted=())
    with pytest.raises(StatsRejected):apply_import(session,c,report['archives'],report['plan']['review_token'])


@pytest.fixture
def db_session(restricted_db_session):
    """All new database refresh cases use an actual restricted ingestion login."""
    yield restricted_db_session


def test_cli_output_never_prints_approval_or_private_evidence(monkeypatch,capsys,tmp_path):
    monkeypatch.setattr(runner,'Settings',lambda:SimpleNamespace(db_host='db',db_name='nfl_research_dev',db_user='nfl_ingest',db_purpose='runtime'))
    engine=Mock();monkeypatch.setattr(runner,'make_engine',lambda _:engine)
    report=dict(outcome='review_required',counts={'new_pairs':1},plan={'review_token':'SYNTHETIC_APPROVAL_SECRET'},
                private_evidence='SYNTHETIC_PRIVATE_EVIDENCE')
    monkeypatch.setattr(runner,'prepare_refresh',lambda *a,**k:(report,tmp_path/'report.json'))
    result=runner.main(['--source','nflverse-weekly','--schedule','s','--identity-map','i','--references','r'])
    assert result==0
    output=capsys.readouterr().out
    assert 'SYNTHETIC' not in output and set(json.loads(output))=={'outcome','report','counts'}
    engine.dispose.assert_called_once()


def test_input_checkpoint_collision_rejected_before_writing(offline,tmp_path):
    _,files,_=offline;root=tmp_path/'refresh';root.mkdir()
    status=root/'status.json';status.write_text('{"marker":"original synthetic input"}')
    with pytest.raises(StatsRejected,match='input_state_path_collision'):
        runner.prepare_refresh(FakeSession,root,status,files['identity_path'],files['references_path'],acquire=provider(files))
    assert status.read_text()=='{"marker":"original synthetic input"}'


def test_invalid_reference_input_fails_before_network(offline,tmp_path):
    _,files,_=offline
    bad=tmp_path/'invalid-reference.json';bad.write_text('{}')
    def forbidden(_):pytest.fail('invalid inputs must not trigger downloads')
    report,_=runner.prepare_refresh(FakeSession,tmp_path/'refresh',files['schedule_path'],
        files['identity_path'],bad,acquire=forbidden)
    assert report['outcome']=='validation_failed' and report['error']=='reference_input_invalid'
    assert report['phase']=='input_validation' and not report['acquisitions']


def test_database_transaction_end_failure_does_not_claim_valid_handoff(offline,tmp_path):
    from contextlib import contextmanager
    from sqlalchemy.exc import OperationalError
    _,files,_=offline
    class BrokenSession(FakeSession):
        @contextmanager
        def begin(self):
            yield
            raise OperationalError('SYNTHETIC_PRIVATE_SQL',{},Exception('SYNTHETIC_PRIVATE_DETAILS'))
    report,_=run(files,tmp_path/'refresh',session_factory=BrokenSession)
    assert report['outcome']=='database_failed' and report['counts'] is None
    assert 'handoff' not in report and 'validation_passed_at' not in report
    assert 'SYNTHETIC_PRIVATE' not in json.dumps(report)
    assert read_json(tmp_path/'refresh'/'status.json')['last_successful_validation_at'] is None


def test_publisher_evidence_and_partial_acquisition_remain_distinct(offline,tmp_path):
    _,files,_=offline;original=provider(files)
    def evidence(year):
        data,receipt=original(year)
        receipt['publisher_metadata']=dict(id=year,size=len(data),digest='sha256:'+receipt['sha256'],
            updated_at='2026-01-01T00:00:00+00:00',browser_download_url=receipt['source_url'])
        receipt['integrity']='publisher_digest_matched'
        return data,receipt
    report,_=run(files,tmp_path/'good',evidence)
    state=read_json(tmp_path/'good'/'status.json')
    assert state['source_observations']['2024']['publisher_asset_updated_at']=='2026-01-01T00:00:00+00:00'
    assert state['source_observations']['2024']['retrieved_at']!='2026-01-01T00:00:00+00:00'
    assert len(list((tmp_path/'good'/'acquisitions').glob('*.json')))==3
    def partial(year):
        if year==2026:raise AcquisitionError('http_404')
        return evidence(year)
    failed,_=run(files,tmp_path/'partial',partial)
    assert failed['outcome']=='source_failed' and failed['failed_source_season']==2026
    assert len(list((tmp_path/'partial'/'acquisitions').glob('*.json')))==2
    assert read_json(tmp_path/'partial'/'status.json').get('last_successful_source_check_at') is None


def test_refresh_cannot_relabel_operator_files_as_official_checks(offline,tmp_path):
    _,files,_=offline;original=provider(files)
    def local(year):
        data,_=original(year)
        return data,describe(data,year,'operator_local_file')
    report,_=run(files,tmp_path/'refresh',local)
    assert report['outcome']=='validation_failed' and report['error']=='refresh_requires_official_acquisition'
    assert 'handoff' not in report and report['counts'] is None
