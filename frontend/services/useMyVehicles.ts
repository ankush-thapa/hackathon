import { useCallback, useState } from 'react';
import { useFocusEffect } from 'expo-router';
import { ApiError } from './api';
import { VehicleListNotReady, fetchMyVehicles, useVehicles } from './vehicles';

/**
 * The logged-in user's vehicles from GET /v1/vehicles, reloaded whenever the screen gains focus
 * (so a vehicle just added elsewhere shows up). Keeps the shared store as the source of truth.
 */
export function useMyVehicles(onAuthError?: () => void) {
    const vehicles = useVehicles();
    const [loaded, setLoaded] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const reload = useCallback(async () => {
        setError(null);
        try {
            await fetchMyVehicles();
        } catch (e) {
            if (e instanceof ApiError && e.status === 401) onAuthError?.();
            else if (!(e instanceof VehicleListNotReady)) setError(e instanceof ApiError ? e.message : 'Could not load your vehicles.');
        } finally {
            setLoaded(true);
        }
    }, [onAuthError]);

    useFocusEffect(useCallback(() => { reload(); }, [reload]));
    return { vehicles, loading: !loaded, error, reload };
}
