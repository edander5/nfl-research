import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import { App } from '../App';
import { research } from '../api/research';
import type { MetricAggregate, TeamTrendsResponse, TrendWindow } from '../api/research';
import type { Game } from '../api/types';
import { TeamPerformanceTrends } from '../components/TeamPerformanceTrends';
import { ThemeToggle } from '../theme/ThemeToggle';
import { detail, emptyRankings, game, noMarkets, noTeamLogs, noTrends } from './fixtures';

// Synthetic API averages deliberately differ by team, metric and selected window.
function fixture(url: string): TeamTrendsResponse {
  const value = noTrends(url), size = value.data.requested_game_count;
  const offset = value.data.team.id === game().away_team.id ? 200 : 100;
  const aggregate = (average: number): MetricAggregate => ({total:average*size,average,games_with_values:size});
  value.data.eligible_game_count = size;
  value.data.offense = {net_passing_yards:aggregate(offset+size),rushing_yards:aggregate(offset+2),reported_points_scored:aggregate(offset+3)};
  value.data.defense = {net_passing_yards_allowed:aggregate(offset+4),rushing_yards_allowed:aggregate(offset+5),reported_points_allowed:aggregate(offset+6)};
  Object.assign(value.meta, {available_eligible_games:size,accepted_games_in_season_stage:size,
    selected_unknown_status_games:size,selected_unverified_score_games:size,window_complete:true,selected_metrics_complete:true});
  return value;
}
const json = (body: unknown, status=200) => new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json'}});
type Handler = (url: string, init?: RequestInit) => Response | Promise<Response>;
function mock(handler: Handler = url => json(fixture(url)), data=game()) {
  const fetcher = vi.fn((path: string, init?: RequestInit) => {
    const url=String(path);
    if (url.includes('/trends?')) return handler(url,init);
    if (url.startsWith('/api/teams/')) return json(noTeamLogs);
    if (url.endsWith('/markets')) return json(noMarkets(data));
    if (url.startsWith('/api/team-rankings')) return json(emptyRankings);
    return json(detail(data));
  });
  vi.stubGlobal('fetch',fetcher);
  return fetcher;
}
function open(data=game(), full=false) {
  const client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}});
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[`/games/${data.id}?returnTo=%2Fschedule%2F2026%2FREG%2F1`]}>
    {full ? <App/> : <><ThemeToggle/><TeamPerformanceTrends key={data.id} game={data}/></>}
  </MemoryRouter></QueryClientProvider>);
  return client;
}
const section = () => screen.getByRole('region',{name:'Team Performance Trends'});
const status = (name='Synthetic Away') => within(section()).getByRole('article',{name:`${name} trend status`});
const table = () => within(section()).getByRole('table');
const rows = () => within(table()).getAllByRole('row').slice(1);
const selectWindow = (window: TrendWindow) => fireEvent.change(screen.getByLabelText('Trends window'),{target:{value:window}});
afterEach(() => { document.documentElement.classList.remove('dark'); localStorage.removeItem('nfl-research-theme'); });

it('defaults to L5 and pairs all six API metrics for both teams without calculating averages', async () => {
  const fetcher=mock();open(); await screen.findByRole('table');
  expect(screen.getByLabelText('Trends window')).toHaveValue('L5');
  expect(rows()).toHaveLength(6);
  const expected = [[205,104],[202,105],[203,106],[105,204],[102,205],[103,206]];
  rows().forEach((row,index) => {
    const cells=within(row).getAllByRole('cell');
    cells.forEach((cell,side) => expect(cell).toHaveTextContent(expected[index][side].toFixed(1)));
    cells.forEach(cell => expect(cell).toHaveTextContent('5 of 5 games'));
  });
  expect(within(table()).getAllByText('Net passing yards per game')).toHaveLength(2);
  expect(within(table()).getAllByText('Net passing yards allowed per game')).toHaveLength(2);
  expect(within(table()).getAllByText('Points scored per game · source-reported')).toHaveLength(2);
  expect(within(table()).getAllByText('Points allowed per game · source-reported')).toHaveLength(2);
  expect(within(status()).getByText('Last 5 Games (5 available)')).toBeInTheDocument();
  expect(fetcher).toHaveBeenCalledTimes(2);
  for (const [path,init] of fetcher.mock.calls) {
    const url=new URL(path,'http://synthetic.invalid');
    expect(url.searchParams.toString()).toBe(`season=2026&season_type=REG&window=L5&matchup_id=${game().id}`);
    expect(init?.signal).toBeInstanceOf(AbortSignal);
  }
});

it('switches L3/L5/L10 for both teams without replacing the section or reloading the page', async () => {
  const fetcher=mock();open(); await screen.findByRole('table');
  const original=section();
  for (const window of ['L3','L10','L5'] as const) {
    selectWindow(window);
    await waitFor(() => expect(within(status()).getByText(`Last ${window.slice(1)} Games (${window.slice(1)} available)`)).toBeInTheDocument());
    expect(within(status('Synthetic Home')).getByText(`Last ${window.slice(1)} Games (${window.slice(1)} available)`)).toBeInTheDocument();
    expect(section()).toBe(original);
  }
  expect(fetcher.mock.calls.filter(([url]) => url.includes('window=L3'))).toHaveLength(2);
  expect(fetcher.mock.calls.filter(([url]) => url.includes('window=L10'))).toHaveLength(2);
});

it('shows actual window counts, each metric count, nulls, zeroes and negative values', async () => {
  mock(url => {
    const value=fixture(url);
    value.data.eligible_game_count=4;
    for (const metric of [...Object.values(value.data.offense),...Object.values(value.data.defense)]) metric.games_with_values=4;
    value.data.offense.net_passing_yards={total:-4,average:-2,games_with_values:2};
    value.data.offense.rushing_yards={total:0,average:0,games_with_values:4};
    value.data.offense.reported_points_scored={total:null,average:null,games_with_values:0};
    value.meta.window_complete=false;value.meta.selected_metrics_complete=false;
    value.meta.excluded_unknown_kickoff_games=1;value.meta.scheduled_games_without_accepted_statistics=2;
    return json(value);
  });
  open();await screen.findByRole('table');
  expect(within(status()).getByText('Last 5 Games (4 available)')).toBeInTheDocument();
  expect(within(status()).getByText(/Partial coverage/)).toBeInTheDocument();
  expect(within(rows()[0]).getByText('-2.0')).toBeInTheDocument();
  expect(within(rows()[0]).getByText('2 of 4 games · Partial metric sample')).toBeInTheDocument();
  expect(within(rows()[1]).getByText('0.0')).toBeInTheDocument();
  expect(within(rows()[2]).getByLabelText('Statistic unavailable')).toHaveTextContent('—');
  expect(within(rows()[2]).getByText('0 of 4 games · Partial metric sample')).toBeInTheDocument();
  expect(within(status()).getByText(/1 accepted games excluded for unknown kickoff/)).toBeInTheDocument();
});

it('renders the available team while the other is loading', async () => {
  mock(url => url.includes(game().away_team.id) ? new Promise<Response>(() => {}) : json(fixture(url)));
  open();await screen.findByRole('table');
  expect(within(status()).getByRole('status')).toHaveTextContent('Loading BBB trends…');
  expect(within(status('Synthetic Home')).getByText('Last 5 Games (5 available)')).toBeInTheDocument();
  expect(within(rows()[0]).getByText('104.0')).toBeInTheDocument();
});

it('isolates team errors and retries only the failed team', async () => {
  let fail=true;
  const fetcher=mock(url => fail && url.includes(game().away_team.id) ? json({},503) : json(fixture(url)));
  open();await screen.findByRole('table');
  expect(within(status()).getByRole('alert')).toHaveTextContent('BBB trends could not be loaded.');
  expect(within(rows()[0]).getByText('104.0')).toBeInTheDocument();
  fail=false;fireEvent.click(within(status()).getByRole('button',{name:'Retry BBB trends'}));
  await within(status()).findByText('Last 5 Games (5 available)');
  expect(fetcher.mock.calls.filter(([url]) => url.includes(game().home_team.id))).toHaveLength(1);
  expect(fetcher.mock.calls.filter(([url]) => url.includes(game().away_team.id))).toHaveLength(2);
});

it('preserves cached data with a clear warning when reloading the same window fails', async () => {
  let fail=false;
  mock(url => fail ? json({},503) : json(fixture(url)));open();await screen.findByRole('table');
  fail=true;fireEvent.click(within(status()).getByRole('button',{name:'Refresh BBB trends'}));
  expect(await within(status()).findByRole('alert')).toHaveTextContent('showing previously loaded trends');
  expect(within(rows()[0]).getByText('205.0')).toBeInTheDocument();
  expect(within(status('Synthetic Home')).queryByRole('alert')).not.toBeInTheDocument();
});

it('shows no eligible games honestly without a zero-filled comparison', async () => {
  mock(url => json(noTrends(url)));open();
  await within(status()).findByText('Last 5 Games (0 available)');
  expect(within(status()).getByText(/No eligible games before this matchup/)).toBeInTheDocument();
  expect(within(section()).queryByRole('table')).not.toBeInTheDocument();
  expect(within(section()).queryByText('0.0')).not.toBeInTheDocument();
});

it('explains unavailable chronology and never falls back to unanchored latest data', async () => {
  const fetcher=mock(url => {
    const value=noTrends(url);value.meta.unavailable_reason='matchup_kickoff_unknown';value.meta.cutoff_utc=null;
    return json(value);
  });
  open(game({scheduled_kickoff_utc:null}));
  await within(status()).findByText(/Matchup chronology unavailable/);
  expect(within(section()).queryByRole('table')).not.toBeInTheDocument();
  expect(fetcher.mock.calls.every(([url]) => url.includes(`matchup_id=${game().id}`))).toBe(true);
  expect(fetcher).toHaveBeenCalledTimes(2);
});

it.each([
  game({season:2024,status:'FINAL',score_finality:'CONFIRMED_FINAL',final_evidence:{url:'https://example.invalid/synthetic-final',verified_at:'2026-11-01T00:00:00Z'}}),
  game({season:2025,season_type:'POST',game_type:'WC',week:19}),
  game({scheduled_kickoff_utc:'2030-01-01T00:00:00Z',reported_home_score:null,reported_away_score:null}),
])('passes matchup context and its own season/stage for historical and upcoming games ($season/$season_type)', async data => {
  const fetcher=mock();open(data);await screen.findByRole('table');
  expect(fetcher.mock.calls.every(([path]) => {
    const query=new URL(path,'http://synthetic.invalid').searchParams;
    return query.get('season')===String(data.season) && query.get('season_type')===data.season_type && query.get('matchup_id')===data.id;
  })).toBe(true);
  expect(within(section()).getByText(/not independently verified pregame snapshots/)).toBeInTheDocument();
  expect(within(section()).getByText(/Points are source-reported/)).toBeInTheDocument();
});

it('ignores late old-window responses and cancels superseded requests', async () => {
  const pending: {resolve: (response: Response) => void;url:string;signal?: AbortSignal|null}[]=[];
  mock((url,init) => url.includes('window=L3') ? new Promise<Response>(resolve => pending.push({resolve,url,signal:init?.signal})) : json(fixture(url)));
  open();await screen.findByRole('table');selectWindow('L3');
  await waitFor(() => expect(pending).toHaveLength(2));
  expect(within(section()).queryByRole('table')).not.toBeInTheDocument();
  selectWindow('L10');await within(status()).findByText('Last 10 Games (10 available)');
  pending.forEach(item => {expect(item.signal?.aborted).toBe(true);item.resolve(json(fixture(item.url)));});
  await waitFor(() => expect(within(rows()[0]).getByText('210.0')).toBeInTheDocument());
  expect(screen.getByLabelText('Trends window')).toHaveValue('L10');
});

it('leaves ranking stage filters, markets, scores, logs and schedule return navigation intact', async () => {
  const fetcher=mock();open(game(),true);await screen.findByRole('table',{name:/Last 5 Games/});
  expect(screen.getByRole('heading',{name:'Team Game Logs'})).toBeInTheDocument();
  expect(screen.getByRole('heading',{name:'Game Betting Markets'})).toBeInTheDocument();
  expect(screen.getByText('Reported scores · Finality unverified')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Comparison stage'),{target:{value:'COMBINED'}});
  await waitFor(() => expect(fetcher.mock.calls.some(([url]) => url.includes('/api/team-rankings?season=2026&season_type=COMBINED'))).toBe(true));
  selectWindow('L3');await within(status()).findByText('Last 3 Games (3 available)');
  const requests=fetcher.mock.calls.filter(([url]) => url.includes('/trends?'));
  expect(requests.every(([url]) => new URL(url,'http://synthetic.invalid').searchParams.get('season_type')==='REG')).toBe(true);
  expect(screen.getByRole('link',{name:'← Back to schedule'})).toHaveAttribute('href','/schedule/2026/REG/1');
});

it('supports light/dark switching with labeled controls and a keyboard-focusable comparison', async () => {
  mock();open();await screen.findByRole('table');
  for (const value of ['dark','light']) {
    fireEvent.change(screen.getByLabelText('Theme'),{target:{value}});
    expect(document.documentElement.classList.contains('dark')).toBe(value==='dark');
    expect(within(rows()[0]).getByText('205.0')).toBeInTheDocument();
    expect(screen.getByRole('region',{name:'Team performance trends comparison'})).toHaveAttribute('tabindex','0');
    expect(screen.getByLabelText('Trends window')).toHaveValue('L5');
  }
});

it.each(['team','season','stage','window','matchup','mode','metric','count','cutoff'])('rejects mismatched or malformed %s data rather than presenting it', async field => {
  vi.stubGlobal('fetch',vi.fn((path:string) => {
    const value=fixture(path);
    if (field==='team') value.data.team.id='different';
    if (field==='season') value.data.season=2024;
    if (field==='stage') value.data.season_type='POST';
    if (field==='window') value.data.window='L10';
    if (field==='matchup') value.meta.matchup_id='different';
    if (field==='mode') value.meta.selection_mode='latest_accepted';
    if (field==='metric') value.data.offense.net_passing_yards.average=null;
    if (field==='count') value.data.offense.net_passing_yards.games_with_values=9;
    if (field==='cutoff') value.meta.cutoff_utc=null;
    return json(value);
  }));
  await expect(research.trends(game().away_team.id,2026,'REG','L5',game().id)).rejects.toThrow('Invalid team trends response');
});

it('rejects HTML responses and forwards cancellation', async () => {
  const controller=new AbortController();
  const fetcher=vi.fn(() => new Response('<html/>',{headers:{'content-type':'text/html'}}));
  vi.stubGlobal('fetch',fetcher);
  await expect(research.trends(game().away_team.id,2026,'REG','L5',game().id,controller.signal)).rejects.toThrow('unexpected response');
  expect(fetcher).toHaveBeenCalledWith(expect.stringContaining('/trends?'),expect.objectContaining({signal:controller.signal}));
});
