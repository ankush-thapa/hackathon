import React, { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { Colors } from '../constants/Colors';
import { MyBooking, MyRidesError, cancelBooking } from '../services/myRides';
import { notifyBookingCancelled } from '../services/notifications';
import { useProfile } from '../services/profile';

const theme = Colors.light;

/** Two-step cancel so a stray tap doesn't cancel (no native confirm dialogs). */
export function CancelBooking({ booking, onCancelled }: { booking: MyBooking; onCancelled: (id: string) => void }) {
    const [confirming, setConfirming] = useState(false);
    const profile = useProfile();
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const confirm = async () => {
        setBusy(true);
        setError(null);
        try {
            await cancelBooking(booking.id_booking);
            onCancelled(booking.id_booking);
            // Tell the driver (best effort; the cancellation already succeeded).
            notifyBookingCancelled({
                driverId: booking.ride.driver.id_user,
                rideId: booking.ride.id_ride,
                bookingId: booking.id_booking,
                riderName: profile.fullName || 'A rider',
                seats: booking.seats_booked,
                from: booking.ride.source.name,
                to: booking.ride.destination.name,
                departure: booking.ride.departure_time,
            });
        } catch (e) {
            setError(e instanceof MyRidesError ? e.message : 'Could not cancel. Please try again.');
            setBusy(false);
        }
    };

    if (!confirming) {
        return (
            <Pressable onPress={() => setConfirming(true)} accessibilityRole="button" hitSlop={8} style={styles.cancel}>
                <Text style={styles.cancelText}>{booking.status === 'requested' ? 'Cancel request' : 'Cancel booking'}</Text>
            </Pressable>
        );
    }
    return (
        <View style={{ gap: 4, marginTop: 6 }}>
            <View style={styles.confirmRow}>
                <Text style={styles.confirmText}>Cancel this booking?</Text>
                {busy ? (
                    <ActivityIndicator color={theme.primary} />
                ) : (
                    <>
                        <Pressable onPress={() => setConfirming(false)} accessibilityRole="button" hitSlop={8}>
                            <Text style={styles.keepText}>Keep</Text>
                        </Pressable>
                        <Pressable onPress={confirm} accessibilityRole="button" hitSlop={8}>
                            <Text style={styles.cancelText}>Yes, cancel</Text>
                        </Pressable>
                    </>
                )}
            </View>
            {error ? <Text style={styles.error}>{error}</Text> : null}
        </View>
    );
}

const styles = StyleSheet.create({
    error: { fontSize: 14, color: theme.error },
    cancel: { alignSelf: 'flex-start', marginTop: 6 },
    cancelText: { fontSize: 14, fontWeight: '700', color: theme.error },
    confirmRow: { flexDirection: 'row', alignItems: 'center', gap: 16, flexWrap: 'wrap' },
    confirmText: { fontSize: 14, color: theme.text, flex: 1 },
    keepText: { fontSize: 14, fontWeight: '700', color: theme.muted },
});
