import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router';
import { research } from '../api/research';
import type { RankedTeam, RankingStage } from '../api/research';
import type { Game } from '../api/types';
import { categories, numeric, stageLabels } from '../rankings/state';
import { ResearchContext, ResearchFailure } from './ResearchShared';
import { Empty, Loading } from './shared';

function TeamMetric({ row }: { row: RankedTeam | undefined }) {
  if (!row || !row.eligible || row.games_with_values === 0) return <><strong className="comparison-unranked">Unranked</strong><span>No contributing statistics</span></>;
  return <><strong className="comparison-rank">{row.rank === null ? 'Unranked' : `#${row.rank}`}</strong>
    <span className="comparison-average">{numeric(row.average, 1)} <small>yds / game</small></span>
    <small>{row.games_with_values} contributing games</small>
    {(row.missing_statistics_games > 0 || row.missing_metric_games > 0) && <small className="coverage-pill">Partial sample · {row.missing_statistics_games} missing stats · {row.missing_metric_games} missing metric</small>}</>;
}

/** Season reconstruction only. Never derive a pregame cutoff from kickoff or scores. */
export function MatchupComparison({ game }: { game: Game }) {
  const [params, setParams] = useSearchParams();
  const requested = params.get('comparison_stage') ?? game.season_type;
  const valid = params.getAll('comparison_stage').length <= 1 && Object.hasOwn(stageLabels, requested);
  const stage = requested as RankingStage;
  const query = useQuery({
    queryKey: ['team-rankings', game.season, stage, 'all'],
    queryFn: ({ signal }) => research.comparison(game.season, stage, signal),
    enabled: valid, staleTime: 60_000, retry: false, refetchOnWindowFocus: false,
  });
  const move = (value: string | null) => {
    const next = new URLSearchParams(params);
    next.delete('comparison_stage');
    if (value) next.set('comparison_stage', value);
    setParams(next);
  };
  const teamLink = (id: string) => `/teams/${encodeURIComponent(id)}/research?${new URLSearchParams({ season: String(game.season), season_type: stage })}`;
  return <section className="matchup-comparison" aria-labelledby="comparison-title">
    <div className="section-heading"><div><p className="eyebrow">{game.season} / TEAM COMPARISON</p><h2 id="comparison-title">Current accepted season comparison</h2><p className="subtitle">Four independent league ranks. NET passing includes sacks.</p></div>
      {valid && <div className="season-control"><label htmlFor="comparison-stage">Comparison stage</label><select id="comparison-stage" value={stage} onChange={e => move(e.target.value)}>{Object.entries(stageLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></div>}
    </div>
    <div className="comparison-warning"><strong>Historical pregame rankings unavailable</strong><p>Completion-before-kickoff evidence is unavailable. This comparison uses current accepted statistics for this game's season and selected stage; it may include this matchup and later games. It is not a pregame snapshot or prediction.</p></div>
    {!valid ? <Empty title="Comparison selection unavailable"><p>Choose a supported season stage.</p><button className="button" onClick={() => move(null)}>Use game's stage</button></Empty> : <>
      {query.isError && <ResearchFailure stale={!!query.data} retry={() => void query.refetch()} />}
      {query.isPending ? <Loading label="Loading matchup comparison…" /> : query.data && <>
        <p className="coverage-note">{game.season} · {stageLabels[stage]} · {query.data.meta.accepted_games} accepted / {query.data.meta.scheduled_games} stored schedule games. {query.data.meta.coverage_complete_for_stored_schedule ? 'Stored schedule covered.' : 'Partial or unavailable coverage; future games may be included in missing coverage.'}</p>
        {!query.data.data.some(category => category.teams.some(row => row.team.id === game.away_team.id || row.team.id === game.home_team.id)) ? <Empty title="No matchup ranking records available"><p>Neither team has ranking records for this selection.</p></Empty> : <div className="research-table-wrap comparison-table-wrap" role="region" aria-label="Matchup rankings comparison" tabIndex={0}>
          <table className="research-table comparison-table"><caption>{game.season} · {stageLabels[stage]} · Current accepted season ranks, not pregame ranks</caption><thead><tr><th scope="col">Category</th><th scope="col"><Link to={teamLink(game.away_team.id)}>{game.away_team.name} ({game.away_team.code})</Link><small className="cell-note">Away</small></th><th scope="col"><Link to={teamLink(game.home_team.id)}>{game.home_team.name} ({game.home_team.code})</Link><small className="cell-note">Home</small></th></tr></thead>
          <tbody>{Object.entries(categories).map(([key, definition]) => {
            const category = query.data.data.find(item => item.category === key);
            return <tr key={key}><th scope="row">{definition.label}<small className="cell-note">{definition.metric}</small><small className="cell-note">{definition.direction}</small></th>{[game.away_team, game.home_team].map(team => <td key={team.id}><TeamMetric row={category?.teams.find(row => row.team.id === team.id)} /></td>)}</tr>;
          })}</tbody></table>
        </div>}
        <p className="coverage-note">Ranks come directly from the full league API population, including competition ties. Display averages are rounded to one decimal; each metric uses only games with non-null values. Missing values are not zero. There is no overall rank.</p>
        <button className="button secondary" disabled={query.isFetching} onClick={() => void query.refetch()}>{query.isFetching ? 'Checking comparison…' : 'Refresh comparison'}</button>
      </>}
    </>}
    <ResearchContext />
  </section>;
}
