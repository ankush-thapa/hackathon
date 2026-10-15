import { postJson, request } from './api';
import { clearSession } from './session';
import { resetNotifications } from './notifications';
import { resetProfile } from './profile';

export const updateContacts = (input: { current_password: string; email?: string; phone?: string }) =>
    request<{ userId: string; email: string | null; phone: string | null; status: string }>('/v1/auth/account',
        { method: 'PATCH', body: JSON.stringify(input) });

export async function changePassword(current_password: string, new_password: string) {
    await postJson('/v1/auth/change-password', { current_password, new_password });
    clearSession(); resetProfile(); resetNotifications();
}

export async function deleteAccount(current_password: string) {
    await request<void>('/v1/auth/account', { method: 'DELETE', body: JSON.stringify({ current_password }) });
    clearSession(); resetProfile(); resetNotifications();
}
