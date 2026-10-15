import React from 'react';
import { Stack } from 'expo-router';
import { View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useFonts, Fredoka_700Bold } from '@expo-google-fonts/fredoka';
import { Header } from '../components/Header';
import { Colors } from '../constants/Colors';

export default function RootLayout() {
    // Rounded display font used for the Hopr wordmark (matches the logo).
    // Render immediately; the wordmark falls back to the system font until it loads.
    useFonts({ Fredoka_700Bold });

    return (
        <SafeAreaProvider>
            <View style={{ flex: 1, backgroundColor: Colors.light.background }}>
                <Header />
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
