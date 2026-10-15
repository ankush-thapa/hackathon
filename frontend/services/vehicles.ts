import { API_URL } from '../constants/Config';
import { MediaError, uploadImage } from './media';
import { authHeader, clearSession } from './session';
import { createStore, useStore } from './store/createStore';

// Mirrors the backend `vehicle` table (app/models/vehicle.py) and POST /v1/vehicles.
// TODO: load the list from GET /v1/vehicles and delete via the API once those endpoints exist;
// until then the list holds vehicles added in this session.

export const VEHICLE_TYPES = ['car', 'hatchback', 'sedan', 'suv', 'bike'] as const;
export type VehicleType = (typeof VEHICLE_TYPES)[number];
export const DEFAULT_VEHICLE_TYPE: VehicleType = 'car';

export const MIN_SEATS = 1;
export const MAX_SEATS = 8;
export const DEFAULT_SEATS = 4;
export const MAX_MAKE_LENGTH = 50;
export const MAX_MODEL_LENGTH = 50;
export const MAX_COLOUR_LENGTH = 30;

export type Vehicle = {
    id: string;
    photoUrl: string | null;
    make: string;
    model: string;
    registrationNumber: string;
    colour: string;
    seatCapacity: number;
    vehicleType: VehicleType;
    isDefault: boolean;
};

export type NewVehicle = {
    photo: { uri: string; mimeType?: string };
    make: string;
    model: string;
    registrationNumber: string;
    colour: string;
    seatCapacity: number;
    vehicleType?: VehicleType;
};

export type VehicleField = 'photo' | 'make' | 'model' | 'registrationNumber' | 'colour' | 'seatCapacity';

export class VehicleError extends Error {
    constructor(message: string, public field?: VehicleField, public sessionExpired = false) {
        super(message);
    }
}

const store = createStore<Vehicle[]>([]);

export const useVehicles = () => useStore(store);
export const getVehicles = () => store.get();

// --- Registration numbers ------------------------------------------------------------------
// Same rules as the backend (app/schemas/vehicle.py), compared without spaces/hyphens:
//   standard  MH 12 AB 1234, DL 3C AB 1234, KA 05 1234   ·   BH series  22 BH 1234 AA
const STANDARD_REG = /^[A-Z]{2}[0-9]{1,2}[A-Z]{0,4}[0-9]{4}$/;
const BH_REG = /^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$/;

export const normalizeRegistration = (value: string) => value.replace(/[\s-]/g, '').toUpperCase();
export const isValidRegistration = (value: string) => {
    const v = normalizeRegistration(value);
    return STANDARD_REG.test(v) || BH_REG.test(v);
};

// --- POST /v1/vehicles -----------------------------------------------------------------------
type VehicleResponse = {
    id: string;
    photo_url: string | null;
    make: string;
    model: string;
    registration_number: string;
    colour: string;
    seat_capacity: number;
    vehicle_type: VehicleType;
    is_default: boolean;
    status: string;
};

const API_FIELDS: Record<string, VehicleField> = {
    photo_url: 'photo',
    make: 'make',
    model: 'model',
    registration_number: 'registrationNumber',
    colour: 'colour',
    seat_capacity: 'seatCapacity',
};

const fromApi = (v: VehicleResponse): Vehicle => ({
    id: v.id,
    photoUrl: v.photo_url,
    make: v.make,
    model: v.model,
    registrationNumber: v.registration_number,
    colour: v.colour,
    seatCapacity: v.seat_capacity,
    vehicleType: v.vehicle_type,
    isDefault: v.is_default,
});

/** Uploads the photo, then creates the vehicle for the logged-in user. Throws VehicleError. */
export async function addVehicle(input: NewVehicle): Promise<Vehicle> {
    let photoUrl: string;
    try {
        photoUrl = await uploadImage(input.photo.uri, input.photo.mimeType);
    } catch (e) {
        throw new VehicleError(e instanceof MediaError ? e.message : 'Could not upload the photo.', 'photo');
    }

    const payload = {
        photo_url: photoUrl,
        make: input.make.trim(),
        model: input.model.trim(),
        registration_number: normalizeRegistration(input.registrationNumber),
        colour: input.colour.trim(),
        seat_capacity: input.seatCapacity,
        vehicle_type: input.vehicleType ?? DEFAULT_VEHICLE_TYPE,
    };

    let res: Response;
    try {
        res = await fetch(`${API_URL}/v1/vehicles`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...authHeader() },
            body: JSON.stringify(payload),
        });
    } catch {
        throw new VehicleError(`Could not reach the server at ${API_URL}`);
    }
    const data = await res.json().catch(() => ({}));

    if (res.status === 401) {
        clearSession();
        throw new VehicleError('Your session has expired. Please log in again.', undefined, true);
    }
    if (res.status === 409) throw new VehicleError('This vehicle is already registered.', 'registrationNumber');
    if (res.status === 422) {
        // { detail: [{ loc: ['body', 'registration_number'], msg: '...' }] }
        const first = Array.isArray(data?.detail) ? data.detail[0] : undefined;
        const field = API_FIELDS[first?.loc?.[first.loc.length - 1]];
        const msg = String(first?.msg ?? '').replace(/^Value error, /, '');
        throw new VehicleError(msg || 'Some details look invalid. Please check and try again.', field);
    }
    if (!res.ok) throw new VehicleError('Something went wrong. Please try again.');

    const vehicle = fromApi(data as VehicleResponse);
    store.set(list => [...(vehicle.isDefault ? list.map(v => ({ ...v, isDefault: false })) : list), vehicle]);
    return vehicle;
}

/** Local only for now (no delete API yet). */
export function removeVehicle(id: string) {
    store.set(list => {
        const rest = list.filter(v => v.id !== id);
        if (rest.length && !rest.some(v => v.isDefault)) rest[0] = { ...rest[0], isDefault: true };
        return rest;
    });
}

export const vehicleLabel = (v: Pick<Vehicle, 'make' | 'model'>) => `${v.make} ${v.model}`;
