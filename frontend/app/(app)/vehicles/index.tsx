import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Colors } from '../../../constants/Colors';
import { PrimaryButton } from '../../../components/PrimaryButton';
import { VehicleCard } from '../../../components/VehicleCard';
import { EmptyState, Screen, SecondaryButton } from '../../../components/ui';
import { fetchMyVehicles, removeVehicle, useVehicles } from '../../../services/vehicles';

export default function MyVehiclesScreen() {
    const router = useRouter();
    const vehicles = useVehicles();
    const [error, setError] = useState<string | null>(null);
    useEffect(() => { fetchMyVehicles().catch(e => setError(e.message)); }, []);
    const onDelete = async (id: string) => {
        setError(null);
        try { await removeVehicle(id); } catch (e) { setError(e instanceof Error ? e.message : 'Could not delete vehicle'); }
    };
    // Set by the Add Vehicle page after a successful add, e.g. /vehicles?added=Maruti%20Suzuki%20Swift
    const { added } = useLocalSearchParams<{ added?: string }>();
    const theme = Colors.light;
    const goToAdd = () => router.push('/vehicles/add');

    return (
        <Screen
            title="My vehicles"
            subtitle={
                vehicles.length === 0
                    ? 'Vehicles you add will show up here.'
                    : `${vehicles.length} ${vehicles.length === 1 ? 'vehicle' : 'vehicles'} added`
            }
            action={vehicles.length > 0 ? <SecondaryButton title="+ Add" onPress={goToAdd} /> : undefined}
        >
            {error ? <Text style={{ color: theme.error }}>{error}</Text> : null}
            {added ? (
                <View style={[styles.success, { backgroundColor: theme.successBg }]} accessibilityLiveRegion="polite">
                    <Text style={[styles.successText, { color: theme.success }]}>{added} added successfully.</Text>
                </View>
            ) : null}
            {vehicles.length === 0 ? (
                <EmptyState
                    title="No vehicles yet"
                    body="Add a vehicle to start offering rides."
                    action={<PrimaryButton title="Add a vehicle" onPress={goToAdd} />}
                />
            ) : (
                vehicles.map(v => <VehicleCard key={v.id} vehicle={v} onDelete={onDelete} />)
            )}
        </Screen>
    );
}

const styles = StyleSheet.create({
    success: { borderRadius: 12, padding: 14 },
    successText: { fontSize: 15, fontWeight: '600' },
});
