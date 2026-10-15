import Constants from 'expo-constants';
import { Platform } from 'react-native';

// Expo Go uses Metro's LAN host, e.g. exp://172.20.10.3:8082 -> http://172.20.10.3:8000.
// Browser clients use the host from which the frontend was opened.
function localApiUrl(): string {
    if (Platform.OS === 'web' && typeof window !== 'undefined') {
        return `http://${window.location.hostname}:8000`;
    }
    const metroHost = Constants.expoConfig?.hostUri;
    if (metroHost) {
        try {
            const hostname = new URL(metroHost.includes('://') ? metroHost : `http://${metroHost}`).hostname;
            if (hostname) return `http://${hostname}:8000`;
        } catch {
            // Fall back for native builds without a usable Metro host.
        }
    }
    return Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000';
}

// Override for deployed backends, a different port, or Expo tunnel mode.
export const API_URL = process.env.EXPO_PUBLIC_API_URL?.trim().replace(/\/+$/, '') || localApiUrl();
