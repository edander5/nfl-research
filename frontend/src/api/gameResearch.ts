import { getResearch } from './research';
import type { StatsPolicy, TeamGameStats } from './research';
import type { Game, Team } from './types';

export type ResearchWindow = 'L3' | 'L5' | 'L10' | 'L20' | 'SEASON' | 'H2H';
export type ResearchSide = 'OVER' | 'UNDER';
export type TotalOutcome = ResearchSide | 'PUSH' | 'UNDETERMINED';
export interface TotalReference {
  line: string | null; outcome: TotalOutcome; unavailable_reason: string | null;
  classification: 'UNVERIFIED_SOURCE_REFERENCE'; provider: 'nflverse'; bookmaker: null;
  quote_updated_at: null; freshness: 'UNKNOWN'; warnings: string[];
  provenance: { artifact_id: string; artifact_sha256: string; source_record_sha256: string;
    artifact_retrieved_at: string | null; artifact_recorded_at: string; origin_status: string;
    source_url: string | null; license_url: string | null; attribution: string | null } | null;
}
export interface GameObservation extends TeamGameStats {
  combined_points: number | null; scores_available: boolean; outcome: TotalOutcome;
  outcome_unavailable_reason: 'scores_unavailable' | 'threshold_required' | null; reference_total: TotalReference;
}
export interface GameResearchResponse {
  data: { team: Team; season: number; season_type: 'REG' | 'POST'; matchup_id: string; opponent_id: string | null;
    market: 'GAME_TOTAL'; period: 'FULL_GAME'; window: ResearchWindow; requested_game_count: number | null;
    line: string | null; threshold_origin: 'MANUAL' | null; side: ResearchSide;
    availability: 'AVAILABLE' | 'PARTIAL' | 'EMPTY' | 'UNAVAILABLE'; observations: GameObservation[];
    summary: { eligible_game_count: number; games_with_usable_scores: number; games_without_usable_scores: number;
      average_combined_points: number | null; over_count: number | null; under_count: number | null; push_count: number | null;
      hit_rate: number | null; hit_rate_numerator: number | null; hit_rate_denominator: number | null;
      hit_rate_denominator_policy: 'usable_scores_including_pushes'; hit_rate_unit: 'fraction';
      outcomes_unavailable_reason: 'threshold_required' | 'no_usable_scores' | null } };
  meta: StatsPolicy & { cutoff_utc: string | null; selection_mode: 'before_matchup';
    unavailable_reason: 'matchup_kickoff_unknown' | 'opponent_identity_unknown' | 'no_h2h_games' | 'no_eligible_games' | null;
    available_eligible_games: number; accepted_games_in_scope: number; excluded_unknown_kickoff_games: number;
    excluded_at_or_after_matchup_games: number; scheduled_games_in_scope: number; scheduled_games_without_accepted_statistics: number;
    selected_unknown_status_games: number; selected_unverified_score_games: number; games_with_reference_total: number;
    games_without_reference_total: number; window_complete: boolean; scores_complete: boolean; references_complete: boolean;
    cross_season: false; completion_before_cutoff_verified: false; reference_lines_verified_pregame: false;
    selection_semantics: string; threshold_semantics: string; reference_semantics: string };
}

// Canonical decimal control state, not a statistic or outcome calculation.
export function canonicalLine(value: string): string | null | undefined {
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (!/^\d{1,7}(?:\.\d{0,6})?$/.test(trimmed) || Number(trimmed) > 1000000) return undefined;
  const [whole, fraction = ''] = trimmed.split('.');
  const decimals = fraction.replace(/0+$/, '');
  return `${whole.replace(/^0+(?=\d)/, '')}${decimals ? '.' + decimals : ''}`;
}

export async function gameResearch(team: Team, game: Game, window: ResearchWindow, line: string | null,
  side: ResearchSide, signal?: AbortSignal): Promise<GameResearchResponse> {
  const params = new URLSearchParams({season:String(game.season),season_type:game.season_type,
    matchup_id:game.id,window,side,market:'GAME_TOTAL',period:'FULL_GAME'});
  if (line !== null) params.set('line',line);
  const response = await getResearch<GameResearchResponse>(`/api/teams/${encodeURIComponent(team.id)}/game-research?${params}`,signal);
  const data = response?.data, meta = response?.meta, summary = data?.summary;
  const integer = (value: unknown): value is number => typeof value === 'number' && Number.isInteger(value) && value >= 0;
  const nullableNumber = (value: unknown) => value === null || typeof value === 'number' && Number.isFinite(value) && value >= 0;
  const outcome = (value: unknown) => ['OVER','UNDER','PUSH','UNDETERMINED'].includes(String(value));
  const opponent = team.id === game.away_team.id ? game.home_team : game.away_team;
  const size = window.startsWith('L') ? Number(window.slice(1)) : null;
  if (data?.team?.id !== team.id || data.season !== game.season || data.season_type !== game.season_type ||
    data.matchup_id !== game.id || data.window !== window || data.side !== side || data.market !== 'GAME_TOTAL' || data.period !== 'FULL_GAME' ||
    data.line !== line || data.threshold_origin !== (line === null ? null : 'MANUAL') || data.requested_game_count !== size ||
    !['AVAILABLE','PARTIAL','EMPTY','UNAVAILABLE'].includes(data.availability) ||
    (data.opponent_id !== opponent.id && !(data.availability === 'UNAVAILABLE' && data.opponent_id === null)) ||
    meta?.selection_mode !== 'before_matchup' || meta.cross_season !== false || meta.completion_before_cutoff_verified !== false || meta.reference_lines_verified_pregame !== false ||
    !Array.isArray(data.observations) || !integer(summary?.eligible_game_count) || summary.eligible_game_count !== data.observations.length ||
    (size !== null && data.observations.length > size) || new Set(data.observations.map(row => row.game_id)).size !== data.observations.length ||
    !integer(summary.games_with_usable_scores) || !integer(summary.games_without_usable_scores) || !nullableNumber(summary.average_combined_points) ||
    !nullableNumber(summary.hit_rate) || (summary.hit_rate !== null && summary.hit_rate > 1) ||
    (line === null && [summary.over_count,summary.under_count,summary.push_count,summary.hit_rate,summary.hit_rate_numerator,summary.hit_rate_denominator].some(value => value !== null)) ||
    ![summary.over_count,summary.under_count,summary.push_count,summary.hit_rate_numerator,summary.hit_rate_denominator].every(value => value === null || integer(value)) ||
    summary.hit_rate_denominator_policy !== 'usable_scores_including_pushes' || summary.hit_rate_unit !== 'fraction' ||
    ![meta.excluded_unknown_kickoff_games,meta.games_without_reference_total,meta.selected_unknown_status_games,meta.selected_unverified_score_games].every(integer) ||
    ![meta.window_complete,meta.scores_complete,meta.references_complete].every(value => typeof value === 'boolean') ||
    (data.observations.length > 0 && (!meta.cutoff_utc || !Number.isFinite(Date.parse(meta.cutoff_utc)))) ||
    data.observations.some(row => !row || row.team?.id !== team.id || row.season !== game.season || row.season_type !== game.season_type ||
      row.game_id === game.id || !row.opponent?.id || !['HOME','AWAY'].includes(row.side) ||
      !row.scheduled_kickoff_utc || !Number.isFinite(Date.parse(row.scheduled_kickoff_utc)) || Date.parse(row.scheduled_kickoff_utc) >= Date.parse(meta.cutoff_utc!) ||
      (window === 'H2H' && row.opponent.id !== opponent.id) || !nullableNumber(row.combined_points) || typeof row.scores_available !== 'boolean' ||
      row.scores_available !== (row.combined_points !== null) || (line === null && row.outcome !== 'UNDETERMINED') ||
      !nullableNumber(row.reported_points_scored) || !nullableNumber(row.reported_points_allowed) || !outcome(row.outcome) ||
      !['UNKNOWN','FINAL'].includes(row.status) || !['NOT_REPORTED','UNVERIFIED','CONFIRMED_FINAL'].includes(row.score_finality) ||
      !row.reference_total || !outcome(row.reference_total.outcome) || row.reference_total.classification !== 'UNVERIFIED_SOURCE_REFERENCE' ||
      row.reference_total.bookmaker !== null || row.reference_total.quote_updated_at !== null || row.reference_total.freshness !== 'UNKNOWN' ||
      (row.reference_total.line !== null && (typeof row.reference_total.line !== 'string' || canonicalLine(row.reference_total.line) == null)))) {
    throw new Error('Invalid Game Total research response.');
  }
  return response;
}
