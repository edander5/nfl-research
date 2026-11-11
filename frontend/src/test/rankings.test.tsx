import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, useLocation, useNavigate } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import type { Category, RankedTeam, RankingsResponse, TeamGamesResponse } from '../api/research';
import { research } from '../api/research';
import { selection, sortedTeams } from '../rankings/state';

const ids = ['00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000004'];
const policy = { definition_version: 'net_pass_negative_sacks_v1' as const, statistics_semantics: 'Synthetic NET definition', score_semantics: 'Reported scores are not proof of FINAL.', aggregate_semantics: 'Reconstructed season statistics', origin_semantics: 'Declared origin' };
function teams(): RankedTeam[] { return [
  { team:{id:ids[0],code:'AAA',name:'Synthetic A'},rank:1,eligible:true,average:200.05,total_yards:4001,games_with_values:20,games_with_accepted_statistics:20,scheduled_games:20,missing_statistics_games:0,missing_metric_games:0 },
  { team:{id:ids[1],code:'BBB',name:'Synthetic B'},rank:2,eligible:true,average:100,total_yards:200,games_with_values:2,games_with_accepted_statistics:2,scheduled_games:3,missing_statistics_games:1,missing_metric_games:0 },
  { team:{id:ids[2],code:'CCC',name:'Synthetic C'},rank:2,eligible:true,average:100,total_yards:100,games_with_values:1,games_with_accepted_statistics:1,scheduled_games:1,missing_statistics_games:0,missing_metric_games:0 },
  { team:{id:ids[3],code:'DDD',name:'Synthetic D'},rank:null,eligible:false,average:null,total_yards:null,games_with_values:0,games_with_accepted_statistics:0,scheduled_games:1,missing_statistics_games:1,missing_metric_games:0 },
]; }
function rankings(url = '/api/team-rankings?season=2026&season_type=REG&category=passing_offense'): RankingsResponse {
  const q = new URL(url,'http://test').searchParams;
  const category = q.get('category') as Category;
  return { data:[{ category,direction:category.includes('defense') ? 'ascending' : 'descending',eligible_team_count:3,teams:teams() }],meta:{...policy,filters:{season:Number(q.get('season')),season_type:q.get('season_type') as 'REG',category,team_id:null},league_team_count:4,scheduled_games:13,accepted_games:12,missing_statistics_games:1,unknown_status_accepted_games:12,missing_metric_team_games:{passing_offense:0,rushing_offense:0,passing_defense:0,rushing_defense:0},unverified_origin_team_games:24,coverage_complete_for_stored_schedule:false,population_semantics:'Synthetic season population',ranking_semantics:'Exact competition ranks',completeness_semantics:'Stored schedule coverage only'} };
}
function logs(): TeamGamesResponse { return { data:[{
  game_id:'synthetic-game',source_game_id:'synthetic-source',season:2025,season_type:'REG',week:2,
  scheduled_kickoff_utc:null,source_gameday:null,team:teams()[0].team,opponent:teams()[1].team,side:'HOME',
  gross_passing_yards:200,original_sack_yards:-15,net_passing_yards:185,rushing_yards:-2,
  net_passing_yards_allowed:100,rushing_yards_allowed:0,reported_points_scored:0,reported_points_allowed:null,
  status:'UNKNOWN',score_finality:'UNVERIFIED',accepted_pair_id:ids[2],selection_generation:1,
  revision_recorded_at:'2026-11-01T00:00:00Z',schedule_source_artifact_id:ids[3],
  provenance:{artifact_id:ids[0],provider:'nflverse',artifact_sha256:'a'.repeat(64),origin_status:'DECLARED',documented_source_url:null,license_url:null,attribution:'Synthetic fixture',source_record_sha256:'b'.repeat(64),source_line:2},
}], meta:{...policy,season:2025,season_type:'REG',week:null,limit:20,offset:0,total_count:1,returned_count:1} }; }
function json(body: unknown, status=200) { return new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json'}}); }
function mock(handler: (url:string)=>Response|Promise<Response> = url => json(url.startsWith('/api/team-rankings') ? rankings(url) : logs())) {
  const fn=vi.fn((url: string, _options?: RequestInit) => handler(String(url)));vi.stubGlobal('fetch',fn);return fn;
}
function Location() { const location=useLocation();const navigate=useNavigate();return <><output aria-label="Current URL">{location.pathname}{location.search}</output><button onClick={() => navigate(-1)}>Browser back</button></>; }
function open(path='/rankings') { const client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}});render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><App/><Location/></MemoryRouter></QueryClientProvider>);return client; }
function teamRows() { return within(screen.getByRole('table')).getAllByRole('row').slice(1); }

describe('team rankings dashboard', () => {
  it('uses the actual API filters and preserves authoritative competition ties and nulls', async () => {
    const fetcher=mock();open();await screen.findByRole('link',{name:/Synthetic A/});
    expect(fetcher.mock.calls[0][0]).toBe('/api/team-rankings?season=2026&season_type=REG&category=passing_offense');
    expect(teamRows().map(row => within(row).getAllByRole('cell')[0].textContent)).toEqual(['1','2','2','—Unranked']);
    expect(screen.getByText('200.1')).toBeInTheDocument();expect(screen.getByText('Unranked')).toBeInTheDocument();
    expect(screen.getByText('Partial or unavailable coverage')).toBeInTheDocument();
    expect(screen.getByText(/not verified historical pregame rankings/)).toBeInTheDocument();
    expect(screen.getByRole('region',{name:'Team rankings table'})).toHaveAttribute('tabindex','0');
  });
  it('changes season, stage and category without losing selections', async () => {
    const fetcher=mock();open('/rankings?season=2024&season_type=POST&category=rushing_offense');
    await screen.findByRole('link',{name:/Synthetic A/});
    fireEvent.change(screen.getByLabelText('Season'),{target:{value:'2025'}});
    fireEvent.change(screen.getByLabelText('Season stage'),{target:{value:'COMBINED'}});
    fireEvent.click(screen.getByRole('link',{name:/Passing Defense/}));
    await waitFor(() => expect(fetcher.mock.calls.some(([url]) => url.includes('season=2025&season_type=COMBINED&category=passing_defense'))).toBe(true));
    expect(screen.getByLabelText('Current URL')).toHaveTextContent('season=2025&season_type=COMBINED&category=passing_defense');
    expect(screen.getByRole('heading',{name:'Passing Defense'})).toBeInTheDocument();
    expect(screen.getByText(/Lowest average allowed ranks #1/, {selector:'.subtitle'})).toBeInTheDocument();
  });
  it('sorts a copy without changing rank numbers, puts nulls last and restores API order', async () => {
    const fetcher=mock();open();await screen.findByRole('link',{name:/Synthetic A/});
    fireEvent.click(screen.getByRole('button',{name:'Sort by team'}));fireEvent.click(screen.getByRole('button',{name:'Sort by team'}));
    expect(teamRows().map(row => within(row).getByRole('link').textContent)).toEqual(expect.arrayContaining([expect.stringContaining('Synthetic D')]));
    expect(within(teamRows()[0]).getByRole('link')).toHaveTextContent('Synthetic D');
    expect(teamRows()[0]).toHaveTextContent('Unranked');expect(teamRows()[1]).toHaveTextContent('2');
    fireEvent.click(screen.getByRole('button',{name:'Sort by yards / game'}));
    expect(within(teamRows().at(-1)!).getByRole('link')).toHaveTextContent('Synthetic D');
    fireEvent.click(screen.getByRole('button',{name:'Restore API order'}));
    expect(within(teamRows()[0]).getByRole('link')).toHaveTextContent('Synthetic A');
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('restores filters and sorting through browser history', async () => {
    mock();open('/rankings?season=2024&season_type=POST&category=passing_defense&sort=team&dir=desc');
    await screen.findByRole('link',{name:/Synthetic A/});
    fireEvent.click(screen.getByRole('link',{name:/Rushing Defense/}));
    fireEvent.click(screen.getByRole('button',{name:'Browser back'}));
    expect(screen.getByLabelText('Current URL')).toHaveTextContent('category=passing_defense&sort=team&dir=desc');
  });
  it('shows loading and retryable network/server errors', async () => {
    let fail=true;mock(() => fail ? json({},503) : json(rankings()));open();
    expect(screen.getByText('Loading team rankings…')).toBeInTheDocument();
    expect(await screen.findByRole('alert')).toBeInTheDocument();fail=false;
    fireEvent.click(screen.getByRole('button',{name:'Try again'}));await screen.findByRole('link',{name:/Synthetic A/});
  });
  it('preserves cached rows on failed manual refresh', async () => {
    let fail=false;mock(url => fail ? Promise.reject(new TypeError('network failed')) : json(rankings(url)));open();
    await screen.findByRole('link',{name:/Synthetic A/});fail=true;
    fireEvent.click(screen.getByRole('button',{name:'Refresh rankings'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Previously loaded');
    expect(screen.getByRole('link',{name:/Synthetic A/})).toBeInTheDocument();
  });
  it('handles empty populations', async () => {
    mock(() => json({...rankings(),data:[]}));open();expect(await screen.findByRole('heading',{name:'No ranking records available'})).toBeInTheDocument();
  });
  it('shows all-zero-game teams as unranked, not an empty population', async () => {
    const data=rankings();data.data[0].teams=[teams()[3]];data.data[0].eligible_team_count=0;mock(() => json(data));open();
    expect(await screen.findByText('Unranked')).toBeInTheDocument();expect(screen.getByText(/No teams have contributing statistics/)).toBeInTheDocument();
  });
  it('does not fetch invalid bookmarks', () => {
    const fetcher=mock();open('/rankings?season=2030');expect(screen.getByRole('heading',{name:'Rankings selection unavailable'})).toBeInTheDocument();expect(fetcher).not.toHaveBeenCalled();
  });
  it('opens lightweight combined team research and returns with all filters', async () => {
    const fetcher=mock();open('/rankings?season=2025&season_type=COMBINED&category=passing_defense&sort=team&dir=asc');
    await screen.findByRole('link',{name:/Synthetic A/});fireEvent.click(screen.getByRole('link',{name:/Synthetic A/}));
    expect(await screen.findByRole('heading',{name:/Team game logs/})).toBeInTheDocument();
    await waitFor(() => expect(fetcher.mock.calls.some(([url]) => url.includes(`/api/teams/${ids[0]}/games?season=2025&season_type=REG&limit=20&offset=0`))).toBe(true));
    expect(fetcher.mock.calls.some(([url]) => url.includes('season_type=POST&limit=20&offset=0'))).toBe(true);
    expect(await screen.findAllByText('UNKNOWN · Finality unverified')).toHaveLength(2);
    expect(screen.queryByText('FINAL · Evidence recorded')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('link',{name:'← Back to team rankings'}));
    expect(screen.getByLabelText('Current URL')).toHaveTextContent('season=2025&season_type=COMBINED&category=passing_defense&sort=team&dir=asc');
  });
  it('handles loading, empty and failed team game logs with retry', async () => {
    let fail=true;
    mock(() => fail ? json({},503) : json({...logs(),data:[],meta:{...logs().meta,total_count:0,returned_count:0}}));
    open(`/teams/${ids[0]}/research?season=2025&season_type=REG`);
    expect(screen.getByText('Loading regular season team games…')).toBeInTheDocument();
    await screen.findByRole('alert');fail=false;
    fireEvent.click(screen.getByRole('button',{name:'Try again'}));
    expect(await screen.findByRole('heading',{name:'No accepted team statistics'})).toBeInTheDocument();
  });
  it('keeps season and stage when using research workspace navigation', async () => {
    const fetcher=mock();open(`/teams/${ids[0]}/research?season=2024&season_type=POST&category=rushing_defense`);
    fireEvent.click(screen.getByRole('link',{name:'Team rankings'}));await screen.findByRole('link',{name:/Synthetic A/});
    expect(fetcher.mock.calls.some(([url]) => url.includes('/api/team-rankings?season=2024&season_type=POST&category=rushing_defense'))).toBe(true);
  });
  it('keeps research navigation and table controls accessible at a narrow viewport', async () => {
    vi.stubGlobal('innerWidth',375);mock();open();await screen.findByRole('link',{name:/Synthetic A/});
    expect(screen.getByRole('navigation',{name:'Workspace'})).toBeInTheDocument();
    expect(screen.getByLabelText('Season stage')).toBeInTheDocument();
    expect(screen.getByRole('region',{name:'Team rankings table'})).toHaveAttribute('tabindex','0');
    expect(screen.getByRole('table')).toHaveAccessibleName(/Display sorting never changes the API rank/);
  });
  it('shows a complete stored-schedule indicator without claiming finality', async () => {
    const data=rankings();data.meta.coverage_complete_for_stored_schedule=true;data.meta.missing_statistics_games=0;
    mock(() => json(data));open();expect(await screen.findByText('Stored schedule covered')).toBeInTheDocument();
    expect(screen.getByText(/Statistics and reported scores do not establish game completion/)).toBeInTheDocument();
  });
  it('supports workspace navigation from team research to rankings', async () => {
    mock();open(`/teams/${ids[0]}/research?season=2025&season_type=REG`);
    fireEvent.click(screen.getByRole('link',{name:'Team rankings'}));await screen.findByRole('link',{name:/Synthetic A/});
    expect(screen.getByRole('link',{name:'League schedule'})).toHaveAttribute('href','/');
  });
});

describe('typed research client and sort policy', () => {
  it('passes abort signals and only contract-supported parameters', async () => {
    const fetcher=mock();const controller=new AbortController();
    await research.rankings(2024,'COMBINED','rushing_defense',controller.signal);
    expect(fetcher.mock.calls[0][0]).toBe('/api/team-rankings?season=2024&season_type=COMBINED&category=rushing_defense');
    expect(fetcher.mock.calls[0][1]).toEqual(expect.objectContaining({signal:controller.signal}));
  });
  it('rejects non-JSON responses without leaking server bodies', async () => {
    vi.stubGlobal('fetch',vi.fn(() => Promise.resolve(new Response('PRIVATE_ERROR',{headers:{'content-type':'text/html'}}))));
    await expect(research.rankings(2024,'REG','passing_offense')).rejects.toThrow('unexpected response');
  });
  it('never mutates rows, reranks ties, or converts nulls to zero', () => {
    const input=teams();const snapshot=JSON.stringify(input);
    expect(sortedTeams(input,'average','asc').map(row => row.rank)).toEqual([2,2,1,null]);
    expect(sortedTeams(input,'average','desc').at(-1)?.rank).toBeNull();
    expect(JSON.stringify(input)).toBe(snapshot);
    expect(selection(new URLSearchParams('season=2024&season=2025'))).toBeNull();
  });
});
