import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { RideCard } from '../../components/RideCard';
import { Card, EmptyState, Screen, SectionTitle, TextLink } from '../../components/ui';
import { Icon } from '../../components/Icon';
import { Colors } from '../../constants/Colors';
import { useProfile } from '../../services/profile';
import { isUpcoming, sortByDeparture, useRides } from '../../services/rides';
import { getSession } from '../../services/session';
import { useVehicles, vehicleLabel } from '../../services/vehicles';

const theme = Colors.light;

function greeting() {
    const h = new Date().getHours();
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
    const rides = useRides();
    const vehicles = useVehicles();
    const session = getSession();

    const firstName = profile.fullName.split(' ')[0];
    const upcoming = rides.filter(isUpcoming).sort(sortByDeparture);
    const defaultVehicle = vehicles.find(v => v.isDefault);

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
            {upcoming.length ? (
                upcoming.slice(0, 2).map(r => (
                    <RideCard key={r.id} ride={r} vehicle={vehicles.find(v => v.id === r.vehicleId)} />
                ))
            ) : (
                <EmptyState title="No upcoming rides" body="Rides you request or offer will show up here." />
            )}

            <SectionTitle title="My vehicles" action={<TextLink label="Manage" onPress={() => router.push('/vehicles')} />} />
            {defaultVehicle ? (
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
});
