// Holds the access token from POST /v1/auth/login.
// On web it's also kept in localStorage so a page refresh stays logged in.
// TODO: on iOS/Android, persist with expo-secure-store (not installed yet) — today a native
// session lasts until the app is closed.

export type Session = {
    accessToken: string;
    tokenType: string;
    userId: string;
    expiresAt: number;
    /** From the login response; false sends the user to /profile-setup. */
    isProfileCompleted: boolean;
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
    if (current && Date.now() >= current.expiresAt) {
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

/** Where a signed-in user should land. */
export const homeRoute = (s: Session | null = getSession()) =>
    // `=== false` so sessions stored before this flag existed aren't sent to setup.
    s && s.isProfileCompleted === false ? '/profile-setup' : '/dashboard';

export function clearSession() {
    current = null;
    try { storage()?.removeItem(KEY); } catch { /* storage unavailable */ }
}

/** Header for authenticated API calls, e.g. fetch(url, { headers: authHeader() }). */
export function authHeader(): Record<string, string> {
    const s = getSession();
    return s ? { Authorization: `${s.tokenType} ${s.accessToken}` } : {};
}
