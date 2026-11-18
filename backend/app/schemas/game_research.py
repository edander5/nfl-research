"""Full-game, same-season research; manual thresholds are never source quotes."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.schedule import SeasonType, TeamView
from app.schemas.team_stats import SeasonFilters, StatsPolicy, TeamGameStats

ResearchWindow = Literal['L3', 'L5', 'L10', 'L20', 'SEASON', 'H2H']
TotalOutcome = Literal['OVER', 'UNDER', 'PUSH', 'UNDETERMINED']


class GameResearchFilters(SeasonFilters):
    matchup_id: UUID
    window: ResearchWindow = 'L5'
    market: Literal['GAME_TOTAL'] = 'GAME_TOTAL'
    period: Literal['FULL_GAME'] = 'FULL_GAME'
    line: Decimal | None = Field(default=None, ge=0, le=1000000, max_digits=13,
                                 decimal_places=6, allow_inf_nan=False)
    side: Literal['OVER', 'UNDER'] = 'OVER'

    @property
    def game_limit(self):
        return int(self.window[1:]) if self.window.startswith('L') else None


class ReferenceTotalProvenance(BaseModel):
    artifact_id: UUID
    artifact_sha256: str
    source_record_sha256: str
    artifact_retrieved_at: datetime | None
    artifact_recorded_at: datetime
    origin_status: str
    source_url: str | None
    license_url: str | None
    attribution: str | None


class HistoricalTotalReference(BaseModel):
    line: Decimal | None = None
    outcome: TotalOutcome = 'UNDETERMINED'
    unavailable_reason: str | None = None
    classification: Literal['UNVERIFIED_SOURCE_REFERENCE'] = 'UNVERIFIED_SOURCE_REFERENCE'
    provider: Literal['nflverse'] = 'nflverse'
    bookmaker: None = None
    quote_updated_at: None = None
    freshness: Literal['UNKNOWN'] = 'UNKNOWN'
    provenance: ReferenceTotalProvenance | None = None
    warnings: list[str] = Field(default_factory=list)


class GameTotalObservation(TeamGameStats):
    combined_points: int | None
    scores_available: bool
    outcome: TotalOutcome
    outcome_unavailable_reason: Literal['scores_unavailable', 'threshold_required'] | None
    reference_total: HistoricalTotalReference


class GameTotalSummary(BaseModel):
    eligible_game_count: int
    games_with_usable_scores: int
    games_without_usable_scores: int
    average_combined_points: float | None
    over_count: int | None
    under_count: int | None
    push_count: int | None
    hit_rate: float | None
    hit_rate_numerator: int | None
    hit_rate_denominator: int | None
    hit_rate_denominator_policy: Literal['usable_scores_including_pushes'] = 'usable_scores_including_pushes'
    hit_rate_unit: Literal['fraction'] = 'fraction'
    outcomes_unavailable_reason: Literal['threshold_required', 'no_usable_scores'] | None


class GameTotalResearch(BaseModel):
    team: TeamView
    season: int
    season_type: SeasonType
    matchup_id: UUID
    opponent_id: UUID | None
    market: Literal['GAME_TOTAL'] = 'GAME_TOTAL'
    period: Literal['FULL_GAME'] = 'FULL_GAME'
    window: ResearchWindow
    requested_game_count: int | None
    line: Decimal | None
    threshold_origin: Literal['MANUAL'] | None
    side: Literal['OVER', 'UNDER']
    availability: Literal['AVAILABLE', 'PARTIAL', 'EMPTY', 'UNAVAILABLE']
    observations: list[GameTotalObservation]
    summary: GameTotalSummary


class GameResearchMeta(StatsPolicy):
    cutoff_utc: datetime | None
    selection_mode: Literal['before_matchup'] = 'before_matchup'
    unavailable_reason: Literal['matchup_kickoff_unknown', 'opponent_identity_unknown', 'no_h2h_games', 'no_eligible_games'] | None
    available_eligible_games: int
    accepted_games_in_scope: int
    excluded_unknown_kickoff_games: int
    excluded_at_or_after_matchup_games: int
    scheduled_games_in_scope: int
    scheduled_games_without_accepted_statistics: int
    selected_unknown_status_games: int
    selected_unverified_score_games: int
    games_with_reference_total: int
    games_without_reference_total: int
    window_complete: bool
    scores_complete: bool
    references_complete: bool
    cross_season: Literal[False] = False
    completion_before_cutoff_verified: Literal[False] = False
    reference_lines_verified_pregame: Literal[False] = False
    selection_semantics: str = 'Current accepted reciprocal rows with known kickoff strictly before matchup, excluding matchup itself. Select requested latest N before checking scores; no backfill. SEASON selects all in the requested season/stage; H2H selects all against the canonical matchup opponent in that same season/stage. Observations newest-first by kickoff/source ID/UUID. No cross-season or combined-stage mode.'
    score_semantics: str = 'Combined points require both source-reported scores. Missing scores are unknown, never zero or Under. UNKNOWN and score finality remain unchanged; earlier kickoff does not verify completion or pregame publication availability.'
    threshold_semantics: str = 'Manual Decimal line is independent of every historical source reference. OVER when combined points > line, UNDER when < line, PUSH on equality. No line means counts/outcomes/rates unavailable, not losses. Hit rate is selected-side hits / usable-score count, including pushes in that denominator; empty denominators produce null. It is a provisional historical frequency, not a prediction or settled wager result.'
    reference_semantics: str = 'Identity/hash-validated nflverse source-reference total only. Bookmaker and quote timing unknown; artifact observation dates are not odds update dates. Never verified opening/closing/pregame quotes. Missing references do not remove score observations.'


class GameResearchResponse(BaseModel):
    data: GameTotalResearch
    meta: GameResearchMeta
