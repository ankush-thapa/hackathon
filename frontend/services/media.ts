import { Platform } from 'react-native';
import { API_URL } from '../constants/Config';

export class MediaError extends Error {}

export type MediaUploadResponse = { url: string; fileName: string; contentType: string; size: number };

/**
 * POST /v1/media/upload — sends a local image (from expo-image-picker) and returns its public URL.
 * The backend accepts JPEG, PNG or WebP up to 5 MB.
 */
export async function uploadImage(uri: string, mimeType = 'image/jpeg'): Promise<string> {
    const form = new FormData();
    if (Platform.OS === 'web') {
        // On web the picker returns a blob:/data: URI; turn it into a real file part.
        const blob = await (await fetch(uri)).blob();
        form.append('file', blob, 'photo');
    } else {
        // React Native's FormData takes { uri, name, type } for files.
        form.append('file', { uri, name: 'photo', type: mimeType } as unknown as Blob);
    }

    let res: Response;
    try {
        res = await fetch(`${API_URL}/v1/media/upload`, { method: 'POST', body: form });
    } catch {
        throw new MediaError(`Could not reach the server at ${API_URL}`);
    }
    if (res.status === 413) throw new MediaError('Photo is too large. Please choose one under 5 MB.');
    if (res.status === 415) throw new MediaError('Photo must be a JPEG, PNG or WebP image.');
    if (!res.ok) throw new MediaError('Could not upload the photo. Please try again.');
    const data = (await res.json()) as MediaUploadResponse;
    return data.url;
}
