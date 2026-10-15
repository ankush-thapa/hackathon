import React from 'react';
import { View } from 'react-native';
import { combine, parseTime } from '../services/format';
import { DateField } from './DateField';
import { TextField } from './TextField';

export const DAYS_AHEAD = 60;

type Props = {
    day: Date;
    onDayChange: (d: Date) => void;
    time: string;
    onTimeChange: (t: string) => void;
    timeError?: string;
};

/** Calendar for the date plus a 24h time field. Both are in the user's local time. */
export const DeparturePicker = ({ day, onDayChange, time, onTimeChange, timeError }: Props) => (
    <View style={{ gap: 16 }}>
        <DateField label="Departure date" value={day} onChange={onDayChange} maxDaysAhead={DAYS_AHEAD} />
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

export function validateDeparture(day: Date, time: string): { error?: string; date?: Date } {
    const t = parseTime(time);
    if (!t) return { error: time.trim() ? 'Use HH:MM, e.g. 08:30' : 'Enter a departure time' };
    const date = combine(day, t); // local date + local time; sent to the API as UTC ISO
    if (date.getTime() <= Date.now()) return { error: 'That time has already passed' };
    return { date };
}
