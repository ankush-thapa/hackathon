import React from 'react';
import { Tabs } from 'expo-router';
import { Footer } from '../../components/Footer';
import { Colors } from '../../constants/Colors';

export default function TabsLayout() {
    return (
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
    );
}
