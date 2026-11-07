from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

SeasonType = Literal['REG', 'POST']
Round = Literal['WC', 'DIV', 'CON', 'SB']
ROUND_WEEKS = {'WC': 19, 'DIV': 20, 'CON': 21, 'SB': 22}


class ScheduleFilters(BaseModel):
    model_config = ConfigDict(extra='forbid')
    season_type: SeasonType = Field(description='Required: regular season or postseason; never combined implicitly')
    week: int | None = Field(default=None, ge=1, le=22, description='REG 1–18; POST 19–22')
    round: Round | None = Field(default=None, description='POST only: WC=19, DIV=20, CON=21, SB=22')

    @model_validator(mode='after')
    def validate_stage(self):
        if self.season_type == 'REG' and (self.round is not None or (self.week is not None and self.week > 18)):
            raise ValueError('REG accepts weeks 1–18 and no postseason round')
        if self.season_type == 'POST':
            if self.week is not None and self.week < 19:
                raise ValueError('POST accepts weeks 19–22')
            if self.round is not None and self.week is not None and ROUND_WEEKS[self.round] != self.week:
                raise ValueError('Postseason round and week must agree')
        return self


class Policy(BaseModel):
    provider: str = 'nflverse'
    score_semantics: str = 'Reported scores; FINAL only when explicitly stored with final evidence. Time and scores never establish finality.'
    coverage_semantics: str = 'Coverage describes imported database records, not source freshness, external correctness or completion.'
    limitations: list[str] = Field(default_factory=lambda: [
        'UNKNOWN does not distinguish scheduled, in-progress or postponed games.',
        'Declared origin is not independently authenticated. The original CSV publisher-checksum discrepancy remains unresolved.',
        'Missing scores and kickoff times stay null. Absent postseason matchups are not fabricated.',
    ])


class StageCoverage(BaseModel):
    season_type: SeasonType
    game_count: int
    weeks: list[int]
    rounds: list[Round]
    reported_score_pairs: int
    missing_score_pairs: int
    unknown_status_games: int
    final_status_games: int
    unknown_kickoff_games: int
    unverified_origin_games: int


class SeasonCoverage(BaseModel):
    season: int
    coverage: list[StageCoverage]


class SeasonsMeta(Policy):
    supported_seasons: list[int] = Field(default_factory=lambda: [2024, 2025, 2026])
    missing_seasons: list[int]
    returned_count: int


class SeasonsResponse(BaseModel):
    data: list[SeasonCoverage]
    meta: SeasonsMeta


class TeamView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str = Field(description='Stored display name; current import uses source abbreviations')


class Provenance(BaseModel):
    artifact_id: UUID
    provider: str
    source_game_id: str
    artifact_sha256: str
    source_record_sha256: str
    source_line: int | None
    origin_status: Literal['DECLARED', 'VERIFIED']
    documented_source_url: str | None
    declared_source_url: str | None
    source_revision: str | None
    publisher_sha256: str | None
    origin_verified_at: datetime | None
    verification_method: str | None
    provider_published_at: datetime | None
    retrieved_at: datetime | None
    recorded_at: datetime = Field(description='Database artifact observation, not download/publication time')
    license_url: str | None
    attribution: str | None


class FinalEvidence(BaseModel):
    url: str
    verified_at: datetime


class GameView(BaseModel):
    id: UUID
    season: int
    season_type: SeasonType
    week: int
    game_type: Literal['REG', 'WC', 'DIV', 'CON', 'SB']
    home_team: TeamView
    away_team: TeamView
    scheduled_kickoff_utc: datetime | None
    source_gameday: date | None
    source_gametime: time | None
    source_timezone: Literal['America/New_York']
    reported_home_score: int | None
    reported_away_score: int | None
    status: Literal['UNKNOWN', 'FINAL']
    score_finality: Literal['NOT_REPORTED', 'UNVERIFIED', 'CONFIRMED_FINAL']
    final_evidence: FinalEvidence | None
    neutral_site: bool | None
    overtime: bool | None
    updated_at: datetime = Field(description='Database game update time, not actual game completion')
    provenance: Provenance


class ScheduleMeta(Policy):
    season: int
    filters: ScheduleFilters
    returned_count: int
    season_coverage: list[StageCoverage]


class ScheduleResponse(BaseModel):
    data: list[GameView]
    meta: ScheduleMeta


class GameResponse(BaseModel):
    data: GameView
    meta: Policy


class ErrorDetail(BaseModel):
    location: list[str | int]
    type: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody
