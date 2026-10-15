import { ApiError, postJson, request } from './api';

// Client for the backend's "my rides" endpoints (app/api/me.py) and booking cancel (app/api/bookings.py).
// Field names match the API (snake_case). IDs are strings because snowflakes exceed JS's safe-integer range.

export { ApiError as MyRidesError };

export type Scope = 'upcoming' | 'past' | 'all';
export type RideStatus = 'open' | 'full' | 'started' | 'completed' | 'cancelled';
export type BookingStatus =
    | 'requested' | 'accepted' | 'rejected' | 'cancelled_by_rider' | 'cancelled_by_driver' | 'expired' | 'completed';

export type StationInfo = { id_station: number; name: string };
export type DriverInfo = { id_user: string; full_name: string | null; photo_url: string | null };
export type VehicleInfo = { make: string; model: string; color: string; vehicle_type: string };

export type RideInfo = {
    id_ride: string;
    status: RideStatus;
    source: StationInfo;
    destination: StationInfo;
    departure_time: string; // ISO, UTC
    estimated_arrival_time: string | null;
    total_seats: number;
    available_seats: number;
    price_per_seat: string | number; // Decimal: serialised as a string
    notes: string | null;
    driver: DriverInfo;
    vehicle: VehicleInfo | null;
};

/** GET /v1/me/rides item: a ride I offered. */
export type MyRide = RideInfo & { requests: { pending_requests: number; accepted_seats: number } };

/** GET /v1/me/bookings item: a booking I made, with its ride. */
export type MyBooking = {
    id_booking: string;
    status: BookingStatus;
    seats_booked: number;
    price_per_seat: string | number;
    total_amount: string | number;
    rider_note: string | null;
    created_at: string;
    ride: RideInfo;
};

export type Page<T> = { items: T[]; next_page: string | null; prev_page: string | null };

const query = (scope: Scope, cursor?: string | null, pageSize = 20) => {
    const p = new URLSearchParams({ when: scope, page_size: String(pageSize) });
    if (cursor) p.set('cursor', cursor);
    return p.toString();
};

// Rides seen in any list, so the detail page opens instantly from My Rides.
const rideCache = new Map<string, MyRide>();

export async function fetchMyRides(scope: Scope, cursor?: string | null) {
    const page = await request<Page<MyRide>>(`/v1/me/rides?${query(scope, cursor)}`);
    page.items.forEach(r => rideCache.set(r.id_ride, r));
    return page;
}

export const cachedMyRide = (idRide: string) => rideCache.get(idRide) ?? null;

/**
 * One of my offered rides by id. There's no GET /v1/rides/{id}, so this pages through
 * /v1/me/rides (upcoming first, then everything) until it finds it. Returns null if not mine.
 */
export async function findMyRide(idRide: string, maxPages = 10): Promise<MyRide | null> {
    for (const scope of ['upcoming', 'all'] as const) {
        let cursor: string | null = null;
        for (let i = 0; i < maxPages; i++) {
            const page: Page<MyRide> = await fetchMyRides(scope, cursor);
            const hit = page.items.find(r => r.id_ride === idRide);
            if (hit) return hit;
            if (!page.next_page) break;
            cursor = page.next_page;
        }
    }
    return null;
}

export const fetchMyBookings = (scope: Scope, cursor?: string | null) =>
    request<Page<MyBooking>>(`/v1/me/bookings?${query(scope, cursor)}`);

/** POST /v1/ride/booking/{id}/cancel: the rider cancels their own request or booking. */
export const cancelBooking = (idBooking: string, reason?: string) =>
    postJson<{ id_booking: string; status: BookingStatus }>(
        `/v1/ride/booking/${idBooking}/cancel`,
        reason ? { reason } : {},
    );

/** "15", "15.50": drops trailing .00 from API decimals. */
export const money = (v: string | number) => {
    const n = Number(v);
    return Number.isFinite(n) ? (Number.isInteger(n) ? String(n) : n.toFixed(2)) : String(v);
};

export const vehicleText = (v: VehicleInfo | null) => (v ? `${v.color} ${v.make} ${v.model}` : null);
