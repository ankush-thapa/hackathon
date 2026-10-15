import React, { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Colors } from '../constants/Colors';
import { addDays, fullDayLabel, sameDay, startOfDay, today } from '../services/format';
import { Icon } from './Icon';

const theme = Colors.light;
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

type Props = {
    label: string;
    value: Date;
    onChange: (d: Date) => void;
    /** How many days ahead can be picked (today is always the first day). */
    maxDaysAhead?: number;
    error?: string;
};

/** A date field that opens a month calendar. Days are local calendar days; past days are disabled. */
export const DateField = ({ label, value, onChange, maxDaysAhead = 60, error }: Props) => {
    const [open, setOpen] = useState(false);
    const [month, setMonth] = useState(() => new Date(value.getFullYear(), value.getMonth(), 1));
    useEffect(() => { if (open) setMonth(new Date(value.getFullYear(), value.getMonth(), 1)); }, [open, value]);

    const min = today(); // recomputed every render, so it's never stale after midnight
    const max = addDays(min, maxDaysAhead);
    const firstMonth = new Date(min.getFullYear(), min.getMonth(), 1);
    const lastMonth = new Date(max.getFullYear(), max.getMonth(), 1);

    // Grid: Monday-first weeks covering the month.
    const lead = (month.getDay() + 6) % 7;
    const daysInMonth = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
    const cells: (Date | null)[] = [
        ...Array.from({ length: lead }, () => null),
        ...Array.from({ length: daysInMonth }, (_, i) => new Date(month.getFullYear(), month.getMonth(), i + 1)),
    ];
    while (cells.length % 7) cells.push(null);

    const canPrev = month > firstMonth;
    const canNext = month < lastMonth;
    const monthTitle = month.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });

    return (
        <View style={{ gap: 6 }}>
            <Text style={styles.label}>{label}</Text>
            <Pressable
                onPress={() => setOpen(o => !o)}
                accessibilityRole="button"
                accessibilityLabel={`${label}: ${fullDayLabel(value)}. ${open ? 'Close' : 'Open'} calendar`}
                style={[styles.field, { borderColor: error ? theme.error : open ? theme.primary : theme.border }]}
            >
                <CalendarGlyph />
                <Text style={styles.fieldText}>{fullDayLabel(value)}</Text>
                <View style={{ transform: [{ rotate: open ? '-90deg' : '90deg' }] }}>
                    <Icon name="chevron" color={theme.muted} size={16} />
                </View>
            </Pressable>
            {error ? <Text style={styles.error}>{error}</Text> : null}

            {open ? (
                <View style={styles.calendar}>
                    <View style={styles.header}>
                        <Pressable
                            onPress={() => canPrev && setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}
                            disabled={!canPrev}
                            accessibilityRole="button"
                            accessibilityLabel="Previous month"
                            style={[styles.nav, !canPrev && { opacity: 0.3 }]}
                        >
                            <Icon name="back" color={theme.text} size={18} />
                        </Pressable>
                        <Text style={styles.monthTitle} accessibilityRole="header">{monthTitle}</Text>
                        <Pressable
                            onPress={() => canNext && setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}
                            disabled={!canNext}
                            accessibilityRole="button"
                            accessibilityLabel="Next month"
                            style={[styles.nav, !canNext && { opacity: 0.3 }]}
                        >
                            <Icon name="chevron" color={theme.text} size={18} />
                        </Pressable>
                    </View>
                    <View style={styles.row}>
                        {WEEKDAYS.map(w => <Text key={w} style={styles.weekday}>{w}</Text>)}
                    </View>
                    {Array.from({ length: cells.length / 7 }, (_, r) => (
                        <View key={r} style={styles.row}>
                            {cells.slice(r * 7, r * 7 + 7).map((d, i) => {
                                if (!d) return <View key={i} style={styles.cell} />;
                                const disabled = d < min || d > max;
                                const selected = sameDay(d, value);
                                const isToday = sameDay(d, min);
                                return (
                                    <Pressable
                                        key={i}
                                        disabled={disabled}
                                        onPress={() => { onChange(startOfDay(d)); setOpen(false); }}
                                        accessibilityRole="button"
                                        accessibilityState={{ selected, disabled }}
                                        accessibilityLabel={fullDayLabel(d)}
                                        style={styles.cell}
                                    >
                                        <View
                                            style={[
                                                styles.day,
                                                isToday && !selected && { borderColor: theme.primary, borderWidth: 1.5 },
                                                selected && { backgroundColor: theme.primary },
                                            ]}
                                        >
                                            <Text
                                                style={[
                                                    styles.dayText,
                                                    disabled && { color: theme.border },
                                                    selected && { color: '#FFFFFF', fontWeight: '800' },
                                                ]}
                                            >
                                                {d.getDate()}
                                            </Text>
                                        </View>
                                    </Pressable>
                                );
                            })}
                        </View>
                    ))}
                    <View style={styles.quick}>
                        <Pressable onPress={() => { onChange(min); setOpen(false); }} hitSlop={8}>
                            <Text style={styles.quickText}>Today</Text>
                        </Pressable>
                        <Pressable onPress={() => { onChange(addDays(min, 1)); setOpen(false); }} hitSlop={8}>
                            <Text style={styles.quickText}>Tomorrow</Text>
                        </Pressable>
                    </View>
                </View>
            ) : null}
        </View>
    );
};

/** Small calendar icon drawn with Views (no icon library). */
const CalendarGlyph = () => (
    <View style={styles.glyph}>
        <View style={[styles.glyphTop, { backgroundColor: theme.primary }]} />
    </View>
);

const styles = StyleSheet.create({
    label: { fontSize: 14, fontWeight: '600', color: theme.text },
    field: {
        flexDirection: 'row', alignItems: 'center', gap: 10, minHeight: 52, borderWidth: 1.5, borderRadius: 12,
        paddingHorizontal: 14, backgroundColor: theme.card,
    },
    fieldText: { flex: 1, fontSize: 16, fontWeight: '600', color: theme.text },
    error: { fontSize: 13, color: theme.error },
    calendar: { borderWidth: 1, borderColor: theme.border, borderRadius: 14, backgroundColor: theme.card, padding: 10, gap: 2 },
    header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 },
    nav: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
    monthTitle: { fontSize: 16, fontWeight: '800', color: theme.text },
    row: { flexDirection: 'row' },
    weekday: { flex: 1, textAlign: 'center', fontSize: 12, fontWeight: '700', color: theme.muted, paddingVertical: 6 },
    cell: { flex: 1, aspectRatio: 1, maxHeight: 48, alignItems: 'center', justifyContent: 'center' },
    day: { width: 38, height: 38, borderRadius: 19, alignItems: 'center', justifyContent: 'center' },
    dayText: { fontSize: 15, color: theme.text },
    quick: { flexDirection: 'row', justifyContent: 'center', gap: 28, paddingTop: 8, paddingBottom: 4 },
    quickText: { fontSize: 14, fontWeight: '700', color: theme.primary },
    glyph: { width: 18, height: 17, borderWidth: 2, borderColor: theme.primary, borderRadius: 4, overflow: 'hidden' },
    glyphTop: { height: 4 },
});
