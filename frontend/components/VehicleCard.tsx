import React, { useState } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { Colors } from '../constants/Colors';
import { Badge } from './ui';
import { Vehicle, vehicleLabel } from '../services/vehicles';

type Props = {
    vehicle: Vehicle;
    onDelete: (id: string) => void;
};

// Stored without spaces (MH12AB1234); show it grouped (MH 12 AB 1234) for readability.
const formatRegistration = (reg: string) =>
    reg.replace(/^([A-Z]{2})(\d{1,2})([A-Z]{0,4})(\d{4})$/, (_, a, b, c, d) => [a, b, c, d].filter(Boolean).join(' '))
        .replace(/^(\d{2})(BH)(\d{4})([A-Z]{1,2})$/, '$1 $2 $3 $4');

export const VehicleCard = ({ vehicle, onDelete }: Props) => {
    const theme = Colors.light;
    // Two-step delete keeps it cross-platform (Alert.alert has no confirm on web).
    const [confirming, setConfirming] = useState(false);

    return (
        <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.border }]}>
            {vehicle.photoUrl ? (
                <Image source={{ uri: vehicle.photoUrl }} style={styles.photo} accessibilityLabel={`Photo of ${vehicleLabel(vehicle)}`} />
            ) : (
                <View style={[styles.photo, { backgroundColor: theme.background }]} />
            )}

            <View style={styles.info}>
                <View style={styles.titleRow}>
                    <Text style={[styles.name, { color: theme.text }]} numberOfLines={1}>{vehicleLabel(vehicle)}</Text>
                    {vehicle.isDefault ? <Badge label="Default" tone="brand" /> : null}
                </View>
                <Text style={[styles.number, { color: theme.text }]}>{formatRegistration(vehicle.registrationNumber)}</Text>
                <Text style={[styles.colorText, { color: theme.muted }]} numberOfLines={1}>
                    {vehicle.colour} · {vehicle.seatCapacity} {vehicle.seatCapacity === 1 ? 'seat' : 'seats'}
                </Text>
            </View>

            {confirming ? (
                <View style={styles.actions}>
                    <Pressable
                        onPress={() => setConfirming(false)}
                        style={({ pressed }) => [styles.btn, { borderColor: theme.border }, pressed && styles.pressed]}
                    >
                        <Text style={[styles.btnText, { color: theme.text }]}>Cancel</Text>
                    </Pressable>
                    <Pressable
                        onPress={() => onDelete(vehicle.id)}
                        style={({ pressed }) => [styles.btn, { backgroundColor: theme.error, borderColor: theme.error }, pressed && styles.pressed]}
                    >
                        <Text style={[styles.btnText, { color: '#FFFFFF' }]}>Delete</Text>
                    </Pressable>
                </View>
            ) : (
                <Pressable
                    onPress={() => setConfirming(true)}
                    accessibilityLabel={`Remove ${vehicleLabel(vehicle)}`}
                    style={({ pressed }) => [styles.btn, { borderColor: theme.error }, pressed && styles.pressed]}
                >
                    <Text style={[styles.btnText, { color: theme.error }]}>Remove</Text>
                </Pressable>
            )}
        </View>
    );
};

const styles = StyleSheet.create({
    card: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 14,
        padding: 12,
        borderWidth: 1,
        borderRadius: 12,
    },
    photo: {
        width: 56,
        height: 56,
        borderRadius: 10,
        backgroundColor: '#EEE',
    },
    info: {
        flex: 1,
        gap: 3,
    },
    titleRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    name: {
        flexShrink: 1,
        fontSize: 17,
        fontWeight: '700',
    },
    number: {
        fontSize: 14,
        fontWeight: '600',
        letterSpacing: 0.5,
    },
    colorText: {
        fontSize: 14,
    },
    actions: {
        flexDirection: 'row',
        gap: 6,
    },
    btn: {
        paddingVertical: 7,
        paddingHorizontal: 12,
        borderRadius: 16,
        borderWidth: 1,
    },
    btnText: {
        fontSize: 13,
        fontWeight: '600',
    },
    pressed: {
        opacity: 0.75,
    },
});
