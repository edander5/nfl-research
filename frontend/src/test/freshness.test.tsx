import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';

import { App } from '../App';
import { api } from '../api/client';
import { formatFreshnessTimestamp, parseFreshness } from '../api/freshness';
import type { FreshnessResponse } from '../api/types';
import { FreshnessIndicator } from '../components/FreshnessIndicator';
import { freshness, schedule, seasons } from './fixtures';

const available: FreshnessResponse = {
  ...freshness,
  data: { ...freshness.data, metadata_state:'available',latest_outcome:'unchanged',
    last_attempt_at:'2026-11-09T08:00:00Z',last_successful_check_at:'2026-11-09T08:01:00Z',
    last_successful_apply_at:'2026-11-08T08:01:00Z',last_data_change_observed_at:'2026-11-07T08:01:00Z',
    check_age_seconds:14340,is_stale:false },
};
function response(data: unknown,status=200) { return new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json'}}); }
function mount(handler: () => Response | Promise<Response> = () => response(available)) {
  const fetcher=vi.fn(handler);vi.stubGlobal('fetch',fetcher);
  const client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}});
  render(<QueryClientProvider client={client}><FreshnessIndicator /></QueryClientProvider>);
  return fetcher;
}

describe('freshness API and local formatting', () => {
  it('reads only the new GET endpoint with cancellation', async () => {
    const fetcher=vi.fn().mockResolvedValue(response(available));vi.stubGlobal('fetch',fetcher);
    const signal=new AbortController().signal;
    await api.freshness(signal);
    expect(fetcher).toHaveBeenCalledWith('/api/data-status/schedule',expect.objectContaining({signal}));
    expect(fetcher.mock.calls[0][1].method).toBeUndefined(); // Fetch defaults to GET.
  });
  it('rejects malformed success bodies without crashing the dashboard', () => {
    expect(() => parseFreshness({data:{},meta:{}})).toThrow('Unexpected refresh history');
    expect(() => parseFreshness({...available,meta:{...available.meta,manual:false}})).toThrow();
  });
  it('formats the same UTC instant on the correct local calendar day', () => {
    const instant='2027-01-01T00:30:00Z';
    const west=formatFreshnessTimestamp(instant,{locale:'en-US',timeZone:'America/Los_Angeles'});
    const east=formatFreshnessTimestamp(instant,{locale:'en-US',timeZone:'Asia/Tokyo'});
    expect(west).toContain('Dec 31, 2026');expect(west).toContain('4:30 PM');expect(west).toContain('PST');
    expect(east).toContain('Jan 1, 2027');expect(east).toContain('9:30 AM');
  });
  it('formats local DST correctly and never guesses a timezone for naive timestamps', () => {
    expect(formatFreshnessTimestamp('2026-07-01T16:00:00Z',{locale:'en-US',timeZone:'America/New_York'})).toContain('EDT');
    expect(formatFreshnessTimestamp('2026-12-01T16:00:00Z',{locale:'en-US',timeZone:'America/New_York'})).toContain('EST');
    expect(formatFreshnessTimestamp('2026-12-01T16:00:00')).toBe('Unavailable');
    expect(formatFreshnessTimestamp('bad')).toBe('Unavailable');
    expect(formatFreshnessTimestamp(null)).toBe('Not recorded');
  });
});

describe('refresh history panel', () => {
  it('distinguishes checks, no-change applies and actual data changes', async () => {
    mount();
    expect(await screen.findByText('Successful apply — no changes')).toBeInTheDocument();
    const panel=screen.getByRole('region',{name:'Schedule data freshness'});
    expect(within(panel).getByText('Manual · Not a live feed')).toBeInTheDocument();
    const field=(label:string) => within(panel).getByText(label).nextElementSibling!.querySelector('time');
    expect(field('Last successful check')).toHaveAttribute('datetime','2026-11-09T08:01:00Z');
    expect(field('Last successful apply (may be unchanged)')).toHaveAttribute('datetime','2026-11-08T08:01:00Z');
    expect(field('Last observed data change')).toHaveAttribute('datetime','2026-11-07T08:01:00Z');
    expect(within(panel).getByText(/game status may remain UNKNOWN/)).toBeInTheDocument();
    expect(within(panel).getByText(/local timezone; kickoffs remain Eastern/)).toBeInTheDocument();
  });
  it('shows loading without blocking the rest of the page', () => {
    mount(() => new Promise<Response>(() => {}));
    expect(screen.getByText('Loading refresh history…')).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Reload refresh history'})).toBeDisabled();
  });
  it.each(['missing','incomplete','invalid','unreadable'] as const)('handles %s metadata', async state => {
    mount(() => response({...freshness,data:{...freshness.data,metadata_state:state}}));
    await screen.findByText(/Latest recorded outcome:/);
    expect(screen.queryByText(/Last successful check is older/)).not.toBeInTheDocument();
    expect(screen.getByText('Last recorded attempt').nextElementSibling).toHaveTextContent('Not recorded');
    expect(screen.getByRole('button',{name:'Reload refresh history'})).toBeEnabled();
  });
  it('shows stale check age as operational history, not proof of outdated scores', async () => {
    mount(() => response({...available,data:{...available.data,is_stale:true,check_age_seconds:150000}}));
    expect(await screen.findByText('Last successful check is older than 36 hours.')).toBeInTheDocument();
    expect(screen.queryByText('Live')).not.toBeInTheDocument();
  });
  it('keeps previous success observations visible after a failed runner attempt', async () => {
    mount(() => response({...available,data:{...available.data,latest_outcome:'download_failed'}}));
    expect(await screen.findByText('Download failed')).toBeInTheDocument();
    expect(screen.getByText(/Earlier successful observations remain below/)).toBeInTheDocument();
    expect(screen.getByText('Last observed data change').nextElementSibling!.querySelector('time')).toHaveAttribute('datetime','2026-11-07T08:01:00Z');
  });
  it.each(['http','network','invalid_json_shape'])('supports retry after %s failure', async failure => {
    let failed=true;
    mount(() => !failed ? response(available) : failure==='http' ? response({},503) :
      failure==='network' ? Promise.reject(new TypeError('network')) : response({data:{}}));
    expect(await screen.findByText(/Refresh history is unavailable/)).toBeInTheDocument();
    failed=false;fireEvent.click(screen.getByRole('button',{name:'Reload refresh history'}));
    expect(await screen.findByText('Successful apply — no changes')).toBeInTheDocument();
  });
  it('labels cached history when a manual reload fails', async () => {
    let failed=false;mount(() => failed ? response({},503) : response(available));
    await screen.findByText('Successful apply — no changes');
    failed=true;fireEvent.click(screen.getByRole('button',{name:'Reload refresh history'}));
    expect(await screen.findByText(/showing previously loaded metadata/)).toBeInTheDocument();
    expect(screen.getByText('Last observed data change').nextElementSibling!.querySelector('time')).toHaveAttribute('datetime','2026-11-07T08:01:00Z');
  });
  it('does not refresh on focus/reconnect and starts no polling', async () => {
    const fetcher=mount();await screen.findByText('Successful apply — no changes');
    await act(async () => {
      window.dispatchEvent(new Event('focus'));document.dispatchEvent(new Event('visibilitychange'));
      window.dispatchEvent(new Event('online'));
      await new Promise(resolve => setTimeout(resolve,20));
    });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('does not hide valid schedules when freshness is unavailable', async () => {
    vi.stubGlobal('fetch',vi.fn((url:string) => Promise.resolve(url==='/api/data-status/schedule' ? response({},503) :
      response(url==='/api/seasons' ? seasons : schedule()))));
    const client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}});
    render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/schedule/2026/REG/1']}><App /></MemoryRouter></QueryClientProvider>);
    expect(await screen.findByText('Synthetic Away')).toBeInTheDocument();
    expect(await screen.findByText(/Refresh history is unavailable/)).toBeInTheDocument();
    expect(screen.getByText('UNKNOWN · Finality unverified')).toBeInTheDocument();
  });
});
