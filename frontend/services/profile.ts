import { Platform } from 'react-native';
import { Profile, ProfileInput } from '../data/profile';
import { ApiError, postJson, request } from './api';
import { USE_MOCK_AUTH } from './auth';
import { getSession } from './session';

export { ApiError as ProfileError };

const requireSession = () => {
    const s = getSession();
    if (!s) throw new ApiError('Your session has expired. Please log in again.', 401);
    return s;
};

/** POST /v1/auth/profile: creates the profile, or fully replaces an existing one. */
export async function saveProfile(input: ProfileInput): Promise<Profile> {
    const { userId } = requireSession();
    if (USE_MOCK_AUTH) {
        await new Promise(r => setTimeout(r, 400));
        return { userId, ...input };
    }
    // userId stays a string: Pydantic coerces it to int server-side, and a JS number would lose precision.
    return postJson<Profile>('/v1/auth/profile', { userId, ...input });
}

type MediaUploadResponse = { url: string; fileName: string; contentType: string; size: number };

export const MAX_PHOTO_BYTES = 5 * 1024 * 1024; // matches the backend's 5 MB limit
export const PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

/** POST /v1/media/upload (multipart). Returns the public URL to store as photoUrl. */
export async function uploadPhoto(asset: { uri: string; mimeType?: string | null; fileName?: string | null }): Promise<string> {
    requireSession();
    if (USE_MOCK_AUTH) return asset.uri; // local preview only
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
