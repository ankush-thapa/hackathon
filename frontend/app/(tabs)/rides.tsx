import React, { useMemo, useState } from 'react';
import { FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import { Colors } from '../../constants/Colors';
import { CURRENCY, MOCK_RIDES, Ride, RideStatus } from '../../data/mockRides';

type Segment = 'upcoming' | 'past';

const theme = Colors.light;

const STATUS_STYLES: Record<RideStatus, { label: string; fg: string; bg: string }> = {
    confirmed: { label: 'Confirmed', fg: '#3F6B45', bg: '#E6EFE7' },
    pending: { label: 'Pending', fg: '#8A6116', bg: '#FBF0DC' },
    completed: { label: 'Completed', fg: theme.muted, bg: '#EEF1F4' },
    cancelled: { label: 'Cancelled', fg: theme.error, bg: '#FBE9E5' },
};

const formatDay = (date: Date) => {
    const today = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(today.getDate() + 1);
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);
    const same = (a: Date, b: Date) => a.toDateString() === b.toDateString();
    if (same(date, today)) return 'Today';
    if (same(date, tomorrow)) return 'Tomorrow';
    if (same(date, yesterday)) return 'Yesterday';
    return date.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' });
};

const formatTime = (date: Date) =>
    date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });

export default function MyRidesScreen() {
    const [segment, setSegment] = useState<Segment>('upcoming');

    const { upcoming, past } = useMemo(() => {
        const now = Date.now();
        const sorted = [...MOCK_RIDES].sort((a, b) => +new Date(a.departAt) - +new Date(b.departAt));
        return {
            upcoming: sorted.filter(r => +new Date(r.departAt) >= now),
            past: sorted.filter(r => +new Date(r.departAt) < now).reverse(),
        };
    }, []);

    const rides = segment === 'upcoming' ? upcoming : past;

    return (
        <FlatList
            data={rides}
            keyExtractor={r => String(r.id)}
            contentContainerStyle={styles.scroll}
            ListHeaderComponent={
                <View style={styles.headerBlock}>
                    <Text style={styles.title}>My Rides</Text>
                    <Text style={styles.subtitle}>Rides you're driving or riding in.</Text>
                    <View style={styles.segmented}>
                        {(['upcoming', 'past'] as Segment[]).map(s => {
                            const active = segment === s;
                            const count = s === 'upcoming' ? upcoming.length : past.length;
                            return (
                                <Pressable
                                    key={s}
                                    onPress={() => setSegment(s)}
                                    accessibilityRole="tab"
                                    accessibilityState={{ selected: active }}
                                    style={[styles.segment, active && styles.segmentActive]}
                                >
                                    <Text style={[styles.segmentLabel, active && styles.segmentLabelActive]}>
                                        {s === 'upcoming' ? 'Upcoming' : 'Past'} ({count})
                                    </Text>
                                </Pressable>
                            );
                        })}
                    </View>
                </View>
            }
            renderItem={({ item }) => <RideCard ride={item} />}
            ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
            ListEmptyComponent={
                <View style={styles.empty}>
                    <Text style={styles.emptyTitle}>
                        {segment === 'upcoming' ? 'No upcoming rides' : 'No past rides yet'}
                    </Text>
                    <Text style={styles.emptyText}>
                        {segment === 'upcoming'
                            ? 'Offer a ride or find one to see it here.'
                            : 'Rides you complete will show up here.'}
                    </Text>
                </View>
            }
        />
    );
}

function RideCard({ ride }: { ride: Ride }) {
    const date = new Date(ride.departAt);
    const status = STATUS_STYLES[ride.status];
    const isDriver = ride.role === 'driver';
    const faded = ride.status === 'cancelled';
    const seatsLeft = ride.seatsTotal - ride.seatsBooked;

    return (
        <Pressable style={({ pressed }) => [styles.card, faded && { opacity: 0.6 }, pressed && { opacity: 0.8 }]}>
            <View style={styles.cardTop}>
                <Text style={styles.when}>
                    {formatDay(date)} · {formatTime(date)}
                </Text>
                <View style={[styles.pill, { backgroundColor: status.bg }]}>
                    <Text style={[styles.pillText, { color: status.fg }]}>{status.label}</Text>
                </View>
            </View>

            <View style={styles.route}>
                <View style={styles.routeRail}>
                    <View style={[styles.dot, { backgroundColor: theme.primary }]} />
                    <View style={styles.line} />
                    <View style={[styles.dot, styles.dotEnd]} />
                </View>
                <View style={styles.routeText}>
                    <Text style={styles.place} numberOfLines={1}>{ride.from}</Text>
                    <Text style={styles.place} numberOfLines={1}>{ride.to}</Text>
                </View>
            </View>

            <View style={styles.divider} />

            <View style={styles.cardBottom}>
                <View style={{ flex: 1, gap: 2 }}>
                    <View style={styles.roleRow}>
                        <View style={[styles.roleChip, isDriver && { backgroundColor: theme.primary }]}>
                            <Text style={[styles.roleText, isDriver && { color: '#FFFFFF' }]}>
                                {isDriver ? 'Driving' : 'Riding'}
                            </Text>
                        </View>
                        {!isDriver && <Text style={styles.driver} numberOfLines={1}>with {ride.driverName}</Text>}
                    </View>
                    <Text style={styles.meta} numberOfLines={1}>
                        {ride.car} · {isDriver ? `${ride.seatsBooked}/${ride.seatsTotal} seats booked` : `${seatsLeft} seat${seatsLeft === 1 ? '' : 's'} left`}
                    </Text>
                </View>
                <View style={{ alignItems: 'flex-end' }}>
                    <Text style={styles.price}>{CURRENCY}{ride.pricePerSeat}</Text>
                    <Text style={styles.meta}>per seat</Text>
                </View>
            </View>
        </Pressable>
    );
}

const styles = StyleSheet.create({
    scroll: {
        flexGrow: 1,
        width: '100%',
        maxWidth: 600,
        alignSelf: 'center',
        paddingHorizontal: 24,
        paddingTop: 32,
        paddingBottom: 32,
    },
    headerBlock: { gap: 4, marginBottom: 16 },
    title: { fontSize: 28, fontWeight: '800', color: theme.text },
    subtitle: { fontSize: 15, color: theme.muted, marginBottom: 12 },
    segmented: {
        flexDirection: 'row',
        backgroundColor: '#F1F0EC',
        borderRadius: 12,
        padding: 4,
    },
    segment: { flex: 1, paddingVertical: 10, borderRadius: 9, alignItems: 'center' },
    segmentActive: {
        backgroundColor: theme.card,
        shadowColor: '#000',
        shadowOpacity: 0.06,
        shadowRadius: 4,
        shadowOffset: { width: 0, height: 1 },
        elevation: 1,
    },
    segmentLabel: { fontSize: 15, fontWeight: '600', color: theme.muted },
    segmentLabelActive: { color: theme.text },

    card: {
        backgroundColor: theme.card,
        borderColor: theme.border,
        borderWidth: 1,
        borderRadius: 14,
        padding: 16,
        gap: 14,
    },
    cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
    when: { fontSize: 15, fontWeight: '700', color: theme.text },
    pill: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
    pillText: { fontSize: 12, fontWeight: '700' },

    route: { flexDirection: 'row', gap: 12 },
    routeRail: { alignItems: 'center', paddingVertical: 5 },
    dot: { width: 10, height: 10, borderRadius: 5 },
    dotEnd: { backgroundColor: theme.card, borderWidth: 2, borderColor: theme.text },
    line: { flex: 1, width: 2, backgroundColor: theme.border, marginVertical: 3 },
    routeText: { flex: 1, gap: 14 },
    place: { fontSize: 16, fontWeight: '600', color: theme.text },

    divider: { height: 1, backgroundColor: theme.border },
    cardBottom: { flexDirection: 'row', alignItems: 'center', gap: 12 },
    roleRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
    roleChip: { backgroundColor: '#EEF1F4', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
    roleText: { fontSize: 12, fontWeight: '700', color: theme.text },
    driver: { fontSize: 14, fontWeight: '600', color: theme.text, flexShrink: 1 },
    meta: { fontSize: 13, color: theme.muted },
    price: { fontSize: 17, fontWeight: '800', color: theme.text },

    empty: { alignItems: 'center', paddingVertical: 48, gap: 6 },
    emptyTitle: { fontSize: 17, fontWeight: '700', color: theme.text },
    emptyText: { fontSize: 14, color: theme.muted, textAlign: 'center' },
});
