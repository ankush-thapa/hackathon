import React from 'react';
import { Stack } from 'expo-router';
import { View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Header } from '../components/Header';
import { Colors } from '../constants/Colors';

export default function RootLayout() {
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
