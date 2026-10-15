import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { ProfileForm } from '../../components/ProfileForm';
import { Colors } from '../../constants/Colors';
import { ProfileInput } from '../../data/profile';
import { ProfileError, fetchProfile } from '../../services/profile';
import { getSession } from '../../services/session';

const theme = Colors.light;

type State =
    | { status: 'loading' }
    | { status: 'error'; message: string }
    | { status: 'ready'; profile: ProfileInput | null };

/** Edit the logged-in user's profile. Loads the saved profile from GET /v1/auth/profile. */
export default function ProfileScreen() {
    const router = useRouter();
    const [state, setState] = useState<State>({ status: 'loading' });
    const session = getSession();

    const load = useCallback(async () => {
        setState({ status: 'loading' });
        try {
            setState({ status: 'ready', profile: await fetchProfile() });
        } catch (e) {
            if (e instanceof ProfileError && e.status === 401) return router.replace('/login');
            setState({ status: 'error', message: e instanceof ProfileError ? e.message : 'Could not load your profile.' });
        }
    }, [router]);

    useEffect(() => { load(); }, [load]);

    if (state.status === 'loading') {
        return (
            <View style={styles.center}>
                <ActivityIndicator color={theme.primary} />
            </View>
        );
    }

    if (state.status === 'error') {
        return (
            <View style={styles.center}>
                <Text style={styles.errorText}>{state.message}</Text>
                <Pressable onPress={load} accessibilityRole="button" style={styles.retry}>
                    <Text style={styles.retryText}>Try again</Text>
                </Pressable>
            </View>
        );
    }

    return (
        <ProfileForm
            title="My profile"
            subtitle={state.profile ? 'Keep your details up to date for co-riders.' : "You haven't set up your profile yet."}
            initial={state.profile}
            submitLabel="Save changes"
            showSavedNotice
            footer={
                session?.email || session?.phone ? (
                    <View style={styles.account}>
                        <Text style={styles.accountTitle}>Account</Text>
                        {session.email ? <Row label="Email" value={session.email} /> : null}
                        {session.phone ? <Row label="Phone" value={session.phone} /> : null}
                    </View>
                ) : null
            }
        />
    );
}

const Row = ({ label, value }: { label: string; value: string }) => (
    <View style={styles.row}>
        <Text style={styles.rowLabel}>{label}</Text>
        <Text style={styles.rowValue} numberOfLines={1}>{value}</Text>
    </View>
);

const styles = StyleSheet.create({
    center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12, padding: 24 },
    errorText: { fontSize: 15, color: theme.error, textAlign: 'center' },
    retry: { paddingVertical: 10, paddingHorizontal: 20, borderRadius: 999, backgroundColor: theme.primary },
    retryText: { color: '#FFFFFF', fontWeight: '700', fontSize: 15 },
    account: { backgroundColor: theme.card, borderColor: theme.border, borderWidth: 1, borderRadius: 14, padding: 16, gap: 10, marginTop: 8 },
    accountTitle: { fontSize: 15, fontWeight: '700', color: theme.text },
    row: { flexDirection: 'row', justifyContent: 'space-between', gap: 12 },
    rowLabel: { fontSize: 14, color: theme.muted },
    rowValue: { fontSize: 14, fontWeight: '600', color: theme.text, flexShrink: 1 },
});
