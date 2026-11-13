import { useQuery } from '@tanstack/react-query';
import { Link, useParams, useSearchParams } from 'react-router';
import { api, ApiError, kickoff, roundLabels, schedulePath } from '../api/client';
import type { Round } from '../api/types';
import { Empty, Failure, Finality, Loading, PolicyNotice, ScoreLabel, SourceLink } from '../components/shared';
import { Card, CardContent } from '../components/ui/card';
import { PreviewTeamLogs } from '../components/PreviewTeamLogs';
import { BettingMarkets } from '../components/BettingMarkets';
import { MatchupComparison } from '../components/MatchupComparison';
export function Matchup() {
  const { gameId = '' } = useParams();
  const [params] = useSearchParams();
  const valid = /^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$/i.test(gameId);
  const query = useQuery({ queryKey: ['game',gameId], queryFn: ({ signal }) => api.game(gameId,signal), enabled: valid });
  if (!valid || query.error instanceof ApiError && query.error.status === 404) return <Empty title="Matchup not found"><p>Use a game link from the weekly schedule.</p><Link className="button" to="/">Browse schedule</Link></Empty>;
  if (query.isPending) return <Loading label="Loading matchup…" />;
  if (!query.data) return <><Link className="back-link" to="/">← Schedule</Link><Failure retry={() => void query.refetch()} /></>;
  const game = query.data.data;
  const fallback = schedulePath(game.season,game.season_type,game.season_type === 'REG' ? String(game.week) : game.game_type);
  const requested = params.get('returnTo') ?? '';
  const back = /^\/schedule\/202[456]\/(REG\/(?:[1-9]|1[0-8])|POST\/(?:WC|DIV|CON|SB|all))$/.test(requested) ? requested : fallback;
  return <><Link className="back-link" to={back}>← Back to schedule</Link><div className="page-heading"><div><p className="eyebrow">{game.season} / {game.season_type === 'REG' ? `REGULAR SEASON · WEEK ${game.week}` : roundLabels[game.game_type as Round]}</p><h1>Game preview<span>.</span></h1><p className="subtitle">{kickoff(game.scheduled_kickoff_utc)}</p></div><Finality game={game} /></div>
  {query.isError && <Failure stale retry={() => void query.refetch()} />}
  <Card className="matchup-hero"><CardContent><div className="matchup-teams"><div><span className="large-team-mark">{game.away_team.code}</span><p>Away</p><h2>{game.away_team.name}</h2><strong className="hero-score">{game.reported_away_score ?? '—'}</strong></div><div className="versus">AT</div><div><span className="large-team-mark home">{game.home_team.code}</span><p>Home</p><h2>{game.home_team.name}</h2><strong className="hero-score">{game.reported_home_score ?? '—'}</strong></div></div><ScoreLabel game={game} /></CardContent></Card>
  <MatchupComparison key={game.id} game={game} />
  <BettingMarkets key={`markets-${game.id}`} gameId={game.id} />
  <PreviewTeamLogs key={`logs-${game.id}`} game={game} />
  <div className="detail-grid"><Card><CardContent><h2 className="detail-title">Game information</h2><dl><dt>Game status</dt><dd>{game.status}</dd><dt>Kickoff</dt><dd>{kickoff(game.scheduled_kickoff_utc)}</dd><dt>UTC kickoff</dt><dd>{game.scheduled_kickoff_utc ?? 'Not available'}</dd><dt>Venue designation</dt><dd>{game.neutral_site === null ? 'Not available' : game.neutral_site ? 'Neutral site' : 'Home site'}</dd><dt>Overtime reported</dt><dd>{game.overtime === null ? 'Not available' : game.overtime ? 'Yes' : 'No'}</dd></dl>{game.status === 'FINAL' && game.final_evidence && <SourceLink url={game.final_evidence.url}>Stored final evidence</SourceLink>}</CardContent></Card>
  <Card><CardContent><h2 className="detail-title">Source &amp; provenance</h2><dl><dt>Provider</dt><dd>{game.provenance.provider}</dd><dt>Source origin</dt><dd>{game.provenance.origin_status === 'VERIFIED' ? 'Verified origin recorded' : 'Declared · Not independently authenticated'}</dd><dt>Retrieved</dt><dd>{game.provenance.retrieved_at ?? 'Not recorded'}</dd><dt>Database artifact observation (UTC)</dt><dd>{game.provenance.recorded_at}</dd><dt>Source game ID</dt><dd>{game.provenance.source_game_id}</dd></dl><div className="source-links"><SourceLink url={game.provenance.documented_source_url}>Documented source</SourceLink><SourceLink url={game.provenance.license_url}>Data license</SourceLink></div><p className="coverage-note">{game.provenance.attribution ?? 'Attribution not recorded.'}</p><details className="hash-details"><summary>Artifact SHA-256</summary><code>{game.provenance.artifact_sha256}</code></details></CardContent></Card></div>
  <PolicyNotice policy={query.data.meta} /></>;
}
