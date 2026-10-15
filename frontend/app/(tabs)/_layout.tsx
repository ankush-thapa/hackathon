import React from 'react';
import { Tabs } from 'expo-router';
import { View } from 'react-native';
import { Header } from '../../components/Header';
import { Footer } from '../../components/Footer';
import { Colors } from '../../constants/Colors';

export default function TabsLayout() {
    return (
        <View style={{ flex: 1 }}>
        <Header />
        <Tabs
            tabBar={props => <Footer {...props} />}
            screenOptions={{
                headerShown: false,
                sceneStyle: { backgroundColor: Colors.light.background },
            }}
        >
            <Tabs.Screen name="dashboard" options={{ title: 'Dashboard' }} />
            <Tabs.Screen name="rides" options={{ title: 'My Rides' }} />
            <Tabs.Screen name="users" options={{ title: 'Users' }} />
        </Tabs>
        </View>
    );
}
