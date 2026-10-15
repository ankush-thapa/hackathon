import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Colors } from '../constants/Colors';
import { combine, dayLabel, nextDays, parseTime } from '../services/format';
import { TextField } from './TextField';

const theme = Colors.light;
export const DAYS_AHEAD = 7;

type Props = {
    dayIndex: number;
    onDayChange: (i: number) => void;
    time: string;
    onTimeChange: (t: string) => void;
    timeError?: string;
};

/** Date chips for the next week plus a 24h time field — no native picker dependency needed. */
export const DeparturePicker = ({ dayIndex, onDayChange, time, onTimeChange, timeError }: Props) => {
    const days = nextDays(DAYS_AHEAD);
    return (
        <View style={{ gap: 16 }}>
            <View style={{ gap: 8 }}>
                <Text style={styles.label}>Departure date</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.days}>
                    {days.map((d, i) => {
                        const selected = i === dayIndex;
                        return (
                            <Pressable
                                key={d.toISOString()}
                                onPress={() => onDayChange(i)}
                                accessibilityRole="radio"
                                accessibilityState={{ selected }}
                                style={[styles.day, selected && { backgroundColor: theme.primary, borderColor: theme.primary }]}
                            >
                                <Text style={[styles.dayText, { color: selected ? '#FFFFFF' : theme.text }]}>{dayLabel(d)}</Text>
                            </Pressable>
                        );
                    })}
                </ScrollView>
            </View>
            <TextField
                label="Departure time"
                placeholder="08:30"
                value={time}
                onChangeText={onTimeChange}
                error={timeError}
                hint="24-hour time, e.g. 08:30 or 18:15"
                keyboardType="numbers-and-punctuation"
                maxLength={5}
            />
        </View>
    );
};

export function validateDeparture(dayIndex: number, time: string): { error?: string; date?: Date } {
    const t = parseTime(time);
    if (!t) return { error: time.trim() ? 'Use HH:MM, e.g. 08:30' : 'Enter a departure time' };
    const date = combine(nextDays(DAYS_AHEAD)[dayIndex], t);
    if (date.getTime() <= Date.now()) return { error: 'That time has already passed' };
    return { date };
}

const styles = StyleSheet.create({
    label: { fontSize: 14, fontWeight: '600', color: theme.text },
    days: { gap: 8, paddingRight: 8 },
    day: {
        minHeight: 40, borderWidth: 1.5, borderColor: theme.border, borderRadius: 999,
        paddingHorizontal: 14, justifyContent: 'center', backgroundColor: theme.card,
    },
    dayText: { fontSize: 14, fontWeight: '600' },
});
