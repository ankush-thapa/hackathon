import React, { useState } from 'react';
import {
    Image,
    KeyboardAvoidingView,
    Platform,
    Pressable,
    ScrollView,
    StyleSheet,
    Switch,
    Text,
    View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { PrimaryButton } from '../components/PrimaryButton';
import { TextField } from '../components/TextField';
import { Colors } from '../constants/Colors';
import {
    Gender,
    LIMITS,
    VehicleType,
    normalizeRegistration,
    saveProfile,
} from '../data/profile';

const theme = Colors.light;
const MIN_AGE = 18;

type Form = {
    fullName: string;
    photoUrl: string;
    dateOfBirth: string;
    gender: Gender | '';
    about: string;
    offerRides: boolean;
    make: string;
    model: string;
    color: string;
    registrationNumber: string;
    seatCapacity: number;
    vehicleType: VehicleType | '';
};

const EMPTY: Form = {
    fullName: '', photoUrl: '', dateOfBirth: '', gender: '', about: '',
    offerRides: false, make: '', model: '', color: '', registrationNumber: '', seatCapacity: 3, vehicleType: '',
};

const GENDER_OPTIONS: { value: Gender; label: string }[] = [
    { value: 'female', label: 'Female' },
    { value: 'male', label: 'Male' },
    { value: 'other', label: 'Other' },
    { value: 'prefer_not_to_say', label: 'Prefer not to say' },
];

const VEHICLE_OPTIONS: { value: VehicleType; label: string }[] = [
    { value: 'hatchback', label: 'Hatchback' },
    { value: 'sedan', label: 'Sedan' },
    { value: 'suv', label: 'SUV' },
    { value: 'bike', label: 'Bike' },
];

function parseDob(value: string): Date | null {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    if (!m) return null;
    const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];
    const date = new Date(y, mo - 1, d);
    return date.getFullYear() === y && date.getMonth() === mo - 1 && date.getDate() === d ? date : null;
}

function ageOn(dob: Date, today = new Date()) {
    let age = today.getFullYear() - dob.getFullYear();
    const m = today.getMonth() - dob.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) age--;
    return age;
}

const required = (v: string, msg: string, max: number) =>
    !v.trim() ? msg : v.trim().length > max ? `Keep it under ${max} characters` : undefined;

function validate(f: Form) {
    const e: Partial<Record<keyof Form, string>> = {};
    const name = required(f.fullName, 'Enter your full name', LIMITS.fullName);
    if (name) e.fullName = name;
    else if (f.fullName.trim().length < 2) e.fullName = 'Enter your full name';

    if (f.photoUrl.trim()) {
        if (!/^https?:\/\/\S+$/i.test(f.photoUrl.trim())) e.photoUrl = 'Enter a link starting with http:// or https://';
        else if (f.photoUrl.trim().length > LIMITS.photoUrl) e.photoUrl = `Keep it under ${LIMITS.photoUrl} characters`;
    }
    if (f.dateOfBirth.trim()) {
        const dob = parseDob(f.dateOfBirth.trim());
        if (!dob) e.dateOfBirth = 'Use YYYY-MM-DD, e.g. 1995-04-21';
        else if (dob > new Date()) e.dateOfBirth = "Date of birth can't be in the future";
        else if (ageOn(dob) < MIN_AGE) e.dateOfBirth = `You must be at least ${MIN_AGE}`;
    }
    if (f.about.length > LIMITS.about) e.about = `Keep it under ${LIMITS.about} characters`;

    if (f.offerRides) {
        const checks: [keyof Form, string, number][] = [
            ['make', 'Enter the make, e.g. Toyota', LIMITS.make],
            ['model', 'Enter the model, e.g. Camry', LIMITS.model],
            ['color', 'Enter the colour', LIMITS.color],
        ];
        for (const [k, msg, max] of checks) {
            const err = required(f[k] as string, msg, max);
            if (err) e[k] = err;
        }
        const reg = normalizeRegistration(f.registrationNumber);
        if (!reg) e.registrationNumber = 'Enter the registration number';
        else if (reg.length > LIMITS.registrationNumber) e.registrationNumber = `Keep it under ${LIMITS.registrationNumber} characters`;
        if (!f.vehicleType) e.vehicleType = 'Choose a vehicle type';
    }
    return e;
}

export default function ProfileSetupScreen() {
    const router = useRouter();
    const [form, setForm] = useState<Form>(EMPTY);
    const [submitted, setSubmitted] = useState(false);
    const [saving, setSaving] = useState(false);
    const [photoFailed, setPhotoFailed] = useState(false);

    const errors = validate(form);
    const err = (k: keyof Form) => (submitted ? errors[k] : undefined);
    const set = <K extends keyof Form>(k: K) => (v: Form[K]) => setForm(prev => ({ ...prev, [k]: v }));

    const maxSeats = form.vehicleType === 'bike' ? 1 : LIMITS.maxSeats;
    const setVehicleType = (t: VehicleType) =>
        setForm(prev => ({ ...prev, vehicleType: t, seatCapacity: Math.min(prev.seatCapacity, t === 'bike' ? 1 : LIMITS.maxSeats) }));

    const initials = form.fullName.trim().split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join('');
    const photo = form.photoUrl.trim();
    const showPhoto = !!photo && !errors.photoUrl && !photoFailed;

    const onSubmit = async () => {
        setSubmitted(true);
        if (Object.keys(errors).length) return;
        setSaving(true);
        try {
            await saveProfile({
                profile: {
                    fullName: form.fullName.trim(),
                    photoUrl: photo || undefined,
                    about: form.about.trim() || undefined,
                    dateOfBirth: form.dateOfBirth.trim() || undefined,
                    gender: form.gender || undefined,
                },
                vehicle: form.offerRides
                    ? {
                          make: form.make.trim(),
                          model: form.model.trim(),
                          color: form.color.trim(),
                          registrationNumber: normalizeRegistration(form.registrationNumber),
                          seatCapacity: form.seatCapacity,
                          vehicleType: form.vehicleType as VehicleType,
                          isDefault: true, // first vehicle becomes the default
                      }
                    : undefined,
            });
            router.replace('/home');
        } finally {
            setSaving(false);
        }
    };

    return (
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
            <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
                <View style={styles.main}>
                    <Text style={styles.title}>Set up your profile</Text>
                    <Text style={styles.subtitle}>This is what co-riders see when you share a ride.</Text>

                    {/* user_profile */}
                    <Section title="About you">
                        <View style={styles.avatarRow}>
                            <View style={styles.avatar}>
                                {showPhoto ? (
                                    <Image source={{ uri: photo }} style={styles.avatarImg} onError={() => setPhotoFailed(true)} />
                                ) : (
                                    <Text style={styles.avatarText}>{initials || '?'}</Text>
                                )}
                            </View>
                            <View style={{ flex: 1 }}>
                                <TextField
                                    label="Photo link (optional)"
                                    value={form.photoUrl}
                                    onChangeText={v => { setPhotoFailed(false); set('photoUrl')(v); }}
                                    error={err('photoUrl')}
                                    placeholder="https://…"
                                    keyboardType="url"
                                    maxLength={LIMITS.photoUrl}
                                />
                            </View>
                        </View>
                        <TextField
                            label="Full name"
                            value={form.fullName}
                            onChangeText={set('fullName')}
                            error={err('fullName')}
                            placeholder="e.g. Ritesh Bisht"
                            autoCapitalize="words"
                            textContentType="name"
                            maxLength={LIMITS.fullName}
                        />
                        <TextField
                            label="Date of birth (optional)"
                            value={form.dateOfBirth}
                            onChangeText={set('dateOfBirth')}
                            error={err('dateOfBirth')}
                            placeholder="YYYY-MM-DD"
                            keyboardType="numbers-and-punctuation"
                            maxLength={10}
                        />
                        <View style={{ gap: 8 }}>
                            <Text style={styles.label}>Gender <Text style={styles.optional}>(optional)</Text></Text>
                            <Chips
                                options={GENDER_OPTIONS}
                                value={form.gender}
                                onChange={v => set('gender')(form.gender === v ? '' : v)}
                            />
                        </View>
                        <View>
                            <TextField
                                label="About you (optional)"
                                value={form.about}
                                onChangeText={set('about')}
                                error={err('about')}
                                placeholder="Music taste, chatty or quiet, where you work…"
                                autoCapitalize="sentences"
                                autoCorrect
                                multiline
                                maxLength={LIMITS.about}
                                style={{ minHeight: 88, textAlignVertical: 'top' }}
                            />
                            <Text style={styles.counter}>{form.about.length}/{LIMITS.about}</Text>
                        </View>
                    </Section>

                    {/* vehicle */}
                    <Section title="Your vehicle">
                        <View style={styles.switchRow}>
                            <View style={{ flex: 1, gap: 2 }}>
                                <Text style={styles.label}>I want to offer rides</Text>
                                <Text style={styles.hint}>Add the vehicle you'll drive. You can skip this if you only need rides.</Text>
                            </View>
                            <Switch
                                value={form.offerRides}
                                onValueChange={set('offerRides')}
                                trackColor={{ true: theme.primary, false: theme.border }}
                                thumbColor="#FFFFFF"
                                accessibilityLabel="I want to offer rides"
                            />
                        </View>

                        {form.offerRides && (
                            <>
                                <View style={{ gap: 8 }}>
                                    <Text style={styles.label}>Vehicle type</Text>
                                    <Chips options={VEHICLE_OPTIONS} value={form.vehicleType} onChange={setVehicleType} />
                                    {err('vehicleType') && <Text style={styles.error}>{err('vehicleType')}</Text>}
                                </View>
                                <View style={styles.row}>
                                    <View style={{ flex: 1 }}>
                                        <TextField label="Make" value={form.make} onChangeText={set('make')} error={err('make')} placeholder="Toyota" autoCapitalize="words" maxLength={LIMITS.make} />
                                    </View>
                                    <View style={{ flex: 1 }}>
                                        <TextField label="Model" value={form.model} onChangeText={set('model')} error={err('model')} placeholder="Camry" autoCapitalize="words" maxLength={LIMITS.model} />
                                    </View>
                                </View>
                                <View style={styles.row}>
                                    <View style={{ flex: 1 }}>
                                        <TextField label="Colour" value={form.color} onChangeText={set('color')} error={err('color')} placeholder="White" autoCapitalize="words" maxLength={LIMITS.color} />
                                    </View>
                                    <View style={{ flex: 1 }}>
                                        <TextField
                                            label="Registration no."
                                            value={form.registrationNumber}
                                            onChangeText={v => set('registrationNumber')(v.toUpperCase())}
                                            error={err('registrationNumber')}
                                            placeholder="DXB A 12345"
                                            autoCapitalize="characters"
                                            maxLength={LIMITS.registrationNumber + 6}
                                        />
                                    </View>
                                </View>
                                <View style={styles.switchRow}>
                                    <View style={{ flex: 1, gap: 2 }}>
                                        <Text style={styles.label}>Seats you can offer</Text>
                                        <Text style={styles.hint}>
                                            {form.vehicleType === 'bike' ? 'Bikes carry one passenger.' : `Between ${LIMITS.minSeats} and ${LIMITS.maxSeats}.`}
                                        </Text>
                                    </View>
                                    <Stepper
                                        value={form.seatCapacity}
                                        min={LIMITS.minSeats}
                                        max={maxSeats}
                                        onChange={set('seatCapacity')}
                                    />
                                </View>
                            </>
                        )}
                    </Section>

                    <PrimaryButton title="Save and continue" onPress={onSubmit} loading={saving} />
                    {submitted && Object.keys(errors).length > 0 && (
                        <Text style={[styles.error, { textAlign: 'center' }]}>Please fix the highlighted fields.</Text>
                    )}
                    <Pressable onPress={() => router.replace('/home')} hitSlop={8} style={styles.skip} accessibilityRole="button">
                        <Text style={styles.skipText}>Skip for now</Text>
                    </Pressable>
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

function Stepper({ value, min, max, onChange }: { value: number; min: number; max: number; onChange: (v: number) => void }) {
    const btn = (label: string, next: number, disabled: boolean, a11y: string) => (
        <Pressable
            onPress={() => onChange(next)}
            disabled={disabled}
            accessibilityRole="button"
            accessibilityLabel={a11y}
            style={({ pressed }) => [styles.stepBtn, disabled && { opacity: 0.35 }, pressed && { opacity: 0.7 }]}
        >
            <Text style={styles.stepBtnText}>{label}</Text>
        </Pressable>
    );
    return (
        <View style={styles.stepper}>
            {btn('−', value - 1, value <= min, 'Fewer seats')}
            <Text style={styles.stepValue} accessibilityLiveRegion="polite">{value}</Text>
            {btn('+', value + 1, value >= max, 'More seats')}
        </View>
    );
}

const styles = StyleSheet.create({
    scroll: { flexGrow: 1, paddingBottom: 40 },
    main: { width: '100%', maxWidth: 600, alignSelf: 'center', paddingHorizontal: 24, paddingTop: 32, gap: 16 },
    title: { fontSize: 28, fontWeight: '800', color: theme.text },
    subtitle: { fontSize: 15, color: theme.muted, marginTop: -8 },
    card: { backgroundColor: theme.card, borderColor: theme.border, borderWidth: 1, borderRadius: 14, padding: 16, gap: 16 },
    sectionTitle: { fontSize: 17, fontWeight: '700', color: theme.text },
    label: { fontSize: 14, fontWeight: '600', color: theme.text },
    optional: { fontSize: 13, fontWeight: '500', color: theme.muted },
    hint: { fontSize: 13, color: theme.muted },
    error: { fontSize: 13, color: theme.error },
    counter: { fontSize: 12, color: theme.muted, textAlign: 'right', marginTop: 4 },
    row: { flexDirection: 'row', gap: 12 },
    avatarRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 14 },
    avatar: {
        width: 64, height: 64, borderRadius: 32, marginTop: 22,
        backgroundColor: theme.primary, alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
    },
    avatarImg: { width: 64, height: 64 },
    avatarText: { color: '#FFFFFF', fontSize: 22, fontWeight: '700' },
    chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
    chip: { paddingVertical: 8, paddingHorizontal: 14, borderRadius: 20, borderWidth: 1, borderColor: theme.border, backgroundColor: '#FFFFFF' },
    chipActive: { backgroundColor: theme.primary, borderColor: theme.primary },
    chipText: { fontSize: 14, fontWeight: '600', color: theme.text },
    switchRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
    stepper: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: theme.border, borderRadius: 12 },
    stepBtn: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
    stepBtnText: { fontSize: 20, fontWeight: '700', color: theme.primary },
    stepValue: { minWidth: 28, textAlign: 'center', fontSize: 17, fontWeight: '700', color: theme.text },
    skip: { alignSelf: 'center', paddingVertical: 4 },
    skipText: { fontSize: 15, fontWeight: '600', color: theme.muted },
});
