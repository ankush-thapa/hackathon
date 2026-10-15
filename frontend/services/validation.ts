const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
// Login: optional leading +, then 7–15 digits. Spaces, dashes and brackets are ignored.
const PHONE_RE = /^\+?\d{7,15}$/;
// Must match the backend's E.164 rule (+, country code, 8–15 digits in total).
const E164_RE = /^\+[1-9]\d{7,14}$/;

export const MIN_PASSWORD_LENGTH = 8;
export const MAX_PASSWORD_LENGTH = 50;
export const MAX_EMAIL_LENGTH = 254;

export const normalizePhone = (value: string) => value.replace(/[\s\-()]/g, '');

export const isEmail = (value: string) => EMAIL_RE.test(value.trim());
export const isPhone = (value: string) => PHONE_RE.test(normalizePhone(value.trim()));

export function validateIdentifier(value: string): string | undefined {
    const v = value.trim();
    if (!v) return 'Enter your email or phone number';
    if (v.includes('@')) return isEmail(v) ? undefined : 'Enter a valid email';
    const phone = normalizePhone(v);
    if (!/^\+?\d+$/.test(phone)) return 'Enter a valid email or phone number';
    if (!phone.startsWith('+')) return 'Add your country code to the phone number, e.g. +971';
    if (!E164_RE.test(phone)) return 'Enter a valid phone number with country code';
}

export function validateEmail(value: string): string | undefined {
    if (!value.trim()) return 'Enter your email';
    if (!isEmail(value)) return 'Enter a valid email';
    if (value.trim().length > MAX_EMAIL_LENGTH) return 'Email is too long';
}

export function validatePhone(value: string): string | undefined {
    if (!value.trim()) return 'Enter your phone number';
    const phone = normalizePhone(value.trim());
    if (!phone.startsWith('+')) return 'Start with + and your country code, e.g. +971';
    if (!E164_RE.test(phone)) return 'Enter a valid phone number with country code';
}

export function validatePassword(value: string): string | undefined {
    if (!value) return 'Enter a password';
    if (value.length < MIN_PASSWORD_LENGTH) return `Use at least ${MIN_PASSWORD_LENGTH} characters`;
    if (value.length > MAX_PASSWORD_LENGTH) return `Use at most ${MAX_PASSWORD_LENGTH} characters`;
    if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) return 'Include at least one letter and one number';
}

export function validateConfirmPassword(password: string, confirm: string): string | undefined {
    if (!confirm) return 'Confirm your password';
    if (password !== confirm) return "Passwords don't match";
}
