import React, { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { RideCard } from '../../components/RideCard';
import { EmptyState, Screen, SecondaryButton } from '../../components/ui';
import { Colors } from '../../constants/Colors';
import { Ride, RideRole, cancelRide, isUpcoming, sortByDeparture, useRides } from '../../services/rides';
import { useVehicles } from '../../services/vehicles';

const theme = Colors.light;

type Tab = 'upcoming' | 'past';
type RoleFilter = 'all' | RideRole;

const ROLE_FILTERS: { value: RoleFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'driver', label: 'Offering' },
    { value: 'passenger', label: 'Requesting' },
];

/** Rides the user has requested or offered, split into upcoming and past/cancelled. */
export default function MyRidesScreen() {
    const router = useRouter();
    const rides = useRides();
    const vehicles = useVehicles();
    const [tab, setTab] = useState<Tab>('upcoming');
    const [role, setRole] = useState<RoleFilter>('all');

    const { upcoming, past } = useMemo(() => {
        const mine = role === 'all' ? rides : rides.filter(r => r.role === role);
        return {
            upcoming: mine.filter(isUpcoming).sort(sortByDeparture),
            // Most recent first: departed rides and anything cancelled.
            past: mine.filter(r => !isUpcoming(r)).sort((a, b) => sortByDeparture(b, a)),
        };
    }, [rides, role]);

    const list = tab === 'upcoming' ? upcoming : past;

    return (
        <Screen title="My rides" subtitle="Rides you've requested or offered.">
            {/* Upcoming / Past */}
            <View style={styles.segmented} accessibilityRole="tablist">
                {(['upcoming', 'past'] as Tab[]).map(t => {
                    const active = tab === t;
                    const count = t === 'upcoming' ? upcoming.length : past.length;
                    return (
                        <Pressable
                            key={t}
                            onPress={() => setTab(t)}
                            accessibilityRole="tab"
                            accessibilityState={{ selected: active }}
                            style={[styles.segment, active && styles.segmentActive]}
                        >
                            <Text style={[styles.segmentLabel, active && styles.segmentLabelActive]}>
                                {t === 'upcoming' ? 'Upcoming' : 'Past'} ({count})
                            </Text>
                        </Pressable>
                    );
                })}
            </View>

            {/* Role filter */}
            <View style={styles.chips} accessibilityRole="radiogroup" accessibilityLabel="Filter by role">
                {ROLE_FILTERS.map(f => {
                    const selected = role === f.value;
                    return (
                        <Pressable
                            key={f.value}
                            onPress={() => setRole(f.value)}
                            accessibilityRole="radio"
                            accessibilityState={{ selected }}
                            style={[styles.chip, selected && styles.chipActive]}
                        >
                            <Text style={[styles.chipText, selected && { color: '#FFFFFF' }]}>{f.label}</Text>
                        </Pressable>
                    );
                })}
            </View>

            {list.length ? (
                list.map(r => (
                    <RideCard
                        key={r.id}
                        ride={r}
                        vehicle={vehicles.find(v => v.id === r.vehicleId)}
                        footer={tab === 'upcoming' ? <CancelButton ride={r} /> : undefined}
                    />
                ))
            ) : tab === 'upcoming' ? (
                <EmptyState
                    title="No upcoming rides"
                    body={
                        role === 'driver' ? "You haven't offered any rides yet."
                            : role === 'passenger' ? "You haven't requested any rides yet."
                            : 'Request a ride or offer your empty seats to get started.'
                    }
                    action={
                        <View style={styles.emptyActions}>
                            {role !== 'driver' && <SecondaryButton title="Request a ride" onPress={() => router.push('/request-ride')} />}
                            {role !== 'passenger' && <SecondaryButton title="Offer a ride" onPress={() => router.push('/offer-ride')} />}
                        </View>
                    }
                />
            ) : (
                <EmptyState title="No past rides" body="Completed and cancelled rides will show up here." />
            )}
        </Screen>
    );
}

/** Two-step cancel so a stray tap doesn't cancel a ride (no native confirm dialogs). */
function CancelButton({ ride }: { ride: Ride }) {
    const [confirming, setConfirming] = useState(false);
    if (!confirming) {
        return (
            <Pressable onPress={() => setConfirming(true)} accessibilityRole="button" hitSlop={8} style={styles.cancel}>
                <Text style={styles.cancelText}>{ride.role === 'driver' ? 'Cancel offer' : 'Cancel request'}</Text>
            </Pressable>
        );
    }
    return (
        <View style={styles.confirmRow}>
            <Text style={styles.confirmText}>Cancel this ride?</Text>
            <Pressable onPress={() => setConfirming(false)} accessibilityRole="button" hitSlop={8}>
                <Text style={styles.keepText}>Keep</Text>
            </Pressable>
            <Pressable onPress={() => cancelRide(ride.id)} accessibilityRole="button" hitSlop={8}>
                <Text style={styles.cancelText}>Yes, cancel</Text>
            </Pressable>
        </View>
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
    chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
    chip: { paddingVertical: 7, paddingHorizontal: 14, borderRadius: 20, borderWidth: 1, borderColor: theme.border, backgroundColor: theme.card },
    chipActive: { backgroundColor: theme.primary, borderColor: theme.primary },
    chipText: { fontSize: 14, fontWeight: '600', color: theme.text },
    emptyActions: { gap: 10 },
    cancel: { alignSelf: 'flex-start', marginTop: 6 },
    cancelText: { fontSize: 14, fontWeight: '700', color: theme.error },
    confirmRow: { flexDirection: 'row', alignItems: 'center', gap: 16, marginTop: 6, flexWrap: 'wrap' },
    confirmText: { fontSize: 14, color: theme.text, flex: 1 },
    keepText: { fontSize: 14, fontWeight: '700', color: theme.muted },
});
