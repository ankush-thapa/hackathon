import React, { useRef, useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import { Link, useRouter } from 'expo-router';
import { AuthScreen } from '../../components/AuthScreen';
import { PrimaryButton } from '../../components/PrimaryButton';
import { TextField } from '../../components/TextField';
import { Colors } from '../../constants/Colors';
import { AuthError, signup } from '../../services/auth';
import {
    MIN_PASSWORD_LENGTH,
    validateConfirmPassword,
    validateEmail,
    validatePassword,
    validatePhone,
} from '../../services/validation';

type Form = { email: string; phone: string; password: string; confirm: string };
type Errors = Partial<Record<keyof Form, string>>;

const validate = (f: Form): Errors => ({
    email: validateEmail(f.email),
    phone: validatePhone(f.phone),
    password: validatePassword(f.password),
    confirm: validateConfirmPassword(f.password, f.confirm),
});

export default function SignupScreen() {
    const theme = Colors.light;
    const router = useRouter();
    const phoneRef = useRef<TextInput>(null);
    const passwordRef = useRef<TextInput>(null);
    const confirmRef = useRef<TextInput>(null);

    const [form, setForm] = useState<Form>({ email: '', phone: '', password: '', confirm: '' });
    const [submitted, setSubmitted] = useState(false);
    const [loading, setLoading] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);
    // Errors the server returned for a field (e.g. "already registered"); cleared when that field is edited.
    const [serverErrors, setServerErrors] = useState<Errors>({});

    const set = (key: keyof Form) => (value: string) => {
        setForm(prev => ({ ...prev, [key]: value }));
        setServerErrors(prev => ({ ...prev, [key]: undefined }));
    };
    const local = submitted ? validate(form) : {};
    const errors: Errors = {
        email: local.email ?? serverErrors.email,
        phone: local.phone ?? serverErrors.phone,
        password: local.password ?? serverErrors.password,
        confirm: local.confirm,
    };

    const onSubmit = async () => {
        setSubmitted(true);
        setFormError(null);
        setServerErrors({});
        if (Object.values(validate(form)).some(Boolean)) return;

        setLoading(true);
        try {
            const created = await signup({ email: form.email, phone: form.phone, password: form.password });
            // Register doesn't return a session, so send the user to log in with their new account.
            // TODO: add OTP/email verification here once the backend supports it.
            router.replace({ pathname: '/login', params: { registered: '1', identifier: created.email } });
        } catch (err) {
            if (err instanceof AuthError && err.field) {
                setServerErrors({ [err.field]: err.message });
            } else {
                setFormError(err instanceof AuthError ? err.message : 'Something went wrong. Please try again.');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <AuthScreen title="Create your account" subtitle="Find your ride companion, split the cost.">
            <TextField
                label="Email"
                placeholder="you@example.com"
                value={form.email}
                onChangeText={set('email')}
                error={errors.email}
                keyboardType="email-address"
                autoComplete="email"
                textContentType="emailAddress"
                returnKeyType="next"
                onSubmitEditing={() => phoneRef.current?.focus()}
                submitBehavior="submit"
            />
            <TextField
                ref={phoneRef}
                label="Phone"
                placeholder="+971 50 123 4567"
                value={form.phone}
                onChangeText={set('phone')}
                error={errors.phone}
                hint="Include your country code, e.g. +971"
                keyboardType="phone-pad"
                autoComplete="tel"
                textContentType="telephoneNumber"
                returnKeyType="next"
                onSubmitEditing={() => passwordRef.current?.focus()}
                submitBehavior="submit"
            />
            <TextField
                ref={passwordRef}
                label="Password"
                placeholder={`At least ${MIN_PASSWORD_LENGTH} characters`}
                hint="Use letters and at least one number"
                value={form.password}
                onChangeText={set('password')}
                error={errors.password}
                password
                autoComplete="new-password"
                textContentType="newPassword"
                returnKeyType="next"
                onSubmitEditing={() => confirmRef.current?.focus()}
                submitBehavior="submit"
            />
            <TextField
                ref={confirmRef}
                label="Confirm password"
                placeholder="Re-enter your password"
                value={form.confirm}
                onChangeText={set('confirm')}
                error={errors.confirm}
                password
                autoComplete="new-password"
                textContentType="newPassword"
                returnKeyType="go"
                onSubmitEditing={onSubmit}
            />

            {formError ? <Text style={[styles.formError, { color: theme.error }]}>{formError}</Text> : null}

            <View style={styles.actions}>
                <PrimaryButton title="Sign up" onPress={onSubmit} loading={loading} />
                <Text style={[styles.footnote, { color: theme.muted }]}>
                    Already have an account?{' '}
                    <Link href="/login" style={[styles.link, { color: theme.primary }]}>Log in</Link>
                </Text>
            </View>
        </AuthScreen>
    );
}

const styles = StyleSheet.create({
    formError: { fontSize: 14, textAlign: 'center' },
    actions: { marginTop: 6, gap: 16 },
    footnote: { fontSize: 14, textAlign: 'center' },
    link: { fontWeight: '700' },
});
