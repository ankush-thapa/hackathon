import React, { useEffect, useState } from 'react';
import { Text } from 'react-native';
import { Card, Screen, SecondaryButton } from '../../components/ui';
import { markAllRead, markRead, refreshNotifications, useNotifications } from '../../services/notifications';

export default function NotificationsScreen() {
    const items = useNotifications();
    const [error, setError] = useState<string | null>(null);
    const run = async (action: () => Promise<unknown>) => {
        setError(null);
        try { await action(); } catch (e) { setError(e instanceof Error ? e.message : 'Could not load notifications'); }
    };
    useEffect(() => { void run(refreshNotifications); }, []);
    return <Screen title="Notifications">
        {error ? <Text>{error}</Text> : null}
        <SecondaryButton title="Refresh" onPress={() => void run(refreshNotifications)} />
        <SecondaryButton title="Mark all read" onPress={() => void run(markAllRead)} />
        {!items.length ? <Text>No unread notifications.</Text> : items.map(n => <Card key={n.id}>
            <Text>{n.title}</Text><Text>{n.body}</Text>
            <SecondaryButton title="Mark read" onPress={() => void run(() => markRead(n.id))} />
        </Card>)}
    </Screen>;
}
