import React, { useState } from 'react';
import { ActivityIndicator, Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { PrimaryButton } from '../../components/PrimaryButton';
import { TextField } from '../../components/TextField';
import { Card, ChipGroup, FormError, Screen, SectionTitle } from '../../components/ui';
import { Colors } from '../../constants/Colors';
import { Gender, LIMITS } from '../../data/profile';
import { MAX_PHOTO_BYTES, PHOTO_TYPES, ProfileError, saveProfile, uploadPhoto, useProfile } from '../../services/profile';
import { getSession } from '../../services/session';

const theme = Colors.light;
const MIN_AGE = 18;

const GENDER_OPTIONS: { value: Gender; label: string }[] = [
    { value: 'female', label: 'Female' },
    { value: 'male', label: 'Male' },
    { value: 'other', label: 'Other' },
    { value: 'prefer_not_to_say', label: 'Prefer not to say' },
];

type Form = { fullName: string; dateOfBirth: string; gender: Gender | null; about: string };
type Errors = Partial<Record<keyof Form, string>>;

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

function validate(f: Form): Errors {
    const e: Errors = {};
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

/** View and edit the logged-in user's profile. Saves with POST /v1/auth/profile (create or replace). */
export default function ProfileScreen() {
    const router = useRouter();
    const profile = useProfile(); // last saved profile in this app session
    const session = getSession();

    const [form, setForm] = useState<Form>({
        fullName: profile.fullName,
        dateOfBirth: profile.dateOfBirth ?? '',
        gender: profile.gender,
        about: profile.about ?? '',
    });
    const [photoUrl, setPhotoUrl] = useState<string | null>(profile.photoUrl);
    const [uploading, setUploading] = useState(false);
    const [photoError, setPhotoError] = useState<string | null>(null);
    const [submitted, setSubmitted] = useState(false);
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);

    const errors = validate(form);
    const err = (k: keyof Form) => (submitted ? errors[k] : undefined);
    const set = <K extends keyof Form>(k: K) => (v: Form[K]) => {
        setSaved(false);
        setForm(prev => ({ ...prev, [k]: v }));
    };
    const initials = form.fullName.trim().split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join('');

    const pickPhoto = async () => {
        setPhotoError(null);
        const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], allowsEditing: true, aspect: [1, 1], quality: 0.8 });
        if (result.canceled || !result.assets?.[0]) return;
        const asset = result.assets[0];
        if (asset.mimeType && !PHOTO_TYPES.includes(asset.mimeType)) return setPhotoError('Use a JPEG, PNG or WebP image');
        if (asset.fileSize && asset.fileSize > MAX_PHOTO_BYTES) return setPhotoError('Choose an image under 5 MB');
        setUploading(true);
        try {
            setPhotoUrl(await uploadPhoto(asset));
            setSaved(false);
        } catch (e) {
            setPhotoError(e instanceof ProfileError ? e.message : 'Upload failed. Please try again.');
        } finally {
            setUploading(false);
        }
    };

    const onSave = async () => {
        setSubmitted(true);
        setFormError(null);
        setSaved(false);
        if (Object.keys(errors).length || uploading) return;
        setSaving(true);
        try {
            await saveProfile({
                fullName: form.fullName.trim(),
                photoUrl,
                about: form.about.trim() || null,
                dateOfBirth: form.dateOfBirth.trim() || null,
                gender: form.gender,
            });
            setSaved(true);
        } catch (e) {
            if (e instanceof ProfileError && e.status === 401) return router.replace('/login');
            setFormError(e instanceof ProfileError ? e.message : 'Something went wrong. Please try again.');
        } finally {
            setSaving(false);
        }
    };

    return (
        <Screen title="My profile" subtitle="This is what co-riders see when you share a ride.">
            <Card>
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
                        <Text style={styles.name} numberOfLines={1}>{form.fullName.trim() || 'Your name'}</Text>
                        <Text style={styles.hint}>JPEG, PNG or WebP, up to 5 MB.</Text>
                        <View style={styles.photoActions}>
                            <Pressable onPress={pickPhoto} disabled={uploading} hitSlop={6} accessibilityRole="button">
                                <Text style={styles.link}>{uploading ? 'Uploading…' : photoUrl ? 'Change photo' : 'Upload photo'}</Text>
                            </Pressable>
                            {photoUrl && !uploading ? (
                                <Pressable onPress={() => { setPhotoUrl(null); setSaved(false); }} hitSlop={6} accessibilityRole="button">
                                    <Text style={[styles.link, { color: theme.muted }]}>Remove</Text>
                                </Pressable>
                            ) : null}
                        </View>
                        {photoError ? <Text style={styles.error}>{photoError}</Text> : null}
                    </View>
                </View>
            </Card>

            <SectionTitle title="Personal details" />
            <Card style={{ gap: 16 }}>
                <TextField
                    label="Full name"
                    value={form.fullName}
                    onChangeText={set('fullName')}
                    error={err('fullName')}
                    placeholder="e.g. Ritesh Bisht"
                    autoCapitalize="words"
                    autoComplete="name"
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
                <ChipGroup
                    label="Gender (optional)"
                    options={GENDER_OPTIONS}
                    value={form.gender}
                    onChange={v => set('gender')(form.gender === v ? null : v)}
                />
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
            </Card>

            <FormError message={formError} />
            {saved ? (
                <View style={styles.savedBox} accessibilityLiveRegion="polite">
                    <Text style={styles.savedText}>Profile saved</Text>
                </View>
            ) : null}
            <PrimaryButton title="Save changes" onPress={onSave} loading={saving} disabled={uploading} />

            {session?.email || session?.phone ? (
                <>
                    <SectionTitle title="Account" />
                    <Card style={{ gap: 10 }}>
                        {session.email ? <InfoRow label="Email" value={session.email} /> : null}
                        {session.phone ? <InfoRow label="Phone" value={session.phone} /> : null}
                        <Text style={styles.hint}>Login details can't be changed here yet.</Text>
                    </Card>
                </>
            ) : null}
        </Screen>
    );
}

const InfoRow = ({ label, value }: { label: string; value: string }) => (
    <View style={styles.infoRow}>
        <Text style={styles.infoLabel}>{label}</Text>
        <Text style={styles.infoValue} numberOfLines={1}>{value}</Text>
    </View>
);

const styles = StyleSheet.create({
    photoRow: { flexDirection: 'row', alignItems: 'center', gap: 16 },
    avatar: {
        width: 80, height: 80, borderRadius: 40, backgroundColor: theme.primary,
        alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
    },
    avatarImg: { width: 80, height: 80 },
    avatarText: { color: '#FFFFFF', fontSize: 28, fontWeight: '700' },
    avatarOverlay: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,0,0.35)', alignItems: 'center', justifyContent: 'center' },
    name: { fontSize: 18, fontWeight: '800', color: theme.text },
    hint: { fontSize: 13, color: theme.muted },
    photoActions: { flexDirection: 'row', gap: 16, marginTop: 2 },
    link: { fontSize: 14, fontWeight: '700', color: theme.primary },
    error: { fontSize: 13, color: theme.error },
    counter: { fontSize: 12, color: theme.muted, textAlign: 'right', marginTop: 4 },
    savedBox: { backgroundColor: theme.successBg, borderRadius: 12, paddingVertical: 10, alignItems: 'center' },
    savedText: { color: theme.success, fontWeight: '700', fontSize: 14 },
    infoRow: { flexDirection: 'row', justifyContent: 'space-between', gap: 12 },
    infoLabel: { fontSize: 14, color: theme.muted },
    infoValue: { fontSize: 14, fontWeight: '600', color: theme.text, flexShrink: 1 },
});
