import React, { useState } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { Colors } from '../constants/Colors';
import { Vehicle } from '../types/vehicle';

type Props = {
    vehicle: Vehicle;
    onDelete: (id: string) => void;
};

export const VehicleCard = ({ vehicle, onDelete }: Props) => {
    const theme = Colors.light;
    // Two-step delete keeps it cross-platform (Alert.alert has no confirm on web).
    const [confirming, setConfirming] = useState(false);

    return (
        <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.border }]}>
            <Image source={{ uri: vehicle.photoUri }} style={styles.photo} accessibilityLabel={`Photo of ${vehicle.name}`} />

            <View style={styles.info}>
                <Text style={[styles.name, { color: theme.text }]} numberOfLines={1}>{vehicle.name}</Text>
                <Text style={[styles.number, { color: theme.text }]}>{vehicle.number}</Text>
                <Text style={[styles.colorText, { color: theme.muted }]} numberOfLines={1}>Colour: {vehicle.color}</Text>
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
                    accessibilityLabel={`Delete ${vehicle.number}`}
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
    name: {
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
