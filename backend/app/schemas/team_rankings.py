"""Reconstructed season rankings; never a historical pregame eligibility contract."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.schedule import TeamView
from app.schemas.team_stats import StatsPolicy

Category = Literal['passing_offense', 'rushing_offense', 'passing_defense', 'rushing_defense']


class RankingFilters(BaseModel):
    model_config = ConfigDict(extra='forbid')
    season: int = Field(ge=2024, le=2026)
    season_type: Literal['REG', 'POST', 'COMBINED'] = 'REG'
    category: Category | None = None
    team_id: UUID | None = None


class RankedTeam(BaseModel):
    team: TeamView
    rank: int | None
    eligible: bool
    average: float | None
    total_yards: int | None
    games_with_values: int
    games_with_accepted_statistics: int
    scheduled_games: int
    missing_statistics_games: int
    missing_metric_games: int


class CategoryRankings(BaseModel):
    category: Category
    direction: Literal['descending', 'ascending']
    eligible_team_count: int
    teams: list[RankedTeam]


class RankingsMeta(StatsPolicy):
    filters: RankingFilters
    league_team_count: int
    scheduled_games: int
    accepted_games: int
    missing_statistics_games: int
    unknown_status_accepted_games: int
    missing_metric_team_games: dict[str, int]
    unverified_origin_team_games: int
    coverage_complete_for_stored_schedule: bool
    population_semantics: str = 'Teams appearing in the requested season NFL schedule, across either stage. Rank uses all metric-eligible league teams before team filtering.'
    ranking_semantics: str = 'Competition ranks use exact total/count ratios without rounding. Offense descending; defense ascending. Ties sort by team code then UUID. Zero-value-count teams have null rank/average/total.'
    completeness_semantics: str = 'Coverage compares accepted statistics with stored schedule games only. Missing games/metrics are not zero; scheduled games may be future games. Coverage does not establish upstream completeness, freshness or completion.'


class TeamRankingsResponse(BaseModel):
    data: list[CategoryRankings]
    meta: RankingsMeta
