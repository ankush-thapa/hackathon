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
            <Tabs.Screen name="home" options={{ title: 'Home' }} />
            <Tabs.Screen name="users" options={{ title: 'Users' }} />
        </Tabs>
        </View>
    );
}
