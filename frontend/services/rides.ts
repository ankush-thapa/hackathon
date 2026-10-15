import { ApiError, postJson } from './api';
import { clearSession } from './session';
import { createStore, useStore } from './store/createStore';

// Offers go to POST /v1/rides/offer. Ride requests are still kept in memory (no request API yet).
// TODO: load My Rides from the backend once there's an endpoint for the user's own rides.

export type RideRole = 'passenger' | 'driver';
export type RideStatus = 'searching' | 'open' | 'cancelled';

export type Ride = {
    id: string;
    role: RideRole;
    from: string;
    to: string;
    /** ISO date-time of departure. */
    departAt: string;
    /** Passenger: seats needed. Driver: seats offered. */
    seats: number;
    status: RideStatus;
    note?: string;
    /** Driver only. */
    vehicleId?: string;
    pricePerSeat?: number;
};

const store = createStore<Ride[]>([]);

export const useRides = () => useStore(store);

const newId = () => `ride-${Date.now()}-${Math.round(Math.random() * 1e4)}`;

export async function requestRide(input: { from: string; to: string; departAt: Date; seats: number; note?: string }) {
    const ride: Ride = {
        id: newId(),
        role: 'passenger',
        from: input.from.trim(),
        to: input.to.trim(),
        departAt: input.departAt.toISOString(),
        seats: input.seats,
        status: 'searching',
        note: input.note?.trim() || undefined,
    };
    store.set(list => [...list, ride]);
    return ride;
}

// --- POST /v1/rides/offer ------------------------------------------------------------------
export type OfferRideInput = {
    vehicleId: string;
    source: { id: number; name: string };
    destination: { id: number; name: string };
    departAt: Date;
    seats: number;
    pricePerSeat: number;
    notes?: string;
};

type OfferRideResponse = {
    id_ride: string;
    id_vehicle: string;
    departure_time: string;
    total_seats: number;
    available_seats: number;
    price_per_seat: string | number;
    notes: string | null;
    status: string;
};

export type OfferField = 'vehicle' | 'source' | 'destination' | 'departure' | 'seats' | 'price' | 'notes';

export class OfferError extends Error {
    constructor(message: string, public field?: OfferField, public sessionExpired = false) {
        super(message);
    }
}

const OFFER_FIELDS: Record<string, OfferField> = {
    id_vehicle: 'vehicle',
    id_source_station: 'source',
    id_destination_station: 'destination',
    departure_time: 'departure',
    total_seats: 'seats',
    price_per_seat: 'price',
    notes: 'notes',
};

/** Creates the ride on the server, then adds it to My Rides. Throws OfferError. */
export async function offerRide(input: OfferRideInput): Promise<Ride> {
    const payload = {
        id_vehicle: input.vehicleId, // string: snowflake IDs exceed JS safe-integer range
        id_source_station: input.source.id,
        id_destination_station: input.destination.id,
        departure_time: input.departAt.toISOString(),
        total_seats: input.seats,
        price_per_seat: Number(input.pricePerSeat.toFixed(2)),
        ...(input.notes ? { notes: input.notes } : {}),
    };

    let data: OfferRideResponse;
    try {
        data = await postJson<OfferRideResponse>('/v1/rides/offer', payload);
    } catch (e) {
        if (!(e instanceof ApiError)) throw new OfferError('Something went wrong. Please try again.');
        const msg = e.message;
        if (e.status === 401) {
            clearSession();
            throw new OfferError('Your session has expired. Please log in again.', undefined, true);
        }
        if (e.status === 404) {
            if (/vehicle/i.test(msg)) throw new OfferError('This vehicle isn’t linked to your account any more.', 'vehicle');
            if (/source/i.test(msg)) throw new OfferError('This pickup station is no longer available.', 'source');
            if (/destination/i.test(msg)) throw new OfferError('This drop-off station is no longer available.', 'destination');
        }
        if (e.status === 422) {
            if (/capacity/i.test(msg)) throw new OfferError('That’s more seats than this vehicle has.', 'seats');
            if (/departure/i.test(msg)) throw new OfferError('Departure time must be in the future.', 'departure');
            if (/vehicle must be active/i.test(msg)) throw new OfferError('This vehicle is inactive. Choose another one.', 'vehicle');
            if (/different/i.test(msg)) throw new OfferError('Pickup and drop-off must be different stations.', 'destination');
            const field = OFFER_FIELDS[msg.split(':')[0]];
            throw new OfferError(msg, field);
        }
        if (e.status === 409) throw new OfferError(msg);
        throw new OfferError(msg);
    }

    const ride: Ride = {
        id: data.id_ride,
        role: 'driver',
        from: input.source.name,
        to: input.destination.name,
        departAt: data.departure_time,
        seats: data.total_seats,
        status: 'open',
        vehicleId: data.id_vehicle,
        pricePerSeat: Number(data.price_per_seat) || undefined,
        note: data.notes ?? undefined,
    };
    store.set(list => [...list, ride]);
    return ride;
}

export function cancelRide(id: string) {
    store.set(list => list.map(r => (r.id === id ? { ...r, status: 'cancelled' } : r)));
}

export const isUpcoming = (r: Ride) => r.status !== 'cancelled' && new Date(r.departAt).getTime() >= Date.now();

export const sortByDeparture = (a: Ride, b: Ride) => a.departAt.localeCompare(b.departAt);
