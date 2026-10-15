import React, { useEffect, useRef, useState } from 'react';
import { Animated, Platform, Pressable, ScrollView, StyleSheet, Text, View, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Href, usePathname, useRouter } from 'expo-router';
import { Colors } from '../constants/Colors';
import { Icon } from './Icon';

type Item = { label: string; href: Href; path: string; child?: boolean };

export const NAV_ITEMS: Item[] = [
    { label: 'Dashboard', href: '/dashboard', path: '/dashboard' },
    { label: 'My Rides', href: '/rides', path: '/rides' },
    { label: 'My Vehicles', href: '/vehicles', path: '/vehicles' },
    { label: 'Add a vehicle', href: '/vehicles/add', path: '/vehicles/add', child: true },
    { label: 'Request a ride', href: '/request-ride', path: '/request-ride' },
    { label: 'Offer a ride', href: '/offer-ride', path: '/offer-ride' },
];

const NavList = ({ onNavigate }: { onNavigate?: () => void }) => {
    const theme = Colors.light;
    const router = useRouter();
    const pathname = usePathname();

    return (
        <View style={styles.list} accessibilityRole="menu">
            {NAV_ITEMS.map(item => {
                const active = pathname === item.path;
                return (
                    <Pressable
                        key={item.path}
                        accessibilityRole="menuitem"
                        accessibilityState={{ selected: active }}
                        onPress={() => {
                            onNavigate?.();
                            if (!active) router.push(item.href);
                        }}
                        style={({ pressed }) => [
                            styles.item,
                            item.child && styles.childItem,
                            active && { backgroundColor: theme.primarySoft },
                            pressed && !active && { backgroundColor: theme.background },
                        ]}
                    >
                        {item.child ? <View style={[styles.childLine, { backgroundColor: theme.border }]} /> : null}
                        <Text
                            style={[
                                item.child ? styles.childLabel : styles.label,
                                { color: active ? theme.primary : item.child ? theme.muted : theme.text },
                            ]}
                        >
                            {item.child ? `+  ${item.label}` : item.label}
                        </Text>
                    </Pressable>
                );
            })}
        </View>
    );
};

/** Always-visible sidebar for wide screens (tablet / desktop web). */
export const PermanentSidebar = () => {
    const theme = Colors.light;
    return (
        <View style={[styles.permanent, { backgroundColor: theme.card, borderRightColor: theme.border }]}>
            <NavList />
        </View>
    );
};

/** Slide-in drawer for phones. */
export const DrawerSidebar = ({ open, onClose }: { open: boolean; onClose: () => void }) => {
    const theme = Colors.light;
    const insets = useSafeAreaInsets();
    const { width } = useWindowDimensions();
    const drawerWidth = Math.min(300, width * 0.84);
    const progress = useRef(new Animated.Value(0)).current;
    const [mounted, setMounted] = useState(open);

    useEffect(() => {
        if (open) setMounted(true);
        Animated.timing(progress, {
            toValue: open ? 1 : 0,
            duration: 220,
            useNativeDriver: Platform.OS !== 'web',
        }).start(({ finished }) => {
            if (finished && !open) setMounted(false);
        });
    }, [open, progress]);

    if (!mounted) return null;

    return (
        <View style={StyleSheet.absoluteFill} pointerEvents={open ? 'auto' : 'none'}>
            <Animated.View style={[StyleSheet.absoluteFill, styles.backdrop, { opacity: progress }]}>
                <Pressable style={StyleSheet.absoluteFill} onPress={onClose} accessibilityLabel="Close menu" />
            </Animated.View>
            <Animated.View
                style={[
                    styles.drawer,
                    {
                        width: drawerWidth,
                        backgroundColor: theme.card,
                        paddingTop: insets.top,
                        transform: [{ translateX: progress.interpolate({ inputRange: [0, 1], outputRange: [-drawerWidth, 0] }) }],
                    },
                ]}
            >
                <View style={[styles.drawerHeader, { borderBottomColor: theme.border }]}>
                    <Text style={[styles.drawerTitle, { color: theme.text }]}>Menu</Text>
                    <Pressable onPress={onClose} accessibilityRole="button" accessibilityLabel="Close menu" style={styles.close}>
                        <Icon name="close" color={theme.text} size={22} />
                    </Pressable>
                </View>
                <ScrollView>
                    <NavList onNavigate={onClose} />
                </ScrollView>
            </Animated.View>
        </View>
    );
};

const styles = StyleSheet.create({
    list: { padding: 12, gap: 2 },
    item: { minHeight: 48, borderRadius: 12, paddingHorizontal: 14, flexDirection: 'row', alignItems: 'center' },
    childItem: { minHeight: 42, marginLeft: 14, paddingLeft: 16 },
    childLine: { position: 'absolute', left: 0, top: 6, bottom: 6, width: 2, borderRadius: 1 },
    label: { fontSize: 16, fontWeight: '600' },
    childLabel: { fontSize: 15, fontWeight: '600' },
    permanent: { width: 248, borderRightWidth: 1 },
    backdrop: { backgroundColor: 'rgba(42, 26, 22, 0.45)' },
    drawer: { position: 'absolute', top: 0, bottom: 0, left: 0, shadowColor: '#000', shadowOpacity: 0.2, shadowRadius: 16, elevation: 12 },
    drawerHeader: { height: 60, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingLeft: 24, paddingRight: 8, borderBottomWidth: 1 },
    drawerTitle: { fontSize: 18, fontWeight: '800' },
    close: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
});
