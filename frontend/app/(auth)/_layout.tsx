import React from 'react';
import { Stack } from 'expo-router';
import { View } from 'react-native';
import { Header } from '../../components/Header';
import { Colors } from '../../constants/Colors';

export default function AuthLayout() {
    return (
        <View style={{ flex: 1 }}>
            <Header />
            <Stack
                screenOptions={{
                    headerShown: false,
                    contentStyle: { backgroundColor: Colors.light.background },
                }}
            />
        </View>
    );
}
