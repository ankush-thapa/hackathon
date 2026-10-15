import { useEffect } from 'react';
import { createStore, useStore } from './store/createStore';
import { postJson, request } from './api';
import { getSession } from './session';

export type Notification = { id: string; title: string; body: string; createdAt: string; read: boolean };
type Item = { idNotification: string; type: string; message: string; createdAt: string; read: boolean };
const store = createStore<Notification[]>([]);
const unreadStore = createStore(0);
let generation = 0;
export const resetNotifications = () => { generation++; store.set([]); unreadStore.set(0); };
export async function refreshNotifications() {
    const session = getSession();
    const before = generation;
    if (!session) { resetNotifications(); return; }
    const data = await request<{ items: Item[]; unreadCount: number }>('/v1/notifications?limit=50');
    if (before !== generation || getSession()?.userId !== session.userId) return;
    store.set(data.items.map(n => ({ id: n.idNotification, title: n.type.replace(/_/g, ' '), body: n.message,
        createdAt: n.createdAt, read: n.read })));
    unreadStore.set(data.unreadCount);
}
export function useNotifications() { return useStore(store); }
export function useUnreadCount() {
    const count = useStore(unreadStore);
    useEffect(() => {
        const refresh = () => refreshNotifications().catch(() => undefined);
        refresh();
        const timer = setInterval(refresh, 30000);
        return () => clearInterval(timer);
    }, []);
    return count;
}
// Existing offer screen calls this after success; authoritative events come from the server.
export function notify(_title: string, _body: string) { void refreshNotifications().catch(() => undefined); }
export async function markRead(id: string) { await postJson(`/v1/notifications/${id}/read`, {}); await refreshNotifications(); }
export async function markAllRead() { await postJson('/v1/notifications/read-all', {}); await refreshNotifications(); }
