"""Transactional reconciliation. Caller owns the transaction and must roll it back on error."""
import hashlib
import json
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Game, SourceArtifact, Team, TeamAlias
from ingestion.validation import Snapshot, TEAM_CODES, Problem, ValidationFailure

PROVIDER = 'nflverse'
SOURCE_URL = 'https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv'


def reject(code: str, message: str):
    raise ValidationFailure([Problem(code, None, 'database', message)])


def capture(snapshot: Snapshot, directory: Path) -> Path:
    """Keep exact source bytes, never overwrite an existing artifact or the input."""
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f'{snapshot.sha256}.csv'
    try:
        with target.open('xb') as stream:
            stream.write(snapshot.data)
    except FileExistsError:
        if hashlib.sha256(target.read_bytes()).hexdigest() != snapshot.sha256:
            reject('snapshot_collision', 'Existing archive bytes do not match their filename hash')
    return target.resolve()


def reconcile(session: Session, snapshot: Snapshot, artifact_path: Path) -> dict:
    """Apply a prevalidated full snapshot; no commit, deletion or status inference."""
    database = session.scalar(text('select current_database()'))
    if database not in ('nfl_research_dev', 'nfl_research_test'):
        reject('database_guard', 'Only isolated nfl_research_dev/nfl_research_test databases are allowed')
    # Serialize importers, including a first import where no game row exists to lock.
    session.execute(text('select pg_advisory_xact_lock(202426, 1)'))
    existing = list(session.scalars(select(Game).where(Game.provider == PROVIDER).with_for_update()))
    teams = {t.code: t for t in session.scalars(select(Team))}
    aliases = {a.source_team_code: a for a in session.scalars(select(TeamAlias).where(TeamAlias.provider == PROVIDER))}
    for code, alias in aliases.items():
        if code not in teams or alias.team_id != teams[code].id:
            reject('team_alias_conflict', 'Existing provider alias disagrees with canonical team code')
    by_id = {g.source_game_id: g for g in existing}
    incoming_ids = {r.values['source_game_id'] for r in snapshot.rows}
    matches, used, corrections = [], set(), []
    for row in snapshot.rows:
        game = by_id.get(row.values['source_game_id'])
        if game is None:
            espn = (row.values['external_ids'] or {}).get('espn')
            candidates = [g for g in existing if espn and (g.external_ids or {}).get('espn') == espn
                          and g.season == row.values['season']
                          and {g.source_home_team, g.source_away_team} == {row.values['source_home_team'], row.values['source_away_team']}]
            if len(candidates) > 1:
                reject('ambiguous_identity', 'Multiple existing games match an ESPN identity')
            if candidates:
                game = candidates[0]
                if game.source_game_id in incoming_ids:
                    reject('identity_collision', 'Both old and corrected source IDs occur in the snapshot')
        if game:
            if game.id in used:
                reject('identity_collision', 'Two source rows map to one canonical game')
            used.add(game.id)
            if game.source_record_sha256 == row.sha256:
                home = teams.get(row.values['source_home_team'])
                away = teams.get(row.values['source_away_team'])
                if (any(getattr(game, key) != value for key, value in row.values.items())
                    or home is None or away is None
                    or game.home_team_id != home.id or game.away_team_id != away.id
                    or game.raw_source_record != row.raw):
                    reject('stored_record_mismatch', 'Stored game disagrees with its unchanged source record; review before repair')
            if game.source_record_sha256 != row.sha256:
                if game.status != 'UNKNOWN':
                    reject('final_correction', 'Correction touches independently finalized game; explicit evidence review required')
                corrections.append(dict(canonical_id=str(game.id), previous_source_id=game.source_game_id,
                                        previous_artifact_id=str(game.source_artifact_id), previous_record_sha256=game.source_record_sha256,
                                        new_source_id=row.values['source_game_id'], new_record_sha256=row.sha256))
        matches.append((row, game))
    if any(g.id not in used for g in existing):
        reject('missing_existing_games', 'Snapshot omits existing games; deletions and ambiguous source-ID changes require review')
    inserted = sum(g is None for _, g in matches)
    updated = len(corrections)
    result = dict(inserted=inserted, updated=updated, unchanged=len(matches)-inserted-updated,
                  selected=len(matches), rows_read=snapshot.rows_read, sha256=snapshot.sha256, counts=snapshot.counts(),
                  reported_scores=snapshot.score_counts(), warnings=list(snapshot.warnings))
    if not inserted and not updated:
        return result
    # SourceArtifact retains an immutable snapshot and append-only correction receipt.
    artifact = SourceArtifact(
        provider=PROVIDER, artifact_path=str(artifact_path), sha256=snapshot.sha256,
        byte_size=len(snapshot.data), documented_source_url=SOURCE_URL,
        declared_source_url=None, origin_status='DECLARED',
        license_url='https://creativecommons.org/licenses/by/4.0/',
        attribution='Schedule data: nflverse / Lee Sharpe (nfldata), via nflverse-data schedules release; CC BY 4.0. Modified: team normalization and Eastern-to-UTC conversion.',
        provenance_notes=json.dumps(dict(kind='schedule_import', version=1,
            origin='Owner-declared official download; independently authenticated origin unresolved; published checksum discrepancy remains open',
            historical_listing_sha256='0284c8bfa49ee3707d5d77844d264919c29a586378bb0304734e38ca65654583',
            historical_listing_observed_date='2026-11-05',
            corrections=corrections, summary=result), sort_keys=True),
    )
    session.add(artifact)
    session.flush()
    for code in TEAM_CODES:
        if code not in teams:
            teams[code] = Team(code=code, name=code)  # Source supplies codes, not verified display names.
            session.add(teams[code])
    session.flush()
    for code in TEAM_CODES:
        if code in aliases:
            if aliases[code].team_id != teams[code].id:
                reject('team_alias_conflict', 'Existing provider alias disagrees with canonical team code')
        else:
            session.add(TeamAlias(provider=PROVIDER, source_team_code=code, team_id=teams[code].id))
    for row, game in matches:
        if game is not None and game.source_record_sha256 == row.sha256:
            continue
        values = dict(row.values, home_team_id=teams[row.values['source_home_team']].id,
                      away_team_id=teams[row.values['source_away_team']].id,
                      source_artifact_id=artifact.id, source_record_sha256=row.sha256,
                      source_line=row.line, raw_source_record=row.raw)
        if game is None:
            session.add(Game(provider=PROVIDER, status='UNKNOWN', **values))
        else:
            for key, value in values.items():
                setattr(game, key, value)
    session.flush()
    result['artifact_id'] = str(artifact.id)
    return result
