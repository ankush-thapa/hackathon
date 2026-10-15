import { ApiError, postJson, request } from './api';
import { timeLabel } from './format';

// Driver-side handling of seat requests, built only on existing endpoints:
//
// The backend has no "list the requests on my ride" endpoint, so the rider's app sends the
// driver a `booking_requested` notification (POST /v1/notifications) carrying the booking id
// right after booking. The driver's app reads those from GET /v1/notifications (unread only),
// then approves (POST /v1/ride/booking/{id}/approve) or declines (POST …/cancel, which the API
// records as cancelled_by_driver), tells the rider, and marks the notification read.
//
// Limitation: requests made without that notification (older bookings, other clients) won't
// show here; the ride card still shows the backend's pending count.

export { ApiError as RideRequestError };

type NotificationType =
    | 'booking_requested' | 'booking_accepted' | 'booking_rejected' | 'booking_cancelled' | 'ride_cancelled' | 'ride_modified';

type NotificationItem = {
    idNotification: string;
    type: NotificationType;
    idRide: string;
    idBooking: string | null;
    message: string;
    createdAt: string;
};

export type RideRequest = { idNotification: string; idRide: string; idBooking: string; message: string; createdAt: string };

type BookingResponse = { id_booking: string; id_ride: string; id_rider: string; id_driver: string; seats_booked: number; status: string };

const send = (body: { idUser: string; type: NotificationType; idRide: string; idBooking?: string; message: string }) =>
    postJson<NotificationItem>('/v1/notifications', { ...body, message: body.message.slice(0, 255) });

const markRead = (idNotification: string) =>
    request<void>(`/v1/notifications/${idNotification}/read`, { method: 'POST' });

/** Rider side: tell the driver about a new request. Best effort: booking already succeeded. */
export async function notifyDriverOfRequest(input: {
    idDriver: string; idRide: string; idBooking: string; departureTime: string; seats: number; riderName: string; note?: string;
}) {
    const seats = `${input.seats} seat${input.seats === 1 ? '' : 's'}`;
    const note = input.note?.trim() ? ` · “${input.note.trim()}”` : '';
    try {
        await send({
            idUser: input.idDriver,
            type: 'booking_requested',
            idRide: input.idRide,
            idBooking: input.idBooking,
            message: `${input.riderName} requested ${seats} on your ${timeLabel(new Date(input.departureTime))} ride${note}`,
        });
    } catch {
        // The booking exists either way; the driver still sees the pending count.
    }
}

/** Driver side: pending seat requests, grouped by ride id. */
export async function fetchPendingRequests(): Promise<Record<string, RideRequest[]>> {
    const res = await request<{ items: NotificationItem[] }>('/v1/notifications?limit=50');
    const byRide: Record<string, RideRequest[]> = {};
    for (const n of res.items) {
        if (n.type !== 'booking_requested' || !n.idBooking) continue;
        (byRide[n.idRide] ??= []).push({
            idNotification: n.idNotification, idRide: n.idRide, idBooking: n.idBooking, message: n.message, createdAt: n.createdAt,
        });
    }
    Object.values(byRide).forEach(list => list.sort((a, b) => a.createdAt.localeCompare(b.createdAt)));
    return byRide;
}

/** 409 "not awaiting approval": the rider cancelled or it was already handled. */
const isStale = (e: unknown) => e instanceof ApiError && e.status === 409 && /not awaiting approval|cannot be cancelled/i.test(e.message);

export type Outcome = 'approved' | 'declined' | 'gone';

async function finish(req: RideRequest, booking: BookingResponse | null, type: NotificationType, message: string) {
    await markRead(req.idNotification).catch(() => undefined);
    if (booking) await send({ idUser: booking.id_rider, type, idRide: req.idRide, idBooking: req.idBooking, message }).catch(() => undefined);
}

export async function approveRequest(req: RideRequest, driverName: string): Promise<Outcome> {
    try {
        const b = await postJson<BookingResponse>(`/v1/ride/booking/${req.idBooking}/approve`, {});
        await finish(req, b, 'booking_accepted', `${driverName} confirmed your ${b.seats_booked === 1 ? 'seat' : `${b.seats_booked} seats`}`);
        return 'approved';
    } catch (e) {
        if (isStale(e)) {
            await finish(req, null, 'booking_accepted', '');
            return 'gone';
        }
        throw e;
    }
}

export async function declineRequest(req: RideRequest, driverName: string): Promise<Outcome> {
    try {
        const b = await postJson<BookingResponse>(`/v1/ride/booking/${req.idBooking}/cancel`, { reason: 'Declined by driver' });
        await finish(req, b, 'booking_rejected', `${driverName} couldn't take your request this time`);
        return 'declined';
    } catch (e) {
        if (isStale(e)) {
            await finish(req, null, 'booking_rejected', '');
            return 'gone';
        }
        throw e;
    }
}
