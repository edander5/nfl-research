import type { ReactNode } from 'react';
import { Link } from 'react-router';
import type { Game, Policy } from '../api/types';
import { kickoff, safeUrl } from '../api/client';
export function Loading({ label = 'Loading schedule…' }: { label?: string }) { return <div role="status" className="state"><span className="loader" />{label}</div>; }
export function Failure({ retry, stale = false }: { retry: () => void; stale?: boolean }) { return <div role="alert" className="error-panel"><strong>{stale ? 'Refresh failed. Showing previously loaded data.' : 'We couldn’t load this view.'}</strong><p>Check your connection and the schedule service, then try again.</p><button className="button secondary" onClick={retry}>Try again</button></div>; }
export function Empty({ title, children }: { title: string; children?: ReactNode }) { return <div className="state"><span aria-hidden="true" className="empty-symbol">⊞</span><h2>{title}</h2>{children}</div>; }
export function PolicyNotice({ policy }: { policy: Policy }) { return <details className="policy"><summary>About these records &amp; source coverage</summary><p>{policy.score_semantics}</p><p>{policy.coverage_semantics}</p><ul>{policy.limitations.map(text => <li key={text}>{text}</li>)}</ul></details>; }
export function Finality({ game }: { game: Game }) {
  const final = game.status === 'FINAL' && game.score_finality === 'CONFIRMED_FINAL' && !!game.final_evidence;
  return <span className={`status-chip ${final ? 'confirmed' : ''}`}>{final ? 'FINAL · Evidence recorded' : 'UNKNOWN · Finality unverified'}</span>;
}
export function ScoreLabel({ game }: { game: Game }) {
  return <span className="score-note">{game.reported_home_score === null && game.reported_away_score === null ? 'Scores not reported' : game.status === 'FINAL' && game.score_finality === 'CONFIRMED_FINAL' && game.final_evidence ? 'Confirmed final scores' : 'Reported scores · Finality unverified'}</span>;
}
export function GameCard({ game, returnTo }: { game: Game; returnTo: string }) {
  return <Link className="game-card" to={`/games/${game.id}?returnTo=${encodeURIComponent(returnTo)}`} aria-label={`${game.away_team.name} at ${game.home_team.name}, view matchup`}>
    <div className="game-meta"><span>{kickoff(game.scheduled_kickoff_utc)}</span><span aria-hidden="true">↗</span></div>
    <div className="team-row"><span className="team-mark">{game.away_team.code}</span><div className="team-label"><strong>{game.away_team.name}</strong><small>Away</small></div><span className="score">{game.reported_away_score ?? '—'}</span></div>
    <div className="team-row"><span className="team-mark home">{game.home_team.code}</span><div className="team-label"><strong>{game.home_team.name}</strong><small>Home</small></div><span className="score">{game.reported_home_score ?? '—'}</span></div>
    <div className="game-footer"><Finality game={game} /><ScoreLabel game={game} /></div>
  </Link>;
}
export function SourceLink({ url, children }: { url: string | null; children: ReactNode }) { const href = safeUrl(url); return href ? <a className="text-link" href={href} target="_blank" rel="noreferrer">{children} ↗</a> : <span>{children}: unavailable</span>; }
