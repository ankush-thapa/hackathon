import { request } from './api';

// GET /v1/users/{id}/profile — another user's public profile. Visible for yourself, anyone offering a
// bookable ride, and anyone you share a ride with; otherwise 404. Never includes phone, email or exact DOB.

export type PublicProfile = {
    userId: string;
    fullName: string | null;
    photoUrl: string | null;
    about: string | null;
    gender: string | null;
    age: number | null;
    memberSince: string; // ISO, UTC
    ridesDriven: number;
    ridesTaken: number;
    vehicle: { make: string; model: string; color: string; vehicleType: string } | null;
};

export const fetchPublicProfile = (userId: string) => request<PublicProfile>(`/v1/users/${userId}/profile`);

/** Route to a user's profile page. `name`/`photo`/`role` let the page show something instantly while it loads. */
export const profileHref = (userId: string, hint?: { name?: string | null; photo?: string | null; role?: string }) => ({
    pathname: '/users/[id]' as const,
    params: {
        id: userId,
        ...(hint?.name ? { name: hint.name } : {}),
        ...(hint?.photo ? { photo: hint.photo } : {}),
        ...(hint?.role ? { role: hint.role } : {}),
    },
});
