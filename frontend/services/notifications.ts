import { createStore, useStore } from './store/createStore';

// No notifications API yet, so the list is seeded locally and new ride activity is added
// on the device. TODO: load from the backend (and push notifications) when available.

export type Notification = {
    id: string;
    title: string;
    body: string;
    createdAt: string; // ISO
    read: boolean;
};

const minutesAgo = (m: number) => new Date(Date.now() - m * 60_000).toISOString();

const store = createStore<Notification[]>([
    {
        id: 'welcome',
        title: 'Welcome to Hopr',
        body: 'Request a ride or offer one to start sharing the journey.',
        createdAt: minutesAgo(2),
        read: false,
    },
    {
        id: 'vehicle-tip',
        title: 'Driving? Add your vehicle',
        body: 'Add a vehicle once and reuse it every time you offer a ride.',
        createdAt: minutesAgo(1),
        read: false,
    },
]);

export const useNotifications = () => useStore(store);
export const useUnreadCount = () => useStore(store).filter(n => !n.read).length;

export function notify(title: string, body: string) {
    store.set(list => [{ id: `n-${Date.now()}`, title, body, createdAt: new Date().toISOString(), read: false }, ...list]);
}

export const markRead = (id: string) => store.set(list => list.map(n => (n.id === id ? { ...n, read: true } : n)));
export const markAllRead = () => store.set(list => list.map(n => ({ ...n, read: true })));
