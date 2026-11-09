import { useQueries } from '@tanstack/react-query';
import { useState } from 'react';
import { Navigate } from 'react-router';
import { api, schedulePath } from '../api/client';
import type { SeasonCoverage } from '../api/types';
import { Empty, Failure, Loading } from '../components/shared';
import { defaultSelection } from '../schedule/defaultSelection';

export function ScheduleDefault({ seasons }: { seasons: SeasonCoverage[] }) {
  // Pick once on home entry; do not move a user's explicit URL at midnight/refetch.
  const [now] = useState(() => new Date(Date.now()));
  const stages = seasons.flatMap(year => year.coverage.filter(c => c.game_count > 0)
    .map(c => ({ season: year.season, stage: c.season_type })));
  const calendars = useQueries({ queries: stages.map(({ season, stage }) => ({
    queryKey: ['schedule', season, stage, 'all'],
    queryFn: ({ signal }: { signal: AbortSignal }) => api.schedule(season, stage, 'all', signal),
  })) });
  if (calendars.some(query => query.isError && !query.data)) {
    return <Failure retry={() => { void Promise.all(calendars.filter(q => q.isError).map(q => q.refetch())); }} />;
  }
  if (calendars.some(query => query.isPending)) return <Loading label="Finding the current schedule week…" />;
  const selection = defaultSelection(calendars.flatMap(query => query.data?.data ?? []), seasons, now);
  if (!selection) return <Empty title="No schedule dates available"><p>No selectable weeks or postseason rounds are available.</p></Empty>;
  const notice = selection.reason === 'undated'
    ? 'Schedule dates are unavailable. Showing the first available selection in the newest available season.'
    : calendars.some(query => query.isError) ? 'Some schedule dates could not be refreshed. The default uses previously loaded records.' : null;
  return <Navigate replace to={schedulePath(selection.season, selection.stage, selection.selection)} state={{ defaultNotice: notice }} />;
}
