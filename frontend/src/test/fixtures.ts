// Synthetic fixtures only. Never bundled as application fallback data.
import type { FreshnessResponse, Game, GameResponse, Policy, ScheduleResponse, SeasonsResponse, StageCoverage } from '../api/types';
export const id = '00000000-0000-0000-0000-000000000001';
export const policy: Policy = { provider:'nflverse',score_semantics:'Reported scores are not verified final results.',coverage_semantics:'Imported records only.',limitations:['Declared origin is not independently authenticated.','The original CSV checksum discrepancy remains unresolved.'] };
export const coverage = (stage: 'REG'|'POST', count=1): StageCoverage => ({season_type:stage,game_count:count,weeks:count ? stage === 'REG' ? [1,2] : [19] : [],rounds:count && stage === 'POST' ? ['WC'] : [],reported_score_pairs:count,missing_score_pairs:0,unknown_status_games:count,final_status_games:0,unknown_kickoff_games:0,unverified_origin_games:count});
export const seasons: SeasonsResponse = {data:[2024,2025,2026].map(season => ({season,coverage:[coverage('REG',2),coverage('POST',season === 2026 ? 0 : 1)]})),meta:{...policy,supported_seasons:[2024,2025,2026],missing_seasons:[],returned_count:3}};
export function game(changes: Partial<Game> = {}): Game { return { id,season:2026,season_type:'REG',week:1,game_type:'REG',home_team:{id:'synthetic-home',code:'AAA',name:'Synthetic Home'},away_team:{id:'synthetic-away',code:'BBB',name:'Synthetic Away'},scheduled_kickoff_utc:'2026-09-13T17:00:00Z',source_gameday:'2026-09-13',source_gametime:'13:00:00',source_timezone:'America/New_York',reported_home_score:0,reported_away_score:7,status:'UNKNOWN',score_finality:'UNVERIFIED',final_evidence:null,neutral_site:null,overtime:null,updated_at:'2026-11-07T00:00:00Z',provenance:{artifact_id:'synthetic-artifact',provider:'nflverse',source_game_id:'synthetic-game',artifact_sha256:'a'.repeat(64),source_record_sha256:'b'.repeat(64),source_line:2,origin_status:'DECLARED',documented_source_url:'https://example.invalid/synthetic-source',declared_source_url:null,source_revision:null,publisher_sha256:null,origin_verified_at:null,verification_method:null,provider_published_at:null,retrieved_at:null,recorded_at:'2026-11-07T00:00:00Z',license_url:'https://creativecommons.org/licenses/by/4.0/',attribution:'Synthetic test fixture'},...changes }; }
export function schedule(data: Game[] = [game()]): ScheduleResponse { return {data,meta:{...policy,season:2026,filters:{season_type:'REG',week:1,round:null},returned_count:data.length,season_coverage:[coverage('REG',2),coverage('POST',0)]}}; }
export const detail = (data=game()): GameResponse => ({data,meta:policy});

export const freshness: FreshnessResponse = {
  data: { metadata_state:'missing',latest_outcome:null,last_attempt_at:null,last_successful_check_at:null,
    last_successful_apply_at:null,last_data_change_observed_at:null,check_age_seconds:null,is_stale:null },
  meta: { as_of:'2026-11-09T12:00:00Z',manual:true,scope:'guarded_manual_refresh_runner',stale_after_seconds:129600,
    apply_semantics:'Successful apply includes no-change reconciliation; data-change time is separate.',
    timestamp_semantics:'Recorded runner observations, not source publication or game completion times. No game status is inferred.' },
};

// Empty, contract-shaped league response for schedule-only regression tests.
export const emptyRankings: import('../api/research').RankingsResponse = {
  data: [], meta: {
    filters: { season: 2026, season_type: 'REG', category: null, team_id: null },
    definition_version: 'net_pass_negative_sacks_v1', statistics_semantics: 'Synthetic NET',
    score_semantics: 'Unverified', aggregate_semantics: 'Reconstructed', origin_semantics: 'Declared',
    league_team_count: 0, scheduled_games: 0, accepted_games: 0, missing_statistics_games: 0,
    unknown_status_accepted_games: 0, unverified_origin_team_games: 0, coverage_complete_for_stored_schedule: false,
    missing_metric_team_games: { passing_offense: 0, rushing_offense: 0, passing_defense: 0, rushing_defense: 0 },
    population_semantics: 'Synthetic', ranking_semantics: 'Competition', completeness_semantics: 'Stored schedule only',
  },
};
