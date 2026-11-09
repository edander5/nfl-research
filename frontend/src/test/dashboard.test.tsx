import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import { api, kickoff, safeUrl } from '../api/client';
import { detail, game, id, schedule, seasons } from './fixtures';
function response(data: unknown, status=200) { return new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json'}}); }
function defaultResponse(url: string) {
  if (url === '/api/seasons') return response(seasons);
  if (url.startsWith('/api/games/')) return response(detail());
  const parsed = new URL(url, 'http://test');
  const year = Number(parsed.pathname.split('/')[3]);
  const stage = parsed.searchParams.get('season_type') === 'POST' ? 'POST' : 'REG';
  const round = parsed.searchParams.get('round') as 'WC' | 'DIV' | 'CON' | 'SB' | null;
  const week = stage === 'REG' ? Number(parsed.searchParams.get('week') ?? 1) : ({ WC:19,DIV:20,CON:21,SB:22 }[round ?? 'WC']);
  const data = schedule([game({season:year,season_type:stage,week,game_type:stage === 'REG' ? 'REG' : round ?? 'WC'})]);
  data.meta = {...data.meta,season:year,filters:{season_type:stage,week:stage === 'REG' ? week : null,round},season_coverage:seasons.data.find(s => s.season === year)!.coverage};
  return response(data);
}
function mock(handler: (url: string) => Response | Promise<Response> = defaultResponse) {
  const fetcher = vi.fn((url: string) => handler(String(url)));
  vi.stubGlobal('fetch',fetcher);
  return fetcher;
}
function open(path='/schedule/2026/REG/1') { const client = new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}}); render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></QueryClientProvider>); return client; }
describe('weekly schedule', () => {
  it('fetches schedule dates and redirects home to the active week', async () => { vi.spyOn(Date, 'now').mockReturnValue(new Date('2026-09-13T17:00:00Z').getTime()); const fetcher=mock();open('/');expect(await screen.findByRole('heading',{name:'Week 1'})).toBeInTheDocument();expect(fetcher.mock.calls.some(([url]) => url === '/api/seasons/2026/schedule?season_type=REG&week=1')).toBe(true); });
  it('displays reported zero and UNKNOWN without claiming FINAL', async () => { mock();open();expect(await screen.findByText('Synthetic Away')).toBeInTheDocument();expect(screen.getByText('0')).toBeInTheDocument();expect(screen.getByText('UNKNOWN · Finality unverified')).toBeInTheDocument();expect(screen.getByText('Reported scores · Finality unverified')).toBeInTheDocument();expect(screen.queryByText('Confirmed final scores')).not.toBeInTheDocument(); });
  it('changes week with bookmarkable route and complete query key', async () => { const fetcher=mock();open();await screen.findByText('Synthetic Away');fireEvent.click(screen.getByRole('link',{name:'W2'}));await waitFor(() => expect(fetcher.mock.calls.some(([url]) => url.endsWith('season_type=REG&week=2'))).toBe(true));expect(screen.getByRole('heading',{name:'Week 2'})).toBeInTheDocument(); });
  it('selects another season and available postseason round', async () => {const fetcher=mock();open();await screen.findByText('Synthetic Away');fireEvent.change(screen.getByLabelText('Season'),{target:{value:'2024'}});await waitFor(() => expect(fetcher.mock.calls.some(([url]) => url.includes('/2024/schedule?season_type=REG'))).toBe(true));fireEvent.click(screen.getByRole('button',{name:'Postseason'}));await waitFor(() => expect(fetcher.mock.calls.some(([url]) => url.endsWith('season_type=POST&round=WC'))).toBe(true));expect(screen.getByRole('heading',{name:'Wild Card'})).toBeInTheDocument();});
  it('keeps missing postseason unavailable and explains coverage', async () => {mock();open();await screen.findByText('Synthetic Away');expect(screen.getByRole('button',{name:/Postseason/})).toBeDisabled();expect(screen.getByText(/No postseason matchups are available for 2026/)).toBeInTheDocument();});
  it('handles a direct absent-postseason link without fabricated games', async () => {mock(url => response(url === '/api/seasons' ? seasons : schedule([])));open('/schedule/2026/POST/all');expect(await screen.findByRole('heading',{name:'No matchups available'})).toBeInTheDocument();expect(screen.queryByText('Synthetic Away')).not.toBeInTheDocument();});
  it('shows loading while seasons are pending', () => {mock(() => new Promise<Response>(() => {}));open();expect(screen.getByRole('status')).toHaveTextContent('Loading available seasons');});
  it('shows game loading while schedule is pending', async () => {mock(url => url === '/api/seasons' ? response(seasons) : new Promise<Response>(() => {}));open();expect(await screen.findByText('Loading schedule…')).toBeInTheDocument();});
  it('handles an empty seasons database', async () => {mock(() => response({...seasons,data:[]}));open();expect(await screen.findByRole('heading',{name:'No seasons available'})).toBeInTheDocument();});
  it('handles HTTP failure and supports retry', async () => {let failed=true;mock(url => response(url === '/api/seasons' ? seasons : failed ? {} : schedule(),url === '/api/seasons' || !failed ? 200 : 503));open();expect(await screen.findByRole('alert')).toBeInTheDocument();failed=false;fireEvent.click(screen.getByRole('button',{name:'Try again'}));expect(await screen.findByText('Synthetic Away')).toBeInTheDocument();});
  it('handles network failure', async () => {mock(() => Promise.reject(new TypeError('Network failure')));open();expect(await screen.findByRole('alert')).toBeInTheDocument();});
  it('preserves cached games when refresh fails', async () => {let failed=false;mock(url => response(url === '/api/seasons' ? seasons : failed ? {} : schedule(),url === '/api/seasons' || !failed ? 200 : 503));open();await screen.findByText('Synthetic Away');failed=true;fireEvent.click(screen.getByRole('button',{name:'Refresh schedule'}));expect(await screen.findByRole('alert')).toHaveTextContent('previously loaded data');expect(screen.getByText('Synthetic Away')).toBeInTheDocument();});
  it('does not request invalid filters', async () => {const fetcher=mock();open('/schedule/2026/REG/99');expect(await screen.findByRole('heading',{name:'Schedule selection unavailable'})).toBeInTheDocument();expect(fetcher.mock.calls).toHaveLength(1);});
});
describe('matchup navigation', () => {
  it('opens a canonical game and returns to the selected week', async () => {mock();open('/schedule/2026/REG/2');await screen.findByText('Synthetic Away');fireEvent.click(screen.getByRole('link',{name:/view matchup/}));expect(await screen.findByRole('heading',{name:/Matchup overview/})).toBeInTheDocument();expect(screen.getByRole('link',{name:'← Back to schedule'})).toHaveAttribute('href','/schedule/2026/REG/2');fireEvent.click(screen.getByRole('link',{name:'← Back to schedule'}));expect(await screen.findByRole('heading',{name:'Week 2'})).toBeInTheDocument();});
  it('supports direct detail links, null scores and unknown kickoff', async () => {mock(() => response(detail(game({reported_home_score:null,reported_away_score:null,scheduled_kickoff_utc:null,score_finality:'NOT_REPORTED'}))));open(`/games/${id}`);expect(await screen.findByRole('heading',{name:/Matchup overview/})).toBeInTheDocument();expect(screen.getByText('Scores not reported')).toBeInTheDocument();expect(screen.getAllByText('Kickoff not announced').length).toBeGreaterThan(0);expect(screen.getByText('Declared · Not independently authenticated')).toBeInTheDocument();});
  it('does not trust external return destinations', async () => {mock();open(`/games/${id}?returnTo=https://example.invalid`);expect(await screen.findByRole('link',{name:'← Back to schedule'})).toHaveAttribute('href','/schedule/2026/REG/1');});
  it('shows stored FINAL only with explicit evidence', async () => {mock(() => response(detail(game({status:'FINAL',score_finality:'CONFIRMED_FINAL',final_evidence:{url:'https://example.invalid/final',verified_at:'2026-11-07T00:00:00Z'}}))));open(`/games/${id}`);expect(await screen.findByText('FINAL · Evidence recorded')).toBeInTheDocument();expect(screen.getByText('Confirmed final scores')).toBeInTheDocument();expect(screen.getByRole('link',{name:/Stored final evidence/})).toHaveAttribute('href','https://example.invalid/final');});
  it('handles game not found', async () => {mock(() => response({},404));open(`/games/${id}`);expect(await screen.findByRole('heading',{name:'Matchup not found'})).toBeInTheDocument();});
  it('rejects malformed UUID without a request', () => {const fetcher=mock();open('/games/invalid');expect(screen.getByRole('heading',{name:'Matchup not found'})).toBeInTheDocument();expect(fetcher).not.toHaveBeenCalled();});
});
describe('API client and formatting', () => {
  it('sends GET with cancellation and encoded round filters', async () => {const fetcher=mock();const signal=new AbortController().signal;await api.schedule(2025,'POST','DIV',signal);expect(fetcher).toHaveBeenCalledWith('/api/seasons/2025/schedule?season_type=POST&round=DIV',expect.objectContaining({signal}));});
  it('rejects HTML proxy errors rather than treating them as data', async () => {vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('<html/>',{headers:{'content-type':'text/html'}})));await expect(api.seasons()).rejects.toThrow('unexpected response');});
  it('uses explicit Eastern daylight and standard time', () => {expect(kickoff('2026-09-13T17:00:00Z')).toContain('EDT');expect(kickoff('2026-12-13T18:00:00Z')).toContain('EST');expect(kickoff(null)).toBe('Kickoff not announced');});
  it('rejects executable source URLs', () => {expect(safeUrl('javascript:alert(1)')).toBeUndefined();expect(safeUrl(null)).toBeUndefined();});
});

describe('current-week home routing', () => {
  it('opens the actual active week instead of week 1', async () => {
    vi.spyOn(Date,'now').mockReturnValue(new Date('2026-11-09T17:00:00Z').getTime());
    const fetcher = mock(url => {
      if (url === '/api/seasons') return response(seasons);
      if (url === '/api/seasons/2026/schedule?season_type=REG') return response(schedule([
        game({week:9,scheduled_kickoff_utc:'2026-11-06T01:15:00Z'}),
        game({week:9,scheduled_kickoff_utc:'2026-11-10T01:15:00Z'}),
        game({week:10,scheduled_kickoff_utc:'2026-11-13T01:15:00Z'}),
      ]));
      return defaultResponse(url);
    });
    open('/');
    expect(await screen.findByRole('heading',{name:'Week 9'})).toBeInTheDocument();
    expect(fetcher.mock.calls.some(([url]) => url.endsWith('season_type=REG&week=9'))).toBe(true);
    fireEvent.click(screen.getByRole('link',{name:'W1'}));
    expect(await screen.findByRole('heading',{name:'Week 1'})).toBeInTheDocument();
  });
  it.each([
    ['/schedule/2024/REG/2','Week 2','/api/seasons/2024/schedule?season_type=REG&week=2'],
    ['/schedule/2025/POST/DIV','Divisional','/api/seasons/2025/schedule?season_type=POST&round=DIV'],
  ])('preserves explicit URL %s without loading the default calendar', async (path,title,endpoint) => {
    vi.spyOn(Date,'now').mockReturnValue(new Date('2026-11-09T17:00:00Z').getTime());
    const fetcher=mock();
    open(path);
    expect(await screen.findByRole('heading',{name:title})).toBeInTheDocument();
    await screen.findByText('Synthetic Away');
    expect(fetcher.mock.calls.map(([url]) => url)).toEqual(['/api/seasons',endpoint]);
  });
  it('opens the current postseason round in the previous calendar-year NFL season', async () => {
    vi.spyOn(Date,'now').mockReturnValue(new Date('2027-02-07T18:00:00Z').getTime());
    const available={...seasons,data:seasons.data.map(y => y.season === 2026 ? {...y,coverage:y.coverage.map(c => c.season_type === 'POST' ? {...c,game_count:1,weeks:[22],rounds:['SB' as const]} : c)} : y)};
    mock(url => url === '/api/seasons' ? response(available) : url.includes('/2026/schedule?season_type=POST') ?
      response(schedule([game({season:2026,season_type:'POST',week:22,game_type:'SB',scheduled_kickoff_utc:'2027-02-07T23:30:00Z'})])) : defaultResponse(url));
    open('/');
    expect(await screen.findByRole('heading',{name:'Super Bowl'})).toBeInTheDocument();
  });
  it('shows a disclosed fallback when all kickoff dates are unknown', async () => {
    mock(url => url === '/api/seasons' ? response(seasons) : response(schedule([
      game({scheduled_kickoff_utc:null,source_gameday:null}),
    ])));
    open('/');
    expect(await screen.findByText(/Schedule dates are unavailable/)).toBeInTheDocument();
    expect(screen.getByRole('heading',{name:'Week 1'})).toBeInTheDocument();
  });
  it('waits for full calendar data before deciding the default', async () => {
    mock(url => url === '/api/seasons' ? response(seasons) : new Promise<Response>(() => {}));
    open('/');
    expect(await screen.findByText('Finding the current schedule week…')).toBeInTheDocument();
    expect(screen.queryByRole('heading',{name:'Week 1'})).not.toBeInTheDocument();
  });
  it('reports calendar request failures rather than guessing week 1', async () => {
    mock(url => url === '/api/seasons' ? response(seasons) : response({},503));
    open('/');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.queryByRole('heading',{name:'Week 1'})).not.toBeInTheDocument();
  });
});
