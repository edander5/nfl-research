from app.repositories.team_stats import METRICS, TREND_METRICS
from app.schemas.team_stats import (TeamGameStats, StatsProvenance, TeamGameLogsResponse, GameLogsMeta,
    GameTeamStatsResponse, GameStatsMeta, TeamSeasonStatsResponse, TeamSeasonStats, SummaryMeta, MetricAggregate,
    TeamTrendsResponse, TeamTrends, TrendsMeta)
from app.services.schedule import GameNotFound


class TeamNotFound(Exception):
    pass


class InvalidTrendMatchup(Exception):
    pass


def validate_matchup(row, team_id, filters):
    if filters.matchup_id is not None:
        if row['matchup_id'] is None:
            raise GameNotFound()
        if (row['matchup_season'] != filters.season or row['matchup_season_type'] != filters.season_type
                or team_id not in (row['matchup_home_team_id'], row['matchup_away_team_id'])):
            raise InvalidTrendMatchup()


def aggregates(row, names):
    return {name: MetricAggregate(total=row[name+'_total'], average=row[name+'_average'],
                                 games_with_values=row[name+'_count']) for name in names}


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
        metrics = aggregates(row, METRICS)
        return TeamSeasonStatsResponse(data=TeamSeasonStats(team=team, **filters.model_dump(),
            games_with_accepted_statistics=row['games_with_accepted_statistics'], **metrics), meta=SummaryMeta())

    def trends(self, team_id, filters):
        team = self.require_team(team_id)
        row, games = self.repository.trends(team_id, filters)
        validate_matchup(row, team_id, filters)
        count = row['selected_count']
        missing = {name: count-row[name+'_count'] for name in TREND_METRICS}
        metrics = aggregates(row, TREND_METRICS)
        anchored = filters.matchup_id is not None
        unknown_cutoff = anchored and row['matchup_scheduled_kickoff_utc'] is None
        return TeamTrendsResponse(data=TeamTrends(team=team, season=filters.season,
            season_type=filters.season_type, window=filters.window, requested_game_count=filters.game_limit,
            eligible_game_count=count,
            offense={name: metrics[name] for name in ('net_passing_yards', 'rushing_yards', 'reported_points_scored')},
            defense={name: metrics[name] for name in ('net_passing_yards_allowed', 'rushing_yards_allowed', 'reported_points_allowed')},
            games=[view(game) for game in games]), meta=TrendsMeta(
                matchup_id=filters.matchup_id, cutoff_utc=row['matchup_scheduled_kickoff_utc'] if anchored else None,
                selection_mode='before_matchup' if anchored else 'latest_accepted',
                unavailable_reason='matchup_kickoff_unknown' if unknown_cutoff else None,
                available_eligible_games=row['eligible_count'], accepted_games_in_season_stage=row['accepted_count'],
                excluded_unknown_kickoff_games=row['unknown_kickoff_count'],
                excluded_at_or_after_matchup_games=(row['accepted_count']-row['unknown_kickoff_count']-row['eligible_count']
                                                   if anchored and not unknown_cutoff else 0),
                scheduled_games_in_scope=row['scheduled_count'],
                scheduled_games_without_accepted_statistics=row['scheduled_count']-row['eligible_count'],
                selected_unknown_status_games=row['unknown_status_count'],
                selected_unverified_score_games=row['unverified_score_count'], missing_metric_games=missing,
                window_complete=count == filters.game_limit,
                selected_metrics_complete=count > 0 and not any(missing.values())))
