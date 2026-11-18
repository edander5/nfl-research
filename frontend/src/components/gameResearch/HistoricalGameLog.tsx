import { Link } from 'react-router';
import type { GameObservation, ResearchSide } from '../../api/gameResearch';
import { historyDate, outcomeLabel } from './HistoricalGameTrendsChart';

export function HistoricalGameLog({observations,line,side}: {observations:GameObservation[];line:string|null;side:ResearchSide}) {
  return <div className="research-table-wrap game-research-log" role="region" aria-label="Game Total historical log" tabIndex={0}>
    <table className="research-table"><caption>Historical Game Total log · newest first · same games as the chart · dates in UTC</caption>
      <thead><tr>{['Date / week','Opponent','Home / away','Team score','Opponent score','Combined points','Unverified reference total','At custom line','Status / score finality'].map(label=><th scope="col" key={label}>{label}</th>)}</tr></thead>
      <tbody>{observations.map(row=><tr key={row.game_id} data-game-id={row.game_id}>
        <th scope="row"><Link className="text-link" to={`/games/${encodeURIComponent(row.game_id)}`}>{historyDate(row)} · W{row.week}</Link></th>
        <td>{row.opponent.name} ({row.opponent.code})</td><td>{row.side==='HOME'?'Home':'Away'}</td>
        <td>{row.reported_points_scored ?? '—'}</td><td>{row.reported_points_allowed ?? '—'}</td><td>{row.combined_points ?? <span aria-label="Combined points unavailable">—</span>}</td>
        <td>{row.reference_total.line ?? <span aria-label="Reference total unavailable">—</span>}<small className="cell-note">{row.reference_total.line===null ? 'Reference unavailable' : `${row.reference_total.outcome} at source reference; quote time/book unknown`}</small></td>
        <td className={`research-outcome-${outcomeLabel(row.outcome,side).toLowerCase()}`}>{line===null?'Line not entered':`${outcomeLabel(row.outcome,side)} · ${row.outcome} at ${line}`}</td>
        <td>{row.status} · {row.score_finality}</td>
      </tr>)}</tbody>
    </table>
  </div>;
}
