import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { expect, it, vi } from 'vitest';
import { App } from '../App';
import { BettingMarkets } from '../components/BettingMarkets';
import { markets } from '../api/markets';
import type { MarketsResponse } from '../api/markets';
import { detail, emptyRankings, game, id, noMarkets, noTeamLogs } from './fixtures';

function fixture(): MarketsResponse {
  const data = noMarkets(); data.data.unavailable_reason = null;
  data.data.references = [{ snapshot_id: 'synthetic-reference', provider: 'nflverse', bookmaker: null,
    classification: 'UNVERIFIED_SOURCE_REFERENCE', quote_updated_at: null, freshness: 'UNKNOWN',
    artifact_id: 'synthetic-artifact', artifact_sha256: 'a'.repeat(64), source_record_sha256: 'b'.repeat(64),
    artifact_retrieved_at: '2026-11-01T12:00:00Z', artifact_recorded_at: '2026-11-02T12:00:00Z',
    origin_status: 'DECLARED', source_url: 'https://example.invalid/source', license_url: 'https://creativecommons.org/licenses/by/4.0/',
    attribution: 'Synthetic nflverse fixture', warnings: [], sides: [
      { market: 'MONEYLINE', side: 'AWAY', line: null, price: '120', result: 'WIN', reason: 'provisional_source_reference_comparison' },
      { market: 'SPREAD', side: 'HOME', line: '-3.5', price: '-110', result: 'LOSS', reason: 'provisional_source_reference_comparison' },
      { market: 'TOTAL', side: 'OVER', line: '44', price: null, result: 'PUSH', reason: 'provisional_source_reference_comparison' },
      { market: 'TOTAL', side: 'UNDER', line: '44', price: '-110', result: 'PUSH', reason: 'provisional_source_reference_comparison' },
    ],
  }]; return data;
}
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
function open(handler: () => Promise<Response> | Response = () => json(fixture()), full = false) {
  const fn = vi.fn((url: string) => url.startsWith('/api/teams/') ? json(noTeamLogs) : url.endsWith('/markets') ? handler() : json(url.startsWith('/api/team-rankings') ? emptyRankings : detail()));
  vi.stubGlobal('fetch', fn);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[`/games/${id}`]}>{full ? <App /> : <BettingMarkets gameId={id} />}</MemoryRouter></QueryClientProvider>);
  return fn;
}
it('displays exact source lines, prices and provisional results without advertising offers', async () => {
  const fn = open(); const table = await screen.findByRole('table');
  expect(within(table).getByText('-3.5')).toBeInTheDocument(); expect(within(table).getByText('+120')).toBeInTheDocument();
  expect(screen.getByText('Current sportsbook offers unavailable')).toBeInTheDocument();
  expect(screen.getByText('Quote freshness UNKNOWN')).toBeInTheDocument(); expect(screen.getByText('nflverse · Sportsbook unknown')).toBeInTheDocument();
  expect(within(table).getByText('Provisional WIN')).toBeInTheDocument(); expect(within(table).getAllByText('Provisional PUSH')).toHaveLength(2);
  expect(screen.getByText(/not verified opening, closing or historical pregame/)).toBeInTheDocument();
  expect(fn.mock.calls[0][0]).toBe(`/api/games/${id}/markets`);
});
it('distinguishes artifact observation dates from missing quote timestamps', async () => {
  open(); await screen.findByRole('table');
  expect(screen.getByText(/Odds last updated: unavailable/)).toHaveTextContent('These are file observations, not quote times.');
  expect(screen.getByText(/Artifact retrieved:/)).toHaveTextContent(new Date('2026-11-01T12:00:00Z').toLocaleString());
});
it('does not infer completion from reported scores or change the Game Preview comparison', async () => {
  open(undefined, true); await screen.findByRole('table');
  expect(screen.getByRole('heading', { name: /Game preview/ })).toBeInTheDocument();
  expect(screen.getByText('Historical pregame rankings unavailable')).toBeInTheDocument();
  expect(screen.getAllByText('Reported scores · Finality unverified').length).toBeGreaterThan(0);
  expect(screen.getByText(/Stored status: UNKNOWN/)).toBeInTheDocument();
  expect(screen.queryByText('Confirmed final scores')).not.toBeInTheDocument();
});
it('shows unavailable market data', async () => {
  open(() => json(noMarkets())); expect(await screen.findByText('Market data unavailable')).toBeInTheDocument();
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
});
it('does not calculate results in the browser and preserves undetermined tie rules', async () => {
  const data = fixture(); data.data.game = game({ reported_home_score: 0, reported_away_score: 0 });
  data.data.references[0].sides[0].result = 'UNDETERMINED'; data.data.references[0].sides[0].reason = 'moneyline_tie_rules_unknown';
  open(() => json(data)); await screen.findByRole('table');
  expect(screen.getByText('Undetermined')).toBeInTheDocument(); expect(screen.getByText('Tie rules unknown')).toBeInTheDocument();
  expect(screen.getByText(/Reported score is tied/)).toBeInTheDocument();
});
it('loads independently and retries failures', async () => {
  let fail = true; open(() => fail ? json({}, 503) : json(fixture()));
  expect(screen.getByText('Loading market references…')).toBeInTheDocument();
  expect(await screen.findByRole('alert')).toBeInTheDocument(); fail = false;
  fireEvent.click(screen.getByRole('button', { name: 'Retry market references' })); await screen.findByRole('table');
});
it('keeps cached references visible when reloading fails', async () => {
  let fail = false; open(() => fail ? Promise.reject(new Error('network')) : json(fixture()));
  await screen.findByRole('table'); fail = true; fireEvent.click(screen.getByRole('button', { name: 'Reload market references' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Previously loaded'); expect(screen.getByRole('table')).toBeInTheDocument();
});
it('rejects mismatched identity and HTML responses', async () => {
  const data = fixture(); data.data.game.id = 'wrong-id';
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(data))); await expect(markets(id)).rejects.toThrow();
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html/>'))); await expect(markets(id)).rejects.toThrow();
});
