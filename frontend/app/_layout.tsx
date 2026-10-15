import React from 'react';
import { Stack } from 'expo-router';
import { View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Header } from '../components/Header';
import { Colors } from '../constants/Colors';
import { VehiclesProvider } from '../context/VehiclesContext';

export default function RootLayout() {
    return (
        <SafeAreaProvider>
            <VehiclesProvider>
                <View style={{ flex: 1, backgroundColor: Colors.light.background }}>
                    <Header />
                    <Stack
                        screenOptions={{
                            headerShown: false,
                            contentStyle: { backgroundColor: Colors.light.background },
                        }}
                    />
                </View>
            </VehiclesProvider>
        </SafeAreaProvider>
    );
}
