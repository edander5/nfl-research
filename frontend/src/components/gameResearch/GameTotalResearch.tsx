import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { gameResearch } from '../../api/gameResearch';
import type { GameResearchResponse, ResearchSide, ResearchWindow } from '../../api/gameResearch';
import type { Game } from '../../api/types';
import { numeric, stageLabels } from '../../rankings/state';
import { Loading, SourceLink } from '../shared';
import { BettingLineControl, RecentGamesSelector, researchWindows } from './ResearchControls';
import { HistoricalGameTrendsChart } from './HistoricalGameTrendsChart';
import { HistoricalGameLog } from './HistoricalGameLog';

export function HitRateSummary({response}: {response:GameResearchResponse}) {
  const {data,meta}=response,summary=data.summary;
  const hits=data.side==='OVER'?summary.over_count:summary.under_count;
  const misses=data.side==='OVER'?summary.under_count:summary.over_count;
  return <div className="game-research-summary" aria-label="Game Total summary">
    <div><span>{data.side==='OVER'?'Over':'Under'} {data.line ?? '— (line not entered)'}</span><strong>{summary.hit_rate===null?'Hit rate unavailable':new Intl.NumberFormat('en-US',{style:'percent',maximumFractionDigits:1}).format(summary.hit_rate)}</strong><small>Historical frequency, not a predicted probability.</small></div>
    <div><span>Hits / misses / pushes</span><strong>{hits ?? '—'} / {misses ?? '—'} / {summary.push_count ?? '—'}</strong><small>Denominator: {summary.hit_rate_denominator ?? 'unavailable'} usable scored games, including pushes.</small></div>
    <div><span>Average combined points</span><strong>{numeric(summary.average_combined_points,1)}</strong><small>{summary.games_with_usable_scores} scored of {summary.eligible_game_count} selected games · {summary.games_without_usable_scores} scores unavailable</small></div>
    <p className="coverage-note">{researchWindows[data.window]} ({summary.eligible_game_count} available){data.requested_game_count!==null?` / ${data.requested_game_count} requested`:''}. {(!meta.window_complete||!meta.scores_complete||!meta.references_complete)&&'Partial coverage. '}{meta.games_without_reference_total} reference totals unavailable · {meta.excluded_unknown_kickoff_games} accepted games excluded for unknown kickoff.</p>
  </div>;
}

export function GameTotalResearch({game}: {game:Game}) {
  const [teamId,setTeamId]=useState(game.away_team.id);
  const [window,setWindow]=useState<ResearchWindow>('L5');
  const [line,setLine]=useState<string|null>(null);
  const [side,setSide]=useState<ResearchSide>('OVER');
  const team=teamId===game.away_team.id?game.away_team:game.home_team;
  const opponent=team.id===game.away_team.id?game.home_team:game.away_team;
  const query=useQuery({queryKey:['game-total-research',game.id,team.id,game.season,game.season_type,window,line,side],
    queryFn:({signal})=>gameResearch(team,game,window,line,side,signal),retry:false,staleTime:60_000,refetchOnWindowFocus:false});
  const response=query.data;
  return <section className="game-total-research" aria-labelledby="game-total-research-title">
    <div className="section-heading"><div><p className="eyebrow">{game.season} / {stageLabels[game.season_type]} / FULL GAME</p><h2 id="game-total-research-title">Game Total Research</h2><p className="subtitle">{team.name} history · current opponent: {opponent.name}</p></div></div>
    <p className="coverage-note">Current accepted, source-reported scores; UNKNOWN and unverified finality remain explicit. Matchup chronology is not an independently verified pregame snapshot. Reference totals are not verified closing odds or live offers.</p>
    <div className="game-research-controls">
      <div className="season-control"><label htmlFor="game-research-team">Analyze team history</label><select id="game-research-team" value={team.id} onChange={event=>setTeamId(event.target.value)}>{[game.away_team,game.home_team].map(item=><option key={item.id} value={item.id}>{item.name} ({item.code})</option>)}</select></div>
      <RecentGamesSelector value={window} onChange={setWindow}/>
      <div className="season-control"><label htmlFor="game-research-side">Research side</label><select id="game-research-side" value={side} onChange={event=>setSide(event.target.value as ResearchSide)}><option value="OVER">Over</option><option value="UNDER">Under</option></select></div>
      <BettingLineControl line={line} onChange={setLine}/>
    </div>
    {query.isError&&<div role="alert" className="error-panel"><strong>{response?'Reload failed; showing previously loaded results for these controls.':'Game Total research could not be loaded.'}</strong><button className="button secondary" onClick={()=>void query.refetch()}>Retry Game Total research</button></div>}
    {query.isPending?<Loading label="Loading Game Total research…"/>:response&&<>
      <HitRateSummary response={response}/>
      {response.data.line===null&&<p className="coverage-note">Enter and apply a custom line to see hit rates and hit/miss outcomes.</p>}
      {response.data.availability==='UNAVAILABLE'?<p role="status">Research unavailable: {response.meta.unavailable_reason==='matchup_kickoff_unknown'?'matchup kickoff is unknown; chronology cannot be established.':'opponent identity is unavailable.'}</p>:
        response.data.observations.length===0?<p role="status">{window==='H2H'?'No eligible head-to-head games against this opponent in the selected season and stage.':'No eligible historical games before this matchup in the selected season and stage.'}</p>:<>
          <HistoricalGameTrendsChart key={`${team.id}-${window}-${line}-${side}`} observations={response.data.observations} line={response.data.line} side={response.data.side}/>
          <HistoricalGameLog observations={response.data.observations} line={response.data.line} side={response.data.side}/>
        </>}
      <button className="button secondary" disabled={query.isFetching} onClick={()=>void query.refetch()}>{query.isFetching?'Refreshing Game Total research…':'Refresh Game Total research'}</button>
      <details className="policy"><summary>Game Total eligibility &amp; provenance</summary><p>Cutoff (UTC): {response.meta.cutoff_utc ?? 'Unavailable'}. Same season and {stageLabels[game.season_type]} only.</p><p>{response.meta.selection_semantics}</p><p>{response.meta.threshold_semantics}</p><p>{response.meta.reference_semantics}</p>
        {response.data.observations.map(row=><div key={row.game_id}><strong>W{row.week} · {row.opponent.code}</strong><p>Accepted pair {row.accepted_pair_id} · generation {row.selection_generation} · {row.provenance.attribution ?? 'Attribution unavailable'}</p><SourceLink url={row.provenance.documented_source_url}>Statistics source</SourceLink>{row.reference_total.provenance&&<p>Reference artifact {row.reference_total.provenance.artifact_id} · recorded {row.reference_total.provenance.artifact_recorded_at}; not a quote timestamp.</p>}</div>)}
      </details>
    </>}
  </section>;
}
