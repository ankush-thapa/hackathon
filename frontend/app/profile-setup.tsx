import React, { useState } from 'react';
import {
    ActivityIndicator,
    Image,
    KeyboardAvoidingView,
    Platform,
    Pressable,
    ScrollView,
    StyleSheet,
    Text,
    View,
} from 'react-native';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { PrimaryButton } from '../components/PrimaryButton';
import { TextField } from '../components/TextField';
import { Colors } from '../constants/Colors';
import { Gender, LIMITS } from '../data/profile';
import { MAX_PHOTO_BYTES, PHOTO_TYPES, ProfileError, saveProfile, uploadPhoto } from '../services/profile';

const theme = Colors.light;
const MIN_AGE = 18;

type Form = { fullName: string; dateOfBirth: string; gender: Gender | ''; about: string };
const EMPTY: Form = { fullName: '', dateOfBirth: '', gender: '', about: '' };

const GENDER_OPTIONS: { value: Gender; label: string }[] = [
    { value: 'female', label: 'Female' },
    { value: 'male', label: 'Male' },
    { value: 'other', label: 'Other' },
    { value: 'prefer_not_to_say', label: 'Prefer not to say' },
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

function validate(f: Form) {
    const e: Partial<Record<keyof Form, string>> = {};
    const name = f.fullName.trim();
    if (!name) e.fullName = 'Enter your full name';
    else if (name.length > LIMITS.fullName) e.fullName = `Keep it under ${LIMITS.fullName} characters`;

    const dobText = f.dateOfBirth.trim();
    if (dobText) {
        const dob = parseDob(dobText);
        if (!dob) e.dateOfBirth = 'Use YYYY-MM-DD, e.g. 1995-04-21';
        else if (dob >= new Date()) e.dateOfBirth = 'Date of birth must be in the past';
        else if (ageOn(dob) < MIN_AGE) e.dateOfBirth = `You must be at least ${MIN_AGE}`;
    }
    if (f.about.trim().length > LIMITS.about) e.about = `Keep it under ${LIMITS.about} characters`;
    return e;
}

export default function ProfileSetupScreen() {
    const router = useRouter();
    const [form, setForm] = useState<Form>(EMPTY);
    const [photoUrl, setPhotoUrl] = useState<string | null>(null);
    const [uploading, setUploading] = useState(false);
    const [photoError, setPhotoError] = useState<string | null>(null);
    const [submitted, setSubmitted] = useState(false);
    const [saving, setSaving] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);

    const errors = validate(form);
    const err = (k: keyof Form) => (submitted ? errors[k] : undefined);
    const set = <K extends keyof Form>(k: K) => (v: Form[K]) => setForm(prev => ({ ...prev, [k]: v }));
    const initials = form.fullName.trim().split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join('');

    const pickPhoto = async () => {
        setPhotoError(null);
        const result = await ImagePicker.launchImageLibraryAsync({
            mediaTypes: ['images'],
            allowsEditing: true,
            aspect: [1, 1],
            quality: 0.8,
        });
        if (result.canceled || !result.assets?.[0]) return;
        const asset = result.assets[0];
        if (asset.mimeType && !PHOTO_TYPES.includes(asset.mimeType)) return setPhotoError('Use a JPEG, PNG or WebP image');
        if (asset.fileSize && asset.fileSize > MAX_PHOTO_BYTES) return setPhotoError('Choose an image under 5 MB');

        setUploading(true);
        try {
            setPhotoUrl(await uploadPhoto(asset));
        } catch (e) {
            setPhotoError(e instanceof ProfileError ? e.message : 'Upload failed. Please try again.');
        } finally {
            setUploading(false);
        }
    };

    const onSubmit = async () => {
        setSubmitted(true);
        setFormError(null);
        if (Object.keys(errors).length || uploading) return;
        setSaving(true);
        try {
            await saveProfile({
                fullName: form.fullName.trim(),
                photoUrl,
                about: form.about.trim() || null,
                dateOfBirth: form.dateOfBirth.trim() || null,
                gender: form.gender || null,
            });
            router.replace('/dashboard');
        } catch (e) {
            setFormError(e instanceof ProfileError ? e.message : 'Something went wrong. Please try again.');
            if (e instanceof ProfileError && e.status === 401) router.replace('/login');
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

                    <View style={styles.card}>
                        <View style={styles.photoRow}>
                            <Pressable
                                onPress={pickPhoto}
                                disabled={uploading}
                                accessibilityRole="button"
                                accessibilityLabel={photoUrl ? 'Change profile photo' : 'Add profile photo'}
                                style={({ pressed }) => [styles.avatar, pressed && { opacity: 0.8 }]}
                            >
                                {photoUrl ? (
                                    <Image source={{ uri: photoUrl }} style={styles.avatarImg} />
                                ) : (
                                    <Text style={styles.avatarText}>{initials || '+'}</Text>
                                )}
                                {uploading && (
                                    <View style={styles.avatarOverlay}>
                                        <ActivityIndicator color="#FFFFFF" />
                                    </View>
                                )}
                            </Pressable>
                            <View style={{ flex: 1, gap: 4 }}>
                                <Text style={styles.label}>Profile photo <Text style={styles.optional}>(optional)</Text></Text>
                                <Text style={styles.hint}>JPEG, PNG or WebP, up to 5 MB.</Text>
                                <View style={styles.photoActions}>
                                    <Pressable onPress={pickPhoto} disabled={uploading} hitSlop={6} accessibilityRole="button">
                                        <Text style={styles.link}>{uploading ? 'Uploading…' : photoUrl ? 'Change photo' : 'Upload photo'}</Text>
                                    </Pressable>
                                    {photoUrl && !uploading && (
                                        <Pressable onPress={() => setPhotoUrl(null)} hitSlop={6} accessibilityRole="button">
                                            <Text style={[styles.link, { color: theme.muted }]}>Remove</Text>
                                        </Pressable>
                                    )}
                                </View>
                                {photoError && <Text style={styles.error}>{photoError}</Text>}
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
                            autoComplete="name"
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
                            <View style={styles.chips}>
                                {GENDER_OPTIONS.map(o => {
                                    const active = form.gender === o.value;
                                    return (
                                        <Pressable
                                            key={o.value}
                                            onPress={() => set('gender')(active ? '' : o.value)}
                                            accessibilityRole="radio"
                                            accessibilityState={{ selected: active }}
                                            style={({ pressed }) => [styles.chip, active && styles.chipActive, pressed && { opacity: 0.75 }]}
                                        >
                                            <Text style={[styles.chipText, active && { color: '#FFFFFF' }]}>{o.label}</Text>
                                        </Pressable>
                                    );
                                })}
                            </View>
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
                    </View>

                    {formError && <Text style={[styles.error, { textAlign: 'center' }]}>{formError}</Text>}
                    <PrimaryButton title="Save and continue" onPress={onSubmit} loading={saving} disabled={uploading} />
                    <Pressable onPress={() => router.replace('/dashboard')} hitSlop={8} style={styles.skip} accessibilityRole="button">
                        <Text style={styles.skipText}>Skip for now</Text>
                    </Pressable>
                </View>
            </ScrollView>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    scroll: { flexGrow: 1, paddingBottom: 40 },
    main: { width: '100%', maxWidth: 600, alignSelf: 'center', paddingHorizontal: 24, paddingTop: 32, gap: 16 },
    title: { fontSize: 28, fontWeight: '800', color: theme.text },
    subtitle: { fontSize: 15, color: theme.muted, marginTop: -8 },
    card: { backgroundColor: theme.card, borderColor: theme.border, borderWidth: 1, borderRadius: 14, padding: 16, gap: 18 },
    label: { fontSize: 14, fontWeight: '600', color: theme.text },
    optional: { fontSize: 13, fontWeight: '500', color: theme.muted },
    hint: { fontSize: 13, color: theme.muted },
    link: { fontSize: 14, fontWeight: '700', color: theme.primary },
    error: { fontSize: 13, color: theme.error },
    counter: { fontSize: 12, color: theme.muted, textAlign: 'right', marginTop: 4 },
    photoRow: { flexDirection: 'row', alignItems: 'center', gap: 16 },
    photoActions: { flexDirection: 'row', gap: 16, marginTop: 2 },
    avatar: {
        width: 76, height: 76, borderRadius: 38,
        backgroundColor: theme.primary, alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
    },
    avatarImg: { width: 76, height: 76 },
    avatarText: { color: '#FFFFFF', fontSize: 26, fontWeight: '700' },
    avatarOverlay: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,0,0.35)', alignItems: 'center', justifyContent: 'center' },
    chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
    chip: { paddingVertical: 8, paddingHorizontal: 14, borderRadius: 20, borderWidth: 1, borderColor: theme.border, backgroundColor: '#FFFFFF' },
    chipActive: { backgroundColor: theme.primary, borderColor: theme.primary },
    chipText: { fontSize: 14, fontWeight: '600', color: theme.text },
    skip: { alignSelf: 'center', paddingVertical: 4 },
    skipText: { fontSize: 15, fontWeight: '600', color: theme.muted },
});
