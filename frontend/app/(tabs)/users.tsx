import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Colors } from '../../constants/Colors';
import { API_URL } from '../../constants/Config';

type UserId = { id: string };

export default function UsersScreen() {
    const theme = Colors.light;
    const [userIds, setUserIds] = useState<string[]>([]);
    const [greetings, setGreetings] = useState<Record<string, string>>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetch(`${API_URL}/users`)
            .then(res => res.json())
            .then((users: UserId[]) => setUserIds(users.map(u => u.id)))
            .catch(() => setError(`Could not reach the API at ${API_URL}`))
            .finally(() => setLoading(false));
    }, []);

    const reveal = async (id: string) => {
        if (greetings[id]) return;
        try {
            const res = await fetch(`${API_URL}/hello/${id}`);
            const data = await res.json();
            setGreetings(prev => ({ ...prev, [id]: data.message ?? data.detail }));
        } catch {
            setGreetings(prev => ({ ...prev, [id]: 'Request failed' }));
        }
    };

    return (
        <ScrollView contentContainerStyle={styles.scroll}>
            <View style={styles.main}>
                <Text style={[styles.title, { color: theme.text }]}>Users</Text>
                <Text style={[styles.subtitle, { color: theme.muted }]}>Tap a number to reveal the user.</Text>

                {loading && <ActivityIndicator color={theme.primary} />}
                {error && <Text style={{ color: theme.error }}>{error}</Text>}

                {userIds.map(id => (
                    <Pressable
                        key={id}
                        onPress={() => reveal(id)}
                        style={({ pressed }) => [
                            styles.row,
                            { backgroundColor: theme.card, borderColor: theme.border },
                            pressed && { opacity: 0.75 },
                        ]}
                    >
                        <View style={[styles.badge, { backgroundColor: theme.primary }]}>
                            <Text style={styles.badgeText}>{id}</Text>
                        </View>
                        <Text style={[styles.name, { color: greetings[id] ? theme.text : theme.muted }]}>
                            {greetings[id] ?? 'Tap to reveal'}
                        </Text>
                    </Pressable>
                ))}
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    scroll: {
        flexGrow: 1,
        paddingBottom: 32,
    },
    main: {
        width: '100%',
        maxWidth: 600,
        alignSelf: 'center',
        paddingHorizontal: 24,
        paddingTop: 32,
        gap: 12,
    },
    title: {
        fontSize: 28,
        fontWeight: '800',
    },
    subtitle: {
        fontSize: 15,
        marginBottom: 8,
    },
    row: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 16,
        padding: 14,
        borderWidth: 1,
        borderRadius: 12,
    },
    badge: {
        width: 40,
        height: 40,
        borderRadius: 20,
        alignItems: 'center',
        justifyContent: 'center',
    },
    badgeText: {
        color: '#FFFFFF',
        fontSize: 18,
        fontWeight: '700',
    },
    name: {
        fontSize: 17,
        fontWeight: '600',
    },
});
