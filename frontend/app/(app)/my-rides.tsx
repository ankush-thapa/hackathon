import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useForegroundRefresh } from '../../services/useForegroundRefresh';
import { Badge, Card, EmptyState, Screen, SecondaryButton, TextLink } from '../../components/ui';
import { Colors } from '../../constants/Colors';
import { CancelBooking } from '../../components/CancelBooking';
import { RideRequestList } from '../../components/RideRequestRow';
import { departureLabel } from '../../services/format';
import { useProfile } from '../../services/profile';
import { CURRENCY } from '../../constants/Currency';
import { RideRequest, fetchRequestsFor } from '../../services/rideRequests';
import {
    BookingStatus,
    MyBooking,
    MyRide,
    MyRidesError,
    RideInfo,
    RideStatus,
    Scope,
    cancelBooking,
    fetchMyBookings,
    fetchMyRides,
    money,
    vehicleText,
} from '../../services/myRides';

const theme = Colors.light;

type Kind = 'offered' | 'booked';
type Tone = 'neutral' | 'brand' | 'success' | 'muted';

const RIDE_STATUS: Record<RideStatus, { label: string; tone: Tone }> = {
    open: { label: 'Open', tone: 'success' },
    full: { label: 'Full', tone: 'brand' },
    started: { label: 'On the way', tone: 'brand' },
    completed: { label: 'Completed', tone: 'muted' },
    cancelled: { label: 'Cancelled', tone: 'muted' },
};

const BOOKING_STATUS: Record<BookingStatus, { label: string; tone: Tone }> = {
    requested: { label: 'Awaiting driver', tone: 'brand' },
    accepted: { label: 'Confirmed', tone: 'success' },
    rejected: { label: 'Declined', tone: 'muted' },
    cancelled_by_rider: { label: 'Cancelled', tone: 'muted' },
    cancelled_by_driver: { label: 'Cancelled by driver', tone: 'muted' },
    expired: { label: 'Expired', tone: 'muted' },
    completed: { label: 'Completed', tone: 'muted' },
};

type ListState<T> = { items: T[]; next: string | null; loading: boolean; loadingMore: boolean; error: string | null };
const initial = <T,>(): ListState<T> => ({ items: [], next: null, loading: true, loadingMore: false, error: null });

/** Rides I'm driving (GET /v1/me/rides) and seats I've booked (GET /v1/me/bookings). */
export default function MyRidesScreen() {
    const router = useRouter();
    const [kind, setKind] = useState<Kind>('booked');
    const [scope, setScope] = useState<Exclude<Scope, 'all'>>('upcoming');
    const [state, setState] = useState<ListState<MyRide | MyBooking>>(initial());
    const reqId = useRef(0); // ignore responses from a tab the user has already left
    // Seat requests on my offered rides, by ride id (from booking_requested notifications).
    const [requests, setRequests] = useState<Record<string, RideRequest[]>>({});

    const onError = useCallback(
        (e: unknown) => {
            if (e instanceof MyRidesError && e.status === 401) {
                router.replace('/login');
                return 'Your session has expired.';
            }
            return e instanceof MyRidesError ? e.message : 'Could not load your rides.';
        },
        [router],
    );

    const load = useCallback(async () => {
        const id = ++reqId.current;
        setState(initial());
        try {
            const page = kind === 'offered' ? await fetchMyRides(scope) : await fetchMyBookings(scope);
            // Load request details only for rides that have pending requests.
            const withRequests = kind === 'offered' && scope === 'upcoming'
                ? (page.items as MyRide[]).filter(r => r.requests.pending_requests > 0).map(r => r.id_ride)
                : [];
            const pending = withRequests.length ? await fetchRequestsFor(withRequests) : {};
            if (id === reqId.current) {
                setRequests(pending);
                setState({ items: page.items, next: page.next_page, loading: false, loadingMore: false, error: null });
            }
        } catch (e) {
            if (id === reqId.current) setState(s => ({ ...s, loading: false, error: onError(e) }));
        }
    }, [kind, scope, onError]);

    useEffect(() => { load(); }, [load]);

    const loadMore = async () => {
        if (!state.next || state.loadingMore) return;
        const id = reqId.current;
        setState(s => ({ ...s, loadingMore: true }));
        try {
            const page = kind === 'offered' ? await fetchMyRides(scope, state.next) : await fetchMyBookings(scope, state.next);
            if (id === reqId.current) {
                setState(s => ({ ...s, items: [...s.items, ...page.items], next: page.next_page, loadingMore: false }));
            }
        } catch (e) {
            if (id === reqId.current) setState(s => ({ ...s, loadingMore: false, error: onError(e) }));
        }
    };

    const view = useRef({ kind, scope, state });
    view.current = { kind, scope, state };
    useForegroundRefresh(async () => {
        const snapshot = view.current;
        if (snapshot.state.loading || snapshot.state.loadingMore) return;
        const id = reqId.current;
        try {
            const items: (MyRide | MyBooking)[] = [];
            let cursor: string | null = null;
            do {
                const page: { items: (MyRide | MyBooking)[]; next_page: string | null } = snapshot.kind === 'offered' ? await fetchMyRides(snapshot.scope, cursor) : await fetchMyBookings(snapshot.scope, cursor);
                items.push(...page.items);
                cursor = page.next_page;
            } while (cursor && items.length < snapshot.state.items.length);
            const withRequests = snapshot.kind === 'offered' && snapshot.scope === 'upcoming'
                ? items.filter((item): item is MyRide => 'id_ride' in item)
                    .filter(ride => ride.requests.pending_requests > 0).map(ride => ride.id_ride)
                : [];
            const pending = withRequests.length ? await fetchRequestsFor(withRequests) : {};
            if (id === reqId.current && !view.current.state.loadingMore && view.current.state.items === snapshot.state.items) {
                setRequests(pending);
                setState(previous => ({ ...previous, items, next: cursor, error: null }));
            }
        } catch (e) { if (id === reqId.current) setState(previous => ({ ...previous, error: onError(e) })); }
    });

    const onBookingCancelled = (idBooking: string) => {
        // Cancelled bookings move to "Past", so drop it from the upcoming list.
        setState(s => ({ ...s, items: s.items.filter(i => !('id_booking' in i) || i.id_booking !== idBooking) }));
    };

    return (
        <Screen title="My rides" subtitle="Seats you've booked and rides you're driving.">
            <Segmented
                value={kind}
                onChange={setKind}
                options={[{ value: 'booked', label: 'Booked' }, { value: 'offered', label: 'Offering' }]}
                label="Ride type"
            />
            <View style={styles.chips} accessibilityRole="radiogroup" accessibilityLabel="When">
                {(['upcoming', 'past'] as const).map(s => {
                    const selected = scope === s;
                    return (
                        <Pressable
                            key={s}
                            onPress={() => setScope(s)}
                            accessibilityRole="radio"
                            accessibilityState={{ selected }}
                            style={[styles.chip, selected && styles.chipActive]}
                        >
                            <Text style={[styles.chipText, selected && { color: '#FFFFFF' }]}>
                                {s === 'upcoming' ? 'Upcoming' : 'Past'}
                            </Text>
                        </Pressable>
                    );
                })}
            </View>

            {state.loading ? (
                <View style={styles.center}><ActivityIndicator color={theme.primary} /></View>
            ) : state.error && !state.items.length ? (
                <View style={styles.center}>
                    <Text style={styles.error}>{state.error}</Text>
                    <SecondaryButton title="Try again" onPress={load} />
                </View>
            ) : !state.items.length ? (
                <Empty kind={kind} scope={scope} onRequest={() => router.push('/request-ride')} onOffer={() => router.push('/offer-ride')} />
            ) : (
                <>
                    {state.items.map(item =>
                        'id_booking' in item ? (
                            <BookingCard key={item.id_booking} booking={item} canCancel={scope === 'upcoming'} onCancelled={onBookingCancelled} />
                        ) : (
                            <OfferedCard
                                key={item.id_ride}
                                ride={item}
                                requests={requests[item.id_ride] ?? []}
                                onHandled={load}
                                onAuthError={onError}
                            />
                        ),
                    )}
                    {state.error ? <Text style={[styles.error, { textAlign: 'center' }]}>{state.error}</Text> : null}
                    {state.next ? (
                        state.loadingMore ? (
                            <ActivityIndicator color={theme.primary} style={{ marginVertical: 8 }} />
                        ) : (
                            <SecondaryButton title="Load more" onPress={loadMore} />
                        )
                    ) : null}
                </>
            )}
        </Screen>
    );
}

function Segmented<T extends string>({ value, onChange, options, label }: {
    value: T; onChange: (v: T) => void; options: { value: T; label: string }[]; label: string;
}) {
    return (
        <View style={styles.segmented} accessibilityRole="tablist" accessibilityLabel={label}>
            {options.map(o => {
                const active = o.value === value;
                return (
                    <Pressable
                        key={o.value}
                        onPress={() => onChange(o.value)}
                        accessibilityRole="tab"
                        accessibilityState={{ selected: active }}
                        style={[styles.segment, active && styles.segmentActive]}
                    >
                        <Text style={[styles.segmentLabel, active && styles.segmentLabelActive]}>{o.label}</Text>
                    </Pressable>
                );
            })}
        </View>
    );
}

function Route({ ride }: { ride: RideInfo }) {
    return (
        <View style={styles.route}>
            <View style={styles.dots}>
                <View style={[styles.dot, { borderColor: theme.primary }]} />
                <View style={[styles.line, { backgroundColor: theme.border }]} />
                <View style={[styles.dot, { backgroundColor: theme.primary, borderColor: theme.primary }]} />
            </View>
            <View style={{ flex: 1, gap: 14 }}>
                <Text style={styles.place} numberOfLines={1}>{ride.source.name}</Text>
                <Text style={styles.place} numberOfLines={1}>{ride.destination.name}</Text>
            </View>
        </View>
    );
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

function OfferedCard({ ride, requests, onHandled, onAuthError }: {
    ride: MyRide; requests: RideRequest[]; onHandled: () => void; onAuthError: (e: unknown) => string;
}) {
    const router = useRouter();
    const status = RIDE_STATUS[ride.status];
    const booked = ride.total_seats - ride.available_seats;
    const pending = ride.requests.pending_requests;
    const car = vehicleText(ride.vehicle);
    return (
        <Card style={ride.status === 'cancelled' ? { opacity: 0.7 } : undefined}>
            <View style={styles.top}>
                <Badge label="Driving" tone="neutral" />
                <Badge label={status.label} tone={status.tone} />
                {pending ? <Badge label={`${plural(pending, 'request')} waiting`} tone="brand" /> : null}
            </View>
            <Route ride={ride} />
            <Text style={styles.meta}>
                {departureLabel(ride.departure_time)} · {booked}/{ride.total_seats} seats booked · {CURRENCY}{money(ride.price_per_seat)}/seat
            </Text>
            {car ? <Text style={styles.meta}>{car}</Text> : null}
            {ride.notes ? <Text style={styles.note}>“{ride.notes}”</Text> : null}
            <View style={{ marginTop: 4 }}>
                <TextLink label="View details" onPress={() => router.push({ pathname: '/my-rides/[id]', params: { id: ride.id_ride } })} />
            </View>
            {requests.length ? (
                <View style={styles.requestsBox}>
                    <RideRequestList requests={requests} onHandled={onHandled} onAuthError={onAuthError} />
                </View>
            ) : null}
        </Card>
    );
}

function BookingCard({ booking, canCancel, onCancelled }: {
    booking: MyBooking; canCancel: boolean; onCancelled: (id: string) => void;
}) {
    const router = useRouter();
    const { ride } = booking;
    const status = BOOKING_STATUS[booking.status];
    const car = vehicleText(ride.vehicle);
    const driver = ride.driver.full_name || 'Driver';
    const cancellable = canCancel && (booking.status === 'requested' || booking.status === 'accepted');
    const finished = !['requested', 'accepted'].includes(booking.status);
    return (
        <Card style={finished ? { opacity: 0.75 } : undefined}>
            <View style={styles.top}>
                <Badge label="Riding" tone="neutral" />
                <Badge label={status.label} tone={status.tone} />
            </View>
            <Route ride={ride} />
            <Text style={styles.meta}>
                {departureLabel(ride.departure_time)} · {plural(booking.seats_booked, 'seat')} · {CURRENCY}{money(booking.total_amount)} total
            </Text>
            <Text style={styles.meta}>With {driver}{car ? ` · ${car}` : ''}</Text>
            {booking.rider_note ? <Text style={styles.note}>“{booking.rider_note}”</Text> : null}
            <View style={styles.cardLinks}>
                <TextLink label="View details" onPress={() => router.push({ pathname: '/my-rides/booking/[id]', params: { id: booking.id_booking } })} />
            </View>
            {cancellable ? <CancelBooking booking={booking} onCancelled={onCancelled} /> : null}
        </Card>
    );
}

function Empty({ kind, scope, onRequest, onOffer }: { kind: Kind; scope: 'upcoming' | 'past'; onRequest: () => void; onOffer: () => void }) {
    if (scope === 'past') {
        return (
            <EmptyState
                title="Nothing here yet"
                body={kind === 'booked' ? 'Finished and cancelled bookings will show up here.' : 'Rides you drove or cancelled will show up here.'}
            />
        );
    }
    return kind === 'booked' ? (
        <EmptyState title="No upcoming bookings" body="Find a ride going your way and book a seat." action={<SecondaryButton title="Request a ride" onPress={onRequest} />} />
    ) : (
        <EmptyState title="No rides offered" body="Share your empty seats and split the cost." action={<SecondaryButton title="Offer a ride" onPress={onOffer} />} />
    );
}

const styles = StyleSheet.create({
    cardLinks: { marginTop: 4 },
    segmented: { flexDirection: 'row', backgroundColor: theme.border, borderRadius: 12, padding: 4 },
    segment: { flex: 1, paddingVertical: 10, borderRadius: 9, alignItems: 'center' },
    segmentActive: {
        backgroundColor: theme.card,
        shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 4, shadowOffset: { width: 0, height: 1 }, elevation: 1,
    },
    segmentLabel: { fontSize: 15, fontWeight: '600', color: theme.muted },
    segmentLabelActive: { color: theme.text },
    chips: { flexDirection: 'row', gap: 8 },
    chip: { paddingVertical: 7, paddingHorizontal: 14, borderRadius: 20, borderWidth: 1, borderColor: theme.border, backgroundColor: theme.card },
    chipActive: { backgroundColor: theme.primary, borderColor: theme.primary },
    chipText: { fontSize: 14, fontWeight: '600', color: theme.text },
    center: { alignItems: 'center', paddingVertical: 40, gap: 12 },
    error: { fontSize: 14, color: theme.error },
    top: { flexDirection: 'row', gap: 8, flexWrap: 'wrap', marginBottom: 6 },
    route: { flexDirection: 'row', gap: 12, alignItems: 'stretch', marginVertical: 4 },
    dots: { alignItems: 'center', paddingVertical: 5, width: 12 },
    dot: { width: 12, height: 12, borderRadius: 6, borderWidth: 2.5 },
    line: { flex: 1, width: 2, marginVertical: 3 },
    place: { fontSize: 16, fontWeight: '700', color: theme.text },
    meta: { fontSize: 14, color: theme.muted },
    note: { fontSize: 14, color: theme.text, fontStyle: 'italic' },
    cancel: { alignSelf: 'flex-start', marginTop: 6 },
    cancelText: { fontSize: 14, fontWeight: '700', color: theme.error },
    confirmRow: { flexDirection: 'row', alignItems: 'center', gap: 16, flexWrap: 'wrap' },
    confirmText: { fontSize: 14, color: theme.text, flex: 1 },
    keepText: { fontSize: 14, fontWeight: '700', color: theme.muted },
    hint: { fontSize: 13, color: theme.muted },
    requestsBox: { marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: theme.border },
});
