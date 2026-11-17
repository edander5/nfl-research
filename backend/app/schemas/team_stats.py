"""Public accepted-statistics contracts; no raw records or review evidence."""
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.schedule import SeasonType, TeamView


class SeasonFilters(BaseModel):
    model_config = ConfigDict(extra='forbid')
    season: int = Field(ge=2024, le=2026)
    season_type: SeasonType


class GameLogFilters(SeasonFilters):
    week: int | None = Field(default=None, ge=1, le=22)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1000000)

    @model_validator(mode='after')
    def stage_week(self):
        if self.week is not None and ((self.season_type == 'REG' and self.week > 18)
                                     or (self.season_type == 'POST' and self.week < 19)):
            raise ValueError('Week must match season type')
        return self


class StatsPolicy(BaseModel):
    definition_version: Literal['net_pass_negative_sacks_v1'] = 'net_pass_negative_sacks_v1'
    statistics_semantics: str = 'Current accepted revisions only; NET passing = gross passing + original signed sack adjustment.'
    score_semantics: str = 'Reported schedule scores are separate from verified-final scores; statistics and timestamps do not establish completion.'
    aggregate_semantics: str = 'Reconstructed historical aggregates, not verified pregame rankings or completion eligibility.'
    origin_semantics: str = 'Declared source origin is not independent authentication; original schedule checksum uncertainty remains.'


class StatsProvenance(BaseModel):
    artifact_id: UUID
    provider: str
    artifact_sha256: str
    origin_status: Literal['DECLARED', 'VERIFIED']
    documented_source_url: str | None
    license_url: str | None
    attribution: str | None
    source_record_sha256: str
    source_line: int | None


class TeamGameStats(BaseModel):
    game_id: UUID
    source_game_id: str
    season: int
    season_type: SeasonType
    week: int
    scheduled_kickoff_utc: datetime | None
    source_gameday: date | None
    team: TeamView
    opponent: TeamView
    side: Literal['HOME', 'AWAY']
    gross_passing_yards: int | None
    original_sack_yards: int | None
    net_passing_yards: int | None
    rushing_yards: int | None
    net_passing_yards_allowed: int | None
    rushing_yards_allowed: int | None
    reported_points_scored: int | None
    reported_points_allowed: int | None
    status: Literal['UNKNOWN', 'FINAL']
    score_finality: Literal['NOT_REPORTED', 'UNVERIFIED', 'CONFIRMED_FINAL']
    accepted_pair_id: UUID
    selection_generation: int
    revision_recorded_at: datetime
    schedule_source_artifact_id: UUID
    provenance: StatsProvenance


class GameLogsMeta(StatsPolicy):
    season: int
    season_type: SeasonType
    week: int | None
    limit: int
    offset: int
    total_count: int
    returned_count: int


class TeamGameLogsResponse(BaseModel):
    data: list[TeamGameStats]
    meta: GameLogsMeta


class GameStatsMeta(StatsPolicy):
    game_id: UUID
    statistics_available: bool
    returned_count: int


class GameTeamStatsResponse(BaseModel):
    data: list[TeamGameStats]
    meta: GameStatsMeta


class MetricAggregate(BaseModel):
    total: int | None
    average: float | None
    games_with_values: int


class TeamSeasonStats(BaseModel):
    team: TeamView
    season: int
    season_type: SeasonType
    games_with_accepted_statistics: int
    net_passing_yards: MetricAggregate
    rushing_yards: MetricAggregate
    net_passing_yards_allowed: MetricAggregate
    rushing_yards_allowed: MetricAggregate
    reported_points_scored: MetricAggregate
    reported_points_allowed: MetricAggregate
    verified_final_points_scored: MetricAggregate
    verified_final_points_allowed: MetricAggregate


class SummaryMeta(StatsPolicy):
    averages: str = 'Each average uses only games with a non-null value for that metric; games_with_values is its denominator. No values means null total/average.'
    coverage: str = 'Accepted-statistics games only; absent games are not eligible zeroes. Verified-final points require stored FINAL status and final evidence.'


class TeamSeasonStatsResponse(BaseModel):
    data: TeamSeasonStats
    meta: SummaryMeta


class TrendFilters(SeasonFilters):
    window: Literal['L3', 'L5', 'L10'] = 'L5'
    matchup_id: UUID | None = None

    @property
    def game_limit(self):
        return int(self.window[1:])


class OffensiveTrends(BaseModel):
    net_passing_yards: MetricAggregate
    rushing_yards: MetricAggregate
    reported_points_scored: MetricAggregate


class DefensiveTrends(BaseModel):
    net_passing_yards_allowed: MetricAggregate
    rushing_yards_allowed: MetricAggregate
    reported_points_allowed: MetricAggregate


class TeamTrends(BaseModel):
    team: TeamView
    season: int
    season_type: SeasonType
    window: Literal['L3', 'L5', 'L10']
    requested_game_count: int
    eligible_game_count: int
    offense: OffensiveTrends
    defense: DefensiveTrends
    games: list[TeamGameStats]


class TrendsMeta(SummaryMeta):
    matchup_id: UUID | None
    cutoff_utc: datetime | None
    selection_mode: Literal['latest_accepted', 'before_matchup']
    unavailable_reason: Literal['matchup_kickoff_unknown'] | None = None
    available_eligible_games: int
    accepted_games_in_season_stage: int
    excluded_unknown_kickoff_games: int
    excluded_at_or_after_matchup_games: int
    scheduled_games_in_scope: int
    scheduled_games_without_accepted_statistics: int
    selected_unknown_status_games: int
    selected_unverified_score_games: int
    missing_metric_games: dict[str, int]
    window_complete: bool
    selected_metrics_complete: bool
    completion_before_cutoff_verified: Literal[False] = False
    selection_semantics: str = 'Latest N accepted reciprocal team-game rows with known kickoff, ordered kickoff/source ID/UUID descending. With matchup_id, require kickoff strictly before the matchup and exclude the matchup itself. Select games before counting non-null metric values; never backfill individual metrics.'
    cutoff_semantics: str = 'Chronological reconstruction from current accepted revisions, not verified completed-before-kickoff eligibility or statistics as originally published. UNKNOWN status and reported points remain unverified. Missing matchup kickoff returns unavailable trends, never an unfiltered fallback.'
    scheduled_coverage_semantics: str = 'Known-kickoff stored schedule in the requested season/stage and cutoff scope; missing accepted statistics may include future games. Unknown-kickoff games are excluded, not zero-performance games.'


class TeamTrendsResponse(BaseModel):
    data: TeamTrends
    meta: TrendsMeta
