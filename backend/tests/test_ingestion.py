"""Synthetic complete schedules; no downloaded CSV is required by these tests."""
import csv
import io
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.models import Game, SourceArtifact, Team, TeamAlias
from ingestion.schedule import main
from ingestion.service import capture, reconcile
from ingestion.validation import TEAM_CODES, ValidationFailure, validate_bytes


@pytest.fixture
def source_rows():
    rows = []
    for season in (2024, 2025, 2026):
        rotation = list(TEAM_CODES)
        for round_index in range(17):
            for pair in range(16):
                home, away = rotation[pair], rotation[-pair-1]
                week = 18 if round_index == 16 and pair >= 8 else round_index+1
                rows.append(dict(game_id=f'{season}_{week:02d}_{away}_{home}', season=str(season),
                    game_type='REG', week=str(week), gameday=f'{season}-09-01', gametime='13:00',
                    home_team=home, away_team=away, home_score='0' if season < 2026 else '',
                    away_score='7' if season < 2026 else '', old_game_id='same-legacy-value',
                    espn=f'{season}{round_index:02d}{pair:02d}', overtime='', location='Home'))
            rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
        if season < 2026:
            for kind, week, count in [('WC',19,6),('DIV',20,4),('CON',21,2),('SB',22,1)]:
                for pair in range(count):
                    home, away = TEAM_CODES[pair*2:pair*2+2]
                    rows.append(dict(game_id=f'{season}_{week:02d}_{away}_{home}', season=str(season),
                        game_type=kind, week=str(week), gameday=f'{season+1}-01-01', gametime='20:00',
                        home_team=home, away_team=away, home_score='21', away_score='14',
                        old_game_id='', espn=f'{season}{week}{pair:02d}', overtime='0', location='Neutral'))
    return rows


def encode(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def snapshot(rows):
    return validate_bytes(encode(rows))


def test_complete_snapshot(source_rows):
    source = snapshot(source_rows)
    assert len(source.rows) == 842
    assert source.counts()['2024'] == dict(REG=272, WC=6, DIV=4, CON=2, SB=1)
    assert source.rows[0].values['reported_home_score'] == 0
    assert next(r for r in source.rows if r.values['season'] == 2026).values['reported_home_score'] is None
    assert source.rows[0].values['scheduled_kickoff_utc'].isoformat() == '2024-09-01T17:00:00+00:00'
    assert source.rows[272].values['scheduled_kickoff_utc'].isoformat() == '2025-01-02T01:00:00+00:00'


@pytest.mark.parametrize('field,value', [('game_id','bad'), ('home_team','XXX'), ('week','19'),
    ('game_type','PRE'), ('home_score','-1'), ('away_score',''), ('home_score','1.5'),
    ('season','202x'), ('gametime','25:00'), ('gametime','01:30'), ('gameday','bad')])
def test_invalid_row_rejected(source_rows, field, value):
    if field == 'gametime' and value == '01:30':
        source_rows[0]['gameday'] = '2024-11-03'  # Ambiguous DST fold.
    source_rows[0][field] = value
    with pytest.raises(ValidationFailure):
        snapshot(source_rows)


def test_duplicate_rejected(source_rows):
    source_rows.append(source_rows[0].copy())
    with pytest.raises(ValidationFailure, match='rejected'):
        snapshot(source_rows)


def test_truncation_rejected(source_rows):
    with pytest.raises(ValidationFailure):
        snapshot(source_rows[:-1])


def test_malformed_csv():
    with pytest.raises(ValidationFailure):
        validate_bytes(b'game_id,season\n"unterminated')


def test_unknown_kickoff_preserved(source_rows):
    source_rows[0].update(gameday='TBD', gametime='')
    assert snapshot(source_rows).rows[0].values['scheduled_kickoff_utc'] is None


def test_score_arithmetic(source_rows):
    for row in source_rows:
        row['result'] = ''
    source_rows[0]['result'] = '99'
    with pytest.raises(ValidationFailure):
        snapshot(source_rows)


def test_snapshot_capture_is_immutable(tmp_path, source_rows):
    source = snapshot(source_rows)
    path = capture(source, tmp_path)
    assert capture(source, tmp_path) == path
    assert path.read_bytes() == source.data
    path.write_bytes(b'corrupt archive')
    with pytest.raises(ValidationFailure):
        capture(source, tmp_path)


def test_cli_dry_run_without_database(tmp_path, source_rows, capsys, monkeypatch):
    path = tmp_path/'games.csv'
    path.write_bytes(encode(source_rows))
    monkeypatch.delenv('APP_DB_NAME', raising=False)
    assert main(['--file', str(path)]) == 0
    assert '"selected": 842' in capsys.readouterr().out
    assert path.read_bytes() == encode(source_rows)


def test_cli_validation_failure(tmp_path, capsys):
    path = tmp_path/'bad.csv'
    path.write_bytes(b'bad')
    assert main(['--file',str(path)]) == 2
    assert '"error": "validation"' in capsys.readouterr().err


def apply(session, rows):
    with session.begin_nested():
        return reconcile(session, snapshot(rows), Path('/synthetic/immutable.csv'))


@pytest.mark.database
def test_import_and_idempotency(db_session, source_rows):
    first = apply(db_session, source_rows)
    assert first['inserted'] == 842
    assert db_session.scalar(select(func.count()).select_from(Team)) == 32
    assert db_session.scalar(select(func.count()).select_from(TeamAlias)) == 32
    assert set(db_session.scalars(select(Game.status))) == {'UNKNOWN'}
    assert db_session.scalar(select(Game.reported_home_score).where(Game.season == 2026).limit(1)) is None
    artifact = db_session.scalar(select(SourceArtifact))
    assert artifact.origin_status == 'DECLARED' and artifact.retrieved_at is None
    assert artifact.publisher_sha256 is None and artifact.origin_verified_at is None
    second = apply(db_session, source_rows)
    assert (second['inserted'], second['updated'], second['unchanged']) == (0,0,842)
    assert db_session.scalar(select(func.count()).select_from(SourceArtifact)) == 1


@pytest.mark.database
def test_correction_and_reversion_keep_canonical_identity(db_session, source_rows):
    apply(db_session, source_rows)
    old = source_rows[0].copy()
    game = db_session.scalar(select(Game).where(Game.source_game_id == old['game_id']))
    canonical = game.id
    source_rows[0]['gametime'] = '16:00'
    assert apply(db_session, source_rows)['updated'] == 1
    assert game.id == canonical and game.source_gametime.hour == 16
    receipt = db_session.get(SourceArtifact, game.source_artifact_id).provenance_notes
    assert str(canonical) in receipt and 'previous_record_sha256' in receipt
    source_rows[0] = old
    assert apply(db_session, source_rows)['updated'] == 1
    assert game.id == canonical and game.source_gametime.hour == 13
    assert db_session.scalar(select(func.count()).select_from(SourceArtifact)) == 3


@pytest.mark.database
def test_changed_source_id_reconciles_by_espn(db_session, source_rows):
    apply(db_session, source_rows)
    old_id = source_rows[0]['game_id']
    game = db_session.scalar(select(Game).where(Game.source_game_id == old_id))
    canonical = game.id
    row = source_rows[0]
    row['home_team'], row['away_team'] = row['away_team'], row['home_team']
    row['game_id'] = f"2024_01_{row['away_team']}_{row['home_team']}"
    assert apply(db_session, source_rows)['updated'] == 1
    assert game.id == canonical and game.source_game_id == row['game_id']


@pytest.mark.database
def test_missing_existing_record_rejects_entire_import(db_session, source_rows):
    apply(db_session, source_rows)
    row = source_rows[0]
    row['home_team'], row['away_team'] = row['away_team'], row['home_team']
    row['game_id'] = f"2024_01_{row['away_team']}_{row['home_team']}"
    row['espn'] = ''  # No independent link to the previous source ID.
    with pytest.raises(ValidationFailure):
        apply(db_session, source_rows)
    assert db_session.scalar(select(func.count()).select_from(Game)) == 842
    assert db_session.scalar(select(func.count()).select_from(SourceArtifact)) == 1


@pytest.mark.database
def test_final_game_correction_rejected(db_session, source_rows):
    from datetime import datetime, timezone
    apply(db_session, source_rows)
    game = db_session.scalar(select(Game).where(Game.source_game_id == source_rows[0]['game_id']))
    game.status = 'FINAL'
    game.final_evidence_url = 'https://example.invalid/synthetic-final-evidence'
    game.final_verified_at = datetime.now(timezone.utc)
    db_session.flush()
    assert apply(db_session, source_rows)['unchanged'] == 842
    source_rows[0]['home_score'] = '1'
    with pytest.raises(ValidationFailure):
        apply(db_session, source_rows)
    assert game.status == 'FINAL'


@pytest.mark.database
def test_late_flush_failure_rolls_back_everything(db_session, source_rows, monkeypatch):
    original_flush = db_session.flush
    def broken_flush(*args, **kwargs):
        writing_games = any(isinstance(item, Game) for item in db_session.new)
        original_flush(*args, **kwargs)
        if writing_games:
            raise RuntimeError('Synthetic failure after writes')
    with pytest.raises(RuntimeError), db_session.begin_nested():
        monkeypatch.setattr(db_session, 'flush', broken_flush)
        reconcile(db_session, snapshot(source_rows), Path('/synthetic/immutable.csv'))
    monkeypatch.setattr(db_session, 'flush', original_flush)
    for model in (Game, SourceArtifact, Team, TeamAlias):
        assert db_session.scalar(select(func.count()).select_from(model)) == 0


def test_available_2026_postseason(source_rows):
    templates = [r for r in source_rows if r['season'] == '2025' and r['game_type'] == 'WC']
    for template in templates:
        row = template.copy()
        row.update(season='2026', game_id=template['game_id'].replace('2025_', '2026_'),
                   espn='new'+template['espn'], gameday='2027-01-01', home_score='', away_score='')
        source_rows.append(row)
    assert snapshot(source_rows).counts()['2026']['WC'] == 6


def test_external_id_collision(source_rows):
    source_rows[1]['espn'] = source_rows[0]['espn']
    with pytest.raises(ValidationFailure):
        snapshot(source_rows)


def test_missing_required_column(source_rows):
    for row in source_rows:
        del row['home_team']
    with pytest.raises(ValidationFailure):
        snapshot(source_rows)


@pytest.mark.database
def test_invalid_snapshot_does_not_change_previous_import(db_session, source_rows):
    apply(db_session, source_rows)
    source_rows[0]['home_score'] = '-3'
    with pytest.raises(ValidationFailure):
        apply(db_session, source_rows)
    assert db_session.scalar(select(func.count()).select_from(SourceArtifact)) == 1
    assert db_session.scalar(select(Game.reported_home_score).where(Game.source_game_id == source_rows[0]['game_id'])) == 0


@pytest.mark.database
def test_failed_correction_restores_previous_state(db_session, source_rows, monkeypatch):
    apply(db_session, source_rows)
    source_rows[0]['home_score'] = '3'
    original_flush = db_session.flush
    def broken_flush(*args, **kwargs):
        changing_game = any(isinstance(item, Game) for item in db_session.dirty)
        original_flush(*args, **kwargs)
        if changing_game:
            raise RuntimeError('Synthetic failure after correction flush')
    with pytest.raises(RuntimeError), db_session.begin_nested():
        monkeypatch.setattr(db_session, 'flush', broken_flush)
        reconcile(db_session, snapshot(source_rows), Path('/synthetic/immutable.csv'))
    monkeypatch.setattr(db_session, 'flush', original_flush)
    assert db_session.scalar(select(func.count()).select_from(SourceArtifact)) == 1
    assert db_session.scalar(select(Game.reported_home_score).where(Game.source_game_id == source_rows[0]['game_id'])) == 0


@pytest.mark.database
@pytest.mark.parametrize('drift', ['alias', 'game'])
def test_unchanged_import_rejects_database_drift(db_session, source_rows, drift):
    apply(db_session, source_rows)
    if drift == 'alias':
        alias = db_session.get(TeamAlias, ('nflverse', TEAM_CODES[0]))
        alias.team_id = db_session.scalar(select(Team.id).where(Team.code == TEAM_CODES[1]))
    else:
        game = db_session.scalar(select(Game).where(Game.source_game_id == source_rows[0]['game_id']))
        game.reported_home_score = 99
    db_session.flush()
    with pytest.raises(ValidationFailure):
        apply(db_session, source_rows)
    assert db_session.scalar(select(func.count()).select_from(SourceArtifact)) == 1
