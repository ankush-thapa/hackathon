import { Platform } from 'react-native';
import { Profile, ProfileInput } from '../data/profile';
import { ApiError, postJson, request } from './api';
import { getSession } from './session';
import { createStore, useStore } from './store/createStore';

export { ApiError as ProfileError };

// The signed-in user's profile, shared across screens (e.g. AppHeader shows fullName).
// There's no GET profile endpoint yet, so it's filled from the last successful save.
const EMPTY: ProfileInput = { fullName: '', photoUrl: null, about: null, dateOfBirth: null, gender: null };
const store = createStore<ProfileInput>(EMPTY);

export const useProfile = () => useStore(store);
export const resetProfile = () => store.set(EMPTY);

const requireSession = () => {
    const s = getSession();
    if (!s) throw new ApiError('Your session has expired. Please log in again.', 401);
    return s;
};

/** POST /v1/auth/profile: creates the profile, or fully replaces an existing one. */
export async function saveProfile(input: ProfileInput): Promise<Profile> {
    const { userId } = requireSession();
    // userId stays a string: Pydantic coerces it to int server-side, and a JS number would lose precision.
    const saved = await postJson<Profile>('/v1/auth/profile', { userId, ...input });
    const { userId: _id, ...rest } = saved;
    store.set(rest);
    return saved;
}

type MediaUploadResponse = { url: string; fileName: string; contentType: string; size: number };

export const MAX_PHOTO_BYTES = 5 * 1024 * 1024; // matches the backend's 5 MB limit
export const PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

/** POST /v1/media/upload (multipart). Returns the public URL to store as photoUrl. */
export async function uploadPhoto(asset: { uri: string; mimeType?: string | null; fileName?: string | null }): Promise<string> {
    requireSession();
    const type = asset.mimeType ?? 'image/jpeg';
    const name = asset.fileName ?? `photo.${type.split('/')[1] ?? 'jpg'}`;
    const form = new FormData();
    if (Platform.OS === 'web') {
        const blob = await (await fetch(asset.uri)).blob();
        form.append('file', blob, name);
    } else {
        form.append('file', { uri: asset.uri, name, type } as any);
    }
    const res = await request<MediaUploadResponse>('/v1/media/upload', { method: 'POST', body: form });
    return res.url;
}


export async function fetchMyProfile(): Promise<Profile> {
    const profile = await request<Profile>('/v1/auth/profile');
    const { userId: _id, ...rest } = profile;
    store.set(rest);
    return profile;
}
