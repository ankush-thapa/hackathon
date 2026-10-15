import { useCallback, useRef } from 'react';
import { AppState, Platform } from 'react-native';
import { useFocusEffect } from 'expo-router';

export function useForegroundRefresh(refresh: () => Promise<void>, enabled = true, interval = 15000) {
    const latest = useRef(refresh);
    latest.current = refresh;
    useFocusEffect(useCallback(() => {
        if (!enabled) return;
        let active = true;
        let running = false;
        const poll = async () => {
            if (!active || running || AppState.currentState === 'background' || AppState.currentState === 'inactive') return;
            if (Platform.OS === 'web' && typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
            running = true;
            try { await latest.current(); } catch { /* caller handles errors; retain the last successful view */ }
            finally { running = false; }
        };
        void poll();
        const timer = setInterval(() => void poll(), interval);
        const sub = AppState.addEventListener('change', state => { if (state === 'active') void poll(); });
        const visible = () => { if (document.visibilityState === 'visible') void poll(); };
        if (Platform.OS === 'web' && typeof document !== 'undefined') document.addEventListener('visibilitychange', visible);
        return () => {
            active = false; clearInterval(timer); sub.remove();
            if (Platform.OS === 'web' && typeof document !== 'undefined') document.removeEventListener('visibilitychange', visible);
        };
    }, [enabled, interval]));
}
