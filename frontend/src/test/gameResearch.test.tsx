import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import { App } from '../App';
import { canonicalLine, gameResearch } from '../api/gameResearch';
import type { GameObservation, GameResearchResponse, ResearchWindow } from '../api/gameResearch';
import type { Game } from '../api/types';
import { GameTotalResearch } from '../components/gameResearch/GameTotalResearch';
import { ThemeToggle } from '../theme/ThemeToggle';
import { detail, emptyRankings, game, noGameResearch, noMarkets, noTeamLogs, noTrends } from './fixtures';

// Synthetic API data only. Classifications/counts here simulate server responses,
// not frontend fallback calculations or production NFL records.
function fixture(path:string,matchup=game()):GameResearchResponse {
  const result=noGameResearch(path),data=result.data;
  const team=data.team.id===matchup.away_team.id?matchup.away_team:matchup.home_team;
  const opponent=team.id===matchup.away_team.id?matchup.home_team:matchup.away_team;
  data.team=team;data.opponent_id=opponent.id;
  const all=[55,44,0,null];
  const values=data.window==='L3'?all.slice(0,3):all;
  const metricOutcome=(value:number|null)=>value===null||data.line===null?'UNDETERMINED':value>Number(data.line)?'OVER':value<Number(data.line)?'UNDER':'PUSH';
  data.observations=values.map((value,index):GameObservation=>{
    const date=new Date(Date.parse(matchup.scheduled_kickoff_utc ?? game().scheduled_kickoff_utc!)-(index+1)*86400000).toISOString();
    return {game_id:`00000000-0000-0000-0000-${String(index+10).padStart(12,'0')}`,source_game_id:`synthetic-${index}`,
      season:data.season,season_type:data.season_type,week:10-index,scheduled_kickoff_utc:date,source_gameday:null,
      team,opponent,side:index%2===0?'HOME':'AWAY',gross_passing_yards:210,original_sack_yards:-10,
      net_passing_yards:200,rushing_yards:80,net_passing_yards_allowed:220,rushing_yards_allowed:90,
      reported_points_scored:value===null?null:0,reported_points_allowed:value,status:'UNKNOWN',score_finality:value===null?'NOT_REPORTED':'UNVERIFIED',
      accepted_pair_id:`synthetic-pair-${index}`,selection_generation:1,revision_recorded_at:'2026-11-01T00:00:00Z',schedule_source_artifact_id:'synthetic-schedule',
      provenance:{artifact_id:'synthetic-stats',provider:'nflverse',artifact_sha256:'a'.repeat(64),origin_status:'DECLARED',documented_source_url:null,license_url:null,attribution:'Synthetic only',source_record_sha256:'b'.repeat(64),source_line:2},
      combined_points:value,scores_available:value!==null,outcome:metricOutcome(value),outcome_unavailable_reason:value===null?'scores_unavailable':data.line===null?'threshold_required':null,
      reference_total:{line:index===0?'40.5':null,outcome:index===0?'OVER':'UNDETERMINED',unavailable_reason:index===0?null:'total_line_unavailable',
        classification:'UNVERIFIED_SOURCE_REFERENCE',provider:'nflverse',bookmaker:null,quote_updated_at:null,freshness:'UNKNOWN',provenance:null,warnings:[]}};
  });
  const known=values.filter((value):value is number=>value!==null);
  const over=data.line===null?null:data.observations.filter(row=>row.outcome==='OVER').length;
  const under=data.line===null?null:data.observations.filter(row=>row.outcome==='UNDER').length;
  const pushes=data.line===null?null:data.observations.filter(row=>row.outcome==='PUSH').length;
  const hits=data.side==='OVER'?over:under;
  data.summary={...data.summary,eligible_game_count:values.length,games_with_usable_scores:known.length,games_without_usable_scores:values.length-known.length,
    average_combined_points:33,over_count:over,under_count:under,push_count:pushes,
    hit_rate:hits===null?null:hits/known.length,hit_rate_numerator:hits,hit_rate_denominator:data.line===null?null:known.length,
    outcomes_unavailable_reason:data.line===null?'threshold_required':null};
  data.availability='PARTIAL';
  result.meta={...result.meta,cutoff_utc:matchup.scheduled_kickoff_utc ?? game().scheduled_kickoff_utc!,unavailable_reason:null,
    available_eligible_games:values.length,accepted_games_in_scope:values.length,selected_unknown_status_games:values.length,
    selected_unverified_score_games:values.length,games_with_reference_total:1,games_without_reference_total:values.length-1,
    scores_complete:known.length===values.length,window_complete:data.requested_game_count===values.length,
    selection_semantics:'Synthetic same-season scope',threshold_semantics:'Synthetic including-push policy',reference_semantics:'Synthetic unverified references'};
  return result;
}
const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json'}});
type Handler=(url:string,init?:RequestInit)=>Response|Promise<Response>;
function mock(handler:Handler=url=>json(fixture(url)),matchup=game()) {
  const fetcher=vi.fn((url:string,init?:RequestInit)=>{
    if(url.includes('/game-research?'))return handler(url,init);
    if(url.includes('/trends?'))return json(noTrends(url));
    if(url.startsWith('/api/teams/'))return json(noTeamLogs);
    if(url.endsWith('/markets'))return json(noMarkets(matchup));
    if(url.startsWith('/api/team-rankings'))return json(emptyRankings);
    return json(detail(matchup));
  });
  vi.stubGlobal('fetch',fetcher);return fetcher;
}
function open(matchup=game(),full=false) {
  const client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}});
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[`/games/${matchup.id}?returnTo=%2Fschedule%2F2026%2FREG%2F1`]}>
    {full?<App/>:<><ThemeToggle/><GameTotalResearch key={matchup.id} game={matchup}/></>}
  </MemoryRouter></QueryClientProvider>);return client;
}
const section=()=>screen.getByRole('region',{name:'Game Total Research'});
const summary=()=>within(section()).getByLabelText('Game Total summary');
const chart=()=>within(section()).getByRole('region',{name:'Game Total history chart'});
const log=()=>within(section()).getByRole('table',{name:/Historical Game Total log/});
function apply(value:string){fireEvent.change(screen.getByLabelText('Custom Game Total line'),{target:{value}});fireEvent.click(screen.getByRole('button',{name:'Apply line'}));}
async function loaded(){return within(section()).findByRole('table',{name:/Historical Game Total log/});}
afterEach(()=>{document.documentElement.classList.remove('dark');localStorage.removeItem('nfl-research-theme');});

it('starts with away-team L5, no invented line, and identical game IDs in chronological chart/newest log',async()=>{
  const fetcher=mock();open();await loaded();
  expect(screen.getByLabelText('Research window')).toHaveValue('L5');
  expect(screen.getByLabelText('Analyze team history')).toHaveValue(game().away_team.id);
  expect(within(section()).getByText(/current opponent: Synthetic Home/)).toBeInTheDocument();
  expect(within(summary()).getByText('Hit rate unavailable')).toBeInTheDocument();
  expect(screen.getByLabelText('Custom Game Total line')).toHaveValue(null);
  const bars=within(chart()).getAllByRole('img');
  const rows=within(log()).getAllByRole('row').slice(1);
  expect(bars.map(bar=>bar.getAttribute('data-game-id'))).toEqual(rows.map(row=>row.getAttribute('data-game-id')).reverse());
  expect(bars).toHaveLength(4);
  expect(within(chart()).queryByLabelText(/Custom threshold/)).not.toBeInTheDocument();
  expect(within(log()).getAllByText('Line not entered')).toHaveLength(4);
  expect(fetcher).toHaveBeenCalledTimes(1);
  const [url,init]=fetcher.mock.calls[0];const query=new URL(url,'http://test').searchParams;
  expect(Object.fromEntries(query)).toEqual({season:'2026',season_type:'REG',matchup_id:game().id,window:'L5',side:'OVER',market:'GAME_TOTAL',period:'FULL_GAME'});
  expect(init?.signal).toBeInstanceOf(AbortSignal);
});

it.each(['L3','L5','L10','L20','SEASON','H2H'] as const)('updates synchronized history with %s and correct team/opponent context',async window=>{
  const fetcher=mock();open();await loaded();
  fireEvent.change(screen.getByLabelText('Research window'),{target:{value:window}});
  await waitFor(()=>expect(fetcher.mock.calls.some(([url])=>new URL(url,'http://test').searchParams.get('window')===window)).toBe(true));
  await loaded();
  expect(within(chart()).getAllByRole('img')).toHaveLength(window==='L3'?3:4);
  expect(within(log()).getAllByRole('row')).toHaveLength(window==='L3'?4:5);
  fireEvent.change(screen.getByLabelText('Analyze team history'),{target:{value:game().home_team.id}});
  await waitFor(()=>expect(fetcher.mock.calls.some(([url])=>url.includes(`/teams/${game().home_team.id}/game-research?`))).toBe(true));
  await loaded();expect(within(section()).getByText(/Synthetic Home history · current opponent: Synthetic Away/)).toBeInTheDocument();
  expect(fetcher.mock.calls.every(([url])=>url.includes(`matchup_id=${game().id}`))).toBe(true);
});

it('applies lines, steps exactly, changes sides, and preserves source reference totals',async()=>{
  const fetcher=mock();open();await loaded();
  apply('44');await waitFor(()=>expect(within(summary()).getByText('33.3%')).toBeInTheDocument());
  expect(within(summary()).getByText('1 / 1 / 1')).toBeInTheDocument();
  expect(within(summary()).getByText(/Denominator: 3 usable scored games, including pushes/)).toBeInTheDocument();
  expect(within(chart()).getByLabelText('Custom threshold 44')).toBeInTheDocument();
  expect(within(log()).getByText('Push · PUSH at 44')).toBeInTheDocument();
  expect(within(log()).getByText('40.5')).toBeInTheDocument();
  expect(within(chart()).getAllByRole('img').some(bar=>bar.classList.contains('research-outcome-hit'))).toBe(true);
  fireEvent.change(screen.getByLabelText('Research side'),{target:{value:'UNDER'}});
  await waitFor(()=>expect(within(summary()).getByText('Under 44')).toBeInTheDocument());
  expect(within(log()).getByText('Miss · OVER at 44')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Increase Game Total line by 0.5'}));
  await waitFor(()=>expect(within(summary()).getByText('Under 44.5')).toBeInTheDocument());
  fireEvent.click(screen.getByRole('button',{name:'Decrease Game Total line by 0.5'}));
  await waitFor(()=>expect(within(summary()).getByText('Under 44')).toBeInTheDocument());
  apply('44.000001');await waitFor(()=>expect(within(summary()).getByText('Under 44.000001')).toBeInTheDocument());
  fireEvent.click(screen.getByRole('button',{name:'Increase Game Total line by 0.5'}));
  await waitFor(()=>expect(within(summary()).getByText('Under 44.500001')).toBeInTheDocument());
  expect(fetcher.mock.calls.some(([url])=>url.includes('line=44.500001'))).toBe(true);
  expect(within(log()).getByText('40.5')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Clear line'}));
  await waitFor(()=>expect(within(summary()).getByText('Hit rate unavailable')).toBeInTheDocument());
  expect(within(chart()).queryByLabelText(/Custom threshold/)).not.toBeInTheDocument();
});

it('renders authoritative server rates and averages instead of calculating them from rows',async()=>{
  mock(url=>{const response=fixture(url);if(response.data.line!==null){response.data.summary.hit_rate=0.37;response.data.summary.average_combined_points=99.9;}return json(response);});
  open();await loaded();apply('44.5');
  await waitFor(()=>expect(within(summary()).getByText('37%')).toBeInTheDocument());expect(within(summary()).getByText('99.9')).toBeInTheDocument();
});

it('keeps draft lines separate, validates bounds/precision, and preserves a valid zero line',async()=>{
  const fetcher=mock();open();await loaded();
  fireEvent.change(screen.getByLabelText('Custom Game Total line'),{target:{value:'44.5'}});
  expect(screen.getByText(/Apply the edited line/)).toBeInTheDocument();expect(fetcher).toHaveBeenCalledTimes(1);
  fireEvent.change(screen.getByLabelText('Custom Game Total line'),{target:{value:'-1'}});
  expect(screen.getByRole('button',{name:'Apply line'})).toBeDisabled();expect(screen.getByRole('alert')).toHaveTextContent('Enter a line');
  fireEvent.change(screen.getByLabelText('Custom Game Total line'),{target:{value:'44.0000001'}});
  expect(screen.getByRole('button',{name:'Apply line'})).toBeDisabled();
  apply('0');await waitFor(()=>expect(within(summary()).getByText('Over 0')).toBeInTheDocument());
  expect(screen.getByRole('button',{name:'Decrease Game Total line by 0.5'})).toBeDisabled();
  expect(within(chart()).getByLabelText('Custom threshold 0')).toBeInTheDocument();
  expect(within(log()).getAllByText('0').length).toBeGreaterThan(0);
});

it('keeps missing scores/reference totals distinct from zero and exposes focusable game details',async()=>{
  mock();open();await loaded();
  expect(within(summary()).getByText(/3 scored of 4 selected games · 1 scores unavailable/)).toBeInTheDocument();
  expect(within(summary()).getByText(/Partial coverage/)).toBeInTheDocument();
  expect(within(log()).getByLabelText('Combined points unavailable')).toHaveTextContent('—');
  expect(within(log()).getAllByLabelText('Reference total unavailable')).toHaveLength(3);
  const missing=within(chart()).getByRole('img',{name:/scores unavailable/});
  expect(missing.querySelector('rect')).toHaveClass('research-missing-bar');
  const zero=within(chart()).getByRole('img',{name:/0 combined points/});
  expect(zero.querySelector('rect')).not.toHaveClass('research-missing-bar');
  fireEvent.focus(zero);expect(within(section()).getByText(/Total 0 · Unavailable/)).toBeInTheDocument();
  expect(within(log()).getAllByText(/UNKNOWN ·/)).toHaveLength(4);
});

it.each(['no_h2h_games','matchup_kickoff_unknown','no_eligible_games'] as const)('explains %s without fabricated bars or rates',async reason=>{
  mock(url=>{const response=noGameResearch(url);response.meta.unavailable_reason=reason;if(reason==='matchup_kickoff_unknown'){response.meta.cutoff_utc=null;response.data.availability='UNAVAILABLE';}return json(response);});
  open();if(reason==='no_h2h_games')fireEvent.change(screen.getByLabelText('Research window'),{target:{value:'H2H'}});
  await within(section()).findByText(reason==='no_h2h_games'?/No eligible head-to-head/:reason==='matchup_kickoff_unknown'?/Research unavailable: matchup kickoff/:/No eligible historical games/);
  expect(within(section()).queryByRole('img')).not.toBeInTheDocument();expect(within(section()).queryByRole('table')).not.toBeInTheDocument();
});

it('keeps other preview sections and navigation intact during research failures, and recovers on retry',async()=>{
  let fail=true;mock(url=>fail?json({},503):json(fixture(url)));open(game(),true);
  await screen.findByRole('region',{name:'Game Total Research'});
  await within(section()).findByRole('alert');
  for(const name of ['Team Game Logs','Current accepted season comparison','Team Performance Trends','Game Betting Markets'])expect(screen.getByRole('heading',{name})).toBeInTheDocument();
  expect(screen.getByText('Reported scores · Finality unverified')).toBeInTheDocument();
  expect(screen.getByRole('link',{name:'← Back to schedule'})).toHaveAttribute('href','/schedule/2026/REG/1');
  fail=false;fireEvent.click(screen.getByRole('button',{name:'Retry Game Total research'}));await loaded();
});

it('retains data only for the same controls on refresh failure',async()=>{
  let fail=false;mock(url=>fail?json({},503):json(fixture(url)));open();await loaded();
  fail=true;fireEvent.click(screen.getByRole('button',{name:'Refresh Game Total research'}));
  expect(await within(section()).findByRole('alert')).toHaveTextContent('previously loaded results for these controls');expect(log()).toBeInTheDocument();
});

it('cancels superseded requests and cannot overwrite a new window with late results',async()=>{
  const pending:{url:string;signal?:AbortSignal|null;resolve:(response:Response)=>void}[]=[];
  mock((url,init)=>url.includes('window=L3')?new Promise<Response>(resolve=>pending.push({url,signal:init?.signal,resolve})):json(fixture(url)));
  open();await loaded();fireEvent.change(screen.getByLabelText('Research window'),{target:{value:'L3'}});
  await waitFor(()=>expect(pending).toHaveLength(1));
  expect(within(section()).getByRole('status')).toHaveTextContent('Loading Game Total research');expect(within(section()).queryByRole('table')).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Research window'),{target:{value:'L20'}});await loaded();
  expect(pending[0].signal?.aborted).toBe(true);pending[0].resolve(json(fixture(pending[0].url)));
  await waitFor(()=>expect(within(summary()).getByText(/Last 20 Games \(4 available\)/)).toBeInTheDocument());
  expect(within(log()).getAllByRole('row')).toHaveLength(5);
});

it.each([game({season:2024,scheduled_kickoff_utc:'2024-12-01T17:00:00Z'}),game({season:2025,season_type:'POST',week:19,game_type:'WC',scheduled_kickoff_utc:'2026-01-01T17:00:00Z'})])('keeps historical matchup season/stage $season/$season_type',async matchup=>{
  const fetcher=mock(url=>json(fixture(url,matchup)),matchup);open(matchup);await loaded();
  expect(fetcher.mock.calls.every(([url])=>url.includes(`season=${matchup.season}&season_type=${matchup.season_type}`)&&url.includes(`matchup_id=${matchup.id}`))).toBe(true);
  expect(within(section()).getByText(/not an independently verified pregame snapshot/)).toBeInTheDocument();
});

it('supports both themes, keyboard chart details, and focusable scrolling/table access',async()=>{
  mock();open();await loaded();apply('44');await waitFor(()=>expect(within(summary()).getByText('Over 44')).toBeInTheDocument());
  for(const theme of ['dark','light']){
    fireEvent.change(screen.getByLabelText('Theme'),{target:{value:theme}});
    expect(document.documentElement.classList.contains('dark')).toBe(theme==='dark');
    expect(chart()).toHaveAttribute('tabindex','0');expect(screen.getByRole('region',{name:'Game Total historical log'})).toHaveAttribute('tabindex','0');
    const bar=within(chart()).getAllByRole('img')[1];expect(bar).toHaveAttribute('tabindex','0');fireEvent.focus(bar);
    expect(screen.getByText(/Source-reported scores; UNKNOWN \/ UNVERIFIED/)).toBeInTheDocument();
  }
});

it.each(['team','window','line','side','cutoff','stage','duplicate','denominator','reference'] as const)('rejects invalid %s response context rather than displaying mixed results',async field=>{
  vi.stubGlobal('fetch',vi.fn((url:string)=>{const response=fixture(url);const row=response.data.observations[0];
    if(field==='team')response.data.team.id='different';if(field==='window')response.data.window='L20';
    if(field==='line')response.data.line='99';if(field==='side')response.data.side='UNDER';
    if(field==='cutoff')row.scheduled_kickoff_utc=game().scheduled_kickoff_utc;
    if(field==='stage')row.season_type='POST';if(field==='duplicate')response.data.observations[1].game_id=row.game_id;
    if(field==='denominator')response.data.summary.hit_rate_denominator_policy='nonpush' as never;
    if(field==='reference')row.reference_total.classification='CLOSING' as never;return json(response);
  }));
  await expect(gameResearch(game().away_team,game(),'L5',null,'OVER')).rejects.toThrow('Invalid Game Total');
});

it('rejects HTML and normalizes manual decimal input without floating threshold comparisons',async()=>{
  expect(canonicalLine('0044.500000')).toBe('44.5');expect(canonicalLine('')).toBeNull();expect(canonicalLine('44.0000001')).toBeUndefined();
  const controller=new AbortController();const fetcher=vi.fn(()=>new Response('<html/>',{headers:{'content-type':'text/html'}}));vi.stubGlobal('fetch',fetcher);
  await expect(gameResearch(game().away_team,game(),'L5',null,'OVER',controller.signal)).rejects.toThrow('unexpected response');
  expect(fetcher).toHaveBeenCalledWith(expect.any(String),expect.objectContaining({signal:controller.signal}));
});
