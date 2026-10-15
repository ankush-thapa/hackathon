import React, { useRef } from 'react';
import { Image, Pressable, ScrollView, StyleSheet, Text, View, useWindowDimensions } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors } from '../constants/Colors';

const theme = Colors.light;
const CREAM = '#F7EFEA';
const INK = '#2A1A16';
const BRAND_FONT = 'Fredoka_700Bold';

const STEPS = [
    { n: '1', title: 'Create your profile', text: 'Sign up with your work email and tell co-riders a little about yourself.' },
    { n: '2', title: 'Find or offer a ride', text: 'Match with colleagues on your route, or share the empty seats in your car.' },
    { n: '3', title: 'Split the cost', text: 'Pay per seat, cut fuel and parking costs, and take a few cars off the road.' },
];

const PERKS = [
    { title: 'Verified co-workers', text: 'Ride only with people from your organisation.' },
    { title: 'Set your schedule', text: 'Daily commutes or one-off trips, on your terms.' },
    { title: 'Greener commute', text: 'Fewer cars on the road, less traffic for everyone.' },
];

export default function LandingScreen() {
    const router = useRouter();
    const insets = useSafeAreaInsets();
    const { width } = useWindowDimensions();
    const wide = width >= 900;
    const showLinks = width >= 768;
    // Explicit size for the illustration (4:3); percentage + aspectRatio is unreliable on web.
    const content = Math.min(width, 1200) - 48;
    const heroW = Math.min(640, wide ? (content - 40) * 0.52 : content);

    const scrollRef = useRef<ScrollView>(null);
    const sectionY = useRef<Record<string, number>>({});
    const scrollTo = (key: string) => scrollRef.current?.scrollTo({ y: sectionY.current[key] ?? 0, animated: true });
    const track = (key: string) => (e: { nativeEvent: { layout: { y: number } } }) => { sectionY.current[key] = e.nativeEvent.layout.y; };

    return (
        <ScrollView ref={scrollRef} style={{ backgroundColor: CREAM }} contentContainerStyle={{ paddingTop: insets.top }}>
            {/* Nav */}
            <View style={styles.navWrap}>
                <View style={[styles.nav, styles.container]}>
                    <Pressable onPress={() => scrollTo('top')} style={styles.brand} accessibilityRole="link" accessibilityLabel="Hopr home">
                        <Image source={require('../assets/app_icon.png')} style={styles.brandIcon} />
                        <Text style={styles.brandName}>Hopr</Text>
                    </Pressable>
                    <View style={styles.navRight}>
                        {showLinks && (
                            <>
                                <NavLink label="How it works" onPress={() => scrollTo('how')} />
                                <NavLink label="Why Hopr" onPress={() => scrollTo('why')} />
                            </>
                        )}
                        <View style={styles.pills}>
                            <Pill label="Sign up" filled onPress={() => router.push('/signup')} />
                            <Pill label="Sign in" onPress={() => router.push('/login')} />
                        </View>
                    </View>
                </View>
            </View>

            {/* Hero */}
            <View onLayout={track('top')} style={[styles.container, styles.hero, wide && styles.heroWide]}>
                <View style={[styles.heroText, wide && { flex: 1 }]}>
                    <Text style={styles.eyebrow}>CARPOOL WITH YOUR COLLEAGUES</Text>
                    <Text style={[styles.headline, { fontSize: wide ? 64 : 44, lineHeight: wide ? 70 : 50 }]}>
                        Let’s ride{'\n'}together!
                    </Text>
                    <Text style={styles.lead}>
                        Share your daily commute with people heading the same way. Save money, skip the parking hunt and make the drive more fun.
                    </Text>
                    <View style={styles.ctaRow}>
                        <Pressable
                            onPress={() => router.push('/signup')}
                            accessibilityRole="button"
                            style={({ pressed }) => [styles.cta, pressed && { opacity: 0.85 }]}
                        >
                            <Text style={styles.ctaText}>Join today</Text>
                        </Pressable>
                        <Pressable onPress={() => router.push('/login')} hitSlop={8} accessibilityRole="link">
                            <Text style={styles.secondaryLink}>I have an account</Text>
                        </Pressable>
                    </View>
                </View>
                <View style={[styles.heroArt, wide && { flex: 1.1 }]}>
                    <Image
                        source={require('../assets/hero.png')}
                        style={{ width: heroW, height: heroW * 0.75 }}
                        resizeMode="contain"
                        accessibilityLabel="Three friends sharing a car ride along a route"
                    />
                </View>
            </View>

            {/* How it works */}
            <View onLayout={track('how')} style={styles.band}>
                <View style={styles.container}>
                    <Text style={styles.sectionTitle}>How it works</Text>
                    <View style={[styles.grid, wide && { flexDirection: 'row' }]}>
                        {STEPS.map(s => (
                            <View key={s.n} style={[styles.card, wide && { flex: 1 }]}>
                                <View style={styles.stepBadge}><Text style={styles.stepBadgeText}>{s.n}</Text></View>
                                <Text style={styles.cardTitle}>{s.title}</Text>
                                <Text style={styles.cardText}>{s.text}</Text>
                            </View>
                        ))}
                    </View>
                </View>
            </View>

            {/* Why Hopr */}
            <View onLayout={track('why')} style={[styles.container, styles.section]}>
                <Text style={styles.sectionTitle}>Why Hopr</Text>
                <View style={[styles.grid, wide && { flexDirection: 'row' }]}>
                    {PERKS.map(p => (
                        <View key={p.title} style={[styles.perk, wide && { flex: 1 }]}>
                            <View style={styles.perkDot} />
                            <View style={{ flex: 1, gap: 4 }}>
                                <Text style={styles.cardTitle}>{p.title}</Text>
                                <Text style={styles.cardText}>{p.text}</Text>
                            </View>
                        </View>
                    ))}
                </View>
            </View>

            {/* Closing CTA */}
            <View style={[styles.container, { paddingBottom: 48 + insets.bottom }]}>
                <View style={[styles.closing, wide && styles.closingWide]}>
                    <View style={{ flex: wide ? 1 : undefined, gap: 6 }}>
                        <Text style={styles.closingTitle}>Your next commute has a free seat.</Text>
                        <Text style={styles.closingText}>Join Hopr in under a minute.</Text>
                    </View>
                    <Pressable
                        onPress={() => router.push('/signup')}
                        accessibilityRole="button"
                        style={({ pressed }) => [styles.closingBtn, pressed && { opacity: 0.85 }]}
                    >
                        <Text style={styles.closingBtnText}>Get started</Text>
                    </Pressable>
                </View>
                <Text style={styles.footer}>© {new Date().getFullYear()} Hopr</Text>
            </View>
        </ScrollView>
    );
}

function NavLink({ label, onPress }: { label: string; onPress: () => void }) {
    return (
        <Pressable onPress={onPress} hitSlop={8} accessibilityRole="link" style={({ pressed }) => pressed && { opacity: 0.6 }}>
            <Text style={styles.navLink}>{label}</Text>
        </Pressable>
    );
}

function Pill({ label, filled, onPress }: { label: string; filled?: boolean; onPress: () => void }) {
    return (
        <Pressable
            onPress={onPress}
            accessibilityRole="button"
            style={({ pressed }) => [styles.pill, filled ? styles.pillFilled : styles.pillOutline, pressed && { opacity: 0.8 }]}
        >
            <Text style={[styles.pillText, { color: filled ? '#FFFFFF' : INK }]}>{label}</Text>
        </Pressable>
    );
}

const styles = StyleSheet.create({
    container: { width: '100%', maxWidth: 1200, alignSelf: 'center', paddingHorizontal: 24 },

    navWrap: { backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: theme.border },
    nav: { height: 72, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
    brand: { flexDirection: 'row', alignItems: 'center', gap: 10 },
    brandIcon: { width: 36, height: 36, borderRadius: 9 },
    brandName: { fontFamily: BRAND_FONT, fontSize: 28, color: INK, transform: [{ skewX: '-10deg' }] },
    navRight: { flexDirection: 'row', alignItems: 'center', gap: 24 },
    navLink: { fontSize: 15, fontWeight: '600', color: INK },
    pill: { paddingVertical: 8, paddingHorizontal: 18, borderRadius: 999, borderWidth: 1.5 },
    pills: { flexDirection: 'row', gap: 10, marginLeft: 8 },
    pillFilled: { backgroundColor: theme.primary, borderColor: theme.primary },
    pillOutline: { backgroundColor: 'transparent', borderColor: '#CDB8AE' },
    pillText: { fontSize: 14, fontWeight: '700' },

    hero: { paddingTop: 48, paddingBottom: 32, gap: 24 },
    heroWide: { flexDirection: 'row', alignItems: 'center', paddingTop: 64, paddingBottom: 56, gap: 40 },
    heroText: { gap: 18 },
    eyebrow: { fontSize: 13, fontWeight: '800', letterSpacing: 1.4, color: theme.primary },
    headline: { fontFamily: BRAND_FONT, color: INK, letterSpacing: -0.5 },
    lead: { fontSize: 17, lineHeight: 26, color: '#5B4A44', maxWidth: 480 },
    ctaRow: { flexDirection: 'row', alignItems: 'center', gap: 24, marginTop: 8, flexWrap: 'wrap' },
    cta: { backgroundColor: theme.primary, paddingVertical: 16, paddingHorizontal: 36, borderRadius: 999 },
    ctaText: { color: '#FFFFFF', fontSize: 18, fontWeight: '800' },
    secondaryLink: { fontSize: 16, fontWeight: '700', color: INK, textDecorationLine: 'underline' },
    heroArt: { alignItems: 'center' },

    band: { backgroundColor: '#FFFFFF', paddingVertical: 56 },
    section: { paddingVertical: 56 },
    sectionTitle: { fontFamily: BRAND_FONT, fontSize: 34, color: INK, marginBottom: 24 },
    grid: { gap: 16 },
    card: { backgroundColor: CREAM, borderRadius: 18, padding: 24, gap: 10 },
    stepBadge: { width: 40, height: 40, borderRadius: 20, backgroundColor: theme.primary, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
    stepBadgeText: { color: '#FFFFFF', fontSize: 18, fontWeight: '800' },
    cardTitle: { fontSize: 18, fontWeight: '800', color: INK },
    cardText: { fontSize: 15, lineHeight: 22, color: '#5B4A44' },
    perk: { flexDirection: 'row', gap: 14, paddingVertical: 8 },
    perkDot: { width: 14, height: 14, borderRadius: 7, backgroundColor: '#5E8C6A', marginTop: 5 },

    closing: { backgroundColor: theme.primary, borderRadius: 24, padding: 32, gap: 20 },
    closingWide: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 48 },
    closingTitle: { fontFamily: BRAND_FONT, fontSize: 28, color: '#FFFFFF' },
    closingText: { fontSize: 16, color: '#F6DED6' },
    closingBtn: { backgroundColor: '#FFFFFF', paddingVertical: 14, paddingHorizontal: 30, borderRadius: 999, alignSelf: 'flex-start' },
    closingBtnText: { color: theme.primary, fontSize: 17, fontWeight: '800' },
    footer: { textAlign: 'center', color: theme.muted, fontSize: 13, marginTop: 28 },
});
