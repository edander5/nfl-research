"""Synthetic transports and in-memory schedules. No public source or database required."""
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4, uuid5, NAMESPACE_DNS

import pytest

from app.models import Game
from ingestion.refresh import candidate, main
from ingestion.refresh_policy import ReviewRejected, compare, guarded_apply
from ingestion.refresh_state import RefreshState, write_json
from ingestion.service import SOURCE_URL, capture
from ingestion.source import SourceConfig, SourceFailure, asset_metadata, check_url, get_bytes, retrieve
from ingestion.validation import validate_bytes
from test_ingestion import source_rows, encode, snapshot


@pytest.fixture
def baseline(source_rows):
    original = snapshot(source_rows)
    now = datetime(2026,11,7,tzinfo=timezone.utc)
    games = [Game(**r.values, id=uuid5(NAMESPACE_DNS,r.values['source_game_id']), provider='nflverse',
        home_team_id=UUID(int=1),away_team_id=UUID(int=2),source_artifact_id=UUID(int=3),
        source_record_sha256=r.sha256,raw_source_record=r.raw.copy(),source_line=r.line,
        status='UNKNOWN',recorded_at=now,updated_at=now) for r in original.rows]
    return original,games


def evidence(data):
    return dict(source='nflverse-release',source_url=SOURCE_URL,metadata_url=SourceConfig().metadata_url,
        sha256=hashlib.sha256(data).hexdigest(),byte_size=len(data),retrieved_at='2026-11-07T20:00:00+00:00',
        metadata=None,metadata_failure='network_failure',origin_status='DECLARED',digest_matches_publisher=False)


def metadata(data, **changes):
    asset=dict(id=123,name='games.csv',state='uploaded',browser_download_url=SOURCE_URL,size=len(data),
               digest='sha256:'+hashlib.sha256(data).hexdigest(),updated_at='2026-11-07T18:00:00Z')
    asset.update(changes)
    return json.dumps(dict(assets=[asset])).encode()


def row_2026(rows, scored=False):
    return next(r for r in rows if r['season']=='2026' and (r['home_score'] != '') == scored)


def test_successful_retrieval_and_complete_validation(source_rows):
    body=encode(source_rows)
    def fetch(url,**kwargs):
        return (metadata(body),{}) if url==SourceConfig().metadata_url else (body,{'Content-Type':'text/csv'})
    data,receipt=retrieve(SourceConfig(),fetch)
    assert len(validate_bytes(data).rows)==842
    assert receipt['sha256']==hashlib.sha256(body).hexdigest()
    assert receipt['digest_matches_publisher'] is True
    assert receipt['origin_status']=='DECLARED'
    assert datetime.fromisoformat(receipt['retrieved_at']).utcoffset() is not None
    assert receipt['source_url']==SOURCE_URL


def test_optional_metadata_failure_is_declared(source_rows):
    body=encode(source_rows)
    def fetch(url,**kwargs):
        if url==SourceConfig().metadata_url:
            raise SourceFailure('http_403')
        return body,{}
    _,receipt=retrieve(SourceConfig(),fetch)
    assert receipt['metadata'] is None and receipt['metadata_failure']=='http_403'
    assert receipt['origin_status']=='DECLARED' and not receipt['digest_matches_publisher']


@pytest.mark.parametrize('problem', ['digest','size','race','html'])
def test_integrity_failures_retain_complete_bytes(source_rows,problem):
    body=encode(source_rows)
    calls=0
    def fetch(url,**kwargs):
        nonlocal calls
        if url==SourceConfig().metadata_url:
            calls+=1
            return metadata(body,**({'digest':'sha256:'+'0'*64} if problem=='digest' else
                {'size':len(body)+1} if problem=='size' else
                {'id':456} if problem=='race' and calls==2 else {})),{}
        return body,{'Content-Type':'text/html' if problem=='html' else 'text/csv'}
    with pytest.raises(SourceFailure) as failure:
        retrieve(SourceConfig(),fetch)
    assert failure.value.data==body
    assert failure.value.evidence['integrity_error']


def test_network_failure():
    def fetch(*args,**kwargs):
        raise SourceFailure('network_failure')
    with pytest.raises(SourceFailure,match='network_failure'):
        retrieve(SourceConfig(),fetch)


@pytest.mark.parametrize('url',['http://github.com/file','https://example.invalid/file','https://user:password@github.com/file'])
def test_source_redirect_allowlist(url):
    with pytest.raises(SourceFailure):
        check_url(url)


@pytest.mark.parametrize('body,length,limit,code',[(b'abc','4',10,'truncated_download'),(b'abc',None,2,'download_too_large')])
def test_low_level_truncation_and_size(monkeypatch,body,length,limit,code):
    class Response(io.BytesIO):
        status=200
        url=SOURCE_URL
        headers={'Content-Length':length}
    opener=SimpleNamespace(open=lambda *args,**kwargs:Response(body))
    monkeypatch.setattr('ingestion.source.build_opener',lambda *args:opener)
    with pytest.raises(SourceFailure,match=code):
        get_bytes(SOURCE_URL,limit=limit,config=SourceConfig())


def test_invalid_metadata_rejected():
    with pytest.raises(SourceFailure):
        asset_metadata(b'{}')


def test_unchanged_plan_and_stable_token(baseline):
    original,games=baseline
    first=compare(original,games,evidence(original.data))
    assert first==compare(original,games,evidence(original.data))
    assert not first['changes'] and not first['blockers'] and not first['requires_review']


def test_new_scores_require_snapshot_specific_review(source_rows,baseline,monkeypatch):
    _,games=baseline
    row_2026(source_rows).update(home_score='20',away_score='17')
    new=snapshot(source_rows)
    receipt=evidence(new.data)
    plan=compare(new,games,receipt)
    assert plan['summary']['newly_reported_scores']==1 and plan['requires_review']
    assert not plan['blockers']
    with pytest.raises(ReviewRejected):
        guarded_apply(None,new,receipt,Path('/synthetic'),plan,None,'run','candidate')
    called=[]
    monkeypatch.setattr('ingestion.refresh_policy.reconcile',lambda *args,**kw:called.append(kw) or {'updated':1})
    guarded_apply(None,new,receipt,Path('/synthetic'),plan,plan['review_token'],'run','candidate')
    assert called[0]['acquisition']['operator_reviewed'] is True
    assert all(g.status=='UNKNOWN' for g in games)


def test_score_removal_cannot_be_approved(source_rows,baseline):
    _,games=baseline
    target=next(g for g in games if g.season==2026)
    target.reported_home_score=20; target.reported_away_score=17
    target.raw_source_record=dict(target.raw_source_record,home_score='20',away_score='17')
    from ingestion.validation import record_hash
    target.source_record_sha256=record_hash(target.raw_source_record)
    new=snapshot(source_rows);plan=compare(new,games,evidence(new.data))
    assert any(p['code']=='score_removal' for p in plan['blockers'])
    with pytest.raises(ReviewRejected):
        guarded_apply(None,new,evidence(new.data),Path('/synthetic'),plan,plan['review_token'],'run','candidate')


def test_historical_correction_and_final_block(source_rows,baseline):
    _,games=baseline
    source_rows[0]['home_score']='3'
    new=snapshot(source_rows);plan=compare(new,games,evidence(new.data))
    assert plan['summary']['corrected_scores']==1 and plan['summary']['historical_change']==1
    assert plan['requires_review'] and not plan['blockers']
    games[0].status='FINAL'
    assert any(p['code']=='final_record_change' for p in compare(new,games,evidence(new.data))['blockers'])


def test_disappearing_game_and_ambiguous_identity(source_rows,baseline):
    _,games=baseline
    row=source_rows[0]
    row['home_team'],row['away_team']=row['away_team'],row['home_team']
    row['game_id']=f"2024_01_{row['away_team']}_{row['home_team']}"
    row['espn']=''
    new=snapshot(source_rows)
    assert any(p['code']=='missing_game' for p in compare(new,games,evidence(new.data))['blockers'])
    row['espn']=games[0].external_ids['espn']
    new=snapshot(source_rows)
    duplicate={c.name:getattr(games[0],c.name) for c in Game.__table__.columns if c.name not in ('id','source_game_id')}
    games.append(Game(**duplicate,id=uuid4(),source_game_id='synthetic-ambiguous-existing'))
    assert any(p['code']=='ambiguous_identity' for p in compare(new,games,evidence(new.data))['blockers'])


def test_review_invalidated_by_baseline_change(source_rows,baseline):
    _,games=baseline
    row_2026(source_rows)['gametime']='14:00'
    new=snapshot(source_rows)
    token=compare(new,games,evidence(new.data))['review_token']
    games[0].status='FINAL'
    assert compare(new,games,evidence(new.data))['review_token']!=token


def test_candidate_archive_and_invalid_csv(tmp_path,source_rows):
    state=RefreshState(tmp_path/'state');folder=tmp_path/'archives';identifier=str(uuid4())
    body=encode(source_rows);receipt=evidence(body)
    capture(snapshot(source_rows),folder)
    write_json(state.path('candidates',identifier),{'acquisition':receipt},replace=False)
    new,recorded,_=candidate(state,identifier,folder)
    assert new.sha256==receipt['sha256'] and recorded['retrieved_at']==receipt['retrieved_at']
    (folder/f'{new.sha256}.csv').write_bytes(b'broken')
    with pytest.raises(ValueError,match='candidate_archive_changed'):
        candidate(state,identifier,folder)


def test_state_success_and_failure_timestamps(tmp_path):
    state=RefreshState(tmp_path)
    base=dict(run_id=str(uuid4()),started_at='start',completed_at='first',sha256='a'*64,outcome='applied',phase='complete')
    state.finish(base)
    state.finish(dict(base,run_id=str(uuid4()),completed_at='second',outcome='unchanged'))
    state.finish(dict(base,run_id=str(uuid4()),completed_at='third',outcome='failed'))
    status=state.status()
    assert status['last_data_change_observed_at']=='first'
    assert status['last_successful_ingestion_at']=='second'
    assert status['last_outcome']=='failed'


def test_runner_lock(tmp_path):
    state=RefreshState(tmp_path)
    with state.locked():
        with pytest.raises(BlockingIOError),state.locked():
            pass


def test_cli_development_guard(monkeypatch,capsys,tmp_path):
    monkeypatch.setenv('APP_DB_HOST','production.invalid')
    monkeypatch.setenv('APP_DB_NAME','production')
    monkeypatch.setenv('APP_DB_USER','synthetic')
    monkeypatch.setenv('APP_DB_PASSWORD','SYNTHETIC_ONLY')
    assert main(['--source','nflverse-release','--state-dir',str(tmp_path)])==3
    assert 'production.invalid' not in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('failure', ['network','invalid_csv','bad_digest'])
def test_failed_runs_archive_and_record_hashes_without_db(tmp_path,failure):
    from ingestion.refresh import execute
    state=RefreshState(tmp_path/'state')
    body=b'game_id,season\nbroken,2026\n'
    receipt=evidence(body)
    def download(config):
        if failure=='network':
            raise SourceFailure('network_failure')
        if failure=='bad_digest':
            raise SourceFailure('publisher_digest_mismatch',data=body,evidence=dict(receipt,integrity_error='publisher_digest_mismatch'))
        return body,receipt
    run=execute(None,state,tmp_path/'archives',SourceConfig(),download=download)
    assert run['outcome']==('validation_failed' if failure=='invalid_csv' else 'download_failed')
    assert 'last_successful_ingestion_at' not in state.status()
    if failure!='network':
        assert run['sha256']==hashlib.sha256(body).hexdigest()
        assert (tmp_path/'archives'/f"{run['sha256']}.csv").read_bytes()==body
        assert state.load('candidates',run['candidate_id'])['acquisition']['sha256']==run['sha256']


def test_ambiguous_commit_stops_further_runs(tmp_path,source_rows,monkeypatch):
    from contextlib import contextmanager
    from ingestion.refresh import execute
    body=encode(source_rows)
    state=RefreshState(tmp_path/'state')
    class FakeSession:
        def __init__(self,*args): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        @contextmanager
        def begin(self):
            yield
            raise RuntimeError('Synthetic lost commit acknowledgement')
    monkeypatch.setattr('ingestion.refresh.Session',FakeSession)
    monkeypatch.setattr('ingestion.refresh.inspect_database',lambda *args:dict(blockers=[],review_token='review'))
    monkeypatch.setattr('ingestion.refresh.guarded_apply',lambda *args:dict(inserted=0,updated=1,artifact_id=str(uuid4())))
    candidate_id=str(uuid4())
    capture(snapshot(source_rows),tmp_path/'archives')
    write_json(state.path('candidates',candidate_id),dict(acquisition=evidence(body)),replace=False)
    with pytest.raises(ValueError,match='indeterminate_commit'):
        execute(None,state,tmp_path/'archives',SourceConfig(),identifier=candidate_id,apply=True)
    pending=state.pending()
    assert len(pending)==1 and pending[0]['phase']=='commit_pending'
    with pytest.raises(ValueError,match='requires_recovery'):
        execute(None,state,tmp_path/'archives',SourceConfig(),download=lambda _:pytest.fail('must not download'))


@pytest.mark.parametrize('committed',[True,False])
def test_recovery_observes_receipt_or_confirms_no_commit(tmp_path,committed):
    from unittest.mock import Mock
    from ingestion.refresh import recover
    state=RefreshState(tmp_path)
    run=dict(run_id=str(uuid4()),started_at='before',sha256='a'*64,phase='commit_pending',outcome='running',
             result=dict(artifact_id=str(uuid4()),inserted=0,updated=1))
    state.save_run(run)
    session=Mock()
    session.execute.return_value.scalar_one.return_value='nfl_research_test'
    session.get.return_value=SimpleNamespace(provider='nflverse',sha256=run['sha256'],
        provenance_notes=json.dumps({'acquisition':{'run_id':run['run_id']}})) if committed else None
    recovered=recover(session,state,run['run_id'])
    assert recovered['outcome']==('applied' if committed else 'not_applied')
    assert not state.pending()
    assert any('pg_advisory_xact_lock' in str(call.args[0]) for call in session.execute.call_args_list)
    assert ('last_successful_ingestion_at' in state.status())==committed


def test_checkpoint_loss_fails_closed(tmp_path):
    state=RefreshState(tmp_path)
    run=dict(run_id=str(uuid4()),started_at='before',completed_at='after',sha256='a'*64,outcome='applied')
    state.finish(run)
    (tmp_path/'status.json').unlink()
    with pytest.raises(ValueError,match='missing_success_checkpoint'):
        state.status()


def test_kickoff_matchup_and_schema_changes_reported(source_rows,baseline):
    _,games=baseline
    row_2026(source_rows)['gametime']='14:00'
    new=snapshot(source_rows)
    assert compare(new,games,evidence(new.data))['summary']['kickoff_change']==1
    row=source_rows[0]
    row['home_team'],row['away_team']=row['away_team'],row['home_team']
    row['game_id']=f"2024_01_{row['away_team']}_{row['home_team']}"
    new=snapshot(source_rows);plan=compare(new,games,evidence(new.data))
    assert plan['summary']['identity_change']==1 and plan['summary']['matchup_change']==1
    for r in source_rows:
        r['new_unapproved_column']=''
    new=snapshot(source_rows)
    assert any(p['code']=='schema_drift' for p in compare(new,games,evidence(new.data))['blockers'])


def test_apply_cannot_download_in_one_step(tmp_path):
    from ingestion.refresh import execute
    state=RefreshState(tmp_path)
    with pytest.raises(ValueError,match='apply_requires_saved_candidate'):
        execute(None,state,tmp_path/'archives',SourceConfig(),apply=True,
                download=lambda _:pytest.fail('must not download'))


@pytest.mark.parametrize('field,value',[('sha256','0'*64),('origin_status','VERIFIED'),('source_url','https://example.invalid/mirror')])
def test_reconciliation_rejects_mismatched_acquisition_before_sql(baseline,field,value):
    from ingestion.service import reconcile
    from ingestion.validation import ValidationFailure
    original,_=baseline
    receipt=dict(evidence(original.data),**{field:value})
    with pytest.raises(ValidationFailure):
        reconcile(None,original,Path('/synthetic'),acquisition=receipt)
