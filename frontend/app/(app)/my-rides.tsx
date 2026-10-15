import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Badge, Card, EmptyState, Screen, SecondaryButton, TextLink } from '../../components/ui';
import { Colors } from '../../constants/Colors';
import { RideRequestList } from '../../components/RideRequestRow';
import { departureLabel } from '../../services/format';
import { useProfile } from '../../services/profile';
import { CURRENCY } from '../../constants/Currency';
import { RideRequest, fetchPendingRequests } from '../../services/rideRequests';
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
            const [page, pending] = await Promise.all([
                kind === 'offered' ? fetchMyRides(scope) : fetchMyBookings(scope),
                kind === 'offered' && scope === 'upcoming' ? fetchPendingRequests() : Promise.resolve({}),
            ]);
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
            ) : pending && ride.status === 'open' ? (
                <Text style={styles.hint}>Requests made before this update can't be shown here yet.</Text>
            ) : null}
        </Card>
    );
}

function BookingCard({ booking, canCancel, onCancelled }: {
    booking: MyBooking; canCancel: boolean; onCancelled: (id: string) => void;
}) {
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
            {cancellable ? <CancelBooking booking={booking} onCancelled={onCancelled} /> : null}
        </Card>
    );
}

/** Two-step cancel so a stray tap doesn't cancel (no native confirm dialogs). */
function CancelBooking({ booking, onCancelled }: { booking: MyBooking; onCancelled: (id: string) => void }) {
    const [confirming, setConfirming] = useState(false);
    const profile = useProfile();
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const confirm = async () => {
        setBusy(true);
        setError(null);
        try {
            await cancelBooking(booking.id_booking);
            onCancelled(booking.id_booking);
            // Tell the driver (best effort; the cancellation already succeeded).
        } catch (e) {
            setError(e instanceof MyRidesError ? e.message : 'Could not cancel. Please try again.');
            setBusy(false);
        }
    };

    if (!confirming) {
        return (
            <Pressable onPress={() => setConfirming(true)} accessibilityRole="button" hitSlop={8} style={styles.cancel}>
                <Text style={styles.cancelText}>{booking.status === 'requested' ? 'Cancel request' : 'Cancel booking'}</Text>
            </Pressable>
        );
    }
    return (
        <View style={{ gap: 4, marginTop: 6 }}>
            <View style={styles.confirmRow}>
                <Text style={styles.confirmText}>Cancel this booking?</Text>
                {busy ? (
                    <ActivityIndicator color={theme.primary} />
                ) : (
                    <>
                        <Pressable onPress={() => setConfirming(false)} accessibilityRole="button" hitSlop={8}>
                            <Text style={styles.keepText}>Keep</Text>
                        </Pressable>
                        <Pressable onPress={confirm} accessibilityRole="button" hitSlop={8}>
                            <Text style={styles.cancelText}>Yes, cancel</Text>
                        </Pressable>
                    </>
                )}
            </View>
            {error ? <Text style={styles.error}>{error}</Text> : null}
        </View>
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
