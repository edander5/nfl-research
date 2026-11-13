import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useLocation, useNavigate } from 'react-router';
import { research } from '../api/research';
import type { TeamGameStats } from '../api/research';
import { markets } from '../api/markets';
import type { MarketSide } from '../api/markets';
import type { Game, Team, SeasonType } from '../api/types';
import { numeric, stageLabels } from '../rankings/state';
import { newestFirst, referenceFor } from '../gameLogs/presentation';
import { Loading, SourceLink } from './shared';

const PAGE_SIZE = 5;
const signed = (value: string) => /^[+-]/.test(value) ? value : `+${value}`;

async function teamLog(id: string, season: number, stage: SeasonType, signal: AbortSignal) {
  const first = await research.games(id, season, stage, 0, signal);
  const rows = [...first.data];
  // Existing API pages are oldest-first. Load all pages before choosing the newest games.
  while (rows.length < first.meta.total_count) {
    const next = await research.games(id, season, stage, rows.length, signal);
    if (next.meta.total_count !== first.meta.total_count || !next.data.length) throw new Error('Game log changed during loading. Retry.');
    rows.push(...next.data);
  }
  if (rows.length !== first.meta.total_count || new Set(rows.map(row => row.game_id)).size !== rows.length ||
      rows.some(row => row.team.id !== id || row.season !== season || row.season_type !== stage)) throw new Error('Inconsistent game log.');
  return newestFirst(rows);
}

function Outcome({ value, total = false }: { value: MarketSide | undefined; total?: boolean }) {
  if (!value || value.line === null) return <span className="log-unavailable" aria-label="Reference line unavailable">—</span>;
  const result = value.result;
  const symbol = result === 'WIN' ? '✓' : result === 'LOSS' ? '✕' : result === 'PUSH' ? 'P' : '?';
  const label = total ? value.side === 'OVER' ? 'Over' : 'Under' : '';
  return <span className={`log-result log-result-${result.toLowerCase()}`} title={`Unverified source reference · Provisional ${label} ${result}`.trim()}>
    <span>{total ? value.line : signed(value.line)}</span><small aria-label={`Provisional ${label ? label + ' ' : ''}${result}`}>{total && result !== 'PUSH' ? label : ''} {symbol}</small>
  </span>;
}

function LogRow({ row, currentId }: { row: TeamGameStats; currentId: string }) {
  const navigate = useNavigate();
  const location = useLocation();
  const query = useQuery({ queryKey: ['game-markets', row.game_id], queryFn: ({ signal }) => markets(row.game_id, signal),
    staleTime: 60_000, retry: false, refetchOnWindowFocus: false });
  const reference = referenceFor(row, query.data);
  const spread = reference?.sides.find(side => side.market === 'SPREAD' && side.side === row.side);
  const totals = reference?.sides.filter(side => side.market === 'TOTAL');
  const total = totals?.find(side => side.result === 'WIN') ?? totals?.find(side => side.result === 'PUSH') ?? totals?.[0];
  const href = row.game_id === currentId ? `${location.pathname}${location.search}` : `/games/${encodeURIComponent(row.game_id)}`;
  const final = row.status === 'FINAL' && row.score_finality === 'CONFIRMED_FINAL';
  return <tr className={row.game_id === currentId ? 'log-current-game' : undefined} onClick={event => {
    if (!(event.target as HTMLElement).closest('a,button')) navigate(href);
  }}>
    <th scope="row"><Link to={href} aria-label={`View week ${row.week}, ${row.team.code} ${row.side === 'AWAY' ? 'at' : 'vs'} ${row.opponent.code}`}>{row.week}</Link></th>
    <td><Link to={href} className="log-opponent">{row.side === 'AWAY' ? '@' : 'vs'} <strong>{row.opponent.code}</strong></Link></td>
    <td><span className="log-score">{numeric(row.reported_points_scored)}–{numeric(row.reported_points_allowed)}</span><small className="log-finality">{final ? 'FINAL · Evidence' : 'UNKNOWN · Unverified'}</small></td>
    <td>{query.isPending ? <span aria-label="Loading reference spread">…</span> : <Outcome value={spread}/>}{query.isError && <button className="log-market-retry" onClick={() => void query.refetch()}>Retry W{row.week} markets</button>}</td><td>{query.isPending ? <span aria-label="Loading reference total">…</span> : <Outcome value={total} total/>}</td>
    <td>{numeric(row.net_passing_yards)}</td><td>{numeric(row.rushing_yards)}</td>
  </tr>;
}

function TeamLogCard({ team, game }: { team: Team; game: Game }) {
  const [page, setPage] = useState(0);
  const query = useQuery({ queryKey: ['preview-team-games', team.id, game.season, game.season_type],
    queryFn: ({ signal }) => teamLog(team.id, game.season, game.season_type, signal),
    staleTime: 60_000, retry: false, refetchOnWindowFocus: false });
  const pages = Math.max(1, Math.ceil((query.data?.length ?? 0) / PAGE_SIZE));
  const activePage = Math.min(page, pages - 1);
  const rows = query.data?.slice(activePage * PAGE_SIZE, (activePage + 1) * PAGE_SIZE) ?? [];
  return <article className="preview-log-card" aria-label={`${team.name} game log`}>
    <header className="preview-log-header"><span className="log-team-badge" role="img" aria-label={`${team.name} abbreviation badge; logo unavailable`}>{team.code}</span><div><p>{game.season} · {stageLabels[game.season_type]}</p><h3>{team.name}</h3><span>TEAM GAME LOG</span></div><span className="log-side-label">{team.id === game.away_team.id ? 'AWAY' : 'HOME'}</span></header>
    {query.isError && <div role="alert" className="log-state"><p>{query.data ? 'Reload failed; showing previous records.' : 'Game logs could not be loaded.'}</p><button className="text-link" onClick={() => void query.refetch()}>Retry {team.code} game logs</button></div>}
    {query.isPending ? <Loading label={`Loading ${team.code} game logs…`}/> : query.data && <>
      {!rows.length ? <p className="log-state">No accepted team statistics for this season and stage.</p> : <div className="preview-log-scroll" role="region" aria-label={`${team.name} game log table`} tabIndex={0}>
        <table className="preview-log-table"><caption className="sr-only">{team.name} · newest dated games first · NET passing and reported scores; betting results are provisional.</caption><thead><tr>{['WK','OPP','SCORE','SPREAD','TOTAL','PASS','RUSH'].map(label => <th scope="col" key={label}>{label}</th>)}</tr></thead><tbody>{rows.map(row => <LogRow key={row.game_id} row={row} currentId={game.id}/>)}</tbody></table>
      </div>}
      <footer className="preview-log-footer"><span>{query.data.length} accepted games · newest first</span>{pages > 1 && <nav aria-label={`${team.code} game log pages`}><button disabled={activePage === 0} onClick={() => setPage(activePage - 1)} aria-label={`Newer ${team.code} games`}>←</button><span>{activePage + 1} / {pages}</span><button disabled={activePage + 1 >= pages} onClick={() => setPage(activePage + 1)} aria-label={`Older ${team.code} games`}>→</button></nav>}</footer>
      {rows.length > 0 && <details className="log-sources"><summary>Sources &amp; coverage</summary><p>Accepted NET passing and rushing statistics. Missing values are not zero. Unknown kickoff times sort after dated games. This season log is not a historical pregame snapshot.</p>{[...new Map(rows.map(row => [row.provenance.artifact_id, row.provenance])).values()].map(source => <p key={source.artifact_id}>{source.attribution ?? 'nflverse / nflfastR'} · {source.origin_status} · <SourceLink url={source.documented_source_url}>Statistics source</SourceLink> · <SourceLink url={source.license_url}>License</SourceLink></p>)}</details>}
    </>}
  </article>;
}

export function PreviewTeamLogs({ game }: { game: Game }) {
  return <section className="preview-team-logs" aria-labelledby="team-logs-title"><div className="section-heading"><div><p className="eyebrow">{game.season} / {stageLabels[game.season_type]}</p><h2 id="team-logs-title">Team Game Logs</h2></div></div>
    <p className="log-policy">Scores are source-reported. Spread and total indicators are provisional backend comparisons of unverified nflverse reference lines, not settled bets or verified pregame lines. Sportsbook/quote time are unknown; open a game for market provenance. ✓ win/cover · ✕ loss · P push · ? undetermined · — unavailable.</p>
    <div className="preview-log-grid">{[game.away_team, game.home_team].map(team => <TeamLogCard key={`${team.id}-${game.season}-${game.season_type}`} team={team} game={game}/>)}</div>
  </section>;
}
