import React, { useState } from 'react';
import { Redirect, Stack } from 'expo-router';
import { View, useWindowDimensions } from 'react-native';
import { AppHeader } from '../../components/AppHeader';
import { NotificationPoller } from '../../components/NotificationPoller';
import { DrawerSidebar, PermanentSidebar } from '../../components/Sidebar';
import { Colors } from '../../constants/Colors';
import { getSession } from '../../services/session';

const WIDE_SCREEN = 1024;

/** Everything a logged-in user sees: header + sidebar around the pages in this group. */
export default function AppLayout() {
    const { width } = useWindowDimensions();
    const [menuOpen, setMenuOpen] = useState(false);
    const wide = width >= WIDE_SCREEN;

    if (!getSession()) return <Redirect href="/login" />;

    return (
        <View style={{ flex: 1, backgroundColor: Colors.light.background }}>
            <NotificationPoller />
            <AppHeader showMenuButton={!wide} onMenuPress={() => setMenuOpen(true)} />
            <View style={{ flex: 1, flexDirection: 'row' }}>
                {wide ? <PermanentSidebar /> : null}
                <View style={{ flex: 1 }}>
                    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: Colors.light.background } }} />
                </View>
            </View>
            {!wide ? <DrawerSidebar open={menuOpen} onClose={() => setMenuOpen(false)} /> : null}
        </View>
    );
}
