import type { SeasonType, Team as TeamView } from './types';

export type RankingStage = SeasonType | 'COMBINED';
export type Category = 'passing_offense' | 'rushing_offense' | 'passing_defense' | 'rushing_defense';
export interface RankedTeam {
  team: TeamView; rank: number | null; eligible: boolean; average: number | null; total_yards: number | null;
  games_with_values: number; games_with_accepted_statistics: number; scheduled_games: number;
  missing_statistics_games: number; missing_metric_games: number;
}
export interface StatsPolicy {
  definition_version: 'net_pass_negative_sacks_v1'; statistics_semantics: string; score_semantics: string;
  aggregate_semantics: string; origin_semantics: string;
}
export interface RankingsResponse {
  data: { category: Category; direction: 'descending' | 'ascending'; eligible_team_count: number; teams: RankedTeam[] }[];
  meta: StatsPolicy & {
    filters: { season: number; season_type: RankingStage; category: Category | null; team_id: string | null };
    league_team_count: number; scheduled_games: number; accepted_games: number; missing_statistics_games: number;
    unknown_status_accepted_games: number; missing_metric_team_games: Record<Category, number>;
    unverified_origin_team_games: number; coverage_complete_for_stored_schedule: boolean;
    population_semantics: string; ranking_semantics: string; completeness_semantics: string;
  };
}
export interface TeamGameStats {
  game_id: string; source_game_id: string; season: number; season_type: SeasonType; week: number;
  scheduled_kickoff_utc: string | null; source_gameday: string | null; team: TeamView; opponent: TeamView;
  side: 'HOME' | 'AWAY'; gross_passing_yards: number | null; original_sack_yards: number | null;
  net_passing_yards: number | null; rushing_yards: number | null;
  net_passing_yards_allowed: number | null; rushing_yards_allowed: number | null;
  reported_points_scored: number | null; reported_points_allowed: number | null;
  status: 'UNKNOWN' | 'FINAL'; score_finality: 'NOT_REPORTED' | 'UNVERIFIED' | 'CONFIRMED_FINAL';
  accepted_pair_id: string; selection_generation: number; revision_recorded_at: string;
  schedule_source_artifact_id: string;
  provenance: { artifact_id: string; provider: string; artifact_sha256: string; origin_status: 'DECLARED' | 'VERIFIED';
    documented_source_url: string | null; license_url: string | null; attribution: string | null;
    source_record_sha256: string; source_line: number | null };
}
export interface TeamGamesResponse {
  data: TeamGameStats[];
  meta: StatsPolicy & { season: number; season_type: SeasonType; week: number | null;
    limit: number; offset: number; total_count: number; returned_count: number };
}
async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal, headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(response.status === 404 ? 'Team research is unavailable for this selection.' :
    response.status === 422 ? 'These research filters are not supported.' : 'The research service is unavailable. Please try again.');
  if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('The server returned an unexpected response.');
  return response.json() as Promise<T>;
}
export const research = {
  comparison: (season: number, stage: RankingStage, signal?: AbortSignal) =>
    get<RankingsResponse>(`/api/team-rankings?${new URLSearchParams({ season: String(season), season_type: stage })}`, signal),
  rankings: (season: number, stage: RankingStage, category: Category, signal?: AbortSignal) =>
    get<RankingsResponse>(`/api/team-rankings?${new URLSearchParams({ season: String(season), season_type: stage, category })}`, signal),
  games: (id: string, season: number, stage: SeasonType, offset: number, signal?: AbortSignal) =>
    get<TeamGamesResponse>(`/api/teams/${encodeURIComponent(id)}/games?${new URLSearchParams({ season: String(season), season_type: stage, limit: '20', offset: String(offset) })}`, signal),
};
