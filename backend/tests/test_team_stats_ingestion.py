"""Synthetic candidate/plan/database tests. No real artifacts or database required by unit tests."""
import contextlib
import io
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update, delete
from sqlalchemy.exc import IntegrityError

from app.models import (Game, Team, TeamAlias, SourceArtifact, TeamStatsBatch, TeamStatsPair,
                        TeamGameStatRevision, TeamStatsAccepted, TeamStatsSelectionEvent)
from ingestion.team_stats.__main__ import main as offline_audit
from ingestion.team_stats.candidate import load_candidate, archive_candidate, StatsRejected, fingerprint
from ingestion.team_stats.storage import (inspect, plan_import, apply_import, plan_rollback, apply_rollback)
from ingestion.service import reconcile
from ingestion.validation import TEAM_CODES
from test_ingestion import source_rows, encode, snapshot


def make_files(root, schedule_rows, identities=None, change=None):
    root.mkdir(parents=True, exist_ok=True)
    schedule_path=root/'schedule.csv'; schedule_path.write_bytes(encode(schedule_rows))
    if identities is None:
        ids={t:str(uuid4()) for t in TEAM_CODES}
        identities=dict(version=1,teams=[dict(id=v,code=k) for k,v in ids.items()],
            aliases=[dict(provider='nflverse',source_team_code=k,team_id=v) for k,v in ids.items()],
            games=[dict(id=str(uuid4()),source_game_id=g['game_id'],home_team_id=ids[g['home_team']],away_team_id=ids[g['away_team']]) for g in schedule_rows])
    identity_path=root/'identities.json';identity_path.write_text(json.dumps(identities))
    refs=[]; args=['--schedule',str(schedule_path),'--identity-map',str(identity_path),'--output-dir',str(root/'audit')]
    for year in (2024,2025,2026):
        records=[];games=[g for g in schedule_rows if g['season']==str(year)]
        for g in games:
            for team,opponent in ((g['home_team'],g['away_team']),(g['away_team'],g['home_team'])):
                records.append(dict(game_id=g['game_id'],season=g['season'],week=g['week'],season_type='REG' if g['game_type']=='REG' else 'POST',
                    team=team,opponent_team=opponent,passing_yards='200',sack_yards_lost='-10',rushing_yards='0'))
        if change: change(year,records)
        path=root/f'{year}.csv';path.write_bytes(encode(records));args+=['--file',f'{year}={path}']
        first=games[0]
        refs.append(dict(season=year,game_id=first['game_id'],team=first['home_team'],
            source_url='https://static.www.nfl.com/synthetic.pdf',locator='Synthetic fixture only',
            reviewed_at='2026-01-01T00:00:00Z',use='reference_only',gross_passing_yards=200,
            net_passing_yards=190,rushing_yards=0,points_scored=int(first['home_score'] or 0),points_allowed=int(first['away_score'] or 0)))
    reference_path=root/'references.json';reference_path.write_text(json.dumps(dict(version=1,references=refs)))
    args+=['--references',str(reference_path)]
    with contextlib.redirect_stdout(io.StringIO()):
        assert offline_audit(args)==0
    audit_path=next((root/'audit').glob('audit-*.json'))
    return dict(audit_path=audit_path,artifact_dir=root/'audit'/'snapshots',schedule_path=schedule_path,
                identity_path=identity_path,references_path=reference_path)


@pytest.fixture
def files(tmp_path,source_rows):
    return make_files(tmp_path/'input',source_rows)


def test_candidate_revalidates_full_synthetic_snapshot(files):
    c=load_candidate(**files)
    assert len(c.pairs)==842
    assert len(c.blobs)==7
    assert c.evidence['definition']=='net_pass_negative_sacks_v1'
    assert all(t['values']['rushing_yards']==0 and t['values']['original_sack_yards']==-10 for p in c.pairs for t in p['teams'])


@pytest.mark.parametrize('case',['file','missing','derived','receipt','license','definition','identity','reference','schedule','failed_audit','retrieval'])
def test_tampered_or_missing_inputs_rejected(files,case):
    r=json.loads(files['audit_path'].read_text());s=r['seasons']['2024']
    if case=='file': (files['artifact_dir']/(s['sha256']+'.csv')).write_bytes(b'invalid')
    elif case=='missing': (files['artifact_dir']/(s['sha256']+'.csv')).unlink()
    elif case=='derived': s['matched_games'][0]['teams'][0]['net_passing_yards']+=1
    elif case=='receipt': s['receipt']['sha256']='0'*64
    elif case=='license': s['receipt']['license_url']='https://invalid.example'
    elif case=='definition': s['sack_convention']='positive_validated_against_reviewed_reference'
    elif case=='identity': files['identity_path'].write_text('{}')
    elif case=='reference': files['references_path'].write_text('{}')
    elif case=='schedule': files['schedule_path'].write_bytes(b'incomplete')
    elif case=='failed_audit': r['audit_exit_code']=2
    else: s['receipt']['retrieved_at']='2026-01-01T00:00:00Z' # local input cannot invent retrieval
    files['audit_path'].write_text(json.dumps(r))
    with pytest.raises(StatsRejected): load_candidate(**files)


def test_archives_preserve_and_revalidate_inputs(files,tmp_path):
    from ingestion.team_stats.storage import verify_archives
    c=load_candidate(**files);archives=archive_candidate(c,tmp_path/'archives')
    assert archive_candidate(c,tmp_path/'archives')==archives
    verify_archives(c,archives)
    Path(archives['references.json']).write_bytes(b'broken')
    with pytest.raises(StatsRejected,match='archive_hash_mismatch'): verify_archives(c,archives)


def fake_state(candidate):
    games={};teams={};aliases={}
    for p in candidate.pairs:
        # Source fixtures have identical home/away orientation in canonical game IDs.
        _,_,away,home=p['source_game_id'].split('_')
        for t in p['teams']:
            teams[t['team_id']]=SimpleNamespace(code=t['code']);aliases[t['raw']['team']]=t['team_id']
        lookup={t['code']:t['team_id'] for t in p['teams']}
        first=p['teams'][0]['raw']
        games[p['game_id']]=SimpleNamespace(source_game_id=p['source_game_id'],season=p['season'],
            home_team_id=lookup[home],away_team_id=lookup[away],week=int(first['week']),season_type=first['season_type'],reported_home_score=None)
    return dict(games=games,teams=teams,aliases=aliases,selections={},pairs={},rows={},baseline_sha256='a'*64)


def test_review_plan_initial_and_baseline_binding(files):
    c=load_candidate(**files);state=fake_state(c)
    plan=plan_import(state,c)
    assert plan['inserted_pairs']==842 and not plan['blockers']
    assert plan_import(state,c)==plan
    state['baseline_sha256']='b'*64
    assert plan_import(state,c)['review_token']!=plan['review_token']


@pytest.mark.parametrize('change',['uuid','alias','opponent','stage'])
def test_live_identity_drift_fails(files,change):
    c=load_candidate(**files);state=fake_state(c);p=c.pairs[0];g=state['games'][p['game_id']]
    if change=='uuid':g.source_game_id='different'
    elif change=='alias':state['aliases'][p['teams'][0]['raw']['team']]='unknown'
    elif change=='opponent':g.away_team_id='unknown'
    else:g.week=99
    with pytest.raises(StatsRejected):plan_import(state,c)


def test_disappearing_accepted_game_blocked(files):
    c=load_candidate(**files);state=fake_state(c)
    state['selections']['missing']=SimpleNamespace(pair_id=uuid4())
    plan=plan_import(state,c)
    assert any(b['code']=='missing_accepted_game' for b in plan['blockers'])


def test_cli_rejects_before_database_without_required_inputs(tmp_path,capsys):
    from ingestion.team_stats.ingest import main
    result=main(['--audit',str(tmp_path/'missing'),'--report-dir',str(tmp_path/'reports')])
    assert result==2 and 'audit_inputs_required' in capsys.readouterr().out


@pytest.fixture
def db_candidate(db_session,source_rows,tmp_path):
    reconcile(db_session,snapshot(source_rows),tmp_path/'synthetic-schedule.csv')
    identities=dict(version=1,
        teams=[dict(id=str(t.id),code=t.code) for t in db_session.scalars(select(Team))],
        aliases=[dict(provider=a.provider,source_team_code=a.source_team_code,team_id=str(a.team_id)) for a in db_session.scalars(select(TeamAlias))],
        games=[dict(id=str(g.id),source_game_id=g.source_game_id,home_team_id=str(g.home_team_id),away_team_id=str(g.away_team_id)) for g in db_session.scalars(select(Game))])
    files=make_files(tmp_path/'inputs',source_rows,identities)
    c=load_candidate(**files);archives=archive_candidate(c,tmp_path/'archives')
    return db_session,c,archives,files,source_rows,identities


def approved_import(data):
    session,c,archives,*_=data
    plan=plan_import(inspect(session),c)
    with session.begin_nested():
        return apply_import(session,c,archives,plan['review_token'])


@pytest.mark.database
def test_database_initial_idempotent_and_schedule_unchanged(db_candidate):
    s,c,a,*_=db_candidate
    before=[{k:getattr(g,k) for k in ('id','source_record_sha256','status','source_artifact_id','reported_home_score')} for g in s.scalars(select(Game).order_by(Game.id))]
    result=approved_import(db_candidate)
    assert result['outcome']=='applied'
    assert s.scalar(select(func.count()).select_from(TeamStatsAccepted))==842
    assert s.scalar(select(func.count()).select_from(TeamGameStatRevision))==1684
    assert apply_import(s,c,a,None)['outcome']=='unchanged'
    assert s.scalar(select(func.count()).select_from(TeamStatsBatch))==1
    after=[{k:getattr(g,k) for k in ('id','source_record_sha256','status','source_artifact_id','reported_home_score')} for g in s.scalars(select(Game).order_by(Game.id))]
    assert before==after
    for artifact in s.scalars(select(SourceArtifact).where(SourceArtifact.id.in_(select(TeamStatsPair.source_artifact_id)))):
        assert artifact.origin_status=='DECLARED' and artifact.retrieved_at is None


@pytest.mark.database
def test_database_explicit_review_and_stale_token(db_candidate):
    s,c,a,*_=db_candidate
    plan=plan_import(inspect(s),c)
    for token in (None,'wrong'):
        with pytest.raises(StatsRejected),s.begin_nested():apply_import(s,c,a,token)
    game=s.scalar(select(Game).limit(1));game.final_evidence_url='https://example.invalid/synthetic'
    s.flush()
    with pytest.raises(StatsRejected,match='review_required_or_stale'),s.begin_nested():apply_import(s,c,a,plan['review_token'])
    assert s.scalar(select(func.count()).select_from(TeamStatsBatch))==0


@pytest.mark.database
def test_database_failure_rolls_back_all_pairs(db_candidate,monkeypatch):
    import ingestion.team_stats.storage as storage
    s,c,a,*_=db_candidate;plan=plan_import(inspect(s),c);original=storage.publish
    def fail(*args,**kwargs):
        original(*args,**kwargs)
        raise RuntimeError('synthetic failure after pointer flush')
    monkeypatch.setattr(storage,'publish',fail)
    with pytest.raises(RuntimeError):
        with s.begin_nested():apply_import(s,c,a,plan['review_token'])
    assert s.scalar(select(func.count()).select_from(TeamStatsBatch))==0
    assert s.scalar(select(func.count()).select_from(TeamGameStatRevision))==0
    assert s.scalar(select(func.count()).select_from(SourceArtifact))==1


@pytest.mark.database
def test_database_correction_and_logical_rollback(db_candidate,tmp_path):
    s,c,a,files,rows,identities=db_candidate
    initial=approved_import(db_candidate)
    def correction(year,records):
        if year==2024:records[4]['passing_yards']='201' # outside reference game
    changed_files=make_files(tmp_path/'corrected',rows,identities,correction)
    changed=load_candidate(**changed_files);archives=archive_candidate(changed,tmp_path/'changed-archives')
    plan=plan_import(inspect(s),changed)
    assert plan['corrected_pairs']==1 and plan['changes'][0]['kind']=='historical_correction'
    with pytest.raises(StatsRejected),s.begin_nested():apply_import(s,changed,archives,None)
    result=apply_import(s,changed,archives,plan['review_token'])
    assert s.scalar(select(func.count()).select_from(TeamStatsPair))==843
    rollback=plan_rollback(s,inspect(s),result['batch_id'])
    with pytest.raises(StatsRejected),s.begin_nested():apply_rollback(s,result['batch_id'],None)
    restored=apply_rollback(s,result['batch_id'],rollback['review_token'])
    assert restored['outcome']=='rolled_back'
    assert apply_rollback(s,result['batch_id'],None)['outcome']=='unchanged'
    assert s.scalar(select(func.count()).select_from(TeamStatsPair))==843
    assert s.scalar(select(func.count()).select_from(TeamStatsSelectionEvent))==844
    assert apply_import(s,c,a,None)['outcome']=='unchanged'
    with pytest.raises(StatsRejected,match='rollback_has_no_prior_pair'):plan_rollback(s,inspect(s),initial['batch_id'])


@pytest.mark.database
@pytest.mark.parametrize('table',[TeamStatsBatch,TeamStatsPair,TeamGameStatRevision,TeamStatsSelectionEvent])
def test_database_history_immutable(db_candidate,table):
    approved_import(db_candidate);s=db_candidate[0]
    # Even a no-change SQL UPDATE is forbidden on history rows.
    col=next(iter(table.__table__.primary_key.columns))
    with pytest.raises(IntegrityError),s.begin_nested():s.execute(update(table).values({col.name:col}))
    with pytest.raises(IntegrityError),s.begin_nested():s.execute(delete(table))


@pytest.mark.database
def test_database_selection_requires_complete_pair_and_event(db_candidate):
    s,c,a,*_=db_candidate
    approved_import(db_candidate)
    accepted=s.scalar(select(TeamStatsAccepted).limit(1));old=s.get(TeamStatsPair,accepted.pair_id)
    batch=TeamStatsBatch(id=uuid4(),kind='IMPORT',candidate_sha256='0'*64,review_token='0'*64,evidence={});s.add(batch);s.flush()
    pair=TeamStatsPair(id=uuid4(),game_id=old.game_id,home_team_id=old.home_team_id,away_team_id=old.away_team_id,
        batch_id=batch.id,source_artifact_id=old.source_artifact_id,definition_version=old.definition_version,content_sha256='0'*64)
    s.add(pair);s.flush()
    with pytest.raises(IntegrityError),s.begin_nested():
        s.execute(update(TeamStatsAccepted).where(TeamStatsAccepted.game_id==old.game_id).values(pair_id=pair.id,batch_id=batch.id,generation=accepted.generation+1))
    with pytest.raises(IntegrityError),s.begin_nested():s.execute(delete(TeamStatsAccepted))


@pytest.mark.database
def test_database_negative_zero_null_and_membership_constraints(db_candidate):
    s,c,a,*_=db_candidate;approved_import(db_candidate)
    old=s.scalar(select(TeamStatsPair).limit(1))
    batch=TeamStatsBatch(id=uuid4(),kind='IMPORT',candidate_sha256='1'*64,review_token='1'*64,evidence={});s.add(batch);s.flush()
    pair=TeamStatsPair(id=uuid4(),game_id=old.game_id,home_team_id=old.home_team_id,away_team_id=old.away_team_id,
        batch_id=batch.id,source_artifact_id=old.source_artifact_id,definition_version=old.definition_version,content_sha256='1'*64);s.add(pair);s.flush()
    base=dict(pair_id=pair.id,game_id=pair.game_id,team_id=pair.home_team_id,opponent_team_id=pair.away_team_id,
              side='HOME',gross_passing_yards=0,original_sack_yards=-5,net_passing_yards=-5,rushing_yards=-2,
              source_record_sha256='1'*64,source_line=2,raw_source_record={})
    for bad in ({'team_id':uuid4()},{'net_passing_yards':5},{'original_sack_yards':5},{'opponent_team_id':pair.home_team_id}):
        with pytest.raises(IntegrityError),s.begin_nested():s.add(TeamGameStatRevision(**dict(base,**bad)));s.flush()
    # Nullable staged revision preserves missing operands; selection still rejects incomplete pairs.
    s.add(TeamGameStatRevision(**dict(base,original_sack_yards=None,net_passing_yards=None)))
    s.flush()


def test_frozen_migration_matches_model_tables_and_indexes():
    import importlib.util
    from sqlalchemy.schema import CreateTable, CreateIndex
    from sqlalchemy.dialects.postgresql import dialect
    from app.db.base import Base
    path=Path(__file__).parents[1]/'alembic'/'versions'/'0002_team_stats.py'
    spec=importlib.util.spec_from_file_location('stats_migration_review',path)
    migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    statements=[];migration.op=SimpleNamespace(execute=lambda sql:statements.append(sql))
    migration.upgrade()
    normal=lambda value:' '.join(str(value).split())
    actual={normal(sql) for sql in statements if str(sql).lstrip().startswith(('CREATE TABLE','CREATE INDEX'))}
    names=('team_stats_batches','team_stats_pairs','team_game_stat_revisions','team_stats_selection_events','team_stats_accepted')
    expected=set()
    for name in names:
        table=Base.metadata.tables[name]
        expected.add(normal(CreateTable(table).compile(dialect=dialect())))
        expected.update(normal(CreateIndex(index).compile(dialect=dialect())) for index in table.indexes)
    assert actual==expected
    assert all('ALTER TABLE games' not in sql and 'UPDATE games' not in sql for sql in statements)
    assert sum('CREATE TRIGGER' in sql for sql in statements)==9
    assert any('AFTER INSERT OR UPDATE' in sql and 'team_stats_selection_record' in sql for sql in statements)
    assert any('SECURITY DEFINER SET search_path = pg_catalog' in sql for sql in statements)
    assert any('REVOKE ALL' in sql and 'team_stats_selection_events' in sql for sql in statements)


def test_cli_configuration_guard_prevents_database_connection(files,tmp_path,monkeypatch,capsys):
    import ingestion.team_stats.ingest as cli
    monkeypatch.setattr(cli,'Settings',lambda:SimpleNamespace(db_host='production',db_name='nfl_research_dev'))
    monkeypatch.setattr(cli,'make_engine',lambda _:pytest.fail('database must not be opened'))
    args=['--audit',str(files['audit_path']),'--artifact-dir',str(files['artifact_dir']),
          '--schedule',str(files['schedule_path']),'--identity-map',str(files['identity_path']),
          '--references',str(files['references_path']),'--archive-dir',str(tmp_path/'archive'),
          '--report-dir',str(tmp_path/'reports')]
    assert cli.main(args)==2
    assert 'use_compose_development_database' in capsys.readouterr().out


@pytest.mark.database
def test_database_missing_prior_source_archive_blocks_changes(db_candidate):
    s,c,archives,*_=db_candidate
    approved_import(db_candidate)
    Path(archives['2024.csv']).unlink()
    with pytest.raises(StatsRejected,match='stored_archive_missing'):inspect(s)
    assert s.scalar(select(func.count()).select_from(TeamStatsAccepted))==842


@pytest.mark.database
def test_database_rollback_failure_is_atomic(db_candidate,tmp_path,monkeypatch):
    import ingestion.team_stats.storage as storage
    s,c,a,_,rows,identities=db_candidate;approved_import(db_candidate)
    def correction(year,records):
        if year==2024:
            records[4]['passing_yards']='201';records[6]['rushing_yards']='-3'
    files=make_files(tmp_path/'correction',rows,identities,correction)
    changed=load_candidate(**files);archives=archive_candidate(changed,tmp_path/'more')
    plan=plan_import(inspect(s),changed);result=apply_import(s,changed,archives,plan['review_token'])
    plan=plan_rollback(s,inspect(s),result['batch_id'])
    before={str(v.game_id):str(v.pair_id) for v in s.scalars(select(TeamStatsAccepted))}
    original=storage.publish
    def fail(*args):
        original(*args)
        raise RuntimeError('synthetic rollback interruption')
    monkeypatch.setattr(storage,'publish',fail)
    with pytest.raises(RuntimeError):
        with s.begin_nested():apply_rollback(s,result['batch_id'],plan['review_token'])
    after={str(v.game_id):str(v.pair_id) for v in s.scalars(select(TeamStatsAccepted))}
    assert before==after


def test_historical_plan_exposes_raw_and_metric_corrections(files):
    c=load_candidate(**files);state=fake_state(c);p=c.pairs[0]
    prior=uuid4()
    state['selections'][p['game_id']]=SimpleNamespace(pair_id=prior)
    state['pairs'][str(prior)]=SimpleNamespace(id=prior,content_sha256='0'*64)
    before=[]
    for index,t in enumerate(p['teams']):
        raw=dict(t['raw']);values=dict(t['values'])
        if index==0:
            raw['rushing_yards']='-1';values['rushing_yards']=-1
        before.append(SimpleNamespace(team_id=t['team_id'],raw_source_record=raw,**values))
    state['rows'][str(prior)]=before
    plan=plan_import(state,c)
    change=next(ch for ch in plan['changes'] if ch['game_id']==p['game_id'])
    assert change['kind']=='historical_correction'
    fields=[field for team in change['raw_changes'] for field in team['fields']]
    assert dict(field='rushing_yards',before='-1',after='0') in fields
    assert plan['corrected_pairs']==1
