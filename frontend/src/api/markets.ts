import type { Game } from './types';
export interface MarketSide {
  market: 'MONEYLINE' | 'SPREAD' | 'TOTAL'; side: 'AWAY' | 'HOME' | 'OVER' | 'UNDER';
  line: string | null; price: string | null;
  result: 'WIN' | 'LOSS' | 'PUSH' | 'UNDETERMINED'; reason: string;
}
export interface MarketsResponse {
  data: { game: Game; unavailable_reason: string | null; references: {
    snapshot_id: string; provider: 'nflverse'; bookmaker: null; classification: 'UNVERIFIED_SOURCE_REFERENCE';
    quote_updated_at: null; freshness: 'UNKNOWN'; artifact_id: string; artifact_sha256: string;
    source_record_sha256: string; artifact_retrieved_at: string | null; artifact_recorded_at: string;
    origin_status: string; source_url: string | null; license_url: string | null; attribution: string | null;
    sides: MarketSide[]; warnings: string[];
  }[] };
  meta: { current_offers_available: false; verified_pregame_snapshot_available: false; settlement_verified: false;
    semantics: string; timestamp_semantics: string; tie_policy: string; spread_definition: string; price_semantics: string };
}
export async function markets(id: string, signal?: AbortSignal): Promise<MarketsResponse> {
  const response = await fetch(`/api/games/${encodeURIComponent(id)}/markets`, { signal, headers: { Accept: 'application/json' } });
  if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) throw new Error('Market references unavailable.');
  const data = await response.json() as MarketsResponse;
  if (!Array.isArray(data.data?.references) || data.data?.game?.id !== id || data.meta?.settlement_verified !== false) throw new Error('Invalid market reference response.');
  return data;
}
