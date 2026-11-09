"""Pure review plan plus guarded transaction adapter. No finality inference."""
import hashlib
import json
from collections import Counter
from datetime import datetime

from sqlalchemy import select, text

from app.models import Game, SourceArtifact, Team, TeamAlias
from ingestion.service import PROVIDER, reconcile


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def stored_values(game):
    return {c.name: getattr(game, c.name) for c in Game.__table__.columns}


def compare(snapshot, existing, evidence, *, context=None):
    existing = sorted(existing, key=lambda g: str(g.id))
    baseline = fingerprint(dict(games=[stored_values(g) for g in existing], context=context))
    by_id = {g.source_game_id: g for g in existing}
    incoming_ids = {r.values['source_game_id'] for r in snapshot.rows}
    used, changes, blocked = set(), [], []
    if not existing:
        blocked.append(dict(code='empty_baseline', message='Refresh requires an existing imported development schedule'))
    for row in snapshot.rows:
        game = by_id.get(row.values['source_game_id'])
        categories = []
        if game is None:
            espn = (row.values['external_ids'] or {}).get('espn')
            candidates = [g for g in existing if espn and (g.external_ids or {}).get('espn') == espn
                          and g.season == row.values['season']
                          and {g.source_home_team,g.source_away_team} == {row.values['source_home_team'],row.values['source_away_team']}]
            if len(candidates) > 1 or (candidates and candidates[0].source_game_id in incoming_ids):
                blocked.append(dict(code='ambiguous_identity', source_game_id=row.values['source_game_id']))
                continue
            if candidates:
                game = candidates[0]
                categories.append('identity_change')
        if game is not None:
            if game.id in used:
                blocked.append(dict(code='ambiguous_identity', source_game_id=row.values['source_game_id']))
                continue
            used.add(game.id)
            if game.raw_source_record is None:
                blocked.append(dict(code='missing_baseline_record', source_game_id=game.source_game_id))
            elif set(game.raw_source_record) != set(row.raw):
                blocked.append(dict(code='schema_drift', source_game_id=game.source_game_id))
            if game.source_record_sha256 == row.sha256:
                if game.raw_source_record != row.raw or any(getattr(game,k) != v for k,v in row.values.items()):
                    blocked.append(dict(code='stored_record_mismatch', source_game_id=game.source_game_id))
                continue
        before_scores = [game.reported_home_score,game.reported_away_score] if game else [None,None]
        after_scores = [row.values['reported_home_score'],row.values['reported_away_score']]
        if before_scores != after_scores:
            if after_scores[0] is None:
                categories.append('removed_scores')
                blocked.append(dict(code='score_removal', source_game_id=row.values['source_game_id']))
            else:
                categories.append('newly_reported_scores' if before_scores[0] is None else 'corrected_scores')
        if game:
            if game.status != 'UNKNOWN':
                categories.append('touches_final')
                blocked.append(dict(code='final_record_change', source_game_id=game.source_game_id))
            if game.season < 2026:
                categories.append('historical_change')
            if any(getattr(game,k) != row.values[k] for k in ('source_gameday','source_gametime','scheduled_kickoff_utc')):
                categories.append('kickoff_change')
                if game.scheduled_kickoff_utc is not None and row.values['scheduled_kickoff_utc'] is None:
                    blocked.append(dict(code='known_kickoff_removed', source_game_id=game.source_game_id))
            if any(getattr(game,k) != row.values[k] for k in ('source_home_team','source_away_team','season','week','game_type')):
                categories.append('matchup_change')
        else:
            categories.append('new_game')
            if row.values['season'] < 2026:
                categories.append('historical_change')
        before = game.raw_source_record or {} if game else {}
        fields = [dict(field=k, before=before.get(k), after=row.raw.get(k)) for k in sorted(set(before)|set(row.raw))
                  if before.get(k) != row.raw.get(k)]
        changes.append(dict(source_game_id=row.values['source_game_id'], canonical_id=str(game.id) if game else None,
                            previous_source_game_id=game.source_game_id if game else None,
                            categories=categories or ['source_record_change'], fields=fields))
    for game in existing:
        if game.id not in used:
            blocked.append(dict(code='missing_game', source_game_id=game.source_game_id, canonical_id=str(game.id)))
    review = dict(version=1, candidate_sha256=snapshot.sha256, acquisition=evidence, baseline_sha256=baseline,
                  changes=changes, blockers=blocked)
    return dict(review_token=fingerprint(review), sha256=snapshot.sha256, baseline_sha256=baseline,
                selected=len(snapshot.rows), counts=snapshot.counts(), reported_scores=snapshot.score_counts(),
                summary=dict(Counter(category for c in changes for category in c['categories'])),
                changes=changes, blockers=blocked, requires_review=bool(changes),
                warnings=list(snapshot.warnings)+(['Publisher metadata unavailable or lacks digest; origin remains DECLARED']
                    if not evidence.get('digest_matches_publisher') else ['Publisher digest matched; origin still recorded DECLARED']))


def inspect_database(session, snapshot, evidence):
    database = session.scalar(text('select current_database()'))
    if database not in ('nfl_research_dev','nfl_research_test'):
        raise ValueError('database_guard')
    session.execute(text("SET LOCAL lock_timeout = '5s'"))
    session.execute(text('select pg_advisory_xact_lock(202426, 1)'))
    games = list(session.scalars(select(Game).where(Game.provider == PROVIDER).with_for_update()))
    teams = list(session.scalars(select(Team)))
    aliases = list(session.scalars(select(TeamAlias).where(TeamAlias.provider == PROVIDER)))
    artifact_ids = {g.source_artifact_id for g in games}
    artifacts = list(session.scalars(select(SourceArtifact).where(SourceArtifact.id.in_(artifact_ids)))) if artifact_ids else []
    context = dict(teams=sorted([(str(t.id),t.code,t.name) for t in teams]),
                   aliases=sorted([(a.source_team_code,str(a.team_id)) for a in aliases]),
                   artifacts=sorted([{c.name:getattr(a,c.name) for c in SourceArtifact.__table__.columns} for a in artifacts], key=lambda a: str(a['id'])))
    plan = compare(snapshot,games,evidence,context=context)
    team_ids = {t.code:t.id for t in teams}
    if any(team_ids.get(a.source_team_code) != a.team_id for a in aliases) or any(
            team_ids.get(g.source_home_team) != g.home_team_id or team_ids.get(g.source_away_team) != g.away_team_id for g in games):
        plan['blockers'].append(dict(code='team_identity_drift'))
    latest_time = None
    for artifact in artifacts:
        try:
            acquisition = json.loads(artifact.provenance_notes or '{}').get('acquisition',{})
            stamp = (acquisition.get('metadata') or {}).get('asset_updated_at')
            if stamp:
                parsed = datetime.fromisoformat(stamp.replace('Z','+00:00'))
                if parsed.utcoffset() is None:
                    raise ValueError('unaware_source_revision')
                latest_time = max(latest_time,parsed) if latest_time else parsed
        except (ValueError,TypeError,AttributeError):
            plan['blockers'].append(dict(code='invalid_baseline_provenance'))
    stamp = (evidence.get('metadata') or {}).get('asset_updated_at')
    if latest_time and (not stamp or datetime.fromisoformat(stamp.replace('Z','+00:00')) < latest_time):
        plan['blockers'].append(dict(code='older_or_missing_source_revision'))
    return plan


class ReviewRejected(ValueError):
    pass


def guarded_apply(session, snapshot, evidence, archive, plan, approval, run_id, candidate_id):
    if plan['blockers']:
        raise ReviewRejected('blocked_changes')
    if plan['requires_review'] and approval != plan['review_token']:
        raise ReviewRejected('review_required_or_baseline_changed')
    acquisition = dict(evidence, run_id=run_id, candidate_id=candidate_id, review_token=plan['review_token'],
                       operator_reviewed=bool(plan['requires_review']))
    return reconcile(session,snapshot,archive,acquisition=acquisition)
