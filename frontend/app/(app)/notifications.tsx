import React, { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { EmptyState, Screen, SecondaryButton, TextLink } from '../../components/ui';
import { Colors } from '../../constants/Colors';
import { ApiError } from '../../services/api';
import { timeAgo } from '../../services/format';
import {
    NOTIFICATION_META, Notification, markAllRead, markRead, notificationTarget, refreshNotifications, useNotifications,
} from '../../services/notifications';

const theme = Colors.light;

const TONE: Record<'brand' | 'success' | 'error' | 'muted', string> = {
    brand: theme.primary,
    success: theme.success,
    error: theme.error,
    muted: theme.muted,
};

/** Unread notifications from GET /v1/notifications. Opening one marks it read. */
export default function NotificationsScreen() {
    const router = useRouter();
    const { items, unreadCount, loaded, error } = useNotifications();
    const [refreshing, setRefreshing] = useState(false);
    const [actionError, setActionError] = useState<string | null>(null);

    const refresh = useCallback(async () => {
        setRefreshing(true);
        try { await refreshNotifications(); } catch { /* error is shown from the store */ }
        setRefreshing(false);
    }, []);

    // Fetch straight away whenever this page is opened, not just on the 30 s poll.
    useFocusEffect(useCallback(() => { refresh(); }, [refresh]));

    const open = async (n: Notification) => {
        setActionError(null);
        // Driver events → the offered ride; rider events → the booking. Open it even if marking read fails.
        router.push(notificationTarget(n));
        markRead(n.idNotification).catch(() => undefined);
    };

    const readAll = async () => {
        setActionError(null);
        try { await markAllRead(); } catch (e) {
            setActionError(e instanceof ApiError ? e.message : 'Could not mark all as read');
        }
    };

    return (
        <Screen
            title="Notifications"
            subtitle={!loaded ? 'Loading…' : unreadCount ? `${unreadCount} unread` : 'You’re all caught up'}
            action={unreadCount ? <View style={{ paddingTop: 8 }}><TextLink label="Mark all read" onPress={readAll} /></View> : undefined}
        >
            {actionError ? <Text style={styles.error} accessibilityLiveRegion="polite">{actionError}</Text> : null}

            {!loaded ? (
                <View style={styles.center}><ActivityIndicator color={theme.primary} /></View>
            ) : error && !items.length ? (
                <EmptyState title="Couldn’t load notifications" body={error} action={<SecondaryButton title="Try again" onPress={refresh} />} />
            ) : !items.length ? (
                <EmptyState
                    title="No new notifications"
                    body="You’ll hear here when someone requests, accepts or cancels a booking, or when a ride changes."
                />
            ) : (
                <View style={styles.list}>
                    {items.map((n, i) => {
                        const meta = NOTIFICATION_META[n.type] ?? { title: 'Update', tone: 'muted' as const };
                        return (
                            <Pressable
                                key={n.idNotification}
                                onPress={() => open(n)}
                                accessibilityRole="button"
                                accessibilityLabel={`${n.read ? '' : 'Unread. '}${meta.title}. ${n.message}. ${timeAgo(n.createdAt)}`}
                                style={({ pressed }) => [
                                    styles.item,
                                    i > 0 && { borderTopWidth: 1, borderTopColor: theme.border },
                                    !n.read && { backgroundColor: theme.primarySoft },
                                    pressed && { opacity: 0.8 },
                                ]}
                            >
                                <View style={[styles.marker, { backgroundColor: TONE[meta.tone] }, n.read && { opacity: 0.35 }]} />
                                <View style={{ flex: 1, gap: 3 }}>
                                    <View style={styles.row}>
                                        <Text style={[styles.title, { fontWeight: n.read ? '600' : '800' }]} numberOfLines={1}>{meta.title}</Text>
                                        <Text style={styles.time}>{timeAgo(n.createdAt)}</Text>
                                    </View>
                                    <Text style={[styles.body, n.read && { color: theme.muted }]}>{n.message}</Text>
                                </View>
                            </Pressable>
                        );
                    })}
                </View>
            )}

            {loaded ? (
                <View style={{ alignItems: 'center' }}>
                    {refreshing ? <ActivityIndicator color={theme.primary} /> : <TextLink label="Refresh" onPress={refresh} />}
                </View>
            ) : null}
        </Screen>
    );
}

const styles = StyleSheet.create({
    center: { paddingVertical: 40, alignItems: 'center' },
    list: { borderWidth: 1, borderColor: theme.border, borderRadius: 16, overflow: 'hidden', backgroundColor: theme.card },
    item: { flexDirection: 'row', gap: 12, padding: 16 },
    marker: { width: 4, alignSelf: 'stretch', borderRadius: 2 },
    row: { flexDirection: 'row', justifyContent: 'space-between', gap: 8 },
    title: { fontSize: 15, color: theme.text, flexShrink: 1 },
    time: { fontSize: 12, color: theme.muted, marginTop: 2 },
    body: { fontSize: 14, color: theme.text },
    error: { fontSize: 14, color: theme.error, textAlign: 'center' },
});
