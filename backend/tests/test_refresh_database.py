"""PostgreSQL-only tests. Synthetic full snapshots; all DB changes roll back in fixture."""
import json
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.models import Game, SourceArtifact
from ingestion.refresh import execute
from ingestion.refresh_state import RefreshState
from ingestion.service import reconcile
from ingestion.source import SourceConfig
from test_ingestion import source_rows, encode, snapshot
from test_refresh import evidence, row_2026

pytestmark=pytest.mark.database


@pytest.fixture
def seeded(db_session,source_rows,tmp_path):
    reconcile(db_session,snapshot(source_rows),Path('/synthetic/original.csv'))
    return db_session,source_rows,RefreshState(tmp_path/'state'),tmp_path/'archives'


def prepare(seeded):
    session,rows,state,archives=seeded
    body=encode(rows)
    run=execute(session.get_bind(),state,archives,SourceConfig(),download=lambda _: (body,evidence(body)))
    assert run['outcome']=='dry_run'
    return run


def apply(seeded,review,approval=True):
    session,_,state,archives=seeded
    return execute(session.get_bind(),state,archives,SourceConfig(),identifier=review['candidate_id'],apply=True,
                   approval=review['plan']['review_token'] if approval else None)


def test_dry_run_new_scores_review_apply_provenance_and_noop(seeded):
    session,rows,state,_=seeded
    changed=row_2026(rows)
    changed.update(home_score='20',away_score='17')
    original_artifacts=session.scalar(select(func.count()).select_from(SourceArtifact))
    review=prepare(seeded)
    assert review['plan']['summary']['newly_reported_scores']==1
    assert apply(seeded,review,approval=False)['outcome']=='review_required'
    assert session.scalar(select(func.count()).select_from(SourceArtifact))==original_artifacts
    result=apply(seeded,review)
    assert result['outcome']=='applied' and result['result']['updated']==1
    session.expire_all()
    game=session.scalar(select(Game).where(Game.source_game_id==changed['game_id']))
    assert game.reported_home_score==20 and game.status=='UNKNOWN' and game.final_evidence_url is None
    artifact=session.get(SourceArtifact,game.source_artifact_id)
    assert artifact.origin_status=='DECLARED' and artifact.retrieved_at.isoformat().startswith('2026-11-07T20:00:00')
    assert artifact.declared_source_url==SourceConfig().csv_url and artifact.provider_published_at is None
    assert json.loads(artifact.provenance_notes)['acquisition']['run_id']==result['run_id']
    assert apply(seeded,review,approval=False)['outcome']=='unchanged'
    assert session.scalar(select(func.count()).select_from(SourceArtifact))==original_artifacts+1
    assert session.scalar(select(func.count()).select_from(Game))==842
    assert state.status()['last_data_change_observed_at']==result['completed_at']


def test_changed_baseline_invalidates_review(seeded):
    session,rows,_,_=seeded
    row_2026(rows)['gametime']='14:00'
    review=prepare(seeded)
    game=session.scalar(select(Game).limit(1))
    game.final_evidence_url='https://example.invalid/synthetic-baseline-change'
    session.flush()
    result=apply(seeded,review)
    assert result['outcome']=='review_required'
    assert result['plan']['review_token']!=review['plan']['review_token']


def test_correction_and_removed_scores(seeded):
    session,rows,_,_=seeded
    target=rows[0]
    target['home_score']='3'
    review=prepare(seeded)
    assert review['plan']['summary']['historical_change']==1
    assert apply(seeded,review)['outcome']=='applied'
    # Populate then attempt removal of a 2026 score pair using a real consistent imported row.
    current=row_2026(rows)
    current.update(home_score='20',away_score='17')
    review=prepare(seeded);assert apply(seeded,review)['outcome']=='applied'
    current.update(home_score='',away_score='')
    body=encode(rows)
    blocked=execute(session.get_bind(),seeded[2],seeded[3],SourceConfig(),download=lambda _: (body,evidence(body)))
    assert blocked['outcome']=='rejected'
    assert any(b['code']=='score_removal' for b in blocked['plan']['blockers'])
    assert apply(seeded,blocked)['outcome']=='rejected'


def test_rollback_after_reconciliation_flush(seeded,monkeypatch):
    session,rows,state,_=seeded
    row_2026(rows)['gametime']='14:00'
    review=prepare(seeded)
    import ingestion.refresh_policy as policy
    original=policy.reconcile
    def fail_after_writes(*args,**kwargs):
        original(*args,**kwargs)
        raise RuntimeError('Synthetic failure after flushed changes')
    monkeypatch.setattr(policy,'reconcile',fail_after_writes)
    result=apply(seeded,review)
    assert result['outcome']=='failed'
    session.expire_all()
    assert session.scalar(select(func.count()).select_from(SourceArtifact))==1
    assert session.scalar(select(func.count()).select_from(Game))==842
    game=session.scalar(select(Game).where(Game.source_game_id==row_2026(rows)['game_id']))
    assert game.source_gametime.hour==13
    assert 'last_successful_ingestion_at' not in state.status()


def test_original_final_guard_cannot_be_bypassed(seeded):
    from datetime import datetime, timezone
    session,rows,_,_=seeded
    game=session.scalar(select(Game).where(Game.source_game_id==rows[0]['game_id']))
    game.status='FINAL';game.final_evidence_url='https://example.invalid/synthetic-final'
    game.final_verified_at=datetime.now(timezone.utc)
    session.flush()
    rows[0]['gametime']='14:00'
    body=encode(rows)
    review=execute(session.get_bind(),seeded[2],seeded[3],SourceConfig(),download=lambda _: (body,evidence(body)))
    assert review['outcome']=='rejected'
    assert apply(seeded,review)['outcome']=='rejected'
    assert session.scalar(select(func.count()).select_from(SourceArtifact))==1


def test_publisher_digest_persisted_without_authentication_claim(seeded):
    from ingestion.source import retrieve
    from test_refresh import metadata
    session,rows,state,archives=seeded
    row_2026(rows)['gametime']='14:00'
    body=encode(rows)
    def fetch(url,**kwargs):
        return (metadata(body),{}) if url==SourceConfig().metadata_url else (body,{})
    data,receipt=retrieve(SourceConfig(),fetch)
    review=execute(session.get_bind(),state,archives,SourceConfig(),download=lambda _: (data,receipt))
    result=apply(seeded,review)
    assert result['outcome']=='applied'
    artifact=session.get(SourceArtifact,UUID(result['result']['artifact_id']))
    assert artifact.sha256==artifact.publisher_sha256==receipt['sha256']
    assert artifact.origin_status=='DECLARED' and artifact.origin_verified_at is None
    assert artifact.retrieved_at is not None and artifact.provider_published_at is None


def test_missing_game_in_incomplete_snapshot_is_diagnosed(seeded):
    session,rows,state,archives=seeded
    removed=rows.pop()
    body=encode(rows)
    result=execute(session.get_bind(),state,archives,SourceConfig(),download=lambda _: (body,evidence(body)))
    assert result['outcome']=='validation_failed'
    assert removed['game_id'] in result['missing_record_diagnostic']['absent_source_ids']
    assert session.scalar(select(func.count()).select_from(Game))==842
    assert session.scalar(select(func.count()).select_from(SourceArtifact))==1
