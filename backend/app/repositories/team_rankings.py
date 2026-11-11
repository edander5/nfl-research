"""One SQL statement for league population, scheduled coverage and accepted aggregates."""
from sqlalchemy import case, func, or_, select
from app.models import Game, Team
from app.repositories.team_stats import accepted_query

CATEGORIES = {
    'passing_offense': ('net_passing_yards', 'descending'),
    'rushing_offense': ('rushing_yards', 'descending'),
    'passing_defense': ('net_passing_yards_allowed', 'ascending'),
    'rushing_defense': ('rushing_yards_allowed', 'ascending'),
}


def league_query(filters):
    games = select(Game.id, Game.home_team_id, Game.away_team_id, Game.season_type).where(
        Game.provider == 'nflverse', Game.season == filters.season).cte('season_games')
    # Population includes regular-season teams even for a postseason query with no statistics.
    sides = select(games.c.home_team_id.label('team_id')).union(
        select(games.c.away_team_id.label('team_id'))).cte('population')
    stage = filters.season_type
    scheduled = select(Team.id.label('team_id'), func.count(games.c.id).label('scheduled_games')).select_from(
        Team).join(games, or_(games.c.home_team_id == Team.id, games.c.away_team_id == Team.id))
    if stage != 'COMBINED':
        scheduled = scheduled.where(games.c.season_type == stage)
    scheduled = scheduled.group_by(Team.id).cte('scheduled')
    source = accepted_query().subquery()
    stats = select(source).where(source.c.season == filters.season)
    if stage != 'COMBINED':
        stats = stats.where(source.c.season_type == stage)
    stats = stats.cte('accepted')
    fields = [stats.c.team_id, func.count().label('accepted_count'),
              func.sum(case((stats.c.status == 'UNKNOWN', 1), else_=0)).label('unknown_count'),
              func.sum(case((stats.c.origin_status != 'VERIFIED', 1), else_=0)).label('unverified_count')]
    for category, (metric, _) in CATEGORIES.items():
        fields.extend((func.sum(stats.c[metric]).label(category+'_total'),
                       func.count(stats.c[metric]).label(category+'_count')))
    totals = select(*fields).group_by(stats.c.team_id).cte('totals')
    return select(Team.id.label('team_id'), Team.code, Team.name,
        func.coalesce(scheduled.c.scheduled_games, 0).label('scheduled_games'),
        func.coalesce(totals.c.accepted_count, 0).label('accepted_count'),
        func.coalesce(totals.c.unknown_count, 0).label('unknown_count'),
        func.coalesce(totals.c.unverified_count, 0).label('unverified_count'),
        *[column for column in totals.c if column.key not in ('team_id','accepted_count','unknown_count','unverified_count')]
    ).select_from(sides).join(Team, Team.id == sides.c.team_id).outerjoin(
        scheduled, scheduled.c.team_id == Team.id).outerjoin(totals, totals.c.team_id == Team.id).order_by(Team.code, Team.id)


class TeamRankingsRepository:
    def __init__(self, session):
        self.session = session

    def league(self, filters):
        return self.session.execute(league_query(filters)).mappings().all()
