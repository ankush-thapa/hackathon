import { ApiError, postJson, request } from './api';
import { createStore, useStore } from './store/createStore';
import { getSession } from './session';

// Backend: app/api/notifications.py
//   GET  /v1/notifications?limit=        unread only, newest first, plus the total unread count
//   POST /v1/notifications/{id}/read     mark one read (it then drops out of GET)
//   POST /v1/notifications/read-all      mark all read
//   POST /v1/notifications               send one to another participant of the same ride
//
// Booking and ride endpoints create event notifications in the same database transaction.

export const NOTIFICATION_TYPES = [
    'ride_created',
    'booking_requested',
    'booking_accepted',
    'booking_rejected',
    'booking_cancelled',
    'ride_cancelled',
    'ride_modified',
] as const;
export type NotificationType = (typeof NOTIFICATION_TYPES)[number];

export type Notification = {
    idNotification: string;
    type: NotificationType;
    idRide: string;
    idBooking: string | null;
    message: string;
    createdAt: string; // ISO, UTC
    /** Set locally once the user opens it; the server stops returning it after that. */
    read?: boolean;
};

type ListResponse = { items: Notification[]; unreadCount: number };

/** How each type is shown in the list. */
export const NOTIFICATION_META: Record<NotificationType, { title: string; tone: 'brand' | 'success' | 'error' | 'muted' }> = {
    ride_created: { title: 'Ride offered', tone: 'success' },
    booking_requested: { title: 'New ride request', tone: 'brand' },
    booking_accepted: { title: 'Booking confirmed', tone: 'success' },
    booking_rejected: { title: 'Request declined', tone: 'error' },
    booking_cancelled: { title: 'Booking cancelled', tone: 'muted' },
    ride_cancelled: { title: 'Ride cancelled', tone: 'error' },
    ride_modified: { title: 'Ride updated', tone: 'brand' },
};

// --- Shared state ------------------------------------------------------------------------------
type State = { items: Notification[]; unreadCount: number; loaded: boolean; error: string | null };
const EMPTY: State = { items: [], unreadCount: 0, loaded: false, error: null };
const store = createStore<State>(EMPTY);

export const useNotifications = () => useStore(store);
export const useUnreadCount = () => useStore(store).unreadCount;
let generation = 0;
export const resetNotifications = () => { generation++; store.set(EMPTY); };

export const POLL_INTERVAL_MS = 30_000;
const PAGE_SIZE = 50; // API maximum

/** Fetches unread notifications. Items opened this visit stay in the list (shown as read). Throws ApiError. */
export async function refreshNotifications(): Promise<void> {
    const session = getSession();
    const before = generation;
    if (!session) { resetNotifications(); return; }
    try {
        const data = await request<ListResponse>(`/v1/notifications?limit=${PAGE_SIZE}`);
        if (before !== generation || getSession()?.userId !== session.userId) return;
        store.set(prev => {
            const fresh = new Set(data.items.map(n => n.idNotification));
            const keptRead = prev.items.filter(n => n.read && !fresh.has(n.idNotification));
            const items = [...data.items, ...keptRead].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
            return { items, unreadCount: data.unreadCount, loaded: true, error: null };
        });
    } catch (e) {
        if (before !== generation || getSession()?.userId !== session.userId) return;
        store.set(prev => ({ ...prev, loaded: true, error: e instanceof Error ? e.message : 'Could not load notifications' }));
        throw e;
    }
}

export async function markRead(id: string): Promise<void> {
    const target = store.get().items.find(n => n.idNotification === id);
    if (!target || target.read) return;
    // Optimistic: update the badge straight away, roll back if the call fails.
    store.set(prev => ({
        ...prev,
        items: prev.items.map(n => (n.idNotification === id ? { ...n, read: true } : n)),
        unreadCount: Math.max(0, prev.unreadCount - 1),
    }));
    try {
        await request(`/v1/notifications/${id}/read`, { method: 'POST' });
    } catch (e) {
        if (e instanceof ApiError && e.status === 404) return; // already gone on the server
        store.set(prev => ({
            ...prev,
            items: prev.items.map(n => (n.idNotification === id ? { ...n, read: false } : n)),
            unreadCount: prev.unreadCount + 1,
        }));
        throw e;
    }
}

export async function markAllRead(): Promise<void> {
    const before = store.get();
    store.set(prev => ({ ...prev, items: prev.items.map(n => ({ ...n, read: true })), unreadCount: 0 }));
    try {
        await postJson<{ marked: number }>('/v1/notifications/read-all', {});
    } catch (e) {
        store.set(before);
        throw e;
    }
}

// --- Sending (POST /v1/notifications) ----------------------------------------------------------
type SendInput = { toUserId: string; type: NotificationType; rideId: string; bookingId?: string | null; message: string };

const MAX_MESSAGE = 255;

/**
 * Sends a notification to the other person on a ride. Best effort: the booking or ride action has
 * already succeeded, so a failed notification is logged and never shown as an error to the user.
 */
export async function sendNotification({ toUserId, type, rideId, bookingId, message }: SendInput): Promise<void> {
    try {
        await postJson('/v1/notifications', {
            idUser: toUserId, // IDs as strings: snowflakes exceed JS's safe-integer range
            type,
            idRide: rideId,
            ...(bookingId ? { idBooking: bookingId } : {}),
            message: message.trim().slice(0, MAX_MESSAGE),
        });
    } catch (e) {
        console.warn(`Could not send ${type} notification`, e);
    }
}

/** `departure` is the ride's ISO departure time. */
type RideRef = { rideId: string; from: string; to: string; departure: string };
// Messages are stored and read later, so use an absolute date ("Fri 16 Oct, 09:00"), never "Tomorrow".
const when = (iso: string) =>
    new Date(iso).toLocaleString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
const route = (r: RideRef) => `${r.from} → ${r.to} (${when(r.departure)})`;
const seatText = (n: number) => `${n} seat${n === 1 ? '' : 's'}`;

/** Rider → driver, after POST /v1/ride/booking. */
export const notifyBookingRequested = (a: RideRef & { driverId: string; bookingId: string; riderName: string; seats: number }) =>
    sendNotification({
        toUserId: a.driverId, type: 'booking_requested', rideId: a.rideId, bookingId: a.bookingId,
        message: `${a.riderName} requested ${seatText(a.seats)} on your ride ${route(a)}.`,
    });

/** Driver → rider, after approving a request. */
export const notifyBookingAccepted = (a: RideRef & { riderId: string; bookingId: string; driverName: string }) =>
    sendNotification({
        toUserId: a.riderId, type: 'booking_accepted', rideId: a.rideId, bookingId: a.bookingId,
        message: `${a.driverName} accepted your request for ${route(a)}.`,
    });

/** Driver → rider, after declining a request. */
export const notifyBookingRejected = (a: RideRef & { riderId: string; bookingId: string; driverName: string }) =>
    sendNotification({
        toUserId: a.riderId, type: 'booking_rejected', rideId: a.rideId, bookingId: a.bookingId,
        message: `${a.driverName} couldn't take your request for ${route(a)}.`,
    });

/** Rider → driver, after POST /v1/ride/booking/{id}/cancel. */
export const notifyBookingCancelled = (a: RideRef & { driverId: string; bookingId: string; riderName: string; seats: number }) =>
    sendNotification({
        toUserId: a.driverId, type: 'booking_cancelled', rideId: a.rideId, bookingId: a.bookingId,
        message: `${a.riderName} cancelled their ${seatText(a.seats)} on ${route(a)}.`,
    });

/** Driver → each rider with a booking, after cancelling a ride. */
export const notifyRideCancelled = (a: RideRef & { riderIds: string[]; driverName: string }) =>
    Promise.all(a.riderIds.map(id => sendNotification({
        toUserId: id, type: 'ride_cancelled', rideId: a.rideId,
        message: `${a.driverName} cancelled the ride ${route(a)}.`,
    })));

/** Driver → each rider with a booking, after changing a ride. `change` e.g. "New time: 09:30". */
export const notifyRideModified = (a: RideRef & { riderIds: string[]; driverName: string; change: string }) =>
    Promise.all(a.riderIds.map(id => sendNotification({
        toUserId: id, type: 'ride_modified', rideId: a.rideId,
        message: `${a.driverName} updated the ride ${route(a)}. ${a.change}`,
    })));
