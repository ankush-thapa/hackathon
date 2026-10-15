import React, { useState } from 'react';
import {
    ActivityIndicator,
    KeyboardAvoidingView,
    Platform,
    Pressable,
    ScrollView,
    StyleSheet,
    Text,
    TextInput,
    TextInputProps,
    View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Colors } from '../constants/Colors';
import { CommuteRole, Profile, saveProfile } from '../data/profile';

const theme = Colors.light;

type Form = {
    fullName: string;
    phone: string;
    gender: NonNullable<Profile['gender']> | '';
    company: string;
    role: CommuteRole | '';
    homeArea: string;
    workArea: string;
    leaveHomeAt: string;
    leaveWorkAt: string;
    makeModel: string;
    color: string;
    plate: string;
    seats: string;
};

const EMPTY: Form = {
    fullName: '', phone: '', gender: '', company: '', role: '',
    homeArea: '', workArea: '', leaveHomeAt: '08:30', leaveWorkAt: '18:00',
    makeModel: '', color: '', plate: '', seats: '3',
};

const TIME_RE = /^([01]?\d|2[0-3]):[0-5]\d$/;

function validate(f: Form) {
    const e: Partial<Record<keyof Form, string>> = {};
    if (f.fullName.trim().length < 2) e.fullName = 'Enter your full name';
    if (f.phone.replace(/\D/g, '').length < 8) e.phone = 'Enter a valid phone number';
    if (!f.company.trim()) e.company = 'Enter your company';
    if (!f.role) e.role = 'Choose how you commute';
    if (!f.homeArea.trim()) e.homeArea = 'Enter your home area';
    if (!f.workArea.trim()) e.workArea = 'Enter your office area';
    if (!TIME_RE.test(f.leaveHomeAt)) e.leaveHomeAt = 'Use HH:MM (24h)';
    if (!TIME_RE.test(f.leaveWorkAt)) e.leaveWorkAt = 'Use HH:MM (24h)';
    if (f.role === 'driver' || f.role === 'both') {
        if (!f.makeModel.trim()) e.makeModel = 'Enter your car';
        if (!f.color.trim()) e.color = 'Enter the colour';
        if (!f.plate.trim()) e.plate = 'Enter the plate number';
        const seats = Number(f.seats);
        if (!Number.isInteger(seats) || seats < 1 || seats > 7) e.seats = '1–7 seats';
    }
    return e;
}

export default function ProfileSetupScreen() {
    const router = useRouter();
    const [form, setForm] = useState<Form>(EMPTY);
    const [submitted, setSubmitted] = useState(false);
    const [saving, setSaving] = useState(false);

    const errors = validate(form);
    const showErr = (k: keyof Form) => (submitted ? errors[k] : undefined);
    const set = <K extends keyof Form>(k: K) => (v: Form[K]) => setForm(prev => ({ ...prev, [k]: v }));
    const isDriver = form.role === 'driver' || form.role === 'both';

    const onSubmit = async () => {
        setSubmitted(true);
        if (Object.keys(errors).length) return;
        setSaving(true);
        await saveProfile({
            fullName: form.fullName.trim(),
            phone: form.phone.trim(),
            gender: form.gender || undefined,
            company: form.company.trim(),
            role: form.role as CommuteRole,
            homeArea: form.homeArea.trim(),
            workArea: form.workArea.trim(),
            leaveHomeAt: form.leaveHomeAt,
            leaveWorkAt: form.leaveWorkAt,
            vehicle: isDriver
                ? { makeModel: form.makeModel.trim(), color: form.color.trim(), plate: form.plate.trim().toUpperCase(), seats: Number(form.seats) }
                : undefined,
        });
        setSaving(false);
        router.replace('/rides');
    };

    return (
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
            <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
                <View style={styles.main}>
                    <Text style={styles.title}>Set up your profile</Text>
                    <Text style={styles.subtitle}>Tell co-workers who you are and how you commute so we can match you with rides.</Text>

                    <Section title="About you">
                        <Field label="Full name" value={form.fullName} onChangeText={set('fullName')} error={showErr('fullName')} placeholder="e.g. Ritesh Bisht" autoCapitalize="words" textContentType="name" />
                        <Field label="Phone" value={form.phone} onChangeText={set('phone')} error={showErr('phone')} placeholder="+971 50 123 4567" keyboardType="phone-pad" textContentType="telephoneNumber" />
                        <Field label="Company" value={form.company} onChangeText={set('company')} error={showErr('company')} placeholder="e.g. Noon" />
                        <Label text="Gender" optional />
                        <Chips
                            options={[{ value: 'female', label: 'Female' }, { value: 'male', label: 'Male' }, { value: 'other', label: 'Prefer not to say' }]}
                            value={form.gender}
                            onChange={v => set('gender')(form.gender === v ? '' : v)}
                        />
                    </Section>

                    <Section title="How do you commute?">
                        <Chips
                            options={[
                                { value: 'rider', label: 'I need rides' },
                                { value: 'driver', label: 'I offer rides' },
                                { value: 'both', label: 'Both' },
                            ]}
                            value={form.role}
                            onChange={set('role')}
                        />
                        {showErr('role') && <Text style={styles.error}>{showErr('role')}</Text>}
                    </Section>

                    <Section title="Your daily route">
                        <Field label="Home area" value={form.homeArea} onChangeText={set('homeArea')} error={showErr('homeArea')} placeholder="e.g. Dubai Marina" />
                        <Field label="Office area" value={form.workArea} onChangeText={set('workArea')} error={showErr('workArea')} placeholder="e.g. Dubai Internet City" />
                        <View style={styles.row}>
                            <View style={{ flex: 1 }}>
                                <Field label="Leave home" value={form.leaveHomeAt} onChangeText={set('leaveHomeAt')} error={showErr('leaveHomeAt')} placeholder="08:30" keyboardType="numbers-and-punctuation" maxLength={5} />
                            </View>
                            <View style={{ flex: 1 }}>
                                <Field label="Leave office" value={form.leaveWorkAt} onChangeText={set('leaveWorkAt')} error={showErr('leaveWorkAt')} placeholder="18:00" keyboardType="numbers-and-punctuation" maxLength={5} />
                            </View>
                        </View>
                    </Section>

                    {isDriver && (
                        <Section title="Your car">
                            <Field label="Make & model" value={form.makeModel} onChangeText={set('makeModel')} error={showErr('makeModel')} placeholder="e.g. Toyota Camry" />
                            <View style={styles.row}>
                                <View style={{ flex: 1 }}>
                                    <Field label="Colour" value={form.color} onChangeText={set('color')} error={showErr('color')} placeholder="White" />
                                </View>
                                <View style={{ flex: 1 }}>
                                    <Field label="Seats offered" value={form.seats} onChangeText={set('seats')} error={showErr('seats')} placeholder="3" keyboardType="number-pad" maxLength={1} />
                                </View>
                            </View>
                            <Field label="Plate number" value={form.plate} onChangeText={set('plate')} error={showErr('plate')} placeholder="e.g. Dubai A 12345" autoCapitalize="characters" />
                        </Section>
                    )}

                    <Pressable
                        onPress={onSubmit}
                        disabled={saving}
                        accessibilityRole="button"
                        style={({ pressed }) => [styles.button, (pressed || saving) && { opacity: 0.8 }]}
                    >
                        {saving ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.buttonText}>Save and continue</Text>}
                    </Pressable>
                    {submitted && Object.keys(errors).length > 0 && (
                        <Text style={[styles.error, { textAlign: 'center' }]}>Please fix the highlighted fields.</Text>
                    )}
                </View>
            </ScrollView>
        </KeyboardAvoidingView>
    );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <View style={styles.card}>
            <Text style={styles.sectionTitle}>{title}</Text>
            {children}
        </View>
    );
}

function Label({ text, optional }: { text: string; optional?: boolean }) {
    return (
        <Text style={styles.label}>
            {text}{optional && <Text style={styles.optional}>  Optional</Text>}
        </Text>
    );
}

function Field({ label, error, ...props }: TextInputProps & { label: string; error?: string }) {
    const [focused, setFocused] = useState(false);
    return (
        <View style={{ gap: 6 }}>
            <Label text={label} />
            <TextInput
                {...props}
                onFocus={e => { setFocused(true); props.onFocus?.(e); }}
                onBlur={e => { setFocused(false); props.onBlur?.(e); }}
                placeholderTextColor="#A0A7B1"
                accessibilityLabel={label}
                style={[
                    styles.input,
                    focused && { borderColor: theme.primary },
                    !!error && { borderColor: theme.error },
                ]}
            />
            {error && <Text style={styles.error}>{error}</Text>}
        </View>
    );
}

function Chips<T extends string>({ options, value, onChange }: {
    options: { value: T; label: string }[];
    value: T | '';
    onChange: (v: T) => void;
}) {
    return (
        <View style={styles.chips}>
            {options.map(o => {
                const active = value === o.value;
                return (
                    <Pressable
                        key={o.value}
                        onPress={() => onChange(o.value)}
                        accessibilityRole="radio"
                        accessibilityState={{ selected: active }}
                        style={({ pressed }) => [styles.chip, active && styles.chipActive, pressed && { opacity: 0.75 }]}
                    >
                        <Text style={[styles.chipText, active && { color: '#FFFFFF' }]}>{o.label}</Text>
                    </Pressable>
                );
            })}
        </View>
    );
}

const styles = StyleSheet.create({
    scroll: { flexGrow: 1, paddingBottom: 40 },
    main: {
        width: '100%',
        maxWidth: 600,
        alignSelf: 'center',
        paddingHorizontal: 24,
        paddingTop: 32,
        gap: 16,
    },
    title: { fontSize: 28, fontWeight: '800', color: theme.text },
    subtitle: { fontSize: 15, color: theme.muted, marginTop: -8 },
    card: {
        backgroundColor: theme.card,
        borderColor: theme.border,
        borderWidth: 1,
        borderRadius: 14,
        padding: 16,
        gap: 14,
    },
    sectionTitle: { fontSize: 17, fontWeight: '700', color: theme.text },
    label: { fontSize: 14, fontWeight: '600', color: theme.text },
    optional: { fontSize: 12, fontWeight: '500', color: theme.muted },
    input: {
        borderWidth: 1,
        borderColor: theme.border,
        borderRadius: 10,
        paddingHorizontal: 12,
        paddingVertical: Platform.OS === 'ios' ? 12 : 10,
        fontSize: 16,
        color: theme.text,
        backgroundColor: '#FFFFFF',
    },
    error: { fontSize: 13, color: theme.error },
    row: { flexDirection: 'row', gap: 12 },
    chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
    chip: {
        paddingVertical: 8,
        paddingHorizontal: 14,
        borderRadius: 20,
        borderWidth: 1,
        borderColor: theme.border,
        backgroundColor: '#FFFFFF',
    },
    chipActive: { backgroundColor: theme.primary, borderColor: theme.primary },
    chipText: { fontSize: 14, fontWeight: '600', color: theme.text },
    button: {
        backgroundColor: theme.primary,
        borderRadius: 12,
        paddingVertical: 14,
        alignItems: 'center',
        marginTop: 4,
    },
    buttonText: { color: '#FFFFFF', fontSize: 16, fontWeight: '700' },
});
