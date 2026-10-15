import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Colors } from '../constants/Colors';
import { initials } from '../services/format';

export const Avatar = ({ name, size = 34 }: { name: string; size?: number }) => {
    const theme = Colors.light;
    return (
        <View style={[styles.circle, { width: size, height: size, borderRadius: size / 2, backgroundColor: theme.primarySoft }]}>
            <Text style={[styles.text, { color: theme.primary, fontSize: size * 0.4 }]}>{initials(name)}</Text>
        </View>
    );
};

const styles = StyleSheet.create({
    circle: { alignItems: 'center', justifyContent: 'center' },
    text: { fontWeight: '800' },
});
