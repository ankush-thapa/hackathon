import React, { useEffect, useRef } from 'react';
import { Animated, Easing, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Colors } from '../constants/Colors';

type Props = { title: string; subtitle?: string; children: React.ReactNode };

const theme = Colors.light;
const CREAM = '#F7EFEA';

/** Slow up-and-down drift for the background shapes. */
function useFloat(distance: number, duration: number, delay = 0) {
    const v = useRef(new Animated.Value(0)).current;
    useEffect(() => {
        const loop = Animated.loop(
            Animated.sequence([
                Animated.timing(v, { toValue: 1, duration, delay, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
                Animated.timing(v, { toValue: 0, duration, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
            ]),
        );
        loop.start();
        return () => loop.stop();
    }, [v, duration, delay]);
    return { transform: [{ translateY: v.interpolate({ inputRange: [0, 1], outputRange: [0, distance] }) }] };
}

function Pin({ color, style }: { color: string; style: object }) {
    return (
        <View style={[styles.pin, style]}>
            <View style={[styles.pinHead, { backgroundColor: color }]}>
                <View style={styles.pinDot} />
            </View>
            <View style={[styles.pinTip, { borderTopColor: color }]} />
        </View>
    );
}

/** Decorative layer: soft blobs, a dashed "route" and map pins in the Hopr palette. */
function Backdrop() {
    const a = useFloat(18, 4200);
    const b = useFloat(-14, 5200, 600);
    const c = useFloat(10, 3600, 300);
    return (
        <View style={StyleSheet.absoluteFill} pointerEvents="none">
            <Animated.View style={[styles.blob, styles.blobTopRight, a]} />
            <Animated.View style={[styles.blob, styles.blobBottomLeft, b]} />
            <View style={styles.routeRing} />
            <View style={styles.routeRingSmall} />
            <Animated.View style={[styles.pinWrapTop, c]}>
                <Pin color={theme.primary} style={{}} />
            </Animated.View>
            <Animated.View style={[styles.pinWrapBottom, a]}>
                <Pin color="#E9A792" style={{}} />
            </Animated.View>
            <View style={[styles.dot, { top: '22%', left: '12%', backgroundColor: '#5E8C6A' }]} />
            <View style={[styles.dot, { top: '70%', right: '14%', backgroundColor: '#F2C46D' }]} />
            <View style={[styles.dot, styles.dotSmall, { top: '40%', right: '8%', backgroundColor: '#E9A792' }]} />
        </View>
    );
}

/** Mobile-first shell for auth forms: decorative background, centred card, keyboard-safe. */
export const AuthScreen = ({ title, subtitle, children }: Props) => (
    <View style={styles.root}>
        <Backdrop />
        <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
            <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
                <View style={styles.card}>
                    <Text style={styles.title}>{title}</Text>
                    {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
                    <View style={styles.form}>{children}</View>
                </View>
            </ScrollView>
        </KeyboardAvoidingView>
    </View>
);

const styles = StyleSheet.create({
    root: { flex: 1, backgroundColor: CREAM, overflow: 'hidden' },
    flex: { flex: 1 },
    scroll: { flexGrow: 1, justifyContent: 'center', paddingVertical: 40, paddingHorizontal: 16 },
    card: {
        width: '100%',
        maxWidth: 440,
        alignSelf: 'center',
        backgroundColor: 'rgba(255,255,255,0.92)',
        borderRadius: 24,
        borderWidth: 1,
        borderColor: '#EFE2DB',
        paddingHorizontal: 24,
        paddingVertical: 32,
        shadowColor: '#5A2A20',
        shadowOpacity: 0.12,
        shadowRadius: 30,
        shadowOffset: { width: 0, height: 12 },
        elevation: 6,
    },
    title: { fontFamily: 'Fredoka_700Bold', fontSize: 30, color: '#2A1A16', letterSpacing: -0.3 },
    subtitle: { fontSize: 15, marginTop: 6, color: theme.muted },
    form: { marginTop: 28, gap: 18 },

    blob: { position: 'absolute', borderRadius: 9999 },
    blobTopRight: { width: 520, height: 520, top: -200, right: -180, backgroundColor: '#F0D9CF' },
    blobBottomLeft: { width: 460, height: 460, bottom: -200, left: -170, backgroundColor: '#ECD3C8' },
    routeRing: {
        position: 'absolute', width: 760, height: 760, borderRadius: 380, top: -120, left: -380,
        borderWidth: 3, borderStyle: 'dashed', borderColor: 'rgba(142,69,55,0.28)',
    },
    routeRingSmall: {
        position: 'absolute', width: 420, height: 420, borderRadius: 210, bottom: -160, right: -120,
        borderWidth: 3, borderStyle: 'dashed', borderColor: 'rgba(142,69,55,0.22)',
    },
    pinWrapTop: { position: 'absolute', top: '12%', right: '16%' },
    pinWrapBottom: { position: 'absolute', bottom: '14%', left: '14%' },
    pin: { alignItems: 'center', opacity: 0.9 },
    pinHead: { width: 34, height: 34, borderRadius: 17, alignItems: 'center', justifyContent: 'center' },
    pinDot: { width: 12, height: 12, borderRadius: 6, backgroundColor: '#FFF7F4' },
    pinTip: {
        width: 0, height: 0, marginTop: -6,
        borderLeftWidth: 11, borderRightWidth: 11, borderTopWidth: 16,
        borderLeftColor: 'transparent', borderRightColor: 'transparent',
    },
    dot: { position: 'absolute', width: 14, height: 14, borderRadius: 7, opacity: 0.8 },
    dotSmall: { width: 9, height: 9, borderRadius: 5 },
});
