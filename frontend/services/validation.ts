const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
// Optional leading +, then 7–15 digits. Spaces, dashes and brackets are ignored.
const PHONE_RE = /^\+?\d{7,15}$/;

export const MIN_PASSWORD_LENGTH = 8;

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
    if (!isPhone(value)) return 'Enter a valid phone number';
}

export function validatePassword(value: string): string | undefined {
    if (!value) return 'Enter a password';
    if (value.length < MIN_PASSWORD_LENGTH) return `Use at least ${MIN_PASSWORD_LENGTH} characters`;
}

export function validateConfirmPassword(password: string, confirm: string): string | undefined {
    if (!confirm) return 'Confirm your password';
    if (password !== confirm) return "Passwords don't match";
}
