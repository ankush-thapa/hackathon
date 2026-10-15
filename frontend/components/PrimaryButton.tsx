import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text } from 'react-native';
import { Colors } from '../constants/Colors';

type Props = { title: string; onPress: () => void; loading?: boolean; disabled?: boolean };

export const PrimaryButton = ({ title, onPress, loading, disabled }: Props) => {
    const theme = Colors.light;
    const inactive = disabled || loading;
    return (
        <Pressable
            onPress={onPress}
            disabled={inactive}
            accessibilityRole="button"
            accessibilityState={{ disabled: inactive, busy: loading }}
            style={({ pressed }) => [
                styles.button,
                { backgroundColor: theme.primary },
                inactive && { opacity: 0.6 },
                pressed && !inactive && { opacity: 0.85 },
            ]}
        >
            {loading ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.text}>{title}</Text>}
        </Pressable>
    );
};

const styles = StyleSheet.create({
    button: { minHeight: 52, borderRadius: 12, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 20 },
    text: { color: '#FFFFFF', fontSize: 17, fontWeight: '700' },
});
