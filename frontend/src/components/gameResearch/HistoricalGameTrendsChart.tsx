import { useId, useState } from 'react';
import type { GameObservation, ResearchSide, TotalOutcome } from '../../api/gameResearch';

export function outcomeLabel(outcome:TotalOutcome,side:ResearchSide):string {
  return outcome==='PUSH' ? 'Push' : outcome==='UNDETERMINED' ? 'Unavailable' : outcome===side ? 'Hit' : 'Miss';
}
export function historyDate(row:GameObservation):string {
  return row.scheduled_kickoff_utc ? new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}).format(new Date(row.scheduled_kickoff_utc)) : 'Date unavailable';
}
export function HistoricalGameTrendsChart({observations,line,side}: {observations:GameObservation[];line:string|null;side:ResearchSide}) {
  const id=useId();
  const [active,setActive]=useState<string|null>(null);
  const games=[...observations].reverse();
  // Geometry only. All plotted values and outcome colors come from the API.
  const width=Math.max(600,games.length*58+70),height=300,left=48,bottom=220;
  const ceiling=Math.max(10,Math.ceil(Math.max(...games.map(row=>row.combined_points ?? 0),Number(line ?? 0))/10)*10);
  const y=(value:number)=>bottom-value/ceiling*185;
  const spacing=(width-left-20)/Math.max(1,games.length);
  const selected=games.find(row=>row.game_id===active);
  return <figure className="historical-chart">
    <figcaption>Combined points by game · oldest first · UTC dates</figcaption>
    <p className="research-chart-legend">Hit · Miss · Push · Unavailable. Bar details are available by keyboard focus or pointer, and in the game log below.</p>
    <div className="historical-chart-scroll" role="region" aria-label="Game Total history chart" tabIndex={0}>
      <svg viewBox={`0 0 ${width} ${height}`} style={{minWidth:Math.max(420,games.length*46)}} aria-labelledby={`${id}-title ${id}-description`} role="group">
        <title id={`${id}-title`}>Historical combined game points</title><desc id={`${id}-description`}>Zero-based points axis. Each game is also listed in the historical log. Dashed markers represent missing scores, not zero.</desc>
        {[0,1,2,3,4].map(tick=>{const value=ceiling*tick/4;return <g key={tick}><line x1={left} x2={width-10} y1={y(value)} y2={y(value)} className="research-grid-line"/><text x={left-8} y={y(value)+4} textAnchor="end">{value}</text></g>;})}
        {line!==null && <g className="research-threshold" aria-label={`Custom threshold ${line}`}><line x1={left} x2={width-10} y1={y(Number(line))} y2={y(Number(line))}/><text x={left+4} y={Math.max(15,y(Number(line))-6)}>Custom line {line}</text></g>}
        {games.map((row,index)=>{
          const label=outcomeLabel(row.outcome,side),x=left+spacing*index+spacing*0.15;
          const details=`${historyDate(row)}, week ${row.week}, ${row.side==='HOME'?'vs':'at'} ${row.opponent.code}: ${row.combined_points===null?'scores unavailable':`${row.combined_points} combined points`}; ${label}${row.outcome==='UNDETERMINED'?'':` (${row.outcome})`}.`;
          return <g key={row.game_id} data-game-id={row.game_id} className={`research-bar research-outcome-${label.toLowerCase()}`} tabIndex={0} role="img" aria-label={details} onFocus={()=>setActive(row.game_id)} onMouseEnter={()=>setActive(row.game_id)}>
            <title>{details}</title><rect x={x} width={spacing*0.7} y={row.combined_points===null?bottom-8:Math.min(bottom-2,y(row.combined_points))} height={row.combined_points===null?8:Math.max(2,bottom-y(row.combined_points))} className={row.combined_points===null?'research-missing-bar':undefined}/>
            <text x={x+spacing*0.35} y={row.combined_points===null?bottom-14:Math.max(14,y(row.combined_points)-6)} textAnchor="middle">{row.combined_points ?? '—'}</text>
            <text x={x+spacing*0.35} y={bottom+18} textAnchor="middle">{row.opponent.code}</text><text x={x+spacing*0.35} y={bottom+34} textAnchor="middle">{row.scheduled_kickoff_utc?.slice(5,10)}</text>
          </g>;
        })}
      </svg>
    </div>
    <p className="research-chart-detail" aria-live="polite">{selected ? `${historyDate(selected)} · W${selected.week} · ${selected.team.code} ${selected.reported_points_scored ?? '—'}–${selected.reported_points_allowed ?? '—'} ${selected.opponent.code} · Total ${selected.combined_points ?? 'unavailable'} · ${outcomeLabel(selected.outcome,side)}. Source-reported scores; ${selected.status} / ${selected.score_finality}.` : 'Focus a game bar to inspect its reported scores and outcome. Zero totals use a small baseline marker.'}</p>
  </figure>;
}
