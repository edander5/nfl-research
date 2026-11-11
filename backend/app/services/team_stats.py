from app.repositories.team_stats import METRICS
from app.schemas.team_stats import (TeamGameStats, StatsProvenance, TeamGameLogsResponse, GameLogsMeta,
    GameTeamStatsResponse, GameStatsMeta, TeamSeasonStatsResponse, TeamSeasonStats, SummaryMeta, MetricAggregate)
from app.services.schedule import GameNotFound


class TeamNotFound(Exception):
    pass

def view(row):
    values = {name: row[name] for name in TeamGameStats.model_fields if name not in ('team', 'opponent', 'provenance')}
    for prefix in ('team', 'opponent'):
        values[prefix] = dict(id=row[prefix+'_id'], code=row[prefix+'_code'], name=row[prefix+'_name'])
    values['provenance'] = StatsProvenance(**{key: row[key] for key in StatsProvenance.model_fields})
    return TeamGameStats(**values)


class TeamStatsService:
    def __init__(self, repository):
        self.repository = repository

    def require_team(self, team_id):
        team = self.repository.team(team_id)
        if team is None:
            raise TeamNotFound()
        return team

    def logs(self, team_id, filters):
        self.require_team(team_id)
        total, rows = self.repository.logs(team_id, filters)
        return TeamGameLogsResponse(data=[view(row) for row in rows], meta=GameLogsMeta(
            **filters.model_dump(), total_count=total, returned_count=len(rows)))

    def game(self, game_id):
        if not self.repository.game_exists(game_id):
            raise GameNotFound()
        rows = self.repository.game(game_id)
        if rows and (len(rows) != 2 or {row['side'] for row in rows} != {'HOME', 'AWAY'}):
            # Never return a partially accepted pair, even after unexpected privileged damage.
            from sqlalchemy.exc import SQLAlchemyError
            raise SQLAlchemyError('Incomplete accepted pair')
        return GameTeamStatsResponse(data=[view(row) for row in rows], meta=GameStatsMeta(
            game_id=game_id, statistics_available=bool(rows), returned_count=len(rows)))

    def summary(self, team_id, filters):
        team = self.require_team(team_id)
        row = self.repository.summary(team_id, filters)
        metrics = {name: MetricAggregate(total=row[name+'_total'], average=row[name+'_average'],
                                        games_with_values=row[name+'_count']) for name in METRICS}
        return TeamSeasonStatsResponse(data=TeamSeasonStats(team=team, **filters.model_dump(),
            games_with_accepted_statistics=row['games_with_accepted_statistics'], **metrics), meta=SummaryMeta())
