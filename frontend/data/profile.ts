// In-memory profile store. Swap for an API call (e.g. PUT /me/profile) once the backend has auth.

export type CommuteRole = 'rider' | 'driver' | 'both';

export type Vehicle = {
    makeModel: string;
    color: string;
    plate: string;
    seats: number;
};

export type Profile = {
    fullName: string;
    phone: string;
    gender?: 'male' | 'female' | 'other';
    company: string;
    role: CommuteRole;
    homeArea: string;
    workArea: string;
    leaveHomeAt: string; // "08:30"
    leaveWorkAt: string; // "18:00"
    vehicle?: Vehicle;
};

let current: Profile | null = null;

export const getProfile = () => current;

export const saveProfile = async (profile: Profile) => {
    current = profile;
    return profile;
};
