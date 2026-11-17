import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { research } from '../api/research';
import type { MetricAggregate, TrendWindow } from '../api/research';
import type { Game, Team } from '../api/types';
import { numeric, stageLabels } from '../rankings/state';
import { Loading } from './shared';

const windows: Record<TrendWindow, string> = { L3: 'Last 3 Games', L5: 'Last 5 Games', L10: 'Last 10 Games' };

function useTrends(team: Team, game: Game, window: TrendWindow) {
  return useQuery({ queryKey: ['team-trends', team.id, game.season, game.season_type, window, game.id],
    queryFn: ({ signal }) => research.trends(team.id, game.season, game.season_type, window, game.id, signal),
    staleTime: 60_000, retry: false, refetchOnWindowFocus: false });
}
type TrendsQuery = ReturnType<typeof useTrends>;

function TeamStatus({ team, query, window }: { team: Team; query: TrendsQuery; window: TrendWindow }) {
  const response = query.data;
  return <article className="trends-team-status" aria-label={`${team.name} trend status`}>
    <h3>{team.name} <span>({team.code})</span></h3>
    {query.isPending ? <Loading label={`Loading ${team.code} trends…`}/> : <>
      {query.isError && <div role="alert" className="error-panel"><strong>{response ? 'Reload failed; showing previously loaded trends.' : `${team.code} trends could not be loaded.`}</strong>
        <button className="button secondary" onClick={() => void query.refetch()}>Retry {team.code} trends</button></div>}
      {response && <>
        <p className="trends-sample">{windows[window]} ({response.data.eligible_game_count} available)</p>
        {response.meta.unavailable_reason === 'matchup_kickoff_unknown' ? <p>Matchup chronology unavailable: kickoff is unknown. Trends are withheld.</p> :
          response.data.eligible_game_count === 0 ? <p>No eligible games before this matchup in this season and stage.</p> : <>
            {(!response.meta.window_complete || !response.meta.selected_metrics_complete) && <p className="coverage-pill">Partial coverage · see each metric’s sample.</p>}
            <button className="text-link" disabled={query.isFetching} onClick={() => void query.refetch()}>{query.isFetching ? `Checking ${team.code} trends…` : `Refresh ${team.code} trends`}</button>
          </>}
        {(response.meta.excluded_unknown_kickoff_games > 0 || response.meta.scheduled_games_without_accepted_statistics > 0) &&
          <p className="coverage-note">{response.meta.excluded_unknown_kickoff_games} accepted games excluded for unknown kickoff · {response.meta.scheduled_games_without_accepted_statistics} stored games in scope without accepted statistics. Missing games are not zeroes.</p>}
      </>}
    </>}
  </article>;
}

function Metric({ team, query, metric, label, points }: {
  team: Team; query: TrendsQuery; metric: MetricAggregate | undefined; label: string; points: boolean;
}) {
  const available = query.data && query.data.data.eligible_game_count > 0 && !query.data.meta.unavailable_reason;
  return <>
    <strong>{team.name} ({team.code})</strong><small className="cell-note">{label}</small>
    {query.isPending ? <span>Loading…</span> : !available || !metric ? <span className="trends-unavailable">{query.isError ? 'Trends unavailable' : 'No eligible sample'}</span> : <>
      <span className="trends-value">{metric.average === null ? <span aria-label="Statistic unavailable">—</span> : numeric(metric.average, 1)} <small>{points ? 'pts / game' : 'yds / game'}</small></span>
      <small className="cell-note">{metric.games_with_values} of {query.data!.data.eligible_game_count} games{metric.games_with_values < query.data!.data.eligible_game_count ? ' · Partial metric sample' : ''}</small>
      {metric.average === null && <small className="cell-note">Statistic unavailable; missing values are not zero.</small>}
    </>}
  </>;
}

export function TeamPerformanceTrends({ game }: { game: Game }) {
  const [window, setWindow] = useState<TrendWindow>('L5');
  const away = useTrends(game.away_team, game, window);
  const home = useTrends(game.home_team, game, window);
  const hasSample = [away, home].some(query => query.data && query.data.data.eligible_game_count > 0 && !query.data.meta.unavailable_reason);
  const pairings = [[game.away_team, away, game.home_team, home], [game.home_team, home, game.away_team, away]] as const;
  return <section className="team-performance-trends" aria-labelledby="trends-title">
    <div className="section-heading"><div><p className="eyebrow">{game.season} / {stageLabels[game.season_type]}</p><h2 id="trends-title">Team Performance Trends</h2>
      <p className="subtitle">Recent offense versus opposing defense · NET passing includes sacks.</p></div>
      <div className="season-control"><label htmlFor="trends-window">Trends window</label><select id="trends-window" value={window} onChange={event => setWindow(event.target.value as TrendWindow)}>
        {Object.entries(windows).map(([value, label]) => <option key={value} value={value}>{value} — {label}</option>)}
      </select></div>
    </div>
    <p className="coverage-note">Matchup-specific trends use currently accepted statistics before this matchup’s kickoff, not independently verified pregame snapshots. Points are source-reported, not independently verified final results.</p>
    <div className="trends-status-grid"><TeamStatus team={game.away_team} query={away} window={window}/><TeamStatus team={game.home_team} query={home} window={window}/></div>
    {hasSample && <div className="research-table-wrap comparison-table-wrap" role="region" aria-label="Team performance trends comparison" tabIndex={0}>
      <table className="research-table comparison-table trends-table"><caption>{windows[window]} · {game.season} · {stageLabels[game.season_type]} · Current accepted matchup reconstruction</caption>
        <thead><tr><th scope="col">Matchup</th><th scope="col">Offense</th><th scope="col">Opposing defense</th></tr></thead><tbody>
          {pairings.flatMap(([offense, offenseQuery, defense, defenseQuery]) => ([
            ['Net passing yards per game', 'Net passing yards allowed per game', 'net_passing_yards', 'net_passing_yards_allowed', 'passing'],
            ['Rushing yards per game', 'Rushing yards allowed per game', 'rushing_yards', 'rushing_yards_allowed', 'rushing'],
            ['Points scored per game · source-reported', 'Points allowed per game · source-reported', 'reported_points_scored', 'reported_points_allowed', 'points'],
          ] as const).map(([offenseLabel, defenseLabel, offenseKey, defenseKey, kind]) => <tr key={`${offense.id}-${kind}`}>
            <th scope="row">{offense.code} {kind} offense vs. {defense.code} defense</th>
            <td><Metric team={offense} query={offenseQuery} label={offenseLabel} metric={offenseQuery.data?.data.offense[offenseKey]} points={kind === 'points'}/></td>
            <td><Metric team={defense} query={defenseQuery} label={defenseLabel} metric={defenseQuery.data?.data.defense[defenseKey]} points={kind === 'points'}/></td>
          </tr>))}
        </tbody>
      </table>
    </div>}
    {[away, home].some(query => query.data) && <details className="policy"><summary>Trend eligibility &amp; coverage</summary>
      <p>Each average and sample comes from the API. Missing observations are excluded per metric; no older games are added to fill a metric. Season and stage follow this matchup independently of the season-ranking filters.</p>
      {pairings.map(([team, query]) => query.data && <div key={team.id}><strong>{team.name}</strong>
        <p>Cutoff (UTC): {query.data.meta.cutoff_utc ?? 'Unavailable'} · {query.data.meta.selected_unknown_status_games} selected games retain UNKNOWN status · {query.data.meta.selected_unverified_score_games} selected games have unverified scores.</p>
        <p>{query.data.meta.cutoff_semantics}</p></div>)}
    </details>}
  </section>;
}
