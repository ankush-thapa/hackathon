import { createStore, useStore } from './store/createStore';

// Mirrors the backend `vehicle` table (app/models/vehicle.py). There's no vehicle API yet,
// so vehicles live in memory for now. TODO: swap for GET/POST /v1/vehicles when available.

export const VEHICLE_TYPES = ['hatchback', 'sedan', 'suv', 'bike'] as const;
export type VehicleType = (typeof VEHICLE_TYPES)[number];

export const MIN_SEATS = 1;
export const MAX_SEATS = 8;

export type Vehicle = {
    id: string;
    make: string;
    model: string;
    color: string;
    registrationNumber: string;
    seatCapacity: number;
    vehicleType: VehicleType;
    isDefault: boolean;
};

export type NewVehicle = Omit<Vehicle, 'id'>;

const store = createStore<Vehicle[]>([]);

export const useVehicles = () => useStore(store);
export const getVehicles = () => store.get();

/** Same normalisation as the backend: no spaces, upper case. */
export const normalizeRegistration = (value: string) => value.split(/\s+/).join('').toUpperCase();

export class VehicleError extends Error {
    constructor(message: string, public field?: keyof NewVehicle) {
        super(message);
    }
}

export async function addVehicle(input: NewVehicle): Promise<Vehicle> {
    const registrationNumber = normalizeRegistration(input.registrationNumber);
    if (store.get().some(v => v.registrationNumber === registrationNumber)) {
        throw new VehicleError('This registration number is already added', 'registrationNumber');
    }
    const first = store.get().length === 0;
    const vehicle: Vehicle = {
        ...input,
        make: input.make.trim(),
        model: input.model.trim(),
        color: input.color.trim(),
        registrationNumber,
        id: `veh-${Date.now()}`,
        isDefault: input.isDefault || first, // the first vehicle is always the default
    };
    store.set(list => [...(vehicle.isDefault ? list.map(v => ({ ...v, isDefault: false })) : list), vehicle]);
    return vehicle;
}

export function setDefaultVehicle(id: string) {
    store.set(list => list.map(v => ({ ...v, isDefault: v.id === id })));
}

export function removeVehicle(id: string) {
    store.set(list => {
        const rest = list.filter(v => v.id !== id);
        if (rest.length && !rest.some(v => v.isDefault)) rest[0] = { ...rest[0], isDefault: true };
        return rest;
    });
}

export const vehicleLabel = (v: Pick<Vehicle, 'make' | 'model'>) => `${v.make} ${v.model}`;
