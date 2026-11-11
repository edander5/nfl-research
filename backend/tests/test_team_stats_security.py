"""Adversarial candidate/history and real restricted-login PostgreSQL regressions."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text, select, update, insert, func
from sqlalchemy.exc import DBAPIError

from app.models import TeamStatsAccepted, TeamStatsSelectionEvent, TeamStatsBatch, TeamStatsPair, TeamGameStatRevision
from ingestion.team_stats.candidate import load_candidate, archive_candidate, StatsRejected, fingerprint
from ingestion.team_stats.storage import (verify_archives, apply_import, inspect, plan_import,
                                         validate_history, plan_rollback, apply_rollback)
from test_team_stats_ingestion import files, source_rows, db_candidate, make_files, approved_import


@pytest.mark.parametrize('target',['receipt','definition','evidence','pair','blob'])
def test_post_validation_candidate_mutation_rejected(files,tmp_path,target):
    c=load_candidate(**files);archives=archive_candidate(c,tmp_path/'captures')
    if target=='receipt':c.evidence['receipts']['2024']['sha256']='0'*64
    elif target=='definition':c.evidence['definition']='unapproved'
    elif target=='evidence':c.evidence['identities_sha256']='0'*64
    elif target=='pair':c.pairs[0]['teams'][0]['values']['rushing_yards']=123
    else:c.blobs['2024.csv']=b'substitution'
    with pytest.raises(StatsRejected):verify_archives(c,archives)


def test_verified_copy_is_private_and_source_substitution_rejected(files,tmp_path):
    c=load_candidate(**files);archives=archive_candidate(c,tmp_path/'captures')
    checked=verify_archives(c,archives)
    c.evidence['receipts']['2024']['attribution']='post-check mutation'
    assert checked.evidence['receipts']['2024']['attribution']!='post-check mutation'
    Path(archives['2025.csv']).write_bytes(b'changed after capture')
    with pytest.raises(StatsRejected):verify_archives(checked,archives)


def test_candidate_mutation_fails_before_any_database_access(files,tmp_path):
    c=load_candidate(**files);archives=archive_candidate(c,tmp_path/'captures')
    c.evidence['receipts']['2024']['source_url']='https://unapproved.invalid'
    class NoDatabase:
        new=dirty=deleted=()
        def __getattr__(self,name):pytest.fail('database must not be accessed: '+name)
    with pytest.raises(StatsRejected):apply_import(NoDatabase(),c,archives,'old-approval')


def test_pending_session_dml_rejected_before_autoflush(files):
    c=load_candidate(**files)
    with pytest.raises(StatsRejected,match='pending_session_changes'):
        apply_import(SimpleNamespace(new=[object()],dirty=(),deleted=()),c,{},None)


def history_fixture():
    game,batch,a,b=uuid4(),uuid4(),uuid4(),uuid4()
    events=[SimpleNamespace(game_id=game,batch_id=batch,generation=1,before_pair_id=None,after_pair_id=a),
            SimpleNamespace(game_id=game,batch_id=batch,generation=2,before_pair_id=a,after_pair_id=b)]
    selections={str(game):SimpleNamespace(generation=2,pair_id=b,batch_id=batch)}
    return selections,events,a,b


@pytest.mark.parametrize('attack',['orphan','gap','duplicate','false_previous','false_tip','extra_event'])
def test_fabricated_or_broken_acceptance_chain_rejected(attack):
    selections,events,a,b=history_fixture()
    if attack=='orphan':selections={}
    elif attack=='gap':events[1].generation=3
    elif attack=='duplicate':events[1].generation=1
    elif attack=='false_previous':events[1].before_pair_id=uuid4()
    elif attack=='false_tip':next(iter(selections.values())).pair_id=a
    else:events.append(SimpleNamespace(game_id=uuid4(),batch_id=uuid4(),generation=1,before_pair_id=None,after_pair_id=uuid4()))
    with pytest.raises(StatsRejected):validate_history(selections,events)


def test_genuine_rollback_cycle_chain_is_valid_and_changes_baseline():
    selections,events,a,b=history_fixture();validate_history(selections,events)
    before=fingerprint([vars(e) for e in events])
    event=SimpleNamespace(game_id=events[0].game_id,batch_id=uuid4(),generation=3,before_pair_id=b,after_pair_id=a)
    events.append(event);next(iter(selections.values())).__dict__.update(generation=3,pair_id=a,batch_id=event.batch_id)
    validate_history(selections,events)
    assert fingerprint([vars(e) for e in events])!=before


def test_password_verifier_has_no_plaintext():
    from app.db.roles import scram_verifier
    password='SYNTHETIC_PASSWORD_AT_LEAST_24_CHARS'
    verifier=scram_verifier(password)
    assert verifier.startswith('SCRAM-SHA-256$4096:') and password not in verifier
    assert scram_verifier(password)!=verifier # independently salted
    for bad in ('short','REPLACE_WITH_LOCAL_PASSWORD_1234567','contains spaces not supported here'):
        with pytest.raises(ValueError):scram_verifier(bad)


# These cases authenticate with nfl_ingest, not SET ROLE on a superuser connection.
@pytest.fixture
def db_session(restricted_db_session):
    yield restricted_db_session


def denied(session,statement):
    with pytest.raises(DBAPIError) as error:
        with session.begin_nested():session.execute(text(statement))
    assert error.value.orig.sqlstate=='42501'


@pytest.mark.database
def test_actual_restricted_login_flags_and_forbidden_operations(db_candidate):
    s=db_candidate[0]
    assert s.scalar(text('SELECT session_user'))=='nfl_ingest'
    assert s.scalar(text('SELECT current_user'))=='nfl_ingest'
    flags=s.execute(text("SELECT rolsuper,rolcreaterole,rolcreatedb,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user")).one()
    assert not any(flags)
    for table, key in (('team_stats_batches','id'),('team_stats_pairs','id'),
                       ('team_game_stat_revisions','pair_id'),('team_stats_selection_events','id')):
        denied(s,f'UPDATE {table} SET {key}={key}')
        denied(s,f'DELETE FROM {table}')
        denied(s,f'TRUNCATE {table}')
    denied(s,'DELETE FROM team_stats_accepted')
    denied(s,'UPDATE source_artifacts SET sha256=sha256')
    for statement in (
        "UPDATE team_stats_batches SET kind=kind", "DELETE FROM team_stats_batches", "TRUNCATE team_stats_selection_events",
        "TRUNCATE team_stats_pairs CASCADE", "ALTER TABLE team_stats_accepted DISABLE TRIGGER ALL",
        "DROP TABLE team_stats_accepted", "CREATE TABLE public.forbidden(id int)", "CREATE SCHEMA forbidden",
        "SET ROLE nfl_owner", "SET session_replication_role=replica",
        "INSERT INTO team_stats_selection_events(id,batch_id,game_id,generation,after_pair_id) VALUES (gen_random_uuid(),gen_random_uuid(),gen_random_uuid(),1,gen_random_uuid())"):
        denied(s,statement)


@pytest.mark.database
def test_restricted_import_correction_rollback_cycle_and_replayed_approval(db_candidate,tmp_path):
    s,c,archives,_,rows,identities=db_candidate
    initial_plan=plan_import(inspect(s),c)
    initial=apply_import(s,c,archives,initial_plan['review_token'])
    assert apply_import(s,c,archives,None)['outcome']=='unchanged'
    assert s.scalar(select(func.count()).select_from(TeamStatsSelectionEvent))==842
    def correction(year,records):
        if year==2024:records[4]['passing_yards']='201'
    files=make_files(tmp_path/'changed',rows,identities,correction)
    changed=load_candidate(**files);captures=archive_candidate(changed,tmp_path/'more')
    old_plan=plan_import(inspect(s),changed)
    applied=apply_import(s,changed,captures,old_plan['review_token'])
    rollback=plan_rollback(s,inspect(s),applied['batch_id'])
    result=apply_rollback(s,applied['batch_id'],rollback['review_token'])
    assert result['outcome']=='rolled_back'
    fresh_plan=plan_import(inspect(s),changed)
    assert fresh_plan['review_token']!=old_plan['review_token']
    with pytest.raises(StatsRejected,match='review_required_or_stale'),s.begin_nested():
        apply_import(s,changed,captures,old_plan['review_token'])
    assert apply_import(s,changed,captures,fresh_plan['review_token'])['outcome']=='applied'
    state=inspect(s)
    assert any(len(history)==4 for history in state['history'].values())


@pytest.mark.database
def test_never_accepted_pair_cannot_be_selected_as_rollback(db_candidate):
    s,c,archives,*_=db_candidate;approved_import(db_candidate)
    accepted=s.scalar(select(TeamStatsAccepted).limit(1));old=s.get(TeamStatsPair,accepted.pair_id)
    batch=TeamStatsBatch(id=uuid4(),kind='IMPORT',candidate_sha256='0'*64,review_token='0'*64,evidence={});s.add(batch);s.flush()
    never=TeamStatsPair(id=uuid4(),game_id=old.game_id,home_team_id=old.home_team_id,away_team_id=old.away_team_id,
        batch_id=batch.id,source_artifact_id=old.source_artifact_id,previous_pair_id=old.id,definition_version=old.definition_version,content_sha256=old.content_sha256)
    s.add(never);s.flush()
    for row in s.scalars(select(TeamGameStatRevision).where(TeamGameStatRevision.pair_id==old.id)):
        values={col.name:getattr(row,col.name) for col in row.__table__.columns};values['pair_id']=never.id
        s.add(TeamGameStatRevision(**values))
    s.flush()
    rollback=TeamStatsBatch(id=uuid4(),kind='ROLLBACK',candidate_sha256='1'*64,review_token='1'*64,evidence={});s.add(rollback);s.flush()
    with pytest.raises(DBAPIError) as error:
        with s.begin_nested():
            s.execute(update(TeamStatsAccepted).where(TeamStatsAccepted.game_id==old.game_id).values(
                pair_id=never.id,batch_id=rollback.id,generation=accepted.generation+1))
    assert error.value.orig.sqlstate=='23514'
    assert not s.scalar(select(func.count()).select_from(TeamStatsSelectionEvent).where(TeamStatsSelectionEvent.after_pair_id==never.id))


@pytest.mark.database
def test_trigger_history_rolls_back_with_failed_transition(db_candidate,monkeypatch):
    import ingestion.team_stats.storage as storage
    s,c,archives,*_=db_candidate;plan=plan_import(inspect(s),c);original=storage.publish
    def fail(*args):original(*args);raise RuntimeError('synthetic after trigger event insertion')
    monkeypatch.setattr(storage,'publish',fail)
    with pytest.raises(RuntimeError):
        with s.begin_nested():apply_import(s,c,archives,plan['review_token'])
    assert s.scalar(select(func.count()).select_from(TeamStatsSelectionEvent))==0
    assert s.scalar(select(func.count()).select_from(TeamStatsAccepted))==0


def test_python_rollback_rejects_never_accepted_prior_target():
    from ingestion.team_stats.storage import plan_rollback
    game,batch,never,current=uuid4(),uuid4(),uuid4(),uuid4()
    event=SimpleNamespace(game_id=game,batch_id=batch,generation=2,before_pair_id=never,after_pair_id=current)
    state=dict(selections={str(game):SimpleNamespace(pair_id=current)},
               history={str(game):[SimpleNamespace(generation=1,after_pair_id=uuid4())]})
    fake=SimpleNamespace(get=lambda *args:SimpleNamespace(id=batch),scalars=lambda *args:[event])
    with pytest.raises(StatsRejected,match='rollback_target_never_accepted'):plan_rollback(fake,state,batch)


@pytest.mark.database
def test_actual_readonly_api_login_can_read_schedule_but_not_write(pg_engine):
    from pydantic import SecretStr
    from app.core.config import Settings
    from app.db.session import make_engine
    from sqlalchemy.orm import Session
    settings=Settings().model_copy(update=dict(db_user='nfl_api',db_password=SecretStr('SYNTHETIC_API_PASSWORD_123456789'),db_purpose='runtime'))
    engine=make_engine(settings)
    try:
        with Session(engine) as s,s.begin():
            assert s.scalar(text('SELECT session_user'))=='nfl_api'
            assert s.scalar(text('SELECT count(*) FROM games'))>=0
            from app.api.health import ready
            from fastapi import Response
            assert ready(Response(),s)=={'status':'ready'}
            denied(s,'UPDATE games SET status=status')
            denied(s,'INSERT INTO teams(id,code,name) VALUES (gen_random_uuid(),\'ZZZ\',\'forbidden\')')
            denied(s,'SELECT * FROM team_stats_batches')
            denied(s,'SET ROLE nfl_owner')
    finally:engine.dispose()


@pytest.mark.database
def test_concurrent_selection_statement_obeys_schedule_lock(db_candidate):
    from pydantic import SecretStr
    from app.core.config import Settings
    from app.db.session import make_engine
    # The first restricted transaction owns the shared lock from schedule reconciliation.
    s=db_candidate[0]
    settings=Settings().model_copy(update=dict(db_user='nfl_ingest',db_password=SecretStr('SYNTHETIC_INGEST_PASSWORD_123456789'),db_purpose='runtime'))
    engine=make_engine(settings)
    try:
        with engine.connect() as other:
            with pytest.raises(DBAPIError) as error:
                with other.begin():
                    other.execute(text("SET LOCAL lock_timeout='100ms'"))
                    # Even with no matching rows, BEFORE STATEMENT must acquire the lock first.
                    other.execute(text('UPDATE team_stats_accepted SET generation=generation+1 WHERE false'))
            assert error.value.orig.sqlstate=='55P03'
        assert s.scalar(select(func.count()).select_from(TeamStatsAccepted))==0
    finally:engine.dispose()


@pytest.mark.database
def test_runtime_engine_refuses_bootstrap_credentials(pg_engine):
    from app.core.config import Settings
    from app.db.session import make_engine
    engine=make_engine(Settings().model_copy(update=dict(db_purpose='runtime')))
    try:
        with pytest.raises(ValueError,match='restricted_runtime_role_required'):
            with engine.connect():pass
    finally:engine.dispose()


def test_cli_refuses_admin_override(tmp_path,monkeypatch,capsys):
    import ingestion.team_stats.ingest as cli
    monkeypatch.setattr(cli,'Settings',lambda:SimpleNamespace(db_host='db',db_name='nfl_research_dev',db_purpose='migration'))
    monkeypatch.setattr(cli,'make_engine',lambda _:pytest.fail('admin engine must not be opened'))
    assert cli.main(['--rollback-batch',str(uuid4()),'--report-dir',str(tmp_path)])==2
    assert 'restricted_runtime_configuration_required' in capsys.readouterr().out
