import { useEffect } from 'react';
import { AppState, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { ApiError } from '../services/api';
import { POLL_INTERVAL_MS, refreshNotifications, resetNotifications } from '../services/notifications';
import { clearSession } from '../services/session';

/**
 * Keeps the notification badge fresh while a user is logged in: loads right away, then every
 * 30 s while the app is in the foreground (browser tab visible / app active), and immediately
 * when the user comes back to it. Renders nothing.
 */
export function NotificationPoller() {
    const router = useRouter();

    useEffect(() => {
        let timer: ReturnType<typeof setInterval> | null = null;
        let stopped = false;

        const poll = () =>
            refreshNotifications().catch(e => {
                if (e instanceof ApiError && e.status === 401) {
                    stopped = true;
                    stop();
                    clearSession();
                    resetNotifications();
                    router.replace('/login');
                }
            });
        const start = () => {
            if (stopped || timer) return;
            poll();
            timer = setInterval(poll, POLL_INTERVAL_MS);
        };
        const stop = () => {
            if (timer) clearInterval(timer);
            timer = null;
        };

        start();

        // Pause while hidden/backgrounded so we don't poll for nobody.
        const appSub = AppState.addEventListener('change', s => (s === 'active' ? start() : stop()));
        const onVisibility = () => (document.visibilityState === 'visible' ? start() : stop());
        if (Platform.OS === 'web' && typeof document !== 'undefined') document.addEventListener('visibilitychange', onVisibility);

        return () => {
            stopped = true;
            stop();
            appSub.remove();
            if (Platform.OS === 'web' && typeof document !== 'undefined') document.removeEventListener('visibilitychange', onVisibility);
        };
    }, [router]);

    return null;
}
