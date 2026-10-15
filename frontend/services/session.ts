import { API_URL } from '../constants/Config';
// Holds the access token from POST /v1/auth/login.
// On web it's also kept in localStorage so a page refresh stays logged in.
// TODO: on iOS/Android, persist with expo-secure-store (not installed yet) — today a native
// session lasts until the app is closed.

export type Session = {
    accessToken: string;
    refreshToken?: string;
    tokenType: string;
    userId: string;
    expiresAt: number;
    /** The email or phone the user logged in with (the login API doesn't return the profile). */
    email?: string;
    phone?: string;
};

const KEY = 'carpool.session';
let current: Session | null = null;

const storage = (): Storage | null => {
    try {
        return typeof window !== 'undefined' && window.localStorage ? window.localStorage : null;
    } catch {
        return null;
    }
};

export function setSession(session: Session) {
    current = session;
    try { storage()?.setItem(KEY, JSON.stringify(session)); } catch { /* storage unavailable */ }
}

export function getSession(): Session | null {
    if (!current) {
        try {
            const raw = storage()?.getItem(KEY);
            if (raw) current = JSON.parse(raw) as Session;
        } catch { /* ignore corrupt or unavailable storage */ }
    }
    if (current && Date.now() >= current.expiresAt && !current.refreshToken) {
        clearSession();
        return null;
    }
    return current;
}

/** Patch the stored session, e.g. after the profile is saved. */
export function updateSession(patch: Partial<Session>) {
    const s = getSession();
    if (s) setSession({ ...s, ...patch });
}

export function clearSession() {
    current = null;
    try { storage()?.removeItem(KEY); } catch { /* storage unavailable */ }
}

/** Header for authenticated API calls, e.g. fetch(url, { headers: authHeader() }). */
export function authHeader(): Record<string, string> {
    const s = getSession();
    return s ? { Authorization: `${s.tokenType} ${s.accessToken}` } : {};
}


let refreshing: Promise<Session | null> | null = null;
export async function refreshSession(): Promise<Session | null> {
    if (refreshing) return refreshing;
    const session = getSession();
    if (!session?.refreshToken) return null;
    refreshing = (async () => {
        const res = await fetch(`${API_URL}/v1/auth/refresh`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refreshToken: session.refreshToken }),
        });
        if (!res.ok) {
            if (res.status === 401 && getSession()?.refreshToken === session.refreshToken) clearSession();
            throw new Error('Could not refresh your session. Please try again.');
        }
        const data = await res.json();
        if (getSession()?.refreshToken !== session.refreshToken) return getSession();
        const next = { ...session, accessToken: data.accessToken, refreshToken: data.refreshToken,
            expiresAt: Date.now() + data.expiresIn * 1000 };
        setSession(next);
        return next;
    })();
    try { return await refreshing; } finally { refreshing = null; }
}

export async function accessToken(): Promise<string | undefined> {
    const session = getSession();
    if (session && Date.now() >= session.expiresAt - 15000 && session.refreshToken) {
        return (await refreshSession())?.accessToken;
    }
    return session?.accessToken;
}

export async function logoutSession() {
    const session = getSession();
    try {
        if (session) {
            const res = await fetch(`${API_URL}/v1/auth/logout`, {
                method: 'POST', headers: { Authorization: `Bearer ${session.accessToken}` },
            });
            if (!res.ok && res.status !== 401) throw new Error('Could not log out. Please try again.');
        }
    } finally { clearSession(); }
}
