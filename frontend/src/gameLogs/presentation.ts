import type { TeamGameStats } from '../api/research';
import type { MarketsResponse } from '../api/markets';

export function newestFirst(rows: TeamGameStats[]) {
  const timestamp = (row: TeamGameStats) => {
    const value = row.scheduled_kickoff_utc ? Date.parse(row.scheduled_kickoff_utc) : NaN;
    return Number.isFinite(value) ? value : null;
  };
  return [...rows].sort((a, b) => {
    const at = timestamp(a), bt = timestamp(b);
    if (at !== null && bt !== null && at !== bt) return bt - at;
    if (at === null || bt === null) {
      if (at !== bt) return at === null ? 1 : -1;
    }
    return b.week - a.week || a.source_game_id.localeCompare(b.source_game_id) || a.game_id.localeCompare(b.game_id);
  });
}

/** Select the backend's team-oriented result; never calculate a cover or total in the browser. */
export function referenceFor(row: TeamGameStats, response: MarketsResponse | undefined) {
  if (!response || response.data.game.id !== row.game_id) return undefined;
  const game = response.data.game;
  const own = row.side === 'HOME' ? game.home_team : game.away_team;
  const opponent = row.side === 'HOME' ? game.away_team : game.home_team;
  if (own.id !== row.team.id || opponent.id !== row.opponent.id ||
      (row.side === 'HOME' ? game.reported_home_score : game.reported_away_score) !== row.reported_points_scored ||
      (row.side === 'HOME' ? game.reported_away_score : game.reported_home_score) !== row.reported_points_allowed) return undefined;
  // The current contract has at most one reference. Never silently choose a book if that changes.
  if (response.data.references.length !== 1) return undefined;
  return response.data.references[0];
}
