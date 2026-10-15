import React from 'react';
import { useRouter } from 'expo-router';
import { PrimaryButton } from '../../../components/PrimaryButton';
import { VehicleCard } from '../../../components/VehicleCard';
import { EmptyState, Screen, SecondaryButton } from '../../../components/ui';
import { removeVehicle, useVehicles } from '../../../services/vehicles';

export default function MyVehiclesScreen() {
    const router = useRouter();
    const vehicles = useVehicles();
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
            {vehicles.length === 0 ? (
                <EmptyState
                    title="No vehicles yet"
                    body="Add a vehicle to start offering rides."
                    action={<PrimaryButton title="Add a vehicle" onPress={goToAdd} />}
                />
            ) : (
                vehicles.map(v => <VehicleCard key={v.id} vehicle={v} onDelete={removeVehicle} />)
            )}
        </Screen>
    );
}
