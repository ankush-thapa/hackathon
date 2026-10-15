import { ApiError, postJson, request } from './api';
import { fetchMyRides } from './myRides';
export { ApiError as RideRequestError };

// idNotification is retained as the existing component key; it is now the booking ID.
export type RideRequest = { idNotification: string; idRide: string; idBooking: string; message: string; createdAt: string };
type Booking = { id_booking: string; id_ride: string; seats_booked: number; rider_note: string | null;
    rider_name: string | null; created_at: string; status: string };

async function forRide(id: string): Promise<RideRequest[]> {
    const result: RideRequest[] = [];
    let cursor: string | null = null;
    do {
        const q = new URLSearchParams({ status: 'requested', limit: '50' });
        if (cursor) q.set('cursor', cursor);
        const page: { items: Booking[]; next_cursor: string | null } =
            await request(`/v1/rides/${id}/bookings?${q}`);
        result.push(...page.items.map(b => ({ idNotification: b.id_booking, idRide: id, idBooking: b.id_booking,
            message: `${b.rider_name || 'A rider'} requested ${b.seats_booked} seat(s)${b.rider_note ? ` · ${b.rider_note}` : ''}`,
            createdAt: b.created_at })));
        cursor = page.next_cursor;
    } while (cursor);
    return result;
}

export async function fetchPendingRequests(idRide?: string): Promise<Record<string, RideRequest[]>> {
    if (idRide) return { [idRide]: await forRide(idRide) };
    const result: Record<string, RideRequest[]> = {};
    let cursor: string | null = null;
    do {
        const page = await fetchMyRides('upcoming', cursor);
        // Sequential per ride to avoid an unbounded burst of database requests.
        for (const ride of page.items) if (ride.requests.pending_requests) result[ride.id_ride] = await forRide(ride.id_ride);
        cursor = page.next_page;
    } while (cursor);
    return result;
}

export type Outcome = 'approved' | 'declined' | 'gone';
export async function approveRequest(req: RideRequest, _driverName: string): Promise<Outcome> {
    try {
        await postJson(`/v1/ride/booking/${req.idBooking}/approve`, {});
        return 'approved';
    } catch (e) {
        if (e instanceof ApiError && e.status === 409 && /not awaiting approval/i.test(e.message)) return 'gone';
        throw e;
    }
}
export async function declineRequest(req: RideRequest, _driverName: string): Promise<Outcome> {
    try {
        await postJson(`/v1/ride/booking/${req.idBooking}/reject`, { reason: 'Declined by driver' });
        return 'declined';
    } catch (e) {
        if (e instanceof ApiError && e.status === 409 && /cannot be rejected/i.test(e.message)) return 'gone';
        throw e;
    }
}
