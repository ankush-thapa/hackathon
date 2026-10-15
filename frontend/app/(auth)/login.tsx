import React, { useRef, useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import { Link, useRouter } from 'expo-router';
import { AuthScreen } from '../../components/AuthScreen';
import { PrimaryButton } from '../../components/PrimaryButton';
import { TextField } from '../../components/TextField';
import { Colors } from '../../constants/Colors';
import { AuthError, login } from '../../services/auth';
import { validateIdentifier } from '../../services/validation';

type Errors = { identifier?: string; password?: string };

const validate = (identifier: string, password: string): Errors => ({
    identifier: validateIdentifier(identifier),
    password: password ? undefined : 'Enter your password',
});

export default function LoginScreen() {
    const theme = Colors.light;
    const router = useRouter();
    const passwordRef = useRef<TextInput>(null);

    const [identifier, setIdentifier] = useState('');
    const [password, setPassword] = useState('');
    const [submitted, setSubmitted] = useState(false);
    const [loading, setLoading] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);

    // Show field errors only after the first submit attempt, then keep them live as the user types.
    const errors = submitted ? validate(identifier, password) : {};

    const onSubmit = async () => {
        setSubmitted(true);
        setFormError(null);
        const e = validate(identifier, password);
        if (e.identifier || e.password) return;

        setLoading(true);
        try {
            await login(identifier, password);
            // TODO: persist the token (e.g. expo-secure-store) once the backend returns real ones.
            router.replace('/home');
        } catch (err) {
            setFormError(err instanceof AuthError ? err.message : 'Something went wrong. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <AuthScreen title="Welcome back" subtitle="Log in to find or offer a ride.">
            <TextField
                label="Email or phone"
                placeholder="you@example.com or phone number"
                value={identifier}
                onChangeText={setIdentifier}
                error={errors.identifier}
                keyboardType="email-address"
                autoComplete="username"
                textContentType="username"
                returnKeyType="next"
                onSubmitEditing={() => passwordRef.current?.focus()}
                submitBehavior="submit"
            />
            <TextField
                ref={passwordRef}
                label="Password"
                placeholder="Your password"
                value={password}
                onChangeText={setPassword}
                error={errors.password}
                password
                autoComplete="current-password"
                textContentType="password"
                returnKeyType="go"
                onSubmitEditing={onSubmit}
            />

            {formError ? <Text style={[styles.formError, { color: theme.error }]}>{formError}</Text> : null}

            <View style={styles.actions}>
                <PrimaryButton title="Log in" onPress={onSubmit} loading={loading} />
                <Text style={[styles.footnote, { color: theme.muted }]}>
                    Not registered?{' '}
                    <Link href="/signup" style={[styles.link, { color: theme.primary }]}>Sign up here</Link>
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
