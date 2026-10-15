import React, { useState } from 'react';
import { ActivityIndicator, Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Colors } from '../constants/Colors';
import { profileHref } from '../services/users';
import { timeAgo } from '../services/format';
import { RideRequest, RideRequestError, approveRequest, declineRequest } from '../services/rideRequests';
import { CURRENCY } from '../constants/Currency';
import { money } from '../services/myRides';
import { Avatar } from './Avatar';
import { Badge } from './ui';

const theme = Colors.light;

/** One pending request with Approve / Decline. Reloads the list after, so seat counts refresh. */
export function RequestRow({ req, onHandled, onAuthError }: { req: RideRequest; onHandled: () => void; onAuthError: (e: unknown) => string }) {
    const router = useRouter();
    const [busy, setBusy] = useState<'approve' | 'decline' | null>(null);
    const [confirmDecline, setConfirmDecline] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [done, setDone] = useState<string | null>(null);

    const act = async (kind: 'approve' | 'decline') => {
        setBusy(kind);
        setError(null);
        try {
            const outcome = kind === 'approve' ? await approveRequest(req) : await declineRequest(req);
            setDone(outcome === 'approved' ? 'Approved' : outcome === 'declined' ? 'Declined' : 'No longer pending');
            setTimeout(onHandled, 900); // brief confirmation, then refresh counts
        } catch (e) {
            setError(e instanceof RideRequestError ? onAuthError(e) : 'Something went wrong. Please try again.');
            setBusy(null);
        }
    };

    return (
        <View style={styles.requestRow}>
            <Pressable
                style={({ pressed }) => [styles.who, pressed && { opacity: 0.7 }]}
                onPress={() => router.push(profileHref(req.idRider, { name: req.riderName, photo: req.riderPhotoUrl, role: 'Rider' }))}
                accessibilityRole="button"
                accessibilityLabel={`${req.riderName}, ${req.seats} seat${req.seats === 1 ? '' : 's'}. View profile`}
            >
                {req.riderPhotoUrl ? (
                    <Image source={{ uri: req.riderPhotoUrl }} style={styles.photo} />
                ) : (
                    <Avatar name={req.riderName} size={36} />
                )}
                <View style={{ flex: 1 }}>
                    <Text style={styles.requestText}>
                        {req.riderName} · {req.seats} seat{req.seats === 1 ? '' : 's'} · {CURRENCY}{money(req.totalAmount)}
                    </Text>
                    <Text style={styles.hint}>Requested {timeAgo(req.createdAt)} · <Text style={styles.profileLink}>View profile</Text></Text>
                </View>
            </Pressable>
            {req.note ? <Text style={styles.note}>“{req.note}”</Text> : null}
            {done ? (
                <Badge label={done} tone={done === 'Approved' ? 'success' : 'muted'} />
            ) : confirmDecline ? (
                <View style={styles.requestActions}>
                    <Text style={[styles.confirmText, { flex: 1 }]}>Decline this request?</Text>
                    {busy ? <ActivityIndicator color={theme.primary} /> : (
                        <>
                            <Pressable onPress={() => setConfirmDecline(false)} accessibilityRole="button" hitSlop={8}>
                                <Text style={styles.keepText}>Back</Text>
                            </Pressable>
                            <Pressable onPress={() => act('decline')} accessibilityRole="button" hitSlop={8}>
                                <Text style={styles.cancelText}>Yes, decline</Text>
                            </Pressable>
                        </>
                    )}
                </View>
            ) : (
                <View style={styles.requestActions}>
                    <Pressable
                        onPress={() => act('approve')}
                        disabled={!!busy}
                        accessibilityRole="button"
                        style={({ pressed }) => [styles.approveBtn, (pressed || busy) && { opacity: 0.8 }]}
                    >
                        {busy === 'approve' ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.approveText}>Approve</Text>}
                    </Pressable>
                    <Pressable
                        onPress={() => setConfirmDecline(true)}
                        disabled={!!busy}
                        accessibilityRole="button"
                        style={({ pressed }) => [styles.declineBtn, pressed && { opacity: 0.8 }]}
                    >
                        <Text style={styles.declineText}>Decline</Text>
                    </Pressable>
                </View>
            )}
            {error ? <Text style={styles.error}>{error}</Text> : null}
        </View>
    );
}

/** All pending requests for one ride, or nothing when there are none. */
export function RideRequestList({ requests, onHandled, onAuthError, title = 'Seat requests' }: {
    requests: RideRequest[]; onHandled: () => void; onAuthError: (e: unknown) => string; title?: string;
}) {
    if (!requests.length) return null;
    return (
        <View style={styles.requests}>
            {title ? <Text style={styles.requestsTitle}>{title}</Text> : null}
            {requests.map(r => (
                <RequestRow key={r.idBooking} req={r} onHandled={onHandled} onAuthError={onAuthError} />
            ))}
        </View>
    );
}

const styles = StyleSheet.create({
    profileLink: { color: theme.primary, fontWeight: '700' },
    error: { fontSize: 14, color: theme.error },
    hint: { fontSize: 13, color: theme.muted },
    cancelText: { fontSize: 14, fontWeight: '700', color: theme.error },
    confirmText: { fontSize: 14, color: theme.text },
    keepText: { fontSize: 14, fontWeight: '700', color: theme.muted },
    requests: { gap: 12 },
    requestsTitle: { fontSize: 15, fontWeight: '800', color: theme.text },
    requestRow: { gap: 6, padding: 12, borderRadius: 12, backgroundColor: theme.background },
    who: { flexDirection: 'row', alignItems: 'center', gap: 10 },
    photo: { width: 36, height: 36, borderRadius: 18 },
    note: { fontSize: 14, color: theme.text, fontStyle: 'italic' },
    requestText: { fontSize: 15, fontWeight: '600', color: theme.text },
    requestActions: { flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: 4 },
    approveBtn: { backgroundColor: theme.primary, paddingVertical: 9, paddingHorizontal: 20, borderRadius: 999, minWidth: 100, alignItems: 'center' },
    approveText: { color: '#FFFFFF', fontSize: 14, fontWeight: '800' },
    declineBtn: { borderWidth: 1.5, borderColor: theme.border, paddingVertical: 8, paddingHorizontal: 18, borderRadius: 999 },
    declineText: { color: theme.text, fontSize: 14, fontWeight: '700' },
});
