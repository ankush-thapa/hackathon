import React, { useCallback, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { Badge, Card, EmptyState, Screen, SectionTitle, TextLink } from '../../components/ui';
import { Icon } from '../../components/Icon';
import { Colors } from '../../constants/Colors';
import { istHour } from '../../services/format';
import { useProfile } from '../../services/profile';
import { departureLabel } from '../../services/format';
import { MyBooking, MyRide, MyRidesError, RideInfo, fetchMyBookings, fetchMyRides } from '../../services/myRides';
import { getSession } from '../../services/session';
import { useMyVehicles } from '../../services/useMyVehicles';
import { vehicleLabel } from '../../services/vehicles';

const theme = Colors.light;

/** One upcoming trip: a ride I'm driving or a seat I've booked. */
type Trip =
    | { kind: 'driving'; key: string; departure: string; ride: MyRide }
    | { kind: 'riding'; key: string; departure: string; ride: RideInfo; booking: MyBooking };

const BOOKING_LABEL: Record<string, { label: string; tone: 'brand' | 'success' }> = {
    requested: { label: 'Awaiting driver', tone: 'brand' },
    accepted: { label: 'Confirmed', tone: 'success' },
};

/** Next trips from GET /v1/me/rides + GET /v1/me/bookings (upcoming), soonest first. Refetches on focus. */
function useUpcomingTrips(onAuthError: () => void) {
    const [trips, setTrips] = useState<Trip[] | null>(null);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        setError(null);
        try {
            const [rides, bookings] = await Promise.all([fetchMyRides('upcoming'), fetchMyBookings('upcoming')]);
            const list: Trip[] = [
                ...rides.items
                    .filter(r => r.status !== 'cancelled' && r.status !== 'completed')
                    .map(r => ({ kind: 'driving' as const, key: `r-${r.id_ride}`, departure: r.departure_time, ride: r })),
                ...bookings.items.map(b => ({
                    kind: 'riding' as const, key: `b-${b.id_booking}`, departure: b.ride.departure_time, ride: b.ride, booking: b,
                })),
            ];
            setTrips(list.sort((a, b) => a.departure.localeCompare(b.departure)));
        } catch (e) {
            if (e instanceof MyRidesError && e.status === 401) return onAuthError();
            setError(e instanceof MyRidesError ? e.message : 'Could not load your rides.');
        }
    }, [onAuthError]);

    useFocusEffect(useCallback(() => { load(); }, [load]));
    return { trips, error, reload: load };
}

const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`;

function TripCard({ trip, onPress }: { trip: Trip; onPress: () => void }) {
    const { ride } = trip;
    let status: { label: string; tone: 'brand' | 'success' | 'neutral' };
    let detail: string;
    if (trip.kind === 'driving') {
        const booked = ride.total_seats - ride.available_seats;
        const pending = trip.ride.requests.pending_requests;
        status = pending ? { label: `${plural(pending, 'request')} waiting`, tone: 'brand' }
            : ride.status === 'full' ? { label: 'Full', tone: 'success' } : { label: 'Open', tone: 'success' };
        detail = `${booked}/${ride.total_seats} seats booked`;
    } else {
        status = BOOKING_LABEL[trip.booking.status] ?? { label: trip.booking.status, tone: 'neutral' };
        detail = `${plural(trip.booking.seats_booked, 'seat')} · with ${ride.driver.full_name || 'driver'}`;
    }
    return (
        <Card onPress={onPress} accessibilityLabel={`${ride.source.name} to ${ride.destination.name}`}>
            <View style={styles.tripTop}>
                <Badge label={trip.kind === 'driving' ? 'Driving' : 'Riding'} tone="neutral" />
                <Badge label={status.label} tone={status.tone} />
            </View>
            <Text style={styles.tripRoute} numberOfLines={1}>{ride.source.name} → {ride.destination.name}</Text>
            <Text style={styles.actionBody}>{departureLabel(trip.departure)} · {detail}</Text>
        </Card>
    );
}

function greeting() {
    const h = istHour();
    return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}

const ActionCard = ({ title, body, onPress }: { title: string; body: string; onPress: () => void }) => (
    <Card onPress={onPress} accessibilityLabel={title} style={styles.action}>
        <View style={{ flex: 1, gap: 4 }}>
            <Text style={styles.actionTitle}>{title}</Text>
            <Text style={styles.actionBody}>{body}</Text>
        </View>
        <View style={styles.actionArrow}>
            <Icon name="chevron" color="#FFFFFF" size={18} />
        </View>
    </Card>
);

export default function DashboardScreen() {
    const router = useRouter();
    const profile = useProfile();
    const goLogin = useCallback(() => router.replace('/login'), [router]);
    const { trips, error: tripsError, reload } = useUpcomingTrips(goLogin);
    const { vehicles, loading: vehiclesLoading, error: vehiclesError, reload: reloadVehicles } = useMyVehicles(goLogin);
    const session = getSession();

    const firstName = profile.fullName.split(' ')[0];
    const upcoming = trips ?? [];
    const defaultVehicle = vehicles.find(v => v.isDefault) ?? vehicles[0];

    return (
        <Screen
            title={firstName ? `${greeting()}, ${firstName}` : greeting()}
            subtitle={firstName ? 'Where are you heading today?' : session?.email ?? session?.phone ?? 'Where are you heading today?'}
        >
            <View style={styles.actions}>
                <ActionCard title="Request a ride" body="Find someone going your way" onPress={() => router.push('/request-ride')} />
                <ActionCard title="Offer a ride" body="Share empty seats, split the cost" onPress={() => router.push('/offer-ride')} />
            </View>

            {!profile.fullName ? (
                <Card onPress={() => router.push('/profile')} accessibilityLabel="Complete your profile" style={styles.nudge}>
                    <Text style={styles.nudgeTitle}>Complete your profile</Text>
                    <Text style={styles.actionBody}>Add your name so riders and drivers know who they're travelling with.</Text>
                </Card>
            ) : null}

            <SectionTitle
                title="Upcoming rides"
                action={upcoming.length ? <TextLink label="See all" onPress={() => router.push('/my-rides')} /> : undefined}
            />
            {trips === null && !tripsError ? (
                <ActivityIndicator color={theme.primary} style={{ marginVertical: 12 }} />
            ) : tripsError && !upcoming.length ? (
                <EmptyState
                    title="Couldn't load your rides"
                    body={tripsError}
                    action={<View style={{ alignItems: 'center' }}><TextLink label="Try again" onPress={reload} /></View>}
                />
            ) : upcoming.length ? (
                upcoming.slice(0, 3).map(t => (
                    <TripCard
                        key={t.key}
                        trip={t}
                        onPress={() =>
                            t.kind === 'driving'
                                ? router.push({ pathname: '/my-rides/[id]', params: { id: t.ride.id_ride } })
                                : router.push({ pathname: '/my-rides/booking/[id]', params: { id: t.booking.id_booking } })
                        }
                    />
                ))
            ) : (
                <EmptyState title="No upcoming rides" body="Rides you request or offer will show up here." />
            )}

            <SectionTitle title="My vehicles" action={<TextLink label="Manage" onPress={() => router.push('/vehicles')} />} />
            {vehiclesLoading && !vehicles.length ? (
                <ActivityIndicator color={theme.primary} style={{ marginVertical: 12 }} />
            ) : vehiclesError && !vehicles.length ? (
                <EmptyState
                    title="Couldn't load your vehicles"
                    body={vehiclesError}
                    action={<View style={{ alignItems: 'center' }}><TextLink label="Try again" onPress={reloadVehicles} /></View>}
                />
            ) : defaultVehicle ? (
                <Card onPress={() => router.push('/vehicles')} accessibilityLabel="My vehicles">
                    <Text style={styles.vehicleName}>{vehicleLabel(defaultVehicle)}</Text>
                    <Text style={styles.actionBody}>
                        {defaultVehicle.registrationNumber} · {defaultVehicle.seatCapacity} seats
                        {vehicles.length > 1 ? ` · +${vehicles.length - 1} more` : ''}
                    </Text>
                </Card>
            ) : (
                <EmptyState
                    title="No vehicles yet"
                    body="Add a vehicle to start offering rides."
                    action={<View style={{ alignItems: 'center' }}><TextLink label="+ Add a vehicle" onPress={() => router.push('/vehicles/add')} /></View>}
                />
            )}
        </Screen>
    );
}

const styles = StyleSheet.create({
    actions: { gap: 12 },
    action: { flexDirection: 'row', alignItems: 'center', gap: 12, backgroundColor: theme.card, paddingVertical: 18 },
    actionTitle: { fontSize: 17, fontWeight: '800', color: theme.text },
    actionBody: { fontSize: 14, color: theme.muted },
    actionArrow: { width: 36, height: 36, borderRadius: 18, backgroundColor: theme.primary, alignItems: 'center', justifyContent: 'center' },
    nudge: { backgroundColor: theme.primarySoft, borderColor: theme.primarySoft },
    nudgeTitle: { fontSize: 16, fontWeight: '800', color: theme.primary },
    vehicleName: { fontSize: 16, fontWeight: '700', color: theme.text },
    tripTop: { flexDirection: 'row', gap: 8, flexWrap: 'wrap', marginBottom: 4 },
    tripRoute: { fontSize: 16, fontWeight: '700', color: theme.text },
});
