import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import type { Category, RankedTeam, RankingsResponse } from '../api/research';
import { categories } from '../rankings/state';
import { detail, noMarkets, freshness, game, id, schedule, seasons } from './fixtures';

// Synthetic response only. These ranks are provided by the mock API, not calculated by the UI.
function rankings(): RankingsResponse {
  const row = (team: ReturnType<typeof game>['home_team'], rank: number, average: number): RankedTeam => ({
    team, rank, average, eligible: true, total_yards: average * 2, games_with_values: 2,
    games_with_accepted_statistics: 2, scheduled_games: 3, missing_statistics_games: 1, missing_metric_games: 0,
  });
  return { data: (Object.keys(categories) as Category[]).map((category, index) => ({
    category, direction: category.includes('defense') ? 'ascending' : 'descending', eligible_team_count: 32,
    teams: [row(game().home_team, index + 4, 123.45 + index), row(game().away_team, index + 1, 234.56 + index)],
  })), meta: {
    filters: { season: 2026, season_type: 'REG', category: null, team_id: null },
    definition_version: 'net_pass_negative_sacks_v1', statistics_semantics: 'Synthetic NET', score_semantics: 'Unverified',
    aggregate_semantics: 'Reconstructed', origin_semantics: 'Declared', league_team_count: 32,
    scheduled_games: 272, accepted_games: 135, missing_statistics_games: 137, unknown_status_accepted_games: 135,
    missing_metric_team_games: { passing_offense: 0, rushing_offense: 0, passing_defense: 0, rushing_defense: 0 },
    unverified_origin_team_games: 270, coverage_complete_for_stored_schedule: false,
    population_semantics: 'League', ranking_semantics: 'Competition', completeness_semantics: 'Stored schedule only',
  } };
}
function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } }); }
function mock(data = game(), handler: (url: string) => Response | Promise<Response> = () => json(rankings())) {
  const fetcher = vi.fn((path: string) => {
    const url = String(path);
    if (url.endsWith('/markets')) return json(noMarkets(data));
    if (url.startsWith('/api/team-rankings')) return handler(url);
    if (url === `/api/games/${id}`) return json(detail(data));
    if (url === '/api/seasons') return json(seasons);
    if (url === '/api/data-status/schedule') return json(freshness);
    return json(schedule([data]));
  });
  vi.stubGlobal('fetch', fetcher); return fetcher;
}
function Location() { const location = useLocation(); return <output aria-label="Location">{location.pathname}{location.search}</output>; }
function open(path = `/games/${id}`) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><App /><Location /></MemoryRouter></QueryClientProvider>);
  return client;
}
const table = () => screen.getByRole('table');

describe('Game Preview season comparison', () => {
  it('uses one league request for all four categories, canonical identities and authoritative ranks', async () => {
    const fetcher = mock(); open(); await screen.findByRole('table');
    const rows = within(table()).getAllByRole('row').slice(1);
    expect(rows).toHaveLength(4);
    rows.forEach((row, index) => {
      const cells = within(row).getAllByRole('cell');
      expect(cells[0]).toHaveTextContent(`#${index + 1}`);
      expect(cells[1]).toHaveTextContent(`#${index + 4}`);
    });
    expect(screen.getByText('234.6')).toBeInTheDocument();
    expect(within(table()).getAllByText('Highest average ranks #1')).toHaveLength(2);
    expect(within(table()).getAllByText('Lowest average allowed ranks #1')).toHaveLength(2);
    expect(screen.getByRole('columnheader', { name: /Synthetic Away.*BBB/ })).toBeInTheDocument();
    expect(fetcher.mock.calls.filter(([url]) => url.startsWith('/api/team-rankings')).map(([url]) => url))
      .toEqual(['/api/team-rankings?season=2026&season_type=REG']);
  });
  it('labels current revisions honestly even for historical games with reported scores', async () => {
    mock(game({ season: 2024 })); open(); await screen.findByRole('table');
    expect(screen.getByText('Historical pregame rankings unavailable')).toBeInTheDocument();
    expect(screen.getByText(/may include this matchup and later games/)).toBeInTheDocument();
    expect(screen.getByText('Reported scores · Finality unverified')).toBeInTheDocument();
    expect(screen.getByText('UNKNOWN · Finality unverified')).toBeInTheDocument();
    expect(screen.queryByText('Confirmed final scores')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Synthetic Away \(BBB\)/ })).toHaveAttribute('href', '/teams/synthetic-away/research?season=2024&season_type=REG');
  });
  it('defaults postseason to POST and preserves returnTo when explicitly combining stages', async () => {
    const fetcher = mock(game({ season: 2025, season_type: 'POST', week: 19, game_type: 'WC' }));
    open(`/games/${id}?returnTo=${encodeURIComponent('/schedule/2025/POST/WC')}`);
    await screen.findByRole('table');
    expect(fetcher.mock.calls.some(([url]) => url === '/api/team-rankings?season=2025&season_type=POST')).toBe(true);
    expect(screen.getByLabelText('Comparison stage')).toHaveValue('POST');
    fireEvent.change(screen.getByLabelText('Comparison stage'), { target: { value: 'COMBINED' } });
    await waitFor(() => expect(fetcher.mock.calls.some(([url]) => url.endsWith('season_type=COMBINED'))).toBe(true));
    expect(screen.getByLabelText('Location')).toHaveTextContent('comparison_stage=COMBINED');
    expect(screen.getByRole('link', { name: '← Back to schedule' })).toHaveAttribute('href', '/schedule/2025/POST/WC');
  });
  it('honors explicit stage links', async () => {
    const fetcher = mock(); open(`/games/${id}?comparison_stage=POST`); await screen.findByRole('table');
    expect(fetcher.mock.calls.some(([url]) => url === '/api/team-rankings?season=2026&season_type=POST')).toBe(true);
    expect(screen.getByLabelText('Comparison stage')).toHaveValue('POST');
  });
  it.each(['INVALID', 'REG&comparison_stage=POST'])('rejects invalid or repeated stage %s without a rankings request', async value => {
    const fetcher = mock(); open(`/games/${id}?comparison_stage=${value}`);
    expect(await screen.findByText('Comparison selection unavailable')).toBeInTheDocument();
    expect(fetcher.mock.calls.filter(([url]) => url.startsWith('/api/team-rankings'))).toHaveLength(0);
    fireEvent.click(screen.getByRole('button', { name: "Use game's stage" }));
    await screen.findByRole('table'); expect(screen.getByLabelText('Comparison stage')).toHaveValue('REG');
  });
  it('preserves nulls, zeros, negative averages, tied ranks and zero-game teams', async () => {
    const data = rankings();
    data.data[0].teams[0] = { ...data.data[0].teams[0], rank: null, eligible: false, average: null, total_yards: null, games_with_values: 0 };
    data.data[1].teams.forEach(row => { row.rank = 2; row.average = 0; });
    data.data[2].teams[0].average = -3;
    mock(game({ reported_home_score: null, reported_away_score: null, score_finality: 'NOT_REPORTED', scheduled_kickoff_utc: null }), () => json(data));
    open(); await screen.findByRole('table');
    expect(screen.getByText('Unranked')).toBeInTheDocument(); expect(screen.getByText('No contributing statistics')).toBeInTheDocument();
    const rush = within(table()).getAllByRole('row')[2]; expect(within(rush).getAllByText('#2')).toHaveLength(2);
    expect(within(rush).getAllByText('0.0')).toHaveLength(2); expect(screen.getByText('-3.0')).toBeInTheDocument();
    expect(screen.getByText('Scores not reported')).toBeInTheDocument();
    expect(screen.getAllByText('Kickoff not announced').length).toBeGreaterThan(0);
  });
  it('handles missing teams and absent categories independently', async () => {
    const data = rankings(); data.data[0].teams = data.data[0].teams.slice(1); data.data.pop();
    mock(game(), () => json(data)); open(); await screen.findByRole('table');
    expect(screen.getAllByText('No contributing statistics')).toHaveLength(3);
    expect(screen.getByText('#1')).toBeInTheDocument();
  });
  it('keeps Week 1 zero-game teams visible and unranked', async () => {
    const data = rankings();
    data.data.forEach(category => {
      category.eligible_team_count = 0;
      category.teams.forEach(row => Object.assign(row, { eligible: false, rank: null, average: null, total_yards: null, games_with_values: 0, games_with_accepted_statistics: 0 }));
    });
    mock(game({ week: 1 }), () => json(data)); open(); await screen.findByRole('table');
    expect(within(table()).getAllByText('Unranked')).toHaveLength(8);
    expect(within(table()).queryByText('0.0')).not.toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Matchup rankings comparison' })).toHaveAttribute('tabindex', '0');
  });
  it('does not treat evidence for the selected game as pregame eligibility for other games', async () => {
    mock(game({ status: 'FINAL', score_finality: 'CONFIRMED_FINAL', final_evidence: { url: 'https://example.invalid/synthetic-final', verified_at: '2026-11-01T00:00:00Z' } }));
    open(); await screen.findByRole('table');
    expect(screen.getByText('Confirmed final scores')).toBeInTheDocument();
    expect(screen.getByText('Historical pregame rankings unavailable')).toBeInTheDocument();
    expect(screen.getByText(/may include this matchup and later games/)).toBeInTheDocument();
  });
  it('shows an empty population and incomplete coverage without fabricating ranks', async () => {
    mock(game(), () => json({ ...rankings(), data: [] })); open();
    expect(await screen.findByText('No matchup ranking records available')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.getByText(/Partial or unavailable coverage/)).toBeInTheDocument();
  });
  it('keeps the game visible while comparison loads', async () => {
    mock(game(), () => new Promise<Response>(() => {})); open();
    expect(await screen.findByText('Loading matchup comparison…')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Synthetic Away' })).toBeInTheDocument();
  });
  it('isolates comparison errors and supports retry', async () => {
    let fail = true; mock(game(), () => fail ? json({}, 503) : json(rankings())); open();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Synthetic Home' })).toBeInTheDocument();
    fail = false; fireEvent.click(screen.getByRole('button', { name: 'Try again' })); await screen.findByRole('table');
  });
  it('retains prior comparison on failed refresh', async () => {
    let fail = false; mock(game(), () => fail ? Promise.reject(new TypeError('network')) : json(rankings())); open();
    await screen.findByRole('table'); fail = true; fireEvent.click(screen.getByRole('button', { name: 'Refresh comparison' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Previously loaded'); expect(table()).toBeInTheDocument();
  });
  it('navigates from the weekly schedule and returns to the same week', async () => {
    mock(); open('/schedule/2026/REG/1');
    fireEvent.click(await screen.findByRole('link', { name: /Synthetic Away at Synthetic Home, view matchup/ }));
    await screen.findByRole('table'); expect(screen.getByLabelText('Location')).toHaveTextContent(`/games/${id}`);
    fireEvent.click(screen.getByRole('link', { name: '← Back to schedule' }));
    expect(await screen.findByRole('heading', { name: 'Week 1' })).toBeInTheDocument();
  });
});
