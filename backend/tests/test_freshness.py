"""Synthetic checkpoint fixtures; tests neither mutate source data nor use PostgreSQL."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app
from app.repositories.refresh_status import MAX_STATUS_BYTES, RefreshStatusRepository
from app.services.freshness import project_status
from ingestion.refresh_state import RefreshState

NOW = datetime(2026,11,9,12,tzinfo=timezone.utc)


def status(**changes):
    return dict(version=1,last_outcome='applied',last_attempt_at='2026-11-08T08:00:00Z',
        last_successful_check_at='2026-11-08T08:01:00Z',last_successful_ingestion_at='2026-11-08T08:01:00Z',
        last_data_change_observed_at='2026-11-08T08:01:00Z',**changes) if not changes else {
        **status(),**changes,
    }


def project(raw):
    return project_status('available',raw,NOW,36*3600)


def test_exact_checkpoint_projection_and_no_sensitive_fields():
    raw=status(accepted_sha256='SENSITIVE',last_run_id='SENSITIVE',review_token='SENSITIVE',
               local_path='/private/files',credentials={'password':'SENSITIVE'})
    result=project(raw)
    assert result.data.latest_outcome=='applied'
    assert result.data.last_successful_apply_at==datetime(2026,11,8,8,1,tzinfo=timezone.utc)
    assert result.data.is_stale is False
    assert result.meta.manual is True
    body=result.model_dump_json()
    assert 'SENSITIVE' not in body and '/private/files' not in body and 'last_run_id' not in body
    assert set(result.model_dump())=={'data','meta'}


def test_real_writer_model_noop_and_failure_preserve_changed_time(tmp_path):
    from uuid import uuid4
    state=RefreshState(tmp_path)
    def finish(outcome,day):
        state.finish(dict(run_id=str(uuid4()),outcome=outcome,started_at=f'2026-11-{day:02d}T08:00:00Z',
                          completed_at=f'2026-11-{day:02d}T08:01:00Z',sha256='a'*64))
    finish('applied',6)
    finish('unchanged',7)
    finish('download_failed',8)
    before=(tmp_path/'status.json').read_bytes()
    metadata=RefreshStatusRepository(tmp_path).read()
    result=project_status(*metadata,NOW,36*3600)
    assert result.data.latest_outcome=='download_failed'
    assert result.data.last_successful_apply_at.day==7
    assert result.data.last_data_change_observed_at.day==6
    assert result.data.last_successful_check_at.day==7
    assert result.data.is_stale is True
    assert (tmp_path/'status.json').read_bytes()==before


def test_dry_run_does_not_create_an_apply_timestamp():
    result=project(status(last_outcome='dry_run',last_successful_ingestion_at=None,last_data_change_observed_at=None))
    assert result.data.metadata_state=='available'
    assert result.data.last_successful_check_at is not None
    assert result.data.last_successful_apply_at is None


def test_first_failure_has_no_invented_success():
    result=project(dict(version=1,last_outcome='download_failed',last_attempt_at='2026-11-08T08:00:00Z'))
    assert result.data.metadata_state=='available'
    assert result.data.last_successful_check_at is None
    assert result.data.check_age_seconds is None and result.data.is_stale is None


@pytest.mark.parametrize('raw', [
    {}, {'version':1}, status(last_outcome=None), status(last_attempt_at=None),
    status(last_outcome='applied',last_successful_check_at=None,last_successful_ingestion_at=None,last_data_change_observed_at=None),
])
def test_incomplete_metadata_is_never_recent(raw):
    result=project(raw)
    assert result.data.metadata_state=='incomplete'
    assert result.data.is_stale is None


@pytest.mark.parametrize('bad', ['not-a-date','2026-11-08T08:00:00',123,True,'2026-02-30T08:00:00Z','2026-11-10T08:00:00Z'])
def test_invalid_or_future_timestamp_fails_safely(bad):
    result=project(status(last_successful_check_at=bad))
    assert result.data.metadata_state=='invalid'
    assert result.data.last_successful_check_at is None and result.data.is_stale is None


@pytest.mark.parametrize('changes', [dict(version=2),dict(version=True),dict(last_outcome='secret/path'),
    dict(last_data_change_observed_at='2026-11-08T09:00:00Z'),dict(last_successful_ingestion_at='2026-11-08T09:00:00Z')])
def test_unknown_version_outcome_and_inconsistent_times(changes):
    result=project(status(**changes))
    assert result.data.metadata_state=='invalid'
    assert 'secret/path' not in result.model_dump_json()


def test_check_age_threshold_and_offsets():
    boundary=NOW-timedelta(hours=36)
    assert project_status('available',status(last_outcome='dry_run',last_successful_check_at=boundary.isoformat(),
        last_successful_ingestion_at=None,last_data_change_observed_at=None),NOW,36*3600).data.is_stale is False
    older=boundary-timedelta(seconds=1)
    assert project_status('available',status(last_outcome='dry_run',last_successful_check_at=older.isoformat(),
        last_successful_ingestion_at=None,last_data_change_observed_at=None),NOW,36*3600).data.is_stale is True
    result=project(status(last_outcome='dry_run',last_successful_check_at='2026-11-08T11:01:00+03:00',
        last_successful_ingestion_at=None,last_data_change_observed_at=None))
    assert result.data.last_successful_check_at.hour==8


def test_missing_file_does_not_create_state(tmp_path):
    folder=tmp_path/'not-created'
    assert RefreshStatusRepository(folder).read()==('missing',None)
    assert not folder.exists()


@pytest.mark.parametrize('body', [b'{broken',b'[]',b'null',b'\xff',b'x'*(MAX_STATUS_BYTES+1)])
def test_bad_file_content_is_bounded(tmp_path,body):
    path=tmp_path/'status.json';path.write_bytes(body)
    assert RefreshStatusRepository(tmp_path).read()==('invalid',None)
    assert path.read_bytes()==body


def test_permission_failure_and_symlink_do_not_expose_target(tmp_path,monkeypatch):
    secret=tmp_path/'secret';secret.write_text('SENSITIVE')
    (tmp_path/'status.json').symlink_to(secret)
    assert RefreshStatusRepository(tmp_path).read()==('unreadable',None)
    def fail(*args): raise PermissionError('/private/SENSITIVE')
    monkeypatch.setattr('app.repositories.refresh_status.os.open',fail)
    assert RefreshStatusRepository(tmp_path).read()==('unreadable',None)


def app_for(folder):
    app=create_app(Settings(db_host='synthetic.invalid',db_name='nfl_research_test',db_user='synthetic',
                            db_password='SYNTHETIC_ONLY',refresh_state_dir=folder))
    async def forbid_database():
        pytest.fail('freshness must not use a database session')
    app.dependency_overrides[get_session]=forbid_database
    return app


def request(app,method='GET',url='/api/data-status/schedule'):
    async def perform():
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
            return await client.request(method,url)
    return asyncio.run(perform())


def test_api_contract_no_database_no_writes_no_secrets(tmp_path):
    file=tmp_path/'status.json';file.write_text(json.dumps(status(review_token='SENSITIVE',local_path='/private/SENSITIVE')))
    before=file.stat().st_mtime_ns
    response=request(app_for(tmp_path))
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    payload=response.json()
    assert payload['data']['metadata_state']=='available'
    assert payload['meta']['manual'] is True
    assert set(payload['data'])=={'metadata_state','latest_outcome','last_attempt_at','last_successful_check_at',
        'last_successful_apply_at','last_data_change_observed_at','check_age_seconds','is_stale'}
    assert 'SENSITIVE' not in response.text and str(tmp_path) not in response.text
    assert file.stat().st_mtime_ns==before


@pytest.mark.parametrize('contents,expected', [(None,'missing'),('broken','invalid'),('{}','incomplete')])
def test_api_unavailable_metadata_is_domain_state(tmp_path,contents,expected):
    if contents is not None: (tmp_path/'status.json').write_text(contents)
    response=request(app_for(tmp_path))
    assert response.status_code==200 and response.json()['data']['metadata_state']==expected
    assert response.json()['data']['is_stale'] is None


@pytest.mark.parametrize('method',['POST','PUT','PATCH','DELETE'])
def test_api_has_no_write_methods(tmp_path,method):
    assert request(app_for(tmp_path),method).status_code==405
    assert not (tmp_path/'status.json').exists()


def test_api_rejects_query_paths_and_documents_contract(tmp_path):
    app=app_for(tmp_path)
    response=request(app,url='/api/data-status/schedule?file=/private/SENSITIVE')
    assert response.status_code==422 and 'SENSITIVE' not in response.text
    operation=app.openapi()['paths']['/api/data-status/schedule']
    assert set(operation)=={'get'}
    assert 'FreshnessResponse' in operation['get']['responses']['200']['content']['application/json']['schema']['$ref']
