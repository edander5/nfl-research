// Mirrors backend/app/schemas/schedule.py. No alternate endpoint or field names.
export type SeasonType = 'REG' | 'POST';
export type Round = 'WC' | 'DIV' | 'CON' | 'SB';
export interface Policy { provider: string; score_semantics: string; coverage_semantics: string; limitations: string[] }
export interface StageCoverage { season_type: SeasonType; game_count: number; weeks: number[]; rounds: Round[]; reported_score_pairs: number; missing_score_pairs: number; unknown_status_games: number; final_status_games: number; unknown_kickoff_games: number; unverified_origin_games: number }
export interface SeasonCoverage { season: number; coverage: StageCoverage[] }
export interface SeasonsResponse { data: SeasonCoverage[]; meta: Policy & { supported_seasons: number[]; missing_seasons: number[]; returned_count: number } }
export interface Team { id: string; code: string; name: string }
export interface Provenance { artifact_id: string; provider: string; source_game_id: string; artifact_sha256: string; source_record_sha256: string; source_line: number | null; origin_status: 'DECLARED' | 'VERIFIED'; documented_source_url: string | null; declared_source_url: string | null; source_revision: string | null; publisher_sha256: string | null; origin_verified_at: string | null; verification_method: string | null; provider_published_at: string | null; retrieved_at: string | null; recorded_at: string; license_url: string | null; attribution: string | null }
export interface Game { id: string; season: number; season_type: SeasonType; week: number; game_type: 'REG' | Round; home_team: Team; away_team: Team; scheduled_kickoff_utc: string | null; source_gameday: string | null; source_gametime: string | null; source_timezone: 'America/New_York'; reported_home_score: number | null; reported_away_score: number | null; status: 'UNKNOWN' | 'FINAL'; score_finality: 'NOT_REPORTED' | 'UNVERIFIED' | 'CONFIRMED_FINAL'; final_evidence: { url: string; verified_at: string } | null; neutral_site: boolean | null; overtime: boolean | null; updated_at: string; provenance: Provenance }
export interface ScheduleFilters { season_type: SeasonType; week: number | null; round: Round | null }
export interface ScheduleResponse { data: Game[]; meta: Policy & { season: number; filters: ScheduleFilters; returned_count: number; season_coverage: StageCoverage[] } }
export interface GameResponse { data: Game; meta: Policy }
export interface ApiErrorResponse { error: { code: string; message: string; details: { location: (string | number)[]; type: string; message: string }[] } }
