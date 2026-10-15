import React from 'react';
import { Stack } from 'expo-router';
import { View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Colors } from '../constants/Colors';

// Each route group renders its own header: (auth) and (tabs) use the brand Header,
// (app) uses AppHeader with the sidebar, notifications, profile and logout.
export default function RootLayout() {
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
