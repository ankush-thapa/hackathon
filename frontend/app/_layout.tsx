import React from 'react';
import { Stack, usePathname } from 'expo-router';
import { View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Colors } from '../constants/Colors';

// Each route group renders its own header: (auth) and (tabs) use the brand Header,
// (app) uses AppHeader with the sidebar, notifications, profile and logout.
export default function RootLayout() {
    // Rounded display font used for the Hopr wordmark (matches the logo).
    // Render immediately; the wordmark falls back to the system font until it loads.
    useFonts({ Fredoka_700Bold });
    // The landing page (/) draws its own navigation bar.
    const isLanding = usePathname() === '/';

    return (
        <SafeAreaProvider>
            <View style={{ flex: 1, backgroundColor: Colors.light.background }}>
                <Stack
                    screenOptions={{
                        headerShown: false,
                        contentStyle: { backgroundColor: Colors.light.background },
                    }}
                />
            </View>
        </SafeAreaProvider>
    );
}
