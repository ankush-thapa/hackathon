import { ApiError, postJson, request } from './api';
import { Session, getSession, setSession } from './session';
import { isEmail, normalizePhone } from './validation';
import { Session, setSession } from './session';

export type AuthField = 'email' | 'phone' | 'password';

export class AuthError extends Error {
    /** Set when the server's error belongs to one specific form field. */
    field?: AuthField;
    constructor(message: string, field?: AuthField) {
        super(message);
        this.field = field;
    }
}

const GENERIC_ERROR = 'Something went wrong. Please try again.';
const FIELD_LABELS: Record<AuthField, string> = { email: 'Email', phone: 'Phone number', password: 'Password' };

async function post<T>(path: string, body: unknown, toError: (status: number, data: any) => AuthError): Promise<T> {
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
    if (!res.ok) throw toError(res.status, data);
    return data as T;
}

/** 422 bodies look like { detail: [{ loc: ['body', 'phone'], msg: '...' }] }. */
function validationError(data: any, fallback: string): AuthError {
    const first = Array.isArray(data?.detail) ? data.detail[0] : undefined;
    const field = first?.loc?.[first.loc.length - 1] as AuthField | undefined;
    if (field && field in FIELD_LABELS) {
        const msg = String(first.msg ?? '').replace(/^Value error, /, '');
        return new AuthError(`${FIELD_LABELS[field]}: ${msg || 'invalid value'}`, field);
    }
    return new AuthError(fallback);
}

// --- POST /v1/auth/register -------------------------------------------------------------
export type SignupInput = { email: string; phone: string; password: string };
export type RegisterResponse = { userId: string; email: string; phone: string };

export function signup(input: SignupInput): Promise<RegisterResponse> {
    const payload = {
        email: input.email.trim().toLowerCase(),
        phone: normalizePhone(input.phone.trim()),
        password: input.password,
    };
    return post<RegisterResponse>('/v1/auth/register', payload, (status, data) => {
        // 409: "email already registered" / "phone already registered"
        if (status === 409 && typeof data?.detail === 'string') {
            const field = (['email', 'phone'] as const).find(f => data.detail.startsWith(f));
            if (field) return new AuthError(`This ${field === 'email' ? 'email' : 'phone number'} is already registered`, field);
            return new AuthError(data.detail);
        }
        if (status === 422) return validationError(data, 'Some details look invalid. Please check and try again.');
        return new AuthError(GENERIC_ERROR);
    });
}

// --- POST /v1/auth/login ----------------------------------------------------------------
type LoginResponse = { accessToken: string; tokenType?: string; expiresIn: number; userId: string };

/** Logs in with an email or phone number and stores the session on success. */
export async function login(identifier: string, password: string): Promise<Session> {
    const value = identifier.trim();
    const body = isEmail(value) ? { email: value.toLowerCase(), password } : { phone: normalizePhone(value), password };

    const data = await post<LoginResponse>('/v1/auth/login', body, status => {
        if (status === 401) return new AuthError('Incorrect email/phone or password');
        if (status === 403) return new AuthError('This account is blocked. Please contact support.');
        if (status === 422) return new AuthError('Check your email or phone number and try again');
        return new AuthError(GENERIC_ERROR);
    });

    const session: Session = {
        accessToken: data.accessToken,
        tokenType: data.tokenType ?? 'Bearer',
        userId: data.userId,
        expiresAt: Date.now() + data.expiresIn * 1000,
        ...('email' in body ? { email: body.email } : { phone: body.phone }),
    };
    setSession(session);
    return session;
}
