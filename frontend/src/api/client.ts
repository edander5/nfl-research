import { parseFreshness } from './freshness';
import type { GameResponse, Round, ScheduleResponse, SeasonsResponse, SeasonType } from './types';
export class ApiError extends Error { status: number; constructor(status: number) { super(status === 404 ? 'This game was not found.' : status === 422 ? 'These schedule filters are not supported.' : 'The schedule service is unavailable. Please try again.'); this.status = status; } }
async function read<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal, headers: { Accept: 'application/json' } });
  if (!response.ok) throw new ApiError(response.status);
  if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('The server returned an unexpected response.');
  return response.json() as Promise<T>;
}
export const api = {
  freshness: async (signal?: AbortSignal) => parseFreshness(await read<unknown>('/api/data-status/schedule', signal)),
  seasons: (signal?: AbortSignal) => read<SeasonsResponse>('/api/seasons', signal),
  schedule: (season: number, stage: SeasonType, selection: string, signal?: AbortSignal) => {
    const query = new URLSearchParams({ season_type: stage });
    if (selection !== 'all') query.set(stage === 'REG' ? 'week' : 'round', selection);
    return read<ScheduleResponse>(`/api/seasons/${season}/schedule?${query}`, signal);
  },
  game: (id: string, signal?: AbortSignal) => read<GameResponse>(`/api/games/${encodeURIComponent(id)}`, signal),
};
export const roundLabels: Record<Round, string> = { WC: 'Wild Card', DIV: 'Divisional', CON: 'Conference', SB: 'Super Bowl' };
export const schedulePath = (year: number, stage: SeasonType, selection: string) => `/schedule/${year}/${stage}/${selection}`;
export function validSelection(stage: string | undefined, value: string | undefined) {
  return stage === 'REG' ? !!value && /^(?:[1-9]|1[0-8])$/.test(value) : stage === 'POST' && (value === 'all' || Object.hasOwn(roundLabels, value ?? ''));
}
export function kickoff(value: string | null) {
  if (!value) return 'Kickoff not announced';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Kickoff unavailable';
  return new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' }).format(date);
}
export function safeUrl(value: string | null) { try { const url = new URL(value ?? ''); return ['https:', 'http:'].includes(url.protocol) ? url.href : undefined; } catch { return undefined; } }
