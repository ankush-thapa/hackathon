import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Colors } from '../constants/Colors';
import { formatPrice } from '../constants/Currency';
import { departureLabel } from '../services/format';
import { Ride } from '../services/rides';
import { Vehicle, vehicleLabel } from '../services/vehicles';
import { Badge, Card } from './ui';

const theme = Colors.light;

const STATUS: Record<Ride['status'], { label: string; tone: 'brand' | 'success' | 'muted' }> = {
    searching: { label: 'Finding a driver', tone: 'brand' },
    open: { label: 'Open for riders', tone: 'success' },
    cancelled: { label: 'Cancelled', tone: 'muted' },
};

export const RideCard = ({ ride, vehicle, footer }: { ride: Ride; vehicle?: Vehicle; footer?: React.ReactNode }) => {
    const status = STATUS[ride.status];
    const seats = `${ride.seats} seat${ride.seats === 1 ? '' : 's'}`;
    return (
        <Card style={ride.status === 'cancelled' ? { opacity: 0.7 } : undefined}>
            <View style={styles.top}>
                <Badge label={ride.role === 'driver' ? 'Offering' : 'Requesting'} tone="neutral" />
                <Badge label={status.label} tone={status.tone} />
            </View>
            <View style={styles.route}>
                <View style={styles.dots}>
                    <View style={[styles.dot, { borderColor: theme.primary }]} />
                    <View style={[styles.line, { backgroundColor: theme.border }]} />
                    <View style={[styles.dot, { backgroundColor: theme.primary, borderColor: theme.primary }]} />
                </View>
                <View style={{ flex: 1, gap: 14 }}>
                    <Text style={styles.place} numberOfLines={1}>{ride.from}</Text>
                    <Text style={styles.place} numberOfLines={1}>{ride.to}</Text>
                </View>
            </View>
            <Text style={styles.meta}>
                {departureLabel(ride.departAt)} · {ride.role === 'driver' ? `${seats} offered` : `${seats} needed`}
                {ride.pricePerSeat ? ` · ${formatPrice(ride.pricePerSeat)}/seat` : ''}
            </Text>
            {vehicle ? <Text style={styles.meta}>{vehicleLabel(vehicle)} · {vehicle.registrationNumber}</Text> : null}
            {ride.note ? <Text style={styles.note}>“{ride.note}”</Text> : null}
            {footer}
        </Card>
    );
};

const styles = StyleSheet.create({
    top: { flexDirection: 'row', gap: 8, flexWrap: 'wrap', marginBottom: 6 },
    route: { flexDirection: 'row', gap: 12, alignItems: 'stretch', marginVertical: 4 },
    dots: { alignItems: 'center', paddingVertical: 5, width: 12 },
    dot: { width: 12, height: 12, borderRadius: 6, borderWidth: 2.5 },
    line: { flex: 1, width: 2, marginVertical: 3 },
    place: { fontSize: 16, fontWeight: '700', color: theme.text },
    meta: { fontSize: 14, color: theme.muted },
    note: { fontSize: 14, color: theme.text, fontStyle: 'italic' },
});
