import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useParams, useSearchParams } from 'react-router';
import { research } from '../api/research';
import type { SeasonType } from '../api/types';
import { kickoff } from '../api/client';
import { numeric, rankingsPath, selection, stageLabels } from '../rankings/state';
import type { Selection } from '../rankings/state';
import { Empty, Loading, SourceLink } from '../components/shared';
import { ResearchContext, ResearchFailure, ResearchFilters } from '../components/ResearchShared';

function TeamGames({ id, state, stage }: { id: string; state: Selection; stage: SeasonType }) {
  const [offset, setOffset] = useState(0);
  const query = useQuery({ queryKey: ['team-research-games', id, state.season, stage, offset],
    queryFn: ({ signal }) => research.games(id, state.season, stage, offset, signal), staleTime: 60_000,
    retry: false, refetchOnWindowFocus: false });
  return <section aria-label={`${stageLabels[stage]} team games`} className="team-research-section">
    <div className="section-heading"><div><p className="eyebrow">{state.season} · {stageLabels[stage]}</p><h2>{query.data?.data[0]?.team.name ?? 'Team'} game log</h2></div><button className="button secondary" disabled={query.isFetching} onClick={() => void query.refetch()}>Refresh {stage === 'REG' ? 'regular season' : 'postseason'}</button></div>
    {query.isError && <ResearchFailure stale={!!query.data} retry={() => void query.refetch()}/>}
    {query.isPending ? <Loading label={`Loading ${stageLabels[stage].toLowerCase()} team games…`}/> : query.data && <>
      <p className="coverage-note">{query.data.meta.total_count} games with accepted statistics. Missing games are not zero-performance games. Scores below are source-reported; finality is shown separately.</p>
      {!query.data.data.length ? <Empty title="No accepted team statistics"><p>No accepted records are available for this season, stage and page.</p></Empty> : <div className="research-table-wrap" role="region" aria-label={`${stageLabels[stage]} game log table`} tabIndex={0}><table className="research-table team-log-table"><caption>Accepted {stageLabels[stage].toLowerCase()} team games · yards and reported scores</caption><thead><tr><th scope="col">Game</th><th scope="col">NET pass</th><th scope="col">Rush</th><th scope="col">Pass allowed</th><th scope="col">Rush allowed</th><th scope="col">Reported score</th></tr></thead><tbody>{query.data.data.map(game => <tr key={game.game_id}><th scope="row"><strong>W{game.week} · {game.side === 'HOME' ? 'vs' : 'at'} {game.opponent.code}</strong><small className="cell-note">{kickoff(game.scheduled_kickoff_utc)}</small><small className="cell-note">{game.status === 'FINAL' && game.score_finality === 'CONFIRMED_FINAL' ? 'FINAL · Evidence recorded' : 'UNKNOWN · Finality unverified'}</small></th><td>{numeric(game.net_passing_yards)}<small className="cell-note">Gross {numeric(game.gross_passing_yards)} · Sacks {numeric(game.original_sack_yards)}</small></td><td>{numeric(game.rushing_yards)}</td><td>{numeric(game.net_passing_yards_allowed)}</td><td>{numeric(game.rushing_yards_allowed)}</td><td>{numeric(game.reported_points_scored)} – {numeric(game.reported_points_allowed)}<small className="cell-note">Team – opponent</small></td></tr>)}</tbody></table></div>}
      {query.data.meta.total_count > 20 && <nav className="research-pagination" aria-label={`${stageLabels[stage]} game log pages`}><button className="button secondary" disabled={offset === 0 || query.isFetching} onClick={() => setOffset(Math.max(0,offset-20))}>Previous</button><span>{offset+1}–{offset+query.data.meta.returned_count} of {query.data.meta.total_count}</span><button className="button secondary" disabled={offset+20 >= query.data.meta.total_count || query.isFetching} onClick={() => setOffset(offset+20)}>Next</button></nav>}
      {!!query.data.data.length && <details className="policy"><summary>Game-log source references</summary><ul>{[...new Map(query.data.data.map(game => [game.provenance.artifact_id,game.provenance])).values()].map(source => <li key={source.artifact_id}>{source.attribution ?? 'nflverse / nflfastR'} · {source.origin_status} · <SourceLink url={source.documented_source_url}>Source artifact</SourceLink> · <SourceLink url={source.license_url}>License</SourceLink></li>)}</ul></details>}
    </>}
  </section>;
}
export function TeamResearch() {
  const { teamId } = useParams();
  const [params] = useSearchParams();
  const state = selection(params);
  const valid = !!teamId && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(teamId);
  if (!state || !valid) return <Empty title="Team research selection unavailable"><Link className="button" to="/rankings">Browse team rankings</Link></Empty>;
  const stages: SeasonType[] = state.stage === 'COMBINED' ? ['REG','POST'] : [state.stage];
  return <>
    <Link className="back-link" to={rankingsPath(state)}>← Back to team rankings</Link>
    <div className="page-heading"><div><p className="eyebrow">NFL / TEAM RESEARCH</p><h1>Team game logs<span>.</span></h1><p className="subtitle">The accepted records behind the season averages.</p></div><ResearchFilters state={state}/></div>
    {state.stage === 'COMBINED' && <p className="coverage-note">Combined selection: REG and POST records are shown separately to preserve stage context.</p>}
    {stages.map(stage => <TeamGames key={`${teamId}-${state.season}-${stage}`} id={teamId!} state={state} stage={stage}/>)}
    <ResearchContext/>
  </>;
}
