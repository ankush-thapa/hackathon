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
            <Tabs.Screen name="index" options={{ title: 'Home' }} />
            <Tabs.Screen name="users" options={{ title: 'Users' }} />
            <Tabs.Screen name="vehicles" options={{ title: 'Vehicles' }} />
        </Tabs>
    );
}
