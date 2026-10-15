import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Colors } from '../../constants/Colors';
import { PrimaryButton } from '../../components/PrimaryButton';
import { VehicleCard } from '../../components/VehicleCard';
import { useVehicles } from '../../context/VehiclesContext';

export default function MyVehiclesScreen() {
    const theme = Colors.light;
    const router = useRouter();
    const { vehicles, removeVehicle } = useVehicles();

    return (
        <ScrollView contentContainerStyle={styles.scroll}>
            <View style={styles.main}>
                <Text style={[styles.title, { color: theme.text }]}>My vehicles</Text>
                <Text style={[styles.subtitle, { color: theme.muted }]}>
                    {vehicles.length === 0
                        ? 'Vehicles you add will show up here.'
                        : `${vehicles.length} ${vehicles.length === 1 ? 'vehicle' : 'vehicles'} added`}
                </Text>

                {vehicles.length === 0 ? (
                    <View style={[styles.empty, { backgroundColor: theme.card, borderColor: theme.border }]}>
                        <Text style={[styles.emptyTitle, { color: theme.text }]}>No vehicles yet</Text>
                        <Text style={[styles.emptyText, { color: theme.muted }]}>
                            Add a vehicle to start offering rides.
                        </Text>
                        <PrimaryButton title="Add a vehicle" onPress={() => router.push('/add-vehicle')} />
                    </View>
                ) : (
                    <>
                        {vehicles.map(v => <VehicleCard key={v.id} vehicle={v} onDelete={removeVehicle} />)}
                        <View style={styles.addMore}>
                            <PrimaryButton title="Add another vehicle" onPress={() => router.push('/add-vehicle')} />
                        </View>
                    </>
                )}
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    scroll: {
        flexGrow: 1,
        paddingBottom: 32,
    },
    main: {
        width: '100%',
        maxWidth: 600,
        alignSelf: 'center',
        paddingHorizontal: 24,
        paddingTop: 32,
        gap: 12,
    },
    title: {
        fontSize: 28,
        fontWeight: '800',
        letterSpacing: -0.5,
    },
    subtitle: {
        fontSize: 15,
        marginBottom: 8,
    },
    empty: {
        borderWidth: 1,
        borderRadius: 16,
        padding: 24,
        gap: 10,
    },
    emptyTitle: {
        fontSize: 18,
        fontWeight: '700',
    },
    emptyText: {
        fontSize: 15,
        marginBottom: 8,
    },
    addMore: {
        marginTop: 8,
    },
});
