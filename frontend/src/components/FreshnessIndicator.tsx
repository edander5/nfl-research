import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { formatFreshnessTimestamp } from '../api/freshness';
import type { RefreshOutcome } from '../api/types';

const outcomes: Record<RefreshOutcome, string> = {
  applied: 'Applied changes', unchanged: 'Successful apply — no changes', dry_run: 'Dry-run check — nothing applied',
  rejected: 'Candidate rejected', review_required: 'Operator review required', download_failed: 'Download failed',
  validation_failed: 'Validation failed', failed: 'Refresh failed', not_applied: 'Recovery confirmed no apply',
};
const failureOutcomes: RefreshOutcome[] = ['download_failed', 'validation_failed', 'failed'];
const unavailable = {
  missing: 'No recorded refresh metadata is available.',
  incomplete: 'Refresh metadata is incomplete; some observations are unknown.',
  invalid: 'Refresh metadata could not be validated.',
  unreadable: 'Recorded refresh metadata could not be read.',
};

function RecordedTime({ value }: { value: string | null }) {
  return value ? <time dateTime={value}>{formatFreshnessTimestamp(value)}</time> : <>Not recorded</>;
}

export function FreshnessIndicator() {
  const history = useQuery({
    queryKey: ['schedule-freshness'], queryFn: ({ signal }) => api.freshness(signal),
    staleTime: Infinity, retry: false, refetchOnWindowFocus: false, refetchOnReconnect: false,
    refetchOnMount: false, refetchInterval: false,
  });
  const response = history.data;
  const data = response?.data;
  return <section className="freshness-panel" aria-label="Schedule data freshness" aria-busy={history.isFetching}>
    <div className="freshness-heading"><h2>Schedule refresh history</h2><span className="status-chip">Manual · Not a live feed</span></div>
    <div aria-live="polite" className="freshness-message">
      {history.isPending ? <p>Loading refresh history…</p> : history.isError ?
        <p>{response ? 'History reload failed; showing previously loaded metadata.' : 'Refresh history is unavailable. Schedule records can still be viewed.'}</p> :
        data && <>
          {data.metadata_state !== 'available' && <p>{unavailable[data.metadata_state]}</p>}
          <p>Latest recorded outcome: <strong>{data.latest_outcome ? outcomes[data.latest_outcome] : 'Not recorded'}</strong></p>
          {data.latest_outcome && failureOutcomes.includes(data.latest_outcome) && <p>The latest recorded attempt failed. Earlier successful observations remain below.</p>}
          {data.is_stale === true && <p>Last successful check is older than {response!.meta.stale_after_seconds / 3600} hours.</p>}
          {data.metadata_state === 'available' && data.last_successful_check_at === null && <p>No successful check is recorded.</p>}
        </>}
    </div>
    {data && <dl className="freshness-times">
      <div><dt>Last recorded attempt</dt><dd><RecordedTime value={data.last_attempt_at} /></dd></div>
      <div><dt>Last successful check</dt><dd><RecordedTime value={data.last_successful_check_at} /></dd></div>
      <div><dt>Last successful apply (may be unchanged)</dt><dd><RecordedTime value={data.last_successful_apply_at} /></dd></div>
      <div><dt>Last observed data change</dt><dd><RecordedTime value={data.last_data_change_observed_at} /></dd></div>
    </dl>}
    <p className="freshness-explanation">A successful check or apply may change no records. Refresh times are not game completion or source publication times; game status may remain UNKNOWN.</p>
    <div className="freshness-actions"><span>Times use your local timezone; kickoffs remain Eastern.{response && <> Metadata read: <RecordedTime value={response.meta.as_of} />.</>}</span><button type="button" className="button secondary" disabled={history.isFetching} onClick={() => void history.refetch()}>Reload refresh history</button></div>
  </section>;
}
