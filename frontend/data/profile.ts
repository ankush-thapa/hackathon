// Profile + vehicle types that mirror the backend models
// (app/models/user_profile.py and app/models/vehicle.py).
// Stored in memory for now; swap saveProfile for an API call once profile endpoints exist.

export const GENDERS = ['male', 'female', 'other', 'prefer_not_to_say'] as const;
export type Gender = (typeof GENDERS)[number];

export const VEHICLE_TYPES = ['hatchback', 'sedan', 'suv', 'bike'] as const;
export type VehicleType = (typeof VEHICLE_TYPES)[number];

// Column limits from the models, so the form validates the same way the DB will.
export const LIMITS = {
    fullName: 100,
    photoUrl: 500,
    about: 500,
    make: 50,
    model: 50,
    color: 30,
    registrationNumber: 20,
    minSeats: 1,
    maxSeats: 8,
} as const;

/** user_profile */
export type UserProfile = {
    fullName: string;
    photoUrl?: string;
    about?: string;
    dateOfBirth?: string; // YYYY-MM-DD
    gender?: Gender;
};

/** vehicle */
export type Vehicle = {
    make: string;
    model: string;
    color: string;
    registrationNumber: string; // stored without spaces, uppercase
    seatCapacity: number; // 1–8
    vehicleType: VehicleType;
    isDefault: boolean;
};

export type ProfileSetup = { profile: UserProfile; vehicle?: Vehicle };

/** Same normalisation as Vehicle._normalize_registration_number on the backend. */
export const normalizeRegistration = (value: string) => value.replace(/\s+/g, '').toUpperCase();

/** snake_case payloads matching the SQLAlchemy column names. */
export const toApi = ({ profile, vehicle }: ProfileSetup) => ({
    profile: {
        full_name: profile.fullName,
        photo_url: profile.photoUrl ?? null,
        about: profile.about ?? null,
        date_of_birth: profile.dateOfBirth ?? null,
        gender: profile.gender ?? null,
    },
    vehicle: vehicle
        ? {
              make: vehicle.make,
              model: vehicle.model,
              color: vehicle.color,
              registration_number: vehicle.registrationNumber,
              seat_capacity: vehicle.seatCapacity,
              vehicle_type: vehicle.vehicleType,
              is_default: vehicle.isDefault,
          }
        : null,
});

let current: ProfileSetup | null = null;

export const getProfile = () => current;

export const saveProfile = async (data: ProfileSetup) => {
    // TODO: PUT /v1/me/profile and POST /v1/me/vehicles with toApi(data) once the endpoints exist.
    await new Promise(r => setTimeout(r, 400));
    current = data;
    return data;
};
