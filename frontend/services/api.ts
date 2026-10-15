import { API_URL } from '../constants/Config';
import { accessToken, getSession, refreshSession } from './session';

export class ApiError extends Error {
    constructor(message: string, public status?: number) {
        super(message);
    }
}

// FastAPI returns `detail` as a string for HTTPException, or a list of field errors for 422s.
function readDetail(data: any): string {
    const d = data?.detail;
    if (d && typeof d.message === 'string') return d.message;
    if (typeof d === 'string') return d.charAt(0).toUpperCase() + d.slice(1);
    if (Array.isArray(d) && d.length) {
        const first = d[0];
        const field = Array.isArray(first?.loc) ? first.loc[first.loc.length - 1] : undefined;
        const msg = String(first?.msg ?? 'Invalid value').replace(/^Value error, /, '');
        return field && field !== 'body' ? `${field}: ${msg}` : msg;
    }
    return 'Something went wrong. Please try again.';
}

/** fetch wrapper: adds the session token, parses JSON, and turns error responses into ApiError. */
export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const token = await accessToken();
    const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (init.body && !(init.body instanceof FormData)) headers['Content-Type'] = 'application/json';

    let res: Response;
    try {
        res = await fetch(`${API_URL}${path}`, { ...init, headers });
    } catch {
        throw new ApiError(`Could not reach the server at ${API_URL}`);
    }
    let data = res.status === 204 ? {} : await res.json().catch(() => ({}));
    if (res.status === 401 && data?.detail?.code === 'token_expired' && getSession()?.refreshToken) {
        // Another request may already have rotated the token while this request was in flight.
        const current = getSession();
        const next = current?.accessToken !== token ? current : await refreshSession();
        if (next) {
            headers.Authorization = `Bearer ${next.accessToken}`;
            res = await fetch(`${API_URL}${path}`, { ...init, headers });
            data = res.status === 204 ? {} : await res.json().catch(() => ({}));
        }
    }
    if (!res.ok) throw new ApiError(readDetail(data), res.status);
    return data as T;
}

export const postJson = <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) });
