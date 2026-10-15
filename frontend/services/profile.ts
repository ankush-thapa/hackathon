import { createStore, useStore } from './store/createStore';

// Mirrors the backend `user_profile` table (app/models/user_profile.py). There's no profile
// API yet, so edits are kept in memory. TODO: GET/PUT the profile when the API exists.

export const GENDERS = [
    { value: 'male', label: 'Male' },
    { value: 'female', label: 'Female' },
    { value: 'other', label: 'Other' },
    { value: 'prefer_not_to_say', label: 'Prefer not to say' },
] as const;
export type Gender = (typeof GENDERS)[number]['value'];

export type Profile = {
    fullName: string;
    about: string;
    dateOfBirth: string; // YYYY-MM-DD or ''
    gender: Gender | null;
};

export const MAX_NAME_LENGTH = 100;
export const MAX_ABOUT_LENGTH = 500;

const store = createStore<Profile>({ fullName: '', about: '', dateOfBirth: '', gender: null });

export const useProfile = () => useStore(store);

export async function saveProfile(profile: Profile) {
    store.set({ ...profile, fullName: profile.fullName.trim(), about: profile.about.trim() });
}

export function resetProfile() {
    store.set({ fullName: '', about: '', dateOfBirth: '', gender: null });
}
