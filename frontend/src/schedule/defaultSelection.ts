import type { Game, Round, SeasonCoverage, SeasonType } from '../api/types';

export interface DefaultSelection {
  season: number;
  stage: SeasonType;
  selection: string;
  reason: 'active' | 'upcoming' | 'latest' | 'undated';
}

const easternCalendar = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit',
});

export function easternDay(instant: Date): string {
  const parts = easternCalendar.formatToParts(instant);
  const part = (name: string) => parts.find(p => p.type === name)!.value;
  return `${part('year')}-${part('month')}-${part('day')}`;
}

function sourceDay(day: string | null): string | null {
  if (!day || !/^\d{4}-\d{2}-\d{2}$/.test(day)) return null;
  const date = new Date(`${day}T00:00:00Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === day ? day : null;
}

function gameDay(game: Game): string | null {
  // A source Eastern calendar date is still useful when the time is unannounced.
  if (game.scheduled_kickoff_utc && /(?:Z|[+-]\d{2}:\d{2})$/i.test(game.scheduled_kickoff_utc)) {
    const date = new Date(game.scheduled_kickoff_utc);
    if (Number.isFinite(date.getTime())) return easternDay(date);
  }
  return sourceDay(game.source_gameday);
}

export function defaultSelection(games: Game[], seasons: SeasonCoverage[], now: Date): DefaultSelection | null {
  type Window = DefaultSelection & { first: string; last: string; order: number };
  const groups = new Map<string, Window>();
  const choices = new Map<string, DefaultSelection>();
  for (const game of games) {
    const selection = game.season_type === 'REG' ? String(game.week) : game.game_type;
    const key = `${game.season}/${game.season_type}/${selection}`;
    const choice: DefaultSelection = { season: game.season, stage: game.season_type, selection, reason: 'undated' };
    choices.set(key, choice);
    const day = gameDay(game);
    if (!day) continue;
    const previous = groups.get(key);
    groups.set(key, { ...choice, order: game.week, first: previous && previous.first < day ? previous.first : day,
      last: previous && previous.last > day ? previous.last : day });
  }
  const today = easternDay(now);
  const windows = [...groups.values()].sort((a, b) =>
    a.first.localeCompare(b.first) || a.season - b.season || a.order - b.order);
  // Overlapping postponed dates do not drag navigation back to an older week.
  const started = windows.filter(w => w.first <= today).at(-1);
  const active = started && today <= started.last ? started : undefined;
  const upcoming = windows.find(w => w.first > today);
  const latest = started;
  const chosen = active ?? upcoming ?? latest;
  if (chosen) return { season: chosen.season, stage: chosen.stage, selection: chosen.selection,
    reason: active ? 'active' : upcoming ? 'upcoming' : 'latest' };

  // No usable dates: deterministic available-data fallback, not a guessed current week.
  const rounds: Round[] = ['WC', 'DIV', 'CON', 'SB'];
  const fallback = [...choices.values()].sort((a, b) => b.season - a.season ||
    (a.stage === b.stage ? (a.stage === 'REG' ? Number(a.selection) - Number(b.selection) :
      rounds.indexOf(a.selection as Round) - rounds.indexOf(b.selection as Round)) : a.stage === 'REG' ? -1 : 1))[0];
  if (fallback) return fallback;
  for (const year of [...seasons].sort((a, b) => b.season - a.season)) {
    const regular = year.coverage.find(c => c.season_type === 'REG' && c.game_count > 0);
    if (regular?.weeks.length) return { season: year.season, stage: 'REG', selection: String(Math.min(...regular.weeks)), reason: 'undated' };
    const post = year.coverage.find(c => c.season_type === 'POST' && c.game_count > 0);
    const round = rounds.find(r => post?.rounds.includes(r));
    if (round) return { season: year.season, stage: 'POST', selection: round, reason: 'undated' };
  }
  return null;
}
