import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Colors } from '../constants/Colors';

type Props = {
    onPress: () => void;
    accessibilityLabel: string;
    children: React.ReactNode;
    /** Small count bubble, e.g. unread notifications. Hidden when 0. */
    badge?: number;
};

/** 44×44 touch target, the minimum comfortable size on phones. */
export const IconButton = ({ onPress, accessibilityLabel, children, badge }: Props) => {
    const theme = Colors.light;
    return (
        <Pressable
            onPress={onPress}
            accessibilityRole="button"
            accessibilityLabel={badge ? `${accessibilityLabel}, ${badge} unread` : accessibilityLabel}
            style={({ pressed }) => [styles.button, pressed && { backgroundColor: theme.primarySoft }]}
        >
            {children}
            {badge ? (
                <View style={[styles.badge, { backgroundColor: theme.error, borderColor: theme.card }]}>
                    <Text style={styles.badgeText}>{badge > 9 ? '9+' : badge}</Text>
                </View>
            ) : null}
        </Pressable>
    );
};

const styles = StyleSheet.create({
    button: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center' },
    badge: {
        position: 'absolute', top: 5, right: 4, minWidth: 18, height: 18, borderRadius: 9, borderWidth: 2,
        paddingHorizontal: 3, alignItems: 'center', justifyContent: 'center',
    },
    badgeText: { color: '#FFFFFF', fontSize: 10, fontWeight: '800' },
});
