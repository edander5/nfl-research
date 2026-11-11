import type { Category, RankedTeam, RankingStage } from '../api/research';
export const categories: Record<Category, { label: string; metric: string; direction: string }> = {
  passing_offense: { label: 'Passing Offense', metric: 'NET passing yards / game', direction: 'Highest average ranks #1' },
  rushing_offense: { label: 'Rushing Offense', metric: 'Rushing yards / game', direction: 'Highest average ranks #1' },
  passing_defense: { label: 'Passing Defense', metric: 'Opponent NET passing yards allowed / game', direction: 'Lowest average allowed ranks #1' },
  rushing_defense: { label: 'Rushing Defense', metric: 'Opponent rushing yards allowed / game', direction: 'Lowest average allowed ranks #1' },
};
export const stageLabels: Record<RankingStage, string> = { REG: 'Regular season', POST: 'Postseason', COMBINED: 'Combined REG + POST' };
export type Sort = 'api' | 'rank' | 'team' | 'average' | 'total' | 'games';
export interface Selection { season: number; stage: RankingStage; category: Category; sort: Sort; dir: 'asc' | 'desc' }
export function selection(params: URLSearchParams): Selection | null {
  const year = params.get('season') ?? '2026';
  const stage = params.get('season_type') ?? 'REG';
  const category = params.get('category') ?? 'passing_offense';
  const sort = params.get('sort') ?? 'api';
  const dir = params.get('dir') ?? 'asc';
  if ([...params.keys()].some(key => params.getAll(key).length > 1) || !/^202[456]$/.test(year) ||
      !Object.hasOwn(stageLabels, stage) || !Object.hasOwn(categories, category) ||
      !['api','rank','team','average','total','games'].includes(sort) || !['asc','desc'].includes(dir)) return null;
  return { season: Number(year), stage: stage as RankingStage, category: category as Category, sort: sort as Sort, dir: dir as 'asc' | 'desc' };
}
export function paramsFor(state: Selection) {
  return new URLSearchParams({ season: String(state.season), season_type: state.stage, category: state.category, sort: state.sort, dir: state.dir });
}
export function rankingsPath(state: Selection) { return `/rankings?${paramsFor(state)}`; }
export function researchPath(id: string, state: Selection) { return `/teams/${encodeURIComponent(id)}/research?${paramsFor(state)}`; }
export function sortedTeams(rows: RankedTeam[], sort: Sort, dir: Selection['dir']) {
  if (sort === 'api') return rows;
  return rows.map((row, index) => ({ row, index })).sort((a, b) => {
    const value = (row: RankedTeam): number | string | null => sort === 'team' ? row.team.code :
      sort === 'rank' ? row.rank : sort === 'average' ? row.average : sort === 'total' ? row.total_yards : row.games_with_values;
    const av = value(a.row), bv = value(b.row);
    // Missing values stay last in both directions. Never coerce null to zero.
    if (av === null || bv === null) return av === bv ? a.index - b.index : av === null ? 1 : -1;
    const result = typeof av === 'string' && typeof bv === 'string' ? av.localeCompare(bv) : Number(av) - Number(bv);
    return result ? (dir === 'asc' ? result : -result) : a.index - b.index;
  }).map(item => item.row);
}
export const numeric = (value: number | null, digits = 0) => value === null ? '—' : value.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits });
