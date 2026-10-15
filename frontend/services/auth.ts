import { API_URL } from '../constants/Config';
import { isEmail, normalizePhone } from './validation';

// The backend auth APIs aren't ready yet. While this is true, login/signup are faked locally
// so the UI can be built and tested. Flip to false (or set EXPO_PUBLIC_USE_MOCK_AUTH=false)
// once the backend endpoints exist, and adjust the paths/payloads below to match their contract.
const USE_MOCK_AUTH = process.env.EXPO_PUBLIC_USE_MOCK_AUTH !== 'false';

export type AuthUser = { id: number; email?: string; phone?: string };
export type AuthResult = { token: string; user: AuthUser };

export class AuthError extends Error {}

export type SignupInput = { email: string; phone: string; password: string };

async function post<T>(path: string, body: unknown): Promise<T> {
    let res: Response;
    try {
        res = await fetch(`${API_URL}${path}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
    } catch {
        throw new AuthError(`Could not reach the server at ${API_URL}`);
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        const detail = typeof data?.detail === 'string' ? data.detail : 'Something went wrong. Please try again.';
        throw new AuthError(detail);
    }
    return data as T;
}

// --- Mock implementation (in-memory, resets on reload) -------------------------------
const mockUsers: { id: number; email: string; phone: string; password: string }[] = [
    { id: 1, email: 'demo@carpool.app', phone: '+971500000000', password: 'password123' },
];
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

async function mockLogin(identifier: string, password: string): Promise<AuthResult> {
    await delay(600);
    const id = identifier.trim().toLowerCase();
    const phone = normalizePhone(id);
    const user = mockUsers.find(u => u.email === id || u.phone === phone);
    if (!user || user.password !== password) throw new AuthError('Incorrect email/phone or password');
    return { token: `mock-token-${user.id}`, user: { id: user.id, email: user.email, phone: user.phone } };
}

async function mockSignup(input: SignupInput): Promise<AuthResult> {
    await delay(600);
    if (mockUsers.some(u => u.email === input.email)) throw new AuthError('An account with this email already exists');
    if (mockUsers.some(u => u.phone === input.phone)) throw new AuthError('An account with this phone number already exists');
    const user = { id: mockUsers.length + 1, ...input };
    mockUsers.push(user);
    return { token: `mock-token-${user.id}`, user: { id: user.id, email: user.email, phone: user.phone } };
}
// ---------------------------------------------------------------------------------------

export function login(identifier: string, password: string): Promise<AuthResult> {
    if (USE_MOCK_AUTH) return mockLogin(identifier, password);
    const value = identifier.trim();
    const body = isEmail(value) ? { email: value.toLowerCase(), password } : { phone: normalizePhone(value), password };
    return post<AuthResult>('/auth/login', body); // TODO: confirm path & payload with backend
}

export function signup(input: SignupInput): Promise<AuthResult> {
    const payload = { ...input, email: input.email.trim().toLowerCase(), phone: normalizePhone(input.phone.trim()) };
    if (USE_MOCK_AUTH) return mockSignup(payload);
    return post<AuthResult>('/auth/signup', payload); // TODO: confirm path & payload with backend
}
