import { API_URL } from '../constants/Config';
import { isEmail, normalizePhone } from './validation';

// Sign-up talks to the real backend (POST /v1/auth/register).
// Login is still faked locally because the backend has no login endpoint yet. When it lands,
// set USE_MOCK_LOGIN to false (or EXPO_PUBLIC_USE_MOCK_LOGIN=false) and confirm the path/payload.
const USE_MOCK_LOGIN = process.env.EXPO_PUBLIC_USE_MOCK_LOGIN !== 'false';

export type AuthUser = { id: string; email?: string; phone?: string };
export type AuthResult = { token: string; user: AuthUser };

export type SignupField = 'email' | 'phone' | 'password';

export class AuthError extends Error {
    /** Set when the server's error belongs to one specific form field. */
    field?: SignupField;
    constructor(message: string, field?: SignupField) {
        super(message);
        this.field = field;
    }
}

const GENERIC_ERROR = 'Something went wrong. Please try again.';
const FIELD_LABELS: Record<SignupField, string> = { email: 'Email', phone: 'Phone number', password: 'Password' };

/** Turns a FastAPI error body into a message, and a field when it belongs to one. */
function toAuthError(status: number, data: any): AuthError {
    const detail = data?.detail;

    // 409: "email already registered" / "phone already registered"
    if (status === 409 && typeof detail === 'string') {
        const field = (['email', 'phone'] as const).find(f => detail.startsWith(f));
        if (field) return new AuthError(`This ${field === 'email' ? 'email' : 'phone number'} is already registered`, field);
        return new AuthError(detail);
    }

    // 422: [{ loc: ['body', 'phone'], msg: '...' }, ...] — show the first problem on its field.
    if (status === 422 && Array.isArray(detail) && detail.length) {
        const first = detail[0];
        const field = first?.loc?.[first.loc.length - 1] as SignupField | undefined;
        if (field && field in FIELD_LABELS) {
            const msg = String(first.msg ?? '').replace(/^Value error, /, '');
            return new AuthError(`${FIELD_LABELS[field]}: ${msg || 'invalid value'}`, field);
        }
        return new AuthError('Some details look invalid. Please check and try again.');
    }

    if (typeof detail === 'string') return new AuthError(detail);
    return new AuthError(GENERIC_ERROR);
}

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
    if (!res.ok) throw toAuthError(res.status, data);
    return data as T;
}

// --- Sign-up (real API) ----------------------------------------------------------------
export type SignupInput = { email: string; phone: string; password: string };
export type RegisterResponse = { userId: string; email: string; phone: string };

export async function signup(input: SignupInput): Promise<RegisterResponse> {
    const payload = {
        email: input.email.trim().toLowerCase(),
        phone: normalizePhone(input.phone.trim()),
        password: input.password,
    };
    const created = await post<RegisterResponse>('/v1/auth/register', payload);
    // Lets the new account log in through the mock login during the demo. Remove with the mock.
    if (USE_MOCK_LOGIN) mockUsers.push({ id: created.userId, email: created.email, phone: created.phone, password: input.password });
    return created;
}

// --- Login (mock until the backend endpoint exists; in-memory, resets on reload) ----------
const mockUsers: { id: string; email: string; phone: string; password: string }[] = [
    { id: '1', email: 'demo@carpool.app', phone: '+971500000000', password: 'password123' },
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

export function login(identifier: string, password: string): Promise<AuthResult> {
    if (USE_MOCK_LOGIN) return mockLogin(identifier, password);
    const value = identifier.trim();
    const body = isEmail(value) ? { email: value.toLowerCase(), password } : { phone: normalizePhone(value), password };
    return post<AuthResult>('/v1/auth/login', body); // TODO: confirm path & payload with backend
}
