import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { expect, it, vi } from 'vitest';
import { PreviewTeamLogs } from '../components/PreviewTeamLogs';
import { newestFirst, referenceFor } from '../gameLogs/presentation';
import type { TeamGameStats, TeamGamesResponse } from '../api/research';
import { game, noMarkets, noTeamLogs } from './fixtures';

const matchup = game();
function entry(week: number, team = matchup.away_team, side: 'HOME' | 'AWAY' = 'AWAY'): TeamGameStats {
  return { game_id: `00000000-0000-0000-0000-${String(week).padStart(12,'0')}`, source_game_id: `2026_${week}_X_Y`,
    season: 2026, season_type: 'REG', week, scheduled_kickoff_utc: `2026-09-${String(week+1).padStart(2,'0')}T17:00:00Z`,
    source_gameday: null, team, opponent: {id:'opponent-id',code:'OPP',name:'Synthetic opponent'}, side,
    gross_passing_yards: 210, original_sack_yards: -15, net_passing_yards: 195, rushing_yards: 0,
    net_passing_yards_allowed: 100, rushing_yards_allowed: 90, reported_points_scored: 27, reported_points_allowed: 20,
    status:'UNKNOWN', score_finality:'UNVERIFIED', accepted_pair_id:'synthetic-pair',selection_generation:1,
    revision_recorded_at:'2026-11-01T00:00:00Z',schedule_source_artifact_id:'schedule-artifact',
    provenance:{artifact_id:'stats-artifact',provider:'nflverse',artifact_sha256:'a'.repeat(64),origin_status:'DECLARED',
      documented_source_url:'https://example.invalid/stats',license_url:'https://creativecommons.org/licenses/by/4.0/',
      attribution:'Synthetic nflverse stats',source_record_sha256:'b'.repeat(64),source_line:2} };
}
function reference(row: TeamGameStats, result: 'WIN'|'LOSS'|'PUSH'|'UNDETERMINED' = 'WIN') {
  const data = noMarkets(game({id:row.game_id,season:row.season,
    home_team:row.side === 'HOME' ? row.team : row.opponent,away_team:row.side === 'AWAY' ? row.team : row.opponent,
    reported_home_score:row.side === 'HOME' ? row.reported_points_scored : row.reported_points_allowed,
    reported_away_score:row.side === 'AWAY' ? row.reported_points_scored : row.reported_points_allowed}));
  data.data.unavailable_reason = null;
  data.data.references = [{snapshot_id:'synthetic-reference',provider:'nflverse',bookmaker:null,classification:'UNVERIFIED_SOURCE_REFERENCE',
    quote_updated_at:null,freshness:'UNKNOWN',artifact_id:'source-artifact',artifact_sha256:'a'.repeat(64),source_record_sha256:'b'.repeat(64),
    artifact_retrieved_at:null,artifact_recorded_at:'2026-11-01T00:00:00Z',origin_status:'DECLARED',source_url:null,license_url:null,attribution:null,warnings:[],
    sides:[{market:'SPREAD',side:row.side,line:'-3.5',price:'-110',result,reason:'provisional_source_reference_comparison'},
      {market:'TOTAL',side:'OVER',line:'44',price:null,result:'LOSS',reason:'provisional_source_reference_comparison'},
      {market:'TOTAL',side:'UNDER',line:'44',price:null,result:'WIN',reason:'provisional_source_reference_comparison'}]}]; return data;
}
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value),{status,headers:{'content-type':'application/json'}});
function open(away = [entry(1),entry(3),entry(2)], home = [entry(4,matchup.home_team,'HOME')],
  custom?: (url: string) => Response | Promise<Response> | undefined) {
  const all = [...away,...home];
  const fetcher = vi.fn((path: string) => {
    const url = String(path), override = custom?.(url); if (override) return override;
    if (url.startsWith('/api/teams/')) {
      const rows = url.includes(matchup.away_team.id) ? away : home;
      const result: TeamGamesResponse = {...noTeamLogs,data:rows,meta:{...noTeamLogs.meta,total_count:rows.length,returned_count:rows.length}};
      return json(result);
    }
    const row = all.find(row => url === `/api/games/${row.game_id}/markets`)!;
    return json(reference(row));
  });
  vi.stubGlobal('fetch',fetcher);
  const client = new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}});
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/preview']}><Routes>
    <Route path="/preview" element={<PreviewTeamLogs game={matchup}/>}/><Route path="/games/:gameId" element={<h1>Destination preview</h1>}/>
  </Routes></MemoryRouter></QueryClientProvider>); return fetcher;
}
const card = (name='Synthetic Away') => screen.getByRole('article',{name:`${name} game log`});
const dataRows = (name='Synthetic Away') => within(card(name)).getAllByRole('row').slice(1);

it('renders two separate compact cards with badges, season labels and seven columns', async () => {
  open(); await screen.findByRole('table',{name:/Synthetic Away/});
  expect(screen.getAllByRole('article')).toHaveLength(2);
  expect(within(card()).getByRole('img')).toHaveAccessibleName(/badge; logo unavailable/);
  expect(within(card()).getByText('2026 · Regular season')).toBeInTheDocument();
  expect(within(card()).getAllByRole('columnheader').map(cell=>cell.textContent)).toEqual(['WK','OPP','SCORE','SPREAD','TOTAL','PASS','RUSH']);
  expect(screen.getAllByRole('region',{name:/game log table/})).toHaveLength(2);
  expect(within(card()).getByRole('region')).toHaveAttribute('tabindex','0');
});
it('sorts newest first, orients opponents/scores, and preserves NET and zero rushing values', async () => {
  open(); await screen.findByRole('table',{name:/Synthetic Away/});
  expect(dataRows().map(row=>within(row).getByRole('rowheader').textContent)).toEqual(['3','2','1']);
  const cells=within(dataRows()[0]).getAllByRole('cell');
  expect(cells[0]).toHaveTextContent('@ OPP'); expect(cells[1]).toHaveTextContent('27–20');
  expect(cells[4]).toHaveTextContent('195'); expect(cells[5]).toHaveTextContent('0');
  expect(within(dataRows('Synthetic Home')[0]).getAllByRole('cell')[0]).toHaveTextContent('vs OPP');
});
it('displays API results without recalculating, including green win, red loss and neutral push', async () => {
  // LOSS intentionally contradicts the displayed score: the UI must preserve API results.
  const away=[entry(1),entry(2),entry(3)];
  open(away,[], url=>{
    const row=away.find(row=>url===`/api/games/${row.game_id}/markets`);
    return row ? json(reference(row, row.week===1 ? 'WIN' : row.week===2 ? 'LOSS' : 'PUSH')) : undefined;
  });
  expect(await screen.findByLabelText('Provisional LOSS')).toHaveTextContent('✕');
  expect(screen.getByLabelText('Provisional WIN').parentElement).toHaveClass('log-result-win');
  expect(screen.getByLabelText('Provisional PUSH').parentElement).toHaveClass('log-result-push');
  expect(screen.getByLabelText('Provisional LOSS').parentElement).toHaveClass('log-result-loss');
  expect(screen.getAllByLabelText('Provisional Under WIN').length).toBeGreaterThan(0);
  expect(screen.getByText(/not settled bets or verified pregame lines/)).toBeInTheDocument();
});
it('supports row clicks and keyboard-accessible native preview links', async () => {
  open(); await screen.findByRole('table',{name:/Synthetic Away/});
  const link=within(dataRows()[0]).getByRole('link',{name:/View week 3/});
  expect(link).toHaveAttribute('href','/games/00000000-0000-0000-0000-000000000003');
  fireEvent.click(within(dataRows()[0]).getAllByRole('cell')[4]);
  expect(await screen.findByRole('heading',{name:'Destination preview'})).toBeInTheDocument();
});
it('preserves missing values and unverified score labels', async () => {
  const row=entry(1);row.reported_points_scored=null;row.reported_points_allowed=null;row.net_passing_yards=null;row.rushing_yards=-2;
  open([row],[],url=>url.endsWith('/markets') ? json(noMarkets(game({id:row.game_id}))) : undefined);
  await screen.findByRole('table');
  expect(dataRows()[0]).toHaveTextContent('—–—'); expect(dataRows()[0]).toHaveTextContent('UNKNOWN · Unverified');
  expect(within(dataRows()[0]).getAllByRole('cell')[5]).toHaveTextContent('-2');
  expect((await screen.findAllByLabelText('Reference line unavailable')).length).toBe(2);
});
it('paginates newest groups without losing earlier games', async () => {
  open(Array.from({length:7},(_,index)=>entry(index+1)),[]); await screen.findByRole('table');
  expect(dataRows()).toHaveLength(5); expect(dataRows()[0]).toHaveTextContent('7');
  fireEvent.click(screen.getByRole('button',{name:'Older BBB games'}));
  expect(dataRows().map(row=>within(row).getByRole('rowheader').textContent)).toEqual(['2','1']);
  fireEvent.click(screen.getByRole('button',{name:'Newer BBB games'})); expect(dataRows()).toHaveLength(5);
});
it('isolates team-log failures and lets the affected card retry', async () => {
  let fail=true;
  open(undefined,undefined,url=>url.startsWith(`/api/teams/${matchup.away_team.id}/`) && fail ? json({},503) : undefined);
  expect(await screen.findByRole('alert')).toHaveTextContent('Game logs could not be loaded');
  expect(await screen.findByRole('table',{name:/Synthetic Home/})).toBeInTheDocument(); fail=false;
  fireEvent.click(screen.getByRole('button',{name:'Retry BBB game logs'})); await screen.findByRole('table',{name:/Synthetic Away/});
});
it('shows no-data cards gracefully', async () => {
  open([],[]); await waitFor(() => expect(screen.getAllByText('No accepted team statistics for this season and stage.')).toHaveLength(2));
});
it('withholds mismatched market identity or score comparisons', () => {
  const row=entry(2), response=reference(row);
  expect(referenceFor(row,response)).toBeDefined(); response.data.game.reported_away_score=99;
  expect(referenceFor(row,response)).toBeUndefined();
  response.data.game.reported_away_score=27;response.data.game.away_team={...response.data.game.away_team,id:'other-team'};
  expect(referenceFor(row,response)).toBeUndefined();
});
it('keeps unknown kickoff games last with deterministic week ordering and does not mutate inputs', () => {
  const a=entry(1),b=entry(4),c=entry(3);b.scheduled_kickoff_utc=null;c.scheduled_kickoff_utc=null;
  const input=[c,a,b]; expect(newestFirst(input).map(row=>row.week)).toEqual([1,4,3]);
  expect(input.map(row=>row.week)).toEqual([3,1,4]);
});

it('loads all API pages before selecting the newest rows', async () => {
  const first=entry(1),last=entry(9);
  const fetcher=open([first,last],[],url=>{
    if (!url.startsWith(`/api/teams/${matchup.away_team.id}/`)) return undefined;
    const rows=new URL(url,'http://test').searchParams.get('offset')==='0' ? [first] : [last];
    return json({...noTeamLogs,data:rows,meta:{...noTeamLogs.meta,total_count:2,returned_count:1}});
  });
  await screen.findByRole('table');
  expect(within(dataRows()[0]).getByRole('rowheader')).toHaveTextContent('9');
  expect(fetcher.mock.calls.some(([url])=>url.includes('offset=1'))).toBe(true);
});
it('keeps statistics visible on market failures and retries only the failed market', async () => {
  let fail=true;open([entry(2)],[],url=>url.endsWith('/markets') && fail ? json({},503) : undefined);
  const retry=await screen.findByRole('button',{name:'Retry W2 markets'});
  expect(dataRows()[0]).toHaveTextContent('195');fail=false;fireEvent.click(retry);
  expect(await screen.findByLabelText('Provisional WIN')).toBeInTheDocument();
});
