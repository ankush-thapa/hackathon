// Mirrors the backend profile contract:
// app/models/user_profile.py (columns) and app/schemas/profile.py (SaveProfileRequest / ProfileResponse).

export const GENDERS = ['male', 'female', 'other', 'prefer_not_to_say'] as const;
export type Gender = (typeof GENDERS)[number];

// Column / schema limits, so the form validates the same way the API will.
export const LIMITS = { fullName: 100, photoUrl: 500, about: 500 } as const;

export type Profile = {
    userId: string;
    fullName: string;
    photoUrl: string | null;
    about: string | null;
    dateOfBirth: string | null; // YYYY-MM-DD
    gender: Gender | null;
};

export type ProfileInput = Omit<Profile, 'userId'>;
