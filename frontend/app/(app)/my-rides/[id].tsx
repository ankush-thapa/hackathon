import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { RideRequestList } from '../../../components/RideRequestRow';
import { Badge, Card, EmptyState, Screen, SecondaryButton, SectionTitle, TextLink } from '../../../components/ui';
import { Colors } from '../../../constants/Colors';
import { CURRENCY } from '../../../constants/Currency';
import { dayLabel, timeLabel } from '../../../services/format';
import { MyRide, MyRidesError, RideStatus, cachedMyRide, findMyRide, money, vehicleText } from '../../../services/myRides';
import { RideRequest, fetchPendingRequests } from '../../../services/rideRequests';

const theme = Colors.light;

const STATUS: Record<RideStatus, { label: string; tone: 'neutral' | 'brand' | 'success' | 'muted' }> = {
    open: { label: 'Open for riders', tone: 'success' },
    full: { label: 'Full', tone: 'brand' },
    started: { label: 'On the way', tone: 'brand' },
    completed: { label: 'Completed', tone: 'muted' },
    cancelled: { label: 'Cancelled', tone: 'muted' },
};

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

/** Details of a ride I'm driving, with its seat requests to approve or decline. */
export default function RideDetailScreen() {
    const router = useRouter();
    const { id } = useLocalSearchParams<{ id: string }>();
    const [ride, setRide] = useState<MyRide | null>(() => (id ? cachedMyRide(id) : null));
    const [requests, setRequests] = useState<RideRequest[]>([]);
    const [loading, setLoading] = useState(!ride);
    const [notFound, setNotFound] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const onAuthError = useCallback(
        (e: unknown) => {
            if (e instanceof MyRidesError && e.status === 401) {
                router.replace('/login');
                return 'Your session has expired.';
            }
            return e instanceof MyRidesError ? e.message : 'Something went wrong. Please try again.';
        },
        [router],
    );

    /** Fresh ride (seat counts change after approvals) plus its pending requests. */
    const load = useCallback(async () => {
        if (!id) return;
        setError(null);
        try {
            const [fresh, pending] = await Promise.all([findMyRide(id), fetchPendingRequests(id)]);
            setRide(fresh);
            setNotFound(!fresh);
            setRequests((pending as Record<string, RideRequest[]>)[id] ?? []);
        } catch (e) {
            setError(onAuthError(e));
        } finally {
            setLoading(false);
        }
    }, [id, onAuthError]);

    useEffect(() => { load(); }, [load]);

    const back = () => (router.canGoBack() ? router.back() : router.replace('/my-rides'));

    if (loading) {
        return (
            <Screen title="Ride details">
                <View style={styles.center}><ActivityIndicator color={theme.primary} /></View>
            </Screen>
        );
    }

    if (!ride) {
        return (
            <Screen title="Ride details">
                {error ? (
                    <View style={styles.center}>
                        <Text style={styles.error}>{error}</Text>
                        <SecondaryButton title="Try again" onPress={() => { setLoading(true); load(); }} />
                    </View>
                ) : (
                    <EmptyState
                        title={notFound ? 'Ride not found' : 'Could not load this ride'}
                        body="It may have been removed, or it isn't one of the rides you're driving."
                        action={<SecondaryButton title="Back to My rides" onPress={() => router.replace('/my-rides')} />}
                    />
                )}
            </Screen>
        );
    }

    const status = STATUS[ride.status];
    const depart = new Date(ride.departure_time);
    const arrive = ride.estimated_arrival_time ? new Date(ride.estimated_arrival_time) : null;
    const booked = ride.total_seats - ride.available_seats;
    const price = Number(ride.price_per_seat);
    const earnings = price * booked;
    const pending = ride.requests.pending_requests;
    const car = vehicleText(ride.vehicle);
    const actionable = ride.status === 'open' || ride.status === 'full';

    return (
        <Screen
            title={`${ride.source.name} → ${ride.destination.name}`}
            subtitle={`${dayLabel(depart)} · ${timeLabel(depart)}`}
            action={<TextLink label="Back" onPress={back} />}
        >
            <View style={styles.badges}>
                <Badge label="You're driving" tone="neutral" />
                <Badge label={status.label} tone={status.tone} />
                {pending ? <Badge label={`${plural(pending, 'request')} waiting`} tone="brand" /> : null}
            </View>

            {/* Route & times */}
            <Card>
                <View style={styles.route}>
                    <View style={styles.dots}>
                        <View style={[styles.dot, { borderColor: theme.primary }]} />
                        <View style={[styles.line, { backgroundColor: theme.border }]} />
                        <View style={[styles.dot, { backgroundColor: theme.primary, borderColor: theme.primary }]} />
                    </View>
                    <View style={{ flex: 1, gap: 22 }}>
                        <View>
                            <Text style={styles.time}>{timeLabel(depart)}</Text>
                            <Text style={styles.place}>{ride.source.name}</Text>
                        </View>
                        <View>
                            <Text style={styles.time}>{arrive ? timeLabel(arrive) : '—'}</Text>
                            <Text style={styles.place}>{ride.destination.name}</Text>
                            {!arrive ? <Text style={styles.meta}>No arrival time set</Text> : null}
                        </View>
                    </View>
                </View>
            </Card>

            {/* Seats */}
            <Card style={{ gap: 12 }}>
                <View style={styles.statRow}>
                    <Stat label="Booked" value={`${booked}/${ride.total_seats}`} />
                    <Stat label="Free" value={String(ride.available_seats)} />
                    <Stat label="Per seat" value={`${CURRENCY}${money(ride.price_per_seat)}`} />
                </View>
                <SeatBar booked={booked} total={ride.total_seats} />
                <Text style={styles.meta}>
                    {booked ? `${CURRENCY}${money(earnings)} from ${plural(booked, 'confirmed seat')}` : 'No seats confirmed yet'}
                </Text>
            </Card>

            {/* Requests */}
            <SectionTitle title="Seat requests" />
            {requests.length ? (
                <Card>
                    <RideRequestList requests={requests} onHandled={load} onAuthError={onAuthError} title="" />
                </Card>
            ) : (
                <EmptyState
                    title={pending ? `${plural(pending, 'request')} waiting` : 'No requests right now'}
                    body={
                        pending
                            ? "Refresh to load the latest requests."
                            : actionable ? 'New requests from riders will show up here.' : 'This ride is no longer taking requests.'
                    }
                />
            )}

            {/* Vehicle & notes */}
            <SectionTitle title="Ride info" />
            <Card style={{ gap: 10 }}>
                <InfoRow label="Vehicle" value={car ?? 'Not set'} />
                {ride.vehicle ? <InfoRow label="Type" value={ride.vehicle.vehicle_type} /> : null}
                <InfoRow label="Notes" value={ride.notes || 'None'} />
            </Card>

            <SecondaryButton title="Refresh" onPress={load} />
            {error ? <Text style={[styles.error, { textAlign: 'center' }]}>{error}</Text> : null}
        </Screen>
    );
}

const Stat = ({ label, value }: { label: string; value: string }) => (
    <View style={{ flex: 1, gap: 2 }}>
        <Text style={styles.statValue}>{value}</Text>
        <Text style={styles.meta}>{label}</Text>
    </View>
);

const SeatBar = ({ booked, total }: { booked: number; total: number }) => (
    <View style={styles.seatBar} accessibilityLabel={`${booked} of ${total} seats booked`}>
        {Array.from({ length: total }, (_, i) => (
            <View key={i} style={[styles.seat, i < booked && { backgroundColor: theme.primary, borderColor: theme.primary }]} />
        ))}
    </View>
);

const InfoRow = ({ label, value }: { label: string; value: string }) => (
    <View style={styles.infoRow}>
        <Text style={styles.meta}>{label}</Text>
        <Text style={styles.infoValue}>{value}</Text>
    </View>
);

const styles = StyleSheet.create({
    center: { alignItems: 'center', paddingVertical: 40, gap: 12 },
    error: { fontSize: 14, color: theme.error },
    badges: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
    route: { flexDirection: 'row', gap: 14, alignItems: 'stretch', paddingVertical: 4 },
    dots: { alignItems: 'center', paddingVertical: 6, width: 14 },
    dot: { width: 14, height: 14, borderRadius: 7, borderWidth: 3 },
    line: { flex: 1, width: 2, marginVertical: 4 },
    time: { fontSize: 18, fontWeight: '800', color: theme.text },
    place: { fontSize: 16, fontWeight: '600', color: theme.text },
    meta: { fontSize: 14, color: theme.muted },
    statRow: { flexDirection: 'row', gap: 12 },
    statValue: { fontSize: 20, fontWeight: '800', color: theme.text },
    seatBar: { flexDirection: 'row', gap: 6 },
    seat: { flex: 1, height: 10, borderRadius: 5, borderWidth: 1, borderColor: theme.border, backgroundColor: theme.background },
    infoRow: { flexDirection: 'row', justifyContent: 'space-between', gap: 12 },
    infoValue: { fontSize: 14, fontWeight: '600', color: theme.text, flexShrink: 1, textAlign: 'right', textTransform: 'none' },
});
