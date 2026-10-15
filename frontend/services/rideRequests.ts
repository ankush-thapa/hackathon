import { ApiError, postJson, request } from './api';

// Driver-side seat requests, from the backend's authoritative endpoints:
//   GET  /v1/rides/{id}/bookings?status=requested   pending requests with rider name/photo (driver only)
//   POST /v1/ride/booking/{id}/approve               → accepted (takes the seats)
//   POST /v1/ride/booking/{id}/reject                → rejected
// The backend notifies the rider itself for both, so nothing is sent from here.

export { ApiError as RideRequestError };

type RiderBookingItem = {
    id_booking: string;
    id_ride: string;
    id_rider: string;
    seats_booked: number;
    total_amount: string | number;
    rider_note: string | null;
    status: string;
    created_at: string;
    rider_name: string | null;
    rider_photo_url: string | null;
};

export type RideRequest = {
    idBooking: string;
    idRide: string;
    riderName: string;
    riderPhotoUrl: string | null;
    seats: number;
    totalAmount: string | number;
    note: string | null;
    createdAt: string;
};

const toRequest = (b: RiderBookingItem): RideRequest => ({
    idBooking: b.id_booking,
    idRide: b.id_ride,
    riderName: b.rider_name || 'A rider',
    riderPhotoUrl: b.rider_photo_url,
    seats: b.seats_booked,
    totalAmount: b.total_amount,
    note: b.rider_note,
    createdAt: b.created_at,
});

/** Pending requests on one of my rides, oldest first. */
export async function fetchRideRequests(idRide: string): Promise<RideRequest[]> {
    const res = await request<{ items: RiderBookingItem[] }>(`/v1/rides/${idRide}/bookings?status=requested&limit=50`);
    return res.items.map(toRequest).sort((a, b) => a.createdAt.localeCompare(b.createdAt));
}

/** Pending requests for several rides at once, keyed by ride id (only rides that have some). */
export async function fetchRequestsFor(rideIds: string[]): Promise<Record<string, RideRequest[]>> {
    const lists = await Promise.all(rideIds.map(id => fetchRideRequests(id).catch(() => [] as RideRequest[])));
    return Object.fromEntries(rideIds.map((id, i) => [id, lists[i]]));
}

/** 409: the rider cancelled or it was already handled. */
const isStale = (e: unknown) => e instanceof ApiError && e.status === 409;

export type Outcome = 'approved' | 'declined' | 'gone';

export async function approveRequest(req: RideRequest): Promise<Outcome> {
    try {
        await postJson(`/v1/ride/booking/${req.idBooking}/approve`, {});
        return 'approved';
    } catch (e) {
        if (isStale(e) && /not awaiting approval/i.test((e as Error).message)) return 'gone';
        throw e; // e.g. 409 "not enough seats" is worth showing
    }
}

export async function declineRequest(req: RideRequest, reason?: string): Promise<Outcome> {
    try {
        await postJson(`/v1/ride/booking/${req.idBooking}/reject`, reason ? { reason } : {});
        return 'declined';
    } catch (e) {
        if (isStale(e)) return 'gone';
        throw e;
    }
}
