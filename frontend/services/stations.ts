import { request } from './api';

// GET /v1/stations — pickup/drop-off stations (requires a logged-in session).
// Query: search (case-insensitive substring of the name, ≤100 chars), limit (1–200), offset.

export type Station = { id: number; name: string };

type StationListResponse = {
    items: { id_station: number; station_name: string; is_active: boolean }[];
    total: number;
    limit: number;
    offset: number;
};

export const MAX_STATION_SEARCH = 100;

export async function searchStations(search: string, opts: { limit?: number; signal?: AbortSignal } = {}): Promise<Station[]> {
    const params = new URLSearchParams({ limit: String(opts.limit ?? 20) });
    const q = search.trim().slice(0, MAX_STATION_SEARCH);
    if (q) params.set('search', q);
    const data = await request<StationListResponse>(`/v1/stations?${params}`, { signal: opts.signal });
    return data.items.map(s => ({ id: s.id_station, name: s.station_name }));
}
