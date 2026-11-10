import type { FreshnessResponse } from './types';

export function validRecordedTime(value: unknown): value is string {
  return typeof value === 'string' && /T.*(?:Z|[+-]\d{2}:\d{2})$/i.test(value) && Number.isFinite(new Date(value).getTime());
}

export function parseFreshness(value: unknown): FreshnessResponse {
  const object = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v);
  if (object(value) && object(value.data) && object(value.meta)) {
    const { data, meta } = value;
    const timestamps = ['last_attempt_at', 'last_successful_check_at', 'last_successful_apply_at', 'last_data_change_observed_at'];
    const outcomes = ['dry_run','applied','unchanged','rejected','review_required','download_failed','validation_failed','failed','not_applied'];
    if (['available','missing','incomplete','invalid','unreadable'].includes(String(data.metadata_state)) &&
        (data.latest_outcome === null || outcomes.includes(String(data.latest_outcome))) &&
        timestamps.every(k => data[k] === null || validRecordedTime(data[k])) &&
        (data.is_stale === null || typeof data.is_stale === 'boolean') &&
        (data.check_age_seconds === null || typeof data.check_age_seconds === 'number' && Number.isInteger(data.check_age_seconds) && data.check_age_seconds >= 0) &&
        meta.manual === true && meta.scope === 'guarded_manual_refresh_runner' && validRecordedTime(meta.as_of) &&
        typeof meta.stale_after_seconds === 'number' && meta.stale_after_seconds > 0 &&
        typeof meta.apply_semantics === 'string' && typeof meta.timestamp_semantics === 'string') {
      return value as unknown as FreshnessResponse;
    }
  }
  throw new Error('Unexpected refresh history response.');
}

export function formatFreshnessTimestamp(value: string | null, options: { locale?: string; timeZone?: string } = {}): string {
  if (value === null) return 'Not recorded';
  if (!validRecordedTime(value)) return 'Unavailable';
  return new Intl.DateTimeFormat(options.locale, {
    ...(options.timeZone ? { timeZone: options.timeZone } : {}),
    year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short',
  }).format(new Date(value));
}
