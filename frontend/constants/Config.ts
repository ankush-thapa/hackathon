import { Platform } from 'react-native';

// Android emulators reach the host machine at 10.0.2.2; web and iOS simulator use localhost.
const defaultApiUrl = Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000';

export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? defaultApiUrl;
