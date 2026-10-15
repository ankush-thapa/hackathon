import { dayStart } from './format';
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

const searchPage = (p: SearchParams, date: string, cursor?: string | null) => {
    const q = new URLSearchParams({
        idSourceStation: String(p.from),
        idDestinationStation: String(p.to),
        departureDate: date,
        seats: String(p.seats),
        pageSize: '50',
    });
    if (cursor) q.set('cursor', cursor);
    return request<SearchPage>(`/v1/rides?${q}`);
};

/** The picked calendar day as YYYY-MM-DD (never toISOString, which would shift it to UTC). */
const localDate = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

/**
 * Sends exactly the date the user picked as `departureDate`.
 * The API reads that date as a UTC day, so it covers 05:30 IST that day to 05:29 IST the next.
 * Rides from the next morning are filtered out here so the list only shows the picked day;
 * rides before 05:30 on the picked day aren't returned by the API at all.
 * TODO(backend): accept a timezone (or from/to times) so the search can match the local day exactly.
 */
export type DaySearch = { rides: SearchRide[]; date: string; cursor: string | null };

/** True if the ride departs on the picked day, in IST. */
const inLocalDay = (iso: string, day: Date) => {
    const t = new Date(iso).getTime();
    const start = dayStart(day).getTime();
    return t >= start && t < start + 86_400_000;
};

const merge = (a: SearchRide[], b: SearchRide[]) => {
    const seen = new Map(a.map(r => [r.idRide, r]));
    b.forEach(r => seen.set(r.idRide, r));
    return [...seen.values()].sort((x, y) => x.departureTime.localeCompare(y.departureTime));
};

export async function searchRides(p: SearchParams, day: Date): Promise<DaySearch> {
    const date = localDate(day);
    const page = await searchPage(p, date);
    return { rides: merge([], page.items).filter(r => inLocalDay(r.departureTime, day)), date, cursor: page.next_page };
}

export async function searchMore(p: SearchParams, day: Date, prev: DaySearch): Promise<DaySearch> {
    if (!prev.cursor) return prev;
    const page = await searchPage(p, prev.date, prev.cursor);
    const fresh = page.items.filter(r => inLocalDay(r.departureTime, day));
    return { rides: merge(prev.rides, fresh), date: prev.date, cursor: page.next_page };
}

export const hasMore = (s: DaySearch) => !!s.cursor;

export type Booking = { id_booking: string; status: string; seats_booked: number; total_amount: string | number };

/** POST /v1/ride/booking: request seats. Starts as `requested` until the driver approves. */
export const bookRide = (idRide: string, seats: number, note?: string) =>
    postJson<Booking>('/v1/ride/booking', { id_ride: idRide, seats, rider_note: note?.trim() || null });


/** Recheck every loaded ride, preserving pagination cursors. The server omits no-longer-bookable rides. */
export async function refreshAvailability(previous: DaySearch, seats: number): Promise<DaySearch> {
    const available = new Map<string, number>();
    for (let i = 0; i < previous.rides.length; i += 100) {
        const data = await postJson<{ items: { idRide: string; availableSeats: number }[] }>('/v1/rides/availability', {
            id_rides: previous.rides.slice(i, i + 100).map(r => r.idRide), seats,
        });
        data.items.forEach(r => available.set(r.idRide, r.availableSeats));
    }
    return { ...previous, rides: previous.rides.filter(r => available.has(r.idRide)).map(r => ({ ...r, availableSeats: available.get(r.idRide)! })) };
}
