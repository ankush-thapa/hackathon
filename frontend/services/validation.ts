const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
// E.164 (what the backend requires): +, country code, 8–15 digits total. Spaces, dashes and brackets are ignored.
const PHONE_RE = /^\+[1-9]\d{7,14}$/;

export const MIN_PASSWORD_LENGTH = 8;
export const MAX_PASSWORD_LENGTH = 50;

export const normalizePhone = (value: string) => value.replace(/[\s\-()]/g, '');

export const isEmail = (value: string) => EMAIL_RE.test(value.trim());
export const isPhone = (value: string) => PHONE_RE.test(normalizePhone(value.trim()));

export function validateIdentifier(value: string): string | undefined {
    const v = value.trim();
    if (!v) return 'Enter your email or phone number';
    if (v.includes('@') ? !isEmail(v) : !isPhone(v)) return 'Enter a valid email or phone number';
}

export function validateEmail(value: string): string | undefined {
    if (!value.trim()) return 'Enter your email';
    if (!isEmail(value)) return 'Enter a valid email';
}

export function validatePhone(value: string): string | undefined {
    if (!value.trim()) return 'Enter your phone number';
    if (!isPhone(value)) return 'Enter your number with country code, e.g. +971 50 123 4567';
}

export function validatePassword(value: string): string | undefined {
    if (!value) return 'Enter a password';
    if (value.length < MIN_PASSWORD_LENGTH) return `Use at least ${MIN_PASSWORD_LENGTH} characters`;
    if (value.length > MAX_PASSWORD_LENGTH) return `Use at most ${MAX_PASSWORD_LENGTH} characters`;
    if (!/[a-z]/i.test(value) || !/\d/.test(value)) return 'Use at least one letter and one number';
}

export function validateConfirmPassword(password: string, confirm: string): string | undefined {
    if (!confirm) return 'Confirm your password';
    if (password !== confirm) return "Passwords don't match";
}
