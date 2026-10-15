import { ApiError, postJson, request } from './api';
import { Session, getSession, setSession } from './session';
import { isEmail, normalizePhone } from './validation';

// Talks to the FastAPI auth routes (app/api/auth.py). Set EXPO_PUBLIC_USE_MOCK_AUTH=true to
// fake login/signup locally when the backend isn't running.
export const USE_MOCK_AUTH = process.env.EXPO_PUBLIC_USE_MOCK_AUTH === 'true';

export { ApiError as AuthError };

export type SignupInput = { email: string; phone: string; password: string };

type RegisterResponse = { userId: string; email: string; phone: string };
type LoginResponse = { accessToken: string; tokenType: string; expiresIn: number; userId: string; sessionId: string };

const startSession = (r: LoginResponse, extra: Partial<Session> = {}): Session => {
    const session: Session = { userId: r.userId, accessToken: r.accessToken, expiresAt: Date.now() + r.expiresIn * 1000, ...extra };
    setSession(session);
    return session;
};

// --- Mock implementation (in-memory, resets on reload) -------------------------------
const mockUsers: { id: string; email: string; phone: string; password: string }[] = [
    { id: '1', email: 'demo@hopr.app', phone: '+971500000000', password: 'password123' },
];
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

async function mockLogin(identifier: string, password: string): Promise<Session> {
    await delay(600);
    const id = identifier.trim().toLowerCase();
    const user = mockUsers.find(u => u.email === id || u.phone === normalizePhone(id));
    if (!user || user.password !== password) throw new ApiError('Incorrect email/phone or password', 401);
    return startSession({ accessToken: `mock-${user.id}`, tokenType: 'Bearer', expiresIn: 86400, userId: user.id, sessionId: '1' }, { email: user.email, phone: user.phone });
}

async function mockSignup(input: SignupInput): Promise<Session> {
    await delay(600);
    if (mockUsers.some(u => u.email === input.email)) throw new ApiError('Email already registered', 409);
    if (mockUsers.some(u => u.phone === input.phone)) throw new ApiError('Phone already registered', 409);
    mockUsers.push({ id: String(mockUsers.length + 1), ...input });
    return mockLogin(input.email, input.password);
}
// ---------------------------------------------------------------------------------------

/** POST /v1/auth/login with exactly one of email or phone. */
export async function login(identifier: string, password: string): Promise<Session> {
    if (USE_MOCK_AUTH) return mockLogin(identifier, password);
    const value = identifier.trim();
    const body = isEmail(value) ? { email: value.toLowerCase(), password } : { phone: normalizePhone(value), password };
    try {
        const r = await postJson<LoginResponse>('/v1/auth/login', body);
        return startSession(r, 'email' in body ? { email: body.email } : { phone: body.phone });
    } catch (e) {
        if (e instanceof ApiError && e.status === 401) throw new ApiError('Incorrect email/phone or password', 401);
        if (e instanceof ApiError && e.status === 403) throw new ApiError('This account has been blocked', 403);
        throw e;
    }
}

/** POST /v1/auth/register, then log straight in so the next screen has a session. */
export async function signup(input: SignupInput): Promise<Session> {
    const payload = { ...input, email: input.email.trim().toLowerCase(), phone: normalizePhone(input.phone.trim()) };
    if (USE_MOCK_AUTH) return mockSignup(payload);
    try {
        await postJson<RegisterResponse>('/v1/auth/register', payload);
    } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
            throw new ApiError(e.message.startsWith('Email') ? 'An account with this email already exists' : 'An account with this phone number already exists', 409);
        }
        throw e;
    }
    return login(payload.email, payload.password);
}

/** POST /v1/auth/logout. Clears the local session even if the call fails. */
export async function logout() {
    try {
        if (!USE_MOCK_AUTH && getSession()) await request('/v1/auth/logout', { method: 'POST' });
    } finally {
        setSession(null);
    }
}
