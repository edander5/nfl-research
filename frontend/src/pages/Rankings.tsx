import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router';
import { research } from '../api/research';
import { categories, numeric, paramsFor, researchPath, selection, sortedTeams, stageLabels } from '../rankings/state';
import type { Sort } from '../rankings/state';
import { Empty, Loading } from '../components/shared';
import { ResearchContext, ResearchFailure, ResearchFilters } from '../components/ResearchShared';

export function Rankings() {
  const [params, setParams] = useSearchParams();
  const state = selection(params);
  const query = useQuery({ queryKey: ['team-rankings', state?.season, state?.stage, state?.category],
    queryFn: ({ signal }) => research.rankings(state!.season, state!.stage, state!.category, signal),
    enabled: !!state, staleTime: 60_000, retry: false, refetchOnWindowFocus: false });
  if (!state) return <Empty title="Rankings selection unavailable"><p>Choose a season, stage and category supported by this workspace.</p><Link className="button" to="/rankings">Reset rankings filters</Link></Empty>;
  const category = query.data?.data.find(item => item.category === state.category);
  const rows = sortedTeams(category?.teams ?? [], state.sort, state.dir);
  const meta = query.data?.meta;
  const sort = (field: Sort) => setParams(paramsFor({ ...state, sort: field,
    dir: state.sort === field ? (state.dir === 'asc' ? 'desc' : 'asc') : ['average','total','games'].includes(field) ? 'desc' : 'asc' }));
  const headers: [Sort, string][] = [['rank','Rank'],['team','Team'],['average','Yards / game'],['total','Total yards'],['games','Games']];
  return <>
    <div className="page-heading"><div><p className="eyebrow">NFL / TEAM RESEARCH</p><h1>Team rankings<span>.</span></h1><p className="subtitle">Four statistical perspectives. One clear sample at a time.</p></div><ResearchFilters state={state}/></div>
    <nav className="category-nav" aria-label="Ranking categories">{Object.entries(categories).map(([key, item], index) => <Link key={key} to={`/rankings?${paramsFor({ ...state, category: key as typeof state.category })}`} aria-current={key === state.category ? 'page' : undefined}><span className="category-number">0{index+1}</span><strong>{item.label}</strong><small>{item.direction}</small></Link>)}</nav>
    <div className="section-heading"><div><p className="eyebrow">{state.season} · {stageLabels[state.stage]}</p><h2>{categories[state.category].label}</h2><p className="subtitle">{categories[state.category].metric} · {categories[state.category].direction}</p></div><button className="button secondary" disabled={query.isFetching} onClick={() => void query.refetch()}>Refresh rankings</button></div>
    {meta && <section className="ranking-coverage" aria-label="Rankings coverage"><div><strong>{category?.eligible_team_count ?? 0}<span> / {meta.league_team_count}</span></strong><p>Teams with contributing games</p></div><div><strong>{meta.accepted_games}<span> / {meta.scheduled_games}</span></strong><p>Accepted / stored schedule games</p></div><div><span className={`status-chip ${meta.coverage_complete_for_stored_schedule ? 'confirmed' : ''}`}>{meta.coverage_complete_for_stored_schedule ? 'Stored schedule covered' : 'Partial or unavailable coverage'}</span><p>{meta.missing_statistics_games} stored schedule games without accepted statistics. Future games may be included.</p></div></section>}
    {query.isError && <ResearchFailure stale={!!query.data} retry={() => void query.refetch()}/>}
    {query.isFetching && !query.isPending && <p role="status" className="coverage-note">Updating rankings…</p>}
    {query.isPending ? <Loading label="Loading team rankings…"/> : query.data && (!rows.length ? <Empty title="No ranking records available"><p>No teams are available in the stored schedule for this selection.</p></Empty> : <>
      <div className="table-toolbar"><p>{category?.eligible_team_count === 0 ? 'No teams have contributing statistics for this category.' : 'Competition ties share rank numbers. Each metric uses its own non-null game count.'}</p>{state.sort !== 'api' && <button className="text-link" onClick={() => setParams(paramsFor({ ...state, sort: 'api', dir: 'asc' }))}>Restore API order</button>}</div>
      <div className="research-table-wrap" role="region" aria-label="Team rankings table" tabIndex={0}><table className="research-table"><caption>{categories[state.category].label} · Display sorting never changes the API rank. A dash means unavailable, not zero.</caption><thead><tr>{headers.map(([field, label]) => <th key={field} scope="col" aria-sort={state.sort === field ? state.dir === 'asc' ? 'ascending' : 'descending' : 'none'}><button onClick={() => sort(field)} aria-label={`Sort by ${label.toLowerCase()}`}>{label} <span aria-hidden="true">{state.sort === field ? state.dir === 'asc' ? '↑' : '↓' : '↕'}</span></button></th>)}<th scope="col">Coverage</th></tr></thead><tbody>{rows.map(row => <tr key={row.team.id}><td><span className={`rank-number ${row.rank !== null && row.rank <= 3 ? 'rank-leader' : ''}`}>{row.rank ?? '—'}</span>{!row.eligible && <small className="unranked-label">Unranked</small>}</td><th scope="row"><Link className="ranking-team" to={researchPath(row.team.id,state)}><span className="team-mark">{row.team.code}</span><span>{row.team.name}<small>View team games ↗</small></span></Link></th><td className="stat-primary">{numeric(row.average,1)}</td><td>{numeric(row.total_yards)}</td><td>{row.games_with_values}<small className="cell-note">contributing</small></td><td>{!row.eligible ? <span className="coverage-pill">No metric sample</span> : row.missing_statistics_games || row.missing_metric_games ? <span className="coverage-pill">Partial sample</span> : <span className="coverage-ok">Stored games covered</span>}<small className="cell-note">{row.missing_statistics_games} missing stats · {row.missing_metric_games} missing metric</small></td></tr>)}</tbody></table></div>
      <p className="coverage-note">Averages are displayed to one decimal; ranks come directly from unrounded API calculations. Zero-game teams are unranked. Coverage does not establish source freshness or verified final results.</p>
    </>)}
    {meta && <details className="policy"><summary>Ranking definitions &amp; data coverage</summary><p>{meta.ranking_semantics}</p><p>{meta.population_semantics}</p><p>{meta.completeness_semantics}</p><p>{meta.unverified_origin_team_games} team-game records have unverified source origin. {meta.unknown_status_accepted_games} accepted games retain UNKNOWN status.</p><p>Research loaded in this browser: {query.dataUpdatedAt ? new Date(query.dataUpdatedAt).toLocaleString() : 'Unavailable'}. This is not the source update time.</p></details>}
    <ResearchContext/>
  </>;
}
