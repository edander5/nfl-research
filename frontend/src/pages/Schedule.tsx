import { useQuery } from '@tanstack/react-query';
import { Link, Navigate, useLocation, useNavigate, useParams } from 'react-router';
import { api, roundLabels, schedulePath, validSelection } from '../api/client';
import type { Round, SeasonType } from '../api/types';
import { Card, CardContent } from '../components/ui/card';
import { Empty, Failure, GameCard, Loading, PolicyNotice } from '../components/shared';

export function Schedule() {
  const { season, stage, selection } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const seasons = useQuery({ queryKey: ['seasons'], queryFn: ({ signal }) => api.seasons(signal) });
  const year = Number(season);
  const valid = /^202[456]$/.test(season ?? '') && validSelection(stage, selection);
  const available = seasons.data?.data.find(item => item.season === year);
  const games = useQuery({ queryKey: ['schedule', year, stage, selection], queryFn: ({ signal }) => api.schedule(year, stage as SeasonType, selection!, signal), enabled: valid && !!available });
  if (seasons.isPending) return <Loading label="Loading available seasons…" />;
  if (!seasons.data) return <Failure retry={() => void seasons.refetch()} />;
  if (!seasons.data.data.length) return <Empty title="No seasons available"><p>No NFL schedule records are currently available from the service.</p><button className="button secondary" onClick={() => void seasons.refetch()}>Refresh seasons</button></Empty>;
  if (!season) {
    const latest = [...seasons.data.data].sort((a,b) => b.season-a.season)[0];
    return <Navigate replace to={schedulePath(latest.season, 'REG', '1')} />;
  }
  if (!valid || !available) return <Empty title="Schedule selection unavailable"><p>Choose an available season and valid week or round.</p><Link className="button" to="/">Browse schedule</Link></Empty>;
  const coverage = games.data?.meta.season_coverage ?? available.coverage;
  const current = coverage.find(c => c.season_type === stage);
  const post = available.coverage.find(c => c.season_type === 'POST');
  const rounds = post?.rounds ?? [];
  const title = stage === 'REG' ? `Week ${selection}` : selection === 'all' ? 'Postseason' : roundLabels[selection as Round];
  const move = (newYear: number, newStage: SeasonType) => {
    const postCoverage = seasons.data.data.find(y => y.season === newYear)?.coverage.find(c => c.season_type === 'POST');
    navigate(schedulePath(newYear, newStage, newStage === 'REG' ? (stage === 'REG' ? selection! : '1') : postCoverage?.rounds[0] ?? 'all'));
  };
  return <>
    <div className="page-heading"><div><p className="eyebrow">NFL / SCHEDULE EXPLORER</p><h1>League schedule<span>.</span></h1><p className="subtitle">Follow the matchups. Keep the context.</p></div><div className="season-control"><label htmlFor="season">Season</label><select id="season" value={year} onChange={e => move(Number(e.target.value), 'REG')}>{[...seasons.data.data].sort((a,b) => b.season-a.season).map(y => <option key={y.season} value={y.season}>{y.season} season</option>)}</select></div></div>
    {seasons.isError && <Failure stale retry={() => void seasons.refetch()} />}
    <div className="summary-grid"><Card><CardContent><span className="metric-label">Season games</span><strong className="metric">{coverage.reduce((sum,c) => sum+c.game_count,0)}</strong><span className="metric-note">Imported matchup records</span></CardContent></Card><Card><CardContent><span className="metric-label">{stage === 'REG' ? 'Regular season' : 'Postseason'}</span><strong className="metric">{current?.game_count ?? '—'}</strong><span className="metric-note">{current?.reported_score_pairs ?? '—'} with reported scores</span></CardContent></Card><Card className="context-card"><CardContent><span className="metric-label">Know what you’re seeing</span><strong>Reported ≠ confirmed final</strong><p>Scores may be present while game status remains UNKNOWN.</p></CardContent></Card></div>
    <section className="schedule-section" aria-label="Weekly schedule"><div className="stage-bar"><div className="stage-tabs" aria-label="Season stage"><button aria-pressed={stage === 'REG'} onClick={() => move(year,'REG')}>Regular season</button><button aria-pressed={stage === 'POST'} disabled={!post?.game_count && stage !== 'POST'} onClick={() => move(year,'POST')}>Postseason{!post?.game_count && <span> · No matchups</span>}</button></div><span className="timezone-note">Kickoffs in Eastern Time</span></div>
    {!post?.game_count && <p className="coverage-note">No postseason matchups are available for {year}. Coverage reflects imported records.</p>}
    <nav className="week-nav" aria-label={stage === 'REG' ? 'Regular-season weeks' : 'Postseason rounds'}>{stage === 'REG' ? Array.from({length:18},(_,i) => String(i+1)).map(week => <Link key={week} aria-current={selection === week ? 'page' : undefined} to={schedulePath(year,'REG',week)}>W{week}</Link>) : rounds.map(round => <Link key={round} aria-current={selection === round ? 'page' : undefined} to={schedulePath(year,'POST',round)}>{roundLabels[round]}</Link>)}</nav>
    <div className="section-heading"><div><p className="eyebrow">{year} {stage === 'REG' ? 'REGULAR SEASON' : 'POSTSEASON'}</p><h2>{title}</h2></div><div className="results-count">{games.data ? `${games.data.meta.returned_count} matchups` : '—'}<button className="refresh" disabled={games.isFetching} onClick={() => void games.refetch()} aria-label="Refresh schedule">↻</button></div></div>
    {games.isFetching && !games.isPending && <p role="status" className="coverage-note">Refreshing schedule…</p>}
    {games.isError && <Failure stale={!!games.data} retry={() => void games.refetch()} />}
    {games.isPending ? <Loading /> : games.data && (games.data.data.length ? <div className="games-grid">{games.data.data.map(game => <GameCard key={game.id} game={game} returnTo={location.pathname} />)}</div> : <Empty title="No matchups available"><p>{stage === 'POST' ? 'No records have been imported for this postseason selection.' : 'There are no imported games for this week.'}</p></Empty>)}
    {games.data && <PolicyNotice policy={games.data.meta} />}</section>
  </>;
}
