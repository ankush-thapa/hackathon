import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors } from '../constants/Colors';

export const Footer = ({ state, descriptors, navigation }: BottomTabBarProps) => {
    const theme = Colors.light;
    const insets = useSafeAreaInsets();

    return (
        <View style={[
            styles.footerWrapper,
            { backgroundColor: theme.card, borderTopColor: theme.border, paddingBottom: 16 + insets.bottom },
        ]}>
            <View style={styles.footerContainer}>
                <View style={styles.tabs}>
                    {state.routes.map((route, index) => {
                        const focused = state.index === index;
                        const label = descriptors[route.key].options.title ?? route.name;
                        return (
                            <Pressable
                                key={route.key}
                                onPress={() => {
                                    const event = navigation.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
                                    if (!focused && !event.defaultPrevented) navigation.navigate(route.name);
                                }}
                                style={({ pressed }) => [
                                    styles.tab,
                                    focused && { backgroundColor: theme.primary },
                                    pressed && { opacity: 0.75 },
                                ]}
                            >
                                <Text style={[styles.tabLabel, { color: focused ? '#FFFFFF' : theme.text }]}>{label}</Text>
                            </Pressable>
                        );
                    })}
                </View>
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    footerWrapper: {
        width: '100%',
        paddingTop: 16,
        borderTopWidth: 1,
        alignItems: 'center',
    },
    footerContainer: {
        width: '100%',
        maxWidth: 1200,
        paddingHorizontal: 24,
        alignItems: 'center',
        justifyContent: 'center',
    },
    tabs: {
        flexDirection: 'row',
        gap: 8,
    },
    tab: {
        paddingVertical: 8,
        paddingHorizontal: 20,
        borderRadius: 20,
    },
    tabLabel: {
        fontSize: 15,
        fontWeight: '600',
    },
});
