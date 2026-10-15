// Sample rides for the My Rides screen. Replace with an API call (e.g. GET /rides) later.

export type RideRole = 'driver' | 'passenger';
export type RideStatus = 'confirmed' | 'pending' | 'completed' | 'cancelled';

export type Ride = {
    id: number;
    from: string;
    to: string;
    departAt: string; // ISO timestamp
    role: RideRole;
    status: RideStatus;
    driverName: string;
    car: string;
    seatsBooked: number;
    seatsTotal: number;
    pricePerSeat: number;
};

export const CURRENCY = 'AED';

// Dates are relative to "now" so upcoming rides always stay upcoming.
const at = (dayOffset: number, hour: number, minute = 0) => {
    const d = new Date();
    d.setDate(d.getDate() + dayOffset);
    d.setHours(hour, minute, 0, 0);
    return d.toISOString();
};

export const MOCK_RIDES: Ride[] = [
    { id: 1, from: 'Dubai Marina', to: 'Business Bay', departAt: at(0, 18, 30), role: 'driver', status: 'confirmed', driverName: 'You', car: 'Toyota Camry · White', seatsBooked: 2, seatsTotal: 3, pricePerSeat: 15 },
    { id: 2, from: 'JLT Cluster D', to: 'Dubai Internet City', departAt: at(1, 8, 15), role: 'passenger', status: 'confirmed', driverName: 'Aisha K.', car: 'Nissan Altima · Grey', seatsBooked: 3, seatsTotal: 4, pricePerSeat: 10 },
    { id: 3, from: 'Al Barsha', to: 'Dubai Silicon Oasis', departAt: at(2, 9, 0), role: 'passenger', status: 'pending', driverName: 'Rahul M.', car: 'Honda Civic · Blue', seatsBooked: 1, seatsTotal: 3, pricePerSeat: 20 },
    { id: 4, from: 'Downtown Dubai', to: 'Abu Dhabi Corniche', departAt: at(4, 7, 30), role: 'driver', status: 'confirmed', driverName: 'You', car: 'Toyota Camry · White', seatsBooked: 1, seatsTotal: 3, pricePerSeat: 45 },
    { id: 5, from: 'Business Bay', to: 'Dubai Marina', departAt: at(-1, 19, 0), role: 'driver', status: 'completed', driverName: 'You', car: 'Toyota Camry · White', seatsBooked: 3, seatsTotal: 3, pricePerSeat: 15 },
    { id: 6, from: 'Dubai Internet City', to: 'JLT Cluster D', departAt: at(-3, 18, 45), role: 'passenger', status: 'completed', driverName: 'Omar S.', car: 'Kia Optima · Black', seatsBooked: 2, seatsTotal: 4, pricePerSeat: 10 },
    { id: 7, from: 'Deira City Centre', to: 'Dubai Mall', departAt: at(-6, 12, 0), role: 'passenger', status: 'cancelled', driverName: 'Priya N.', car: 'Hyundai Elantra · Red', seatsBooked: 0, seatsTotal: 3, pricePerSeat: 12 },
];
