import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { Vehicle } from '../types/vehicle';

type VehiclesContextValue = {
    vehicles: Vehicle[];
    addVehicle: (vehicle: Omit<Vehicle, 'id'>) => Vehicle;
    removeVehicle: (id: string) => void;
};

const VehiclesContext = createContext<VehiclesContextValue | null>(null);

/**
 * Shared vehicle list for the Add Vehicle and My Vehicles pages.
 * Frontend only: data lives in memory until a backend endpoint exists —
 * swap the bodies of addVehicle/removeVehicle for API calls then.
 */
export const VehiclesProvider = ({ children }: { children: React.ReactNode }) => {
    const [vehicles, setVehicles] = useState<Vehicle[]>([]);

    const addVehicle = useCallback((data: Omit<Vehicle, 'id'>) => {
        const vehicle = { ...data, id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}` };
        setVehicles(prev => [...prev, vehicle]);
        return vehicle;
    }, []);

    const removeVehicle = useCallback((id: string) => {
        setVehicles(prev => prev.filter(v => v.id !== id));
    }, []);

    const value = useMemo(() => ({ vehicles, addVehicle, removeVehicle }), [vehicles, addVehicle, removeVehicle]);
    return <VehiclesContext.Provider value={value}>{children}</VehiclesContext.Provider>;
};

export const useVehicles = () => {
    const ctx = useContext(VehiclesContext);
    if (!ctx) throw new Error('useVehicles must be used inside <VehiclesProvider>');
    return ctx;
};
