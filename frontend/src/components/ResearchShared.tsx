import type { Selection } from '../rankings/state';
import { paramsFor, stageLabels } from '../rankings/state';
import { useSearchParams } from 'react-router';
export function ResearchFilters({ state }: { state: Selection }) {
  const [, setParams] = useSearchParams();
  const move = (changes: Partial<Selection>) => setParams(paramsFor({ ...state, ...changes }));
  return <div className="research-filters"><div className="season-control"><label htmlFor="research-season">Season</label><select id="research-season" value={state.season} onChange={e => move({ season: Number(e.target.value) })}>{[2026,2025,2024].map(year => <option key={year} value={year}>{year} season</option>)}</select></div><div className="season-control"><label htmlFor="research-stage">Season stage</label><select id="research-stage" value={state.stage} onChange={e => move({ stage: e.target.value as Selection['stage'] })}>{Object.entries(stageLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div></div>;
}
export function ResearchFailure({ retry, stale = false }: { retry: () => void; stale?: boolean }) {
  return <div role="alert" className="error-panel"><strong>{stale ? 'Refresh failed. Previously loaded research remains below.' : 'Team research could not be loaded.'}</strong><p>Check the research service and your connection, then try again.</p><button className="button secondary" onClick={retry}>Try again</button></div>;
}
export function ResearchContext() {
  return <div className="research-context"><strong>Reconstructed season statistics</strong><p>These are current accepted records, not verified historical pregame rankings. Statistics and reported scores do not establish game completion; UNKNOWN statuses remain unknown.</p><p>Data via <a className="text-link" href="https://github.com/nflverse/nflverse-data" target="_blank" rel="noreferrer">nflverse / nflfastR</a> · <a className="text-link" href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">CC BY 4.0</a>. NET passing includes the original signed sack adjustment. Source origin is declared; independent authentication and the original schedule checksum discrepancy remain unresolved.</p></div>;
}
