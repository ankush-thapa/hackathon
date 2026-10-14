import React, { useCallback, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { Colors } from '../../constants/Colors';
import { API_URL } from '../../constants/Config';

export default function HomeScreen() {
    const theme = Colors.light;
    const [total, setTotal] = useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Refetch whenever the tab is shown so the count stays current.
    useFocusEffect(useCallback(() => {
        fetch(`${API_URL}/users`)
            .then(res => res.json())
            .then((users: unknown[]) => { setTotal(users.length); setError(null); })
            .catch(() => setError(`Could not reach the API at ${API_URL}`));
    }, []));

    return (
        <View style={styles.main}>
            <Text style={[styles.label, { color: theme.muted }]}>Total users</Text>
            {error ? (
                <Text style={{ color: theme.error }}>{error}</Text>
            ) : total === null ? (
                <ActivityIndicator color={theme.primary} />
            ) : (
                <Text style={[styles.count, { color: theme.text }]}>{total}</Text>
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    main: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
    },
    label: {
        fontSize: 17,
        fontWeight: '600',
    },
    count: {
        fontSize: 72,
        fontWeight: '800',
    },
});
