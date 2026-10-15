import { Platform } from 'react-native';
import { request } from './api';
import { API_URL } from '../constants/Config';
import { accessToken } from './session';

export type DocType = 'driving_license' | 'id_proof' | 'vehicle_rc' | 'insurance';
export type Document = { id_user_doc: string; id_user: string; doc_type: DocType; doc_number: string;
    is_active: boolean; created_at: string; updated_at: string; download_url: string };
export const listDocuments = (cursor?: string) => request<{ items: Document[]; next_cursor: string | null }>(
    `/v1/me/documents${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''}`);
export const deactivateDocument = (id: string) => request<void>(`/v1/me/documents/${id}`, { method: 'DELETE' });
export async function uploadDocument(input: { doc_type: DocType; doc_number: string; uri: string; name: string; mimeType: string }) {
    const data = new FormData();
    data.append('doc_type', input.doc_type); data.append('doc_number', input.doc_number);
    if (Platform.OS === 'web') data.append('file', await (await fetch(input.uri)).blob(), input.name);
    else data.append('file', { uri: input.uri, name: input.name, type: input.mimeType } as unknown as Blob);
    return request<Document>('/v1/me/documents', { method: 'POST', body: data });
}
// download_url requires Authorization, so clients must fetch it with a token rather than open it as a public link.
export async function downloadDocument(doc: Document): Promise<Blob> {
    const res = await fetch(`${API_URL}${doc.download_url}`, { headers: { Authorization: `Bearer ${await accessToken()}` } });
    if (!res.ok) throw new Error('Could not download the document');
    return res.blob();
}
