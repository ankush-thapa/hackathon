import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Avatar } from '../../../../components/Avatar';
import { profileHref } from '../../../../services/users';
import { CancelBooking } from '../../../../components/CancelBooking';
import { Badge, Card, EmptyState, Screen, SecondaryButton, SectionTitle, TextLink } from '../../../../components/ui';
import { Colors } from '../../../../constants/Colors';
import { CURRENCY } from '../../../../constants/Currency';
import { dayLabel, timeAgo, timeLabel } from '../../../../services/format';
import { BookingStatus, MyBooking, MyRidesError, cachedMyBooking, findMyBooking, money, vehicleText } from '../../../../services/myRides';

const theme = Colors.light;
type Tone = 'neutral' | 'brand' | 'success' | 'muted';

/** What each booking status means for the rider, in plain words. */
const STATUS: Record<BookingStatus, { label: string; tone: Tone; explain: string }> = {
    requested: { label: 'Awaiting driver', tone: 'brand', explain: "Your request has been sent. You'll be notified when the driver confirms." },
    accepted: { label: 'Confirmed', tone: 'success', explain: 'Your seat is confirmed. Be at the pickup point a few minutes early.' },
    rejected: { label: 'Declined', tone: 'muted', explain: "The driver couldn't take this request. Try another ride on this route." },
    cancelled_by_rider: { label: 'Cancelled', tone: 'muted', explain: 'You cancelled this booking.' },
    cancelled_by_driver: { label: 'Cancelled by driver', tone: 'muted', explain: "The driver couldn't take this booking. Try another ride on this route." },
    expired: { label: 'Expired', tone: 'muted', explain: 'The driver didn’t respond before the ride left.' },
    completed: { label: 'Completed', tone: 'muted', explain: 'Hope you had a good ride!' },
};

const RIDE_STATUS: Record<string, string> = {
    open: 'Open', full: 'Full', started: 'On the way', completed: 'Completed', cancelled: 'Cancelled by driver',
};

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

/** A seat I booked on someone else's ride. */
export default function BookingDetailScreen() {
    const router = useRouter();
    const { id } = useLocalSearchParams<{ id: string }>();
    const [booking, setBooking] = useState<MyBooking | null>(() => (id ? cachedMyBooking(id) : null));
    const [loading, setLoading] = useState(!booking);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        if (!id) return;
        setError(null);
        try {
            setBooking(await findMyBooking(id));
        } catch (e) {
            if (e instanceof MyRidesError && e.status === 401) return router.replace('/login');
            setError(e instanceof MyRidesError ? e.message : 'Could not load this booking.');
        } finally {
            setLoading(false);
        }
    }, [id, router]);

    useEffect(() => { load(); }, [load]);

    const back = () => (router.canGoBack() ? router.back() : router.replace('/my-rides'));

    if (loading) {
        return (
            <Screen title="Booking details">
                <View style={styles.center}><ActivityIndicator color={theme.primary} /></View>
            </Screen>
        );
    }

    if (!booking) {
        return (
            <Screen title="Booking details">
                {error ? (
                    <View style={styles.center}>
                        <Text style={styles.error}>{error}</Text>
                        <SecondaryButton title="Try again" onPress={() => { setLoading(true); load(); }} />
                    </View>
                ) : (
                    <EmptyState
                        title="Booking not found"
                        body="It may have been removed, or it isn't one of your bookings."
                        action={<SecondaryButton title="Back to My rides" onPress={() => router.replace('/my-rides')} />}
                    />
                )}
            </Screen>
        );
    }

    const { ride } = booking;
    const status = STATUS[booking.status];
    const depart = new Date(ride.departure_time);
    const arrive = ride.estimated_arrival_time ? new Date(ride.estimated_arrival_time) : null;
    const departed = depart.getTime() < Date.now();
    const active = booking.status === 'requested' || booking.status === 'accepted';
    const driverName = ride.driver.full_name || 'Your driver';
    const car = vehicleText(ride.vehicle);
    // Riders can't see each other (backend privacy rule), but seat counts tell us how full the car is.
    const confirmedSeats = ride.total_seats - ride.available_seats;
    const otherSeats = Math.max(0, confirmedSeats - (booking.status === 'accepted' ? booking.seats_booked : 0));

    return (
        <Screen
            title={`${ride.source.name} → ${ride.destination.name}`}
            subtitle={`${dayLabel(depart)} · ${timeLabel(depart)}`}
            action={<TextLink label="Back" onPress={back} />}
        >
            {/* Status */}
            <Card style={[styles.statusCard, active && booking.status === 'accepted' ? { backgroundColor: theme.successBg, borderColor: theme.successBg } : null] as any}>
                <View style={styles.badges}>
                    <Badge label="Riding" tone="neutral" />
                    <Badge label={status.label} tone={status.tone} />
                    {ride.status === 'cancelled' && booking.status !== 'cancelled_by_driver' ? <Badge label="Ride cancelled" tone="muted" /> : null}
                </View>
                <Text style={styles.statusText}>{status.explain}</Text>
                <Text style={styles.meta}>Requested {timeAgo(booking.created_at)}</Text>
            </Card>

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
                            <Text style={styles.meta}>Pickup</Text>
                        </View>
                        <View>
                            <Text style={styles.time}>{arrive ? timeLabel(arrive) : '—'}</Text>
                            <Text style={styles.place}>{ride.destination.name}</Text>
                            <Text style={styles.meta}>{arrive ? 'Estimated arrival' : 'Drop-off'}</Text>
                        </View>
                    </View>
                </View>
            </Card>

            {/* Driver */}
            <SectionTitle title="Driver" />
            <Card>
                <Pressable
                    style={({ pressed }) => [styles.driverRow, pressed && { opacity: 0.7 }]}
                    onPress={() => router.push(profileHref(ride.driver.id_user, { name: ride.driver.full_name, photo: ride.driver.photo_url, role: 'Driver' }))}
                    accessibilityRole="button"
                    accessibilityLabel={`Driver ${driverName}. View profile`}
                >
                    {ride.driver.photo_url ? (
                        <Image source={{ uri: ride.driver.photo_url }} style={styles.driverPhoto} />
                    ) : (
                        <Avatar name={driverName} size={52} />
                    )}
                    <View style={{ flex: 1, gap: 2 }}>
                        <Text style={styles.driverName}>{driverName}</Text>
                        <Text style={styles.meta}>{car ?? 'Vehicle not listed'}</Text>
                        {ride.vehicle ? <Text style={styles.meta}>{ride.vehicle.vehicle_type}</Text> : null}
                    </View>
                    <Text style={styles.viewProfile}>View profile ›</Text>
                </Pressable>
                {ride.notes ? <Text style={styles.note}>Driver's note: “{ride.notes}”</Text> : null}
            </Card>

            {/* Other passengers */}
            <SectionTitle title="Other passengers" />
            <Card style={{ gap: 10 }}>
                <View style={styles.seatBar} accessibilityLabel={`${confirmedSeats} of ${ride.total_seats} seats confirmed`}>
                    {Array.from({ length: ride.total_seats }, (_, i) => {
                        const mine = booking.status === 'accepted' && i < booking.seats_booked;
                        const taken = i < confirmedSeats;
                        return (
                            <View
                                key={i}
                                style={[
                                    styles.seat,
                                    taken && { backgroundColor: theme.primarySoft, borderColor: theme.primarySoft },
                                    mine && { backgroundColor: theme.primary, borderColor: theme.primary },
                                ]}
                            />
                        );
                    })}
                </View>
                <Text style={styles.statusText}>
                    {otherSeats
                        ? `${plural(otherSeats, 'other seat')} confirmed on this ride.`
                        : booking.status === 'accepted' ? "You're the only passenger so far." : 'No confirmed passengers yet.'}
                </Text>
                <Text style={styles.meta}>
                    {booking.status === 'accepted' ? 'Dark: your seats · Light: other passengers · ' : 'Light: confirmed seats · '}
                    {plural(ride.available_seats, 'seat')} still free. Passenger names are only shared with the driver.
                </Text>
            </Card>

            {/* Payment */}
            <SectionTitle title="Your booking" />
            <Card style={{ gap: 10 }}>
                <InfoRow label="Seats" value={plural(booking.seats_booked, 'seat')} />
                <InfoRow label="Price per seat" value={`${CURRENCY}${money(booking.price_per_seat)}`} />
                <View style={styles.divider} />
                <InfoRow label="Total" value={`${CURRENCY}${money(booking.total_amount)}`} strong />
                {booking.rider_note ? <InfoRow label="Your note" value={`“${booking.rider_note}”`} /> : null}
                <InfoRow label="Ride status" value={RIDE_STATUS[ride.status] ?? ride.status} />
                <InfoRow label="Seats left on ride" value={String(ride.available_seats)} />
            </Card>

            {active && !departed ? (
                <CancelBooking booking={booking} onCancelled={load} />
            ) : null}
            {!active || departed ? (
                <SecondaryButton title="Find another ride" onPress={() => router.push('/request-ride')} />
            ) : null}
            {error ? <Text style={[styles.error, { textAlign: 'center' }]}>{error}</Text> : null}
        </Screen>
    );
}

const InfoRow = ({ label, value, strong }: { label: string; value: string; strong?: boolean }) => (
    <View style={styles.infoRow}>
        <Text style={strong ? styles.strongLabel : styles.meta}>{label}</Text>
        <Text style={strong ? styles.strongValue : styles.infoValue}>{value}</Text>
    </View>
);

const styles = StyleSheet.create({
    viewProfile: { fontSize: 14, fontWeight: '700', color: theme.primary },
    center: { alignItems: 'center', paddingVertical: 40, gap: 12 },
    error: { fontSize: 14, color: theme.error },
    statusCard: { gap: 8 },
    badges: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
    statusText: { fontSize: 15, color: theme.text, lineHeight: 21 },
    route: { flexDirection: 'row', gap: 14, alignItems: 'stretch', paddingVertical: 4 },
    dots: { alignItems: 'center', paddingVertical: 6, width: 14 },
    dot: { width: 14, height: 14, borderRadius: 7, borderWidth: 3 },
    line: { flex: 1, width: 2, marginVertical: 4 },
    time: { fontSize: 18, fontWeight: '800', color: theme.text },
    place: { fontSize: 16, fontWeight: '600', color: theme.text },
    meta: { fontSize: 14, color: theme.muted },
    note: { fontSize: 14, color: theme.text, fontStyle: 'italic', marginTop: 8 },
    driverRow: { flexDirection: 'row', alignItems: 'center', gap: 14 },
    driverPhoto: { width: 52, height: 52, borderRadius: 26 },
    driverName: { fontSize: 17, fontWeight: '800', color: theme.text },
    divider: { height: 1, backgroundColor: theme.border },
    seatBar: { flexDirection: 'row', gap: 6 },
    seat: { flex: 1, height: 10, borderRadius: 5, borderWidth: 1, borderColor: theme.border, backgroundColor: theme.background },
    infoRow: { flexDirection: 'row', justifyContent: 'space-between', gap: 12 },
    infoValue: { fontSize: 14, fontWeight: '600', color: theme.text, flexShrink: 1, textAlign: 'right' },
    strongLabel: { fontSize: 15, fontWeight: '800', color: theme.text },
    strongValue: { fontSize: 17, fontWeight: '800', color: theme.text },
});
