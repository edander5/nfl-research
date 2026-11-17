import { useQuery } from '@tanstack/react-query';
import type { MarketSide } from '../api/markets';
import { markets } from '../api/markets';
import { Empty, Loading, ScoreLabel, SourceLink } from './shared';

const signed = (value: string | null) => value === null ? 'Unavailable' : value.startsWith('-') || value.startsWith('+') ? value : `+${value}`;
function MarketCell({ row, total }: { row: MarketSide | undefined; total?: string }) {
  return <div className="market-cell"><strong>{total && `${total} `}{!row ? 'Unavailable' : row.market === 'MONEYLINE' ? signed(row.price) : row.market === 'SPREAD' ? signed(row.line) : row.line ?? 'Unavailable'}</strong>
    {row?.market !== 'MONEYLINE' && <small>Price {signed(row?.price ?? null)}</small>}</div>;
}
const date = (value: string | null) => value && Number.isFinite(Date.parse(value)) ? new Date(value).toLocaleString() : 'Not recorded';
export function BettingMarkets({ gameId }: { gameId: string }) {
  const query = useQuery({ queryKey: ['game-markets', gameId], queryFn: ({ signal }) => markets(gameId, signal),
    staleTime: 60_000, retry: false, refetchOnWindowFocus: false });
  const game = query.data?.data.game;
  return <section className="betting-markets" aria-labelledby="markets-title">
    <div className="section-heading"><div><p className="eyebrow">SOURCE REFERENCE / NO LIVE OFFERS</p><h2 id="markets-title">Game Betting Markets</h2><p className="subtitle">Unverified nflverse reference lines</p></div></div>
    <div className="comparison-warning"><strong>Current sportsbook offers unavailable</strong><p>Bookmaker and quote time are unknown. These values are not verified opening, closing or historical pregame snapshots. Source freshness is unknown. Calculations are hypothetical and provisional, not settled betting outcomes.</p></div>
    {query.isError && <div role="alert" className="error-panel"><strong>{query.data ? 'Refresh failed. Previously loaded references remain below.' : 'Market references could not be loaded.'}</strong><button className="button secondary" onClick={() => void query.refetch()}>Retry market references</button></div>}
    {query.isPending ? <Loading label="Loading market references…" /> : query.data && game && <>
      {query.data.data.unavailable_reason && <Empty title="Market data unavailable"><p>No usable market reference is available for this game. Missing values are not zero.</p></Empty>}
      {query.data.data.references.map(reference => <div key={reference.snapshot_id} className="market-reference">
        <p><strong>{reference.provider} · Sportsbook unknown</strong><span className="status-chip">Quote freshness UNKNOWN</span></p>
        <div className="sportsbook-scroll" role="region" aria-label="Team market references" tabIndex={0}>
          <table className="sportsbook-table"><caption>Unverified source references · No live sportsbook odds</caption><thead><tr><th scope="col">Team</th><th scope="col">Spread</th><th scope="col">Moneyline</th><th scope="col">Game Total (O/U)</th></tr></thead>
          <tbody>{(['AWAY', 'HOME'] as const).map(side => {
            const team = side === 'AWAY' ? game.away_team : game.home_team;
            const total = side === 'AWAY' ? 'OVER' : 'UNDER';
            return <tr key={side}><th scope="row"><span title={team.name}>{team.code}</span><small>{side === 'AWAY' ? 'Away' : 'Home'}</small></th>
              <td><MarketCell row={reference.sides.find(row => row.market === 'SPREAD' && row.side === side)} /></td>
              <td><MarketCell row={reference.sides.find(row => row.market === 'MONEYLINE' && row.side === side)} /></td>
              <td><MarketCell row={reference.sides.find(row => row.market === 'TOTAL' && row.side === total)} total={total === 'OVER' ? 'Over' : 'Under'} /></td></tr>;
          })}</tbody></table>
        </div>
        <p className="coverage-note">Over and Under apply to the combined game score, not individual teams.</p>
        <details className="market-grading"><summary>Hypothetical grading &amp; source details</summary>
        <p className="coverage-note">Odds last updated: unavailable. Artifact retrieved: {date(reference.artifact_retrieved_at)}. Artifact recorded: {date(reference.artifact_recorded_at)}. These are file observations, not quote times.</p>
        <p className="coverage-note">Reported score used: {game.away_team.code} {game.reported_away_score ?? '—'} · {game.home_team.code} {game.reported_home_score ?? '—'} · Stored status: {game.status}. <ScoreLabel game={game} /></p>
        {game.reported_away_score !== null && game.reported_home_score !== null && <p className="coverage-note">{game.reported_away_score === game.reported_home_score ? 'Reported score is tied; moneyline tie rules are unknown.' : `Reported score leader: ${game.reported_away_score > game.reported_home_score ? game.away_team.code : game.home_team.code}. This does not verify game completion.`}</p>}
        <div className="research-table-wrap" role="region" aria-label="Betting market reference table" tabIndex={0}><table className="research-table markets-table"><caption>Source-reference comparisons only · Never verified wager settlement</caption><thead><tr><th scope="col">Market / side</th><th scope="col">Line</th><th scope="col">Reported price</th><th scope="col">Hypothetical result</th></tr></thead><tbody>{reference.sides.map(row => <tr key={`${row.market}-${row.side}`}><th scope="row">{row.market === 'MONEYLINE' ? 'Moneyline' : row.market === 'SPREAD' ? 'Spread' : 'Game total'} · {row.side === 'AWAY' ? game.away_team.code : row.side === 'HOME' ? game.home_team.code : row.side === 'OVER' ? 'Over' : 'Under'}</th><td>{row.market === 'MONEYLINE' ? '—' : row.market === 'SPREAD' ? signed(row.line) : row.line ?? 'Unavailable'}</td><td>{signed(row.price)}</td><td><strong>{row.result === 'UNDETERMINED' ? 'Undetermined' : `Provisional ${row.result}`}</strong><small className="cell-note">{row.reason === 'moneyline_tie_rules_unknown' ? 'Tie rules unknown' : row.reason === 'scores_unavailable' ? 'Scores unavailable' : row.reason === 'market_value_unavailable' ? 'Market value unavailable' : 'Hypothetical source-reference comparison'}</small></td></tr>)}</tbody></table></div>
        {reference.warnings.length > 0 && <p className="coverage-note">Some source fields failed validation and are unavailable.</p>}
        <p className="coverage-note">Origin: {reference.origin_status}. {reference.attribution ?? 'Attribution not recorded.'} Signed spreads and score comparisons are derived by this application.</p>
        <div className="source-links"><SourceLink url={reference.source_url}>Source</SourceLink><SourceLink url={reference.license_url}>Data license</SourceLink></div>
        <details className="policy"><summary>Reference identity &amp; calculation policy</summary><p>Artifact: {reference.artifact_sha256}</p><p>Source record: {reference.source_record_sha256}</p><p>{query.data!.meta.spread_definition}</p><p>{query.data!.meta.tie_policy}</p><p>{query.data!.meta.price_semantics}</p><p>{query.data!.meta.semantics}</p></details>
        </details>
      </div>)}
      <button className="button secondary" disabled={query.isFetching} onClick={() => void query.refetch()}>{query.isFetching ? 'Checking references…' : 'Reload market references'}</button>
    </>}
  </section>;
}
