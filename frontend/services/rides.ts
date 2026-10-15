import { createStore, useStore } from './store/createStore';

// No rides API yet: requests and offers made in the app are kept in memory.
// TODO: replace with the backend's ride endpoints when they exist.

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

export async function offerRide(input: {
    from: string; to: string; departAt: Date; seats: number; vehicleId: string; pricePerSeat?: number; note?: string;
}) {
    const ride: Ride = {
        id: newId(),
        role: 'driver',
        from: input.from.trim(),
        to: input.to.trim(),
        departAt: input.departAt.toISOString(),
        seats: input.seats,
        status: 'open',
        vehicleId: input.vehicleId,
        pricePerSeat: input.pricePerSeat,
        note: input.note?.trim() || undefined,
    };
    store.set(list => [...list, ride]);
    return ride;
}

export function cancelRide(id: string) {
    store.set(list => list.map(r => (r.id === id ? { ...r, status: 'cancelled' } : r)));
}

export const isUpcoming = (r: Ride) => r.status !== 'cancelled' && new Date(r.departAt).getTime() >= Date.now();

export const sortByDeparture = (a: Ride, b: Ride) => a.departAt.localeCompare(b.departAt);
