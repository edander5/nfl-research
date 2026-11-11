"""Explicit column projections from accepted pairs, with reciprocal opponent joins."""
from sqlalchemy import and_, case, func, select, true
from sqlalchemy.orm import aliased

from app.models import Game, SourceArtifact, Team, TeamStatsAccepted, TeamStatsPair, TeamGameStatRevision

METRICS = ('net_passing_yards', 'rushing_yards', 'net_passing_yards_allowed', 'rushing_yards_allowed',
           'reported_points_scored', 'reported_points_allowed', 'verified_final_points_scored', 'verified_final_points_allowed')


def accepted_query():
    own, opponent = aliased(TeamGameStatRevision), aliased(TeamGameStatRevision)
    team, other = aliased(Team), aliased(Team)
    home = own.side == 'HOME'
    scored = case((home, Game.reported_home_score), else_=Game.reported_away_score)
    allowed = case((home, Game.reported_away_score), else_=Game.reported_home_score)
    final = and_(Game.status == 'FINAL', Game.final_evidence_url.is_not(None), Game.final_verified_at.is_not(None))
    return select(
        Game.id.label('game_id'), Game.source_game_id, Game.season, Game.season_type, Game.week,
        Game.scheduled_kickoff_utc, Game.source_gameday, Game.status,
        Game.source_artifact_id.label('schedule_source_artifact_id'),
        team.id.label('team_id'), team.code.label('team_code'), team.name.label('team_name'),
        other.id.label('opponent_id'), other.code.label('opponent_code'), other.name.label('opponent_name'),
        own.side, own.gross_passing_yards, own.original_sack_yards, own.net_passing_yards, own.rushing_yards,
        opponent.net_passing_yards.label('net_passing_yards_allowed'), opponent.rushing_yards.label('rushing_yards_allowed'),
        scored.label('reported_points_scored'), allowed.label('reported_points_allowed'),
        case((final, scored)).label('verified_final_points_scored'), case((final, allowed)).label('verified_final_points_allowed'),
        case((final, 'CONFIRMED_FINAL'), (scored.is_(None), 'NOT_REPORTED'), else_='UNVERIFIED').label('score_finality'),
        TeamStatsAccepted.pair_id.label('accepted_pair_id'), TeamStatsAccepted.generation.label('selection_generation'),
        TeamStatsPair.recorded_at.label('revision_recorded_at'),
        SourceArtifact.id.label('artifact_id'), SourceArtifact.provider, SourceArtifact.sha256.label('artifact_sha256'),
        SourceArtifact.origin_status, SourceArtifact.documented_source_url, SourceArtifact.license_url, SourceArtifact.attribution,
        own.source_record_sha256, own.source_line,
    ).select_from(TeamStatsAccepted).join(Game, Game.id == TeamStatsAccepted.game_id).join(
        TeamStatsPair, and_(TeamStatsPair.id == TeamStatsAccepted.pair_id, TeamStatsPair.game_id == Game.id)
    ).join(own, and_(own.pair_id == TeamStatsAccepted.pair_id, own.game_id == Game.id)).join(
        opponent, and_(opponent.pair_id == own.pair_id, opponent.game_id == own.game_id,
                       opponent.team_id == own.opponent_team_id, opponent.opponent_team_id == own.team_id,
                       opponent.side != own.side)
    ).join(team, team.id == own.team_id).join(other, other.id == own.opponent_team_id).join(
        SourceArtifact, SourceArtifact.id == TeamStatsPair.source_artifact_id
    ).where(Game.provider == 'nflverse', SourceArtifact.provider == 'nflverse',
            TeamStatsPair.definition_version == 'net_pass_negative_sacks_v1')


class TeamStatsRepository:
    def __init__(self, session):
        self.session = session

    def team(self, team_id):
        return self.session.execute(select(Team.id, Team.code, Team.name).where(Team.id == team_id)).mappings().one_or_none()

    def game_exists(self, game_id):
        return self.session.scalar(select(Game.id).where(Game.id == game_id, Game.provider == 'nflverse')) is not None

    def game(self, game_id):
        rows = self.session.execute(accepted_query().where(Game.id == game_id)).mappings().all()
        return sorted(rows, key=lambda row: (row['side'] != 'HOME', str(row['team_id'])))

    def filtered(self, team_id, filters):
        query = accepted_query().subquery()
        statement = select(query).where(query.c.team_id == team_id, query.c.season == filters.season,
                                        query.c.season_type == filters.season_type)
        if getattr(filters, 'week', None) is not None:
            statement = statement.where(query.c.week == filters.week)
        return statement.cte('accepted_stats')

    def logs(self, team_id, filters):
        rows = self.filtered(team_id, filters)
        # One statement snapshot for count and page, including offsets beyond the last row.
        total = select(func.count().label('total_count')).select_from(rows).cte('total')
        page = select(rows).order_by(rows.c.scheduled_kickoff_utc.asc().nulls_last(), rows.c.week,
                                    rows.c.source_game_id, rows.c.game_id).limit(filters.limit).offset(filters.offset).cte('page')
        result = self.session.execute(select(total.c.total_count, page).select_from(total.outerjoin(page, true()))).mappings().all()
        return result[0]['total_count'], [r for r in result if r['game_id'] is not None]

    def summary(self, team_id, filters):
        rows = self.filtered(team_id, filters)
        fields = [func.count().label('games_with_accepted_statistics')]
        for name in METRICS:
            column = rows.c[name]
            fields.extend((func.sum(column).label(name+'_total'), func.avg(column).label(name+'_average'),
                           func.count(column).label(name+'_count')))
        return self.session.execute(select(*fields).select_from(rows)).mappings().one()
