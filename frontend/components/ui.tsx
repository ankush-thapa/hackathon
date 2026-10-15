import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View, ViewStyle } from 'react-native';
import { Colors } from '../constants/Colors';

const theme = Colors.light;

/** Scrollable page body with a title, capped width on large screens. */
export const Screen = ({ title, subtitle, action, children }: {
    title: string; subtitle?: string; action?: React.ReactNode; children: React.ReactNode;
}) => (
    <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <View style={styles.column}>
            <View style={styles.titleRow}>
                <View style={{ flex: 1 }}>
                    <Text style={styles.title} accessibilityRole="header">{title}</Text>
                    {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
                </View>
                {action}
            </View>
            {children}
        </View>
    </ScrollView>
);

export const Card = ({ children, style, onPress, accessibilityLabel }: {
    children: React.ReactNode; style?: ViewStyle; onPress?: () => void; accessibilityLabel?: string;
}) =>
    onPress ? (
        <Pressable
            onPress={onPress}
            accessibilityRole="button"
            accessibilityLabel={accessibilityLabel}
            style={({ pressed }) => [styles.card, style, pressed && { opacity: 0.85 }]}
        >
            {children}
        </Pressable>
    ) : (
        <View style={[styles.card, style]}>{children}</View>
    );

export const SectionTitle = ({ title, action }: { title: string; action?: React.ReactNode }) => (
    <View style={styles.sectionRow}>
        <Text style={styles.sectionTitle} accessibilityRole="header">{title}</Text>
        {action}
    </View>
);

export const TextLink = ({ label, onPress }: { label: string; onPress: () => void }) => (
    <Pressable onPress={onPress} accessibilityRole="link" hitSlop={10}>
        <Text style={styles.link}>{label}</Text>
    </Pressable>
);

export const SecondaryButton = ({ title, onPress }: { title: string; onPress: () => void }) => (
    <Pressable
        onPress={onPress}
        accessibilityRole="button"
        style={({ pressed }) => [styles.secondary, pressed && { backgroundColor: theme.primarySoft }]}
    >
        <Text style={styles.secondaryText}>{title}</Text>
    </Pressable>
);

export const EmptyState = ({ title, body, action }: { title: string; body: string; action?: React.ReactNode }) => (
    <View style={styles.empty}>
        <Text style={styles.emptyTitle}>{title}</Text>
        <Text style={styles.emptyBody}>{body}</Text>
        {action ? <View style={{ marginTop: 8, alignSelf: 'stretch' }}>{action}</View> : null}
    </View>
);

export const Badge = ({ label, tone = 'neutral' }: { label: string; tone?: 'neutral' | 'brand' | 'success' | 'muted' }) => {
    const colors = {
        neutral: { bg: theme.background, fg: theme.text },
        brand: { bg: theme.primarySoft, fg: theme.primary },
        success: { bg: theme.successBg, fg: theme.success },
        muted: { bg: theme.background, fg: theme.muted },
    }[tone];
    return (
        <View style={[styles.badge, { backgroundColor: colors.bg }]}>
            <Text style={[styles.badgeText, { color: colors.fg }]}>{label}</Text>
        </View>
    );
};

/** Single-select chips. */
export function ChipGroup<T extends string | number>({ label, options, value, onChange, error }: {
    label: string; options: { value: T; label: string }[]; value: T | null; onChange: (v: T) => void; error?: string;
}) {
    return (
        <View style={{ gap: 8 }}>
            <Text style={styles.fieldLabel}>{label}</Text>
            <View style={styles.chips} accessibilityRole="radiogroup" accessibilityLabel={label}>
                {options.map(o => {
                    const selected = o.value === value;
                    return (
                        <Pressable
                            key={String(o.value)}
                            onPress={() => onChange(o.value)}
                            accessibilityRole="radio"
                            accessibilityState={{ selected }}
                            style={[
                                styles.chip,
                                { borderColor: error ? theme.error : selected ? theme.primary : theme.border },
                                selected && { backgroundColor: theme.primary },
                            ]}
                        >
                            <Text style={[styles.chipText, { color: selected ? '#FFFFFF' : theme.text }]}>{o.label}</Text>
                        </Pressable>
                    );
                })}
            </View>
            {error ? <Text style={styles.error}>{error}</Text> : null}
        </View>
    );
}

/** − n + control for small counts like seats. */
export const Stepper = ({ label, value, min, max, onChange, hint }: {
    label: string; value: number; min: number; max: number; onChange: (n: number) => void; hint?: string;
}) => (
    <View style={{ gap: 8 }}>
        <Text style={styles.fieldLabel}>{label}</Text>
        <View style={styles.stepper}>
            <Pressable
                onPress={() => onChange(Math.max(min, value - 1))}
                disabled={value <= min}
                accessibilityRole="button"
                accessibilityLabel={`Fewer ${label.toLowerCase()}`}
                style={[styles.stepBtn, value <= min && { opacity: 0.35 }]}
            >
                <Text style={styles.stepBtnText}>−</Text>
            </Pressable>
            <Text style={styles.stepValue} accessibilityLiveRegion="polite">{value}</Text>
            <Pressable
                onPress={() => onChange(Math.min(max, value + 1))}
                disabled={value >= max}
                accessibilityRole="button"
                accessibilityLabel={`More ${label.toLowerCase()}`}
                style={[styles.stepBtn, value >= max && { opacity: 0.35 }]}
            >
                <Text style={styles.stepBtnText}>+</Text>
            </Pressable>
        </View>
        {hint ? <Text style={styles.hint}>{hint}</Text> : null}
    </View>
);

export const FormError = ({ message }: { message: string | null }) =>
    message ? <Text style={[styles.error, { textAlign: 'center', fontSize: 14 }]}>{message}</Text> : null;

const styles = StyleSheet.create({
    scroll: { flexGrow: 1, paddingBottom: 40 },
    column: { width: '100%', maxWidth: 720, alignSelf: 'center', paddingHorizontal: 20, paddingTop: 24, gap: 16 },
    titleRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 12, marginBottom: 4 },
    title: { fontSize: 26, fontWeight: '800', letterSpacing: -0.5, color: theme.text },
    subtitle: { fontSize: 15, marginTop: 4, color: theme.muted },
    card: { backgroundColor: theme.card, borderColor: theme.border, borderWidth: 1, borderRadius: 16, padding: 16, gap: 6 },
    sectionRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 },
    sectionTitle: { fontSize: 18, fontWeight: '800', color: theme.text },
    link: { fontSize: 14, fontWeight: '700', color: theme.primary },
    secondary: {
        minHeight: 48, borderRadius: 12, borderWidth: 1.5, borderColor: theme.primary,
        alignItems: 'center', justifyContent: 'center', paddingHorizontal: 18,
    },
    secondaryText: { fontSize: 16, fontWeight: '700', color: theme.primary },
    empty: {
        borderWidth: 1.5, borderStyle: 'dashed', borderColor: theme.border, borderRadius: 16,
        padding: 20, alignItems: 'center', gap: 4, backgroundColor: theme.card,
    },
    emptyTitle: { fontSize: 16, fontWeight: '700', color: theme.text, textAlign: 'center' },
    emptyBody: { fontSize: 14, color: theme.muted, textAlign: 'center' },
    badge: { borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4, alignSelf: 'flex-start' },
    badgeText: { fontSize: 12, fontWeight: '700' },
    fieldLabel: { fontSize: 14, fontWeight: '600', color: theme.text },
    chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
    chip: { minHeight: 40, borderWidth: 1.5, borderRadius: 999, paddingHorizontal: 14, justifyContent: 'center', backgroundColor: theme.card },
    chipText: { fontSize: 14, fontWeight: '600' },
    error: { fontSize: 13, color: theme.error },
    hint: { fontSize: 13, color: theme.muted },
    stepper: {
        flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', borderWidth: 1.5, borderColor: theme.border,
        borderRadius: 12, backgroundColor: theme.card,
    },
    stepBtn: { width: 48, height: 48, alignItems: 'center', justifyContent: 'center' },
    stepBtnText: { fontSize: 22, fontWeight: '700', color: theme.primary },
    stepValue: { minWidth: 36, textAlign: 'center', fontSize: 18, fontWeight: '800', color: theme.text },
});
