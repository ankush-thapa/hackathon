import { ApiError, postJson, request } from './api';

// Request-a-ride flow: GET /v1/stations → GET /v1/rides (search) → POST /v1/ride/booking.
// Note: /v1/rides responds in camelCase; stations and bookings use snake_case (as the API does).

export { ApiError as RideSearchError };

export type Station = { id_station: number; station_name: string; is_active: boolean };

export type SearchRide = {
    idRide: string;
    source: { idStation: number; name: string };
    destination: { idStation: number; name: string };
    departureTime: string; // ISO, UTC
    estimatedArrivalTime: string | null;
    totalSeats: number;
    availableSeats: number;
    pricePerSeat: string | number;
    notes: string | null;
    driver: { userId: string; fullName: string | null; photoUrl: string | null };
    vehicle: { make: string; model: string; color: string; vehicleType: string } | null;
};

type SearchPage = { items: SearchRide[]; next_page: string | null; prev_page: string | null };

/** Active stations, A–Z. One call is enough for the station counts we expect (max 200). */
export async function fetchStations(): Promise<Station[]> {
    const res = await request<{ items: Station[] }>('/v1/stations?limit=200');
    return res.items;
}

export type SearchParams = { from: number; to: number; seats: number };

const searchPage = (p: SearchParams, utcDate: string, cursor?: string | null) => {
    const q = new URLSearchParams({
        idSourceStation: String(p.from),
        idDestinationStation: String(p.to),
        departureDate: utcDate,
        seats: String(p.seats),
        pageSize: '50',
    });
    if (cursor) q.set('cursor', cursor);
    return request<SearchPage>(`/v1/rides?${q}`);
};

const utcDay = (d: Date) => d.toISOString().slice(0, 10);

/**
 * The API filters by UTC calendar day, but users pick a local day. A local day can span two UTC
 * days (e.g. IST), so we query each of them, keep rides that depart on the chosen local day,
 * and expose one cursor per UTC day for "load more".
 */
export type DaySearch = { rides: SearchRide[]; cursors: Record<string, string | null> };

const inLocalDay = (iso: string, day: Date) => {
    const t = new Date(iso).getTime();
    const start = new Date(day.getFullYear(), day.getMonth(), day.getDate()).getTime();
    return t >= start && t < start + 86_400_000;
};

const merge = (a: SearchRide[], b: SearchRide[]) => {
    const seen = new Map(a.map(r => [r.idRide, r]));
    b.forEach(r => seen.set(r.idRide, r));
    return [...seen.values()].sort((x, y) => x.departureTime.localeCompare(y.departureTime));
};

export async function searchRides(p: SearchParams, day: Date): Promise<DaySearch> {
    const start = new Date(day.getFullYear(), day.getMonth(), day.getDate());
    const end = new Date(start.getTime() + 86_400_000 - 1);
    const utcDays = [...new Set([utcDay(start), utcDay(end)])];
    const pages = await Promise.all(utcDays.map(d => searchPage(p, d)));
    const cursors: Record<string, string | null> = {};
    utcDays.forEach((d, i) => { cursors[d] = pages[i].next_page; });
    const rides = merge([], pages.flatMap(pg => pg.items)).filter(r => inLocalDay(r.departureTime, day));
    return { rides, cursors };
}

export async function searchMore(p: SearchParams, day: Date, prev: DaySearch): Promise<DaySearch> {
    const pending = Object.entries(prev.cursors).filter(([, c]) => c);
    const pages = await Promise.all(pending.map(([d, c]) => searchPage(p, d, c)));
    const cursors = { ...prev.cursors };
    pending.forEach(([d], i) => { cursors[d] = pages[i].next_page; });
    const fresh = pages.flatMap(pg => pg.items).filter(r => inLocalDay(r.departureTime, day));
    return { rides: merge(prev.rides, fresh), cursors };
}

export const hasMore = (s: DaySearch) => Object.values(s.cursors).some(Boolean);

export type Booking = { id_booking: string; status: string; seats_booked: number; total_amount: string | number };

/** POST /v1/ride/booking: request seats. Starts as `requested` until the driver approves. */
export const bookRide = (idRide: string, seats: number, note?: string) =>
    postJson<Booking>('/v1/ride/booking', { id_ride: idRide, seats, rider_note: note?.trim() || null });
