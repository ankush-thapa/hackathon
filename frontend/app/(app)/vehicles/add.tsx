import React, { useState } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Link, useRouter } from 'expo-router';
import { Colors } from '../../../constants/Colors';
import { PrimaryButton } from '../../../components/PrimaryButton';
import { TextField } from '../../../components/TextField';
import { Card, FormError, Screen, Stepper } from '../../../components/ui';
import {
    DEFAULT_SEATS,
    MAX_COLOUR_LENGTH,
    MAX_MAKE_LENGTH,
    MAX_MODEL_LENGTH,
    MAX_SEATS,
    MIN_SEATS,
    VehicleError,
    VehicleField,
    addVehicle,
    getVehicles,
    isValidRegistration,
    normalizeRegistration,
    vehicleLabel,
} from '../../../services/vehicles';

type Errors = Partial<Record<VehicleField, string>>;
type Photo = { uri: string; mimeType?: string };

// Upper-case as you type and collapse repeated spaces; spaces/hyphens are stripped before sending.
const formatRegistration = (value: string) => value.toUpperCase().replace(/\s+/g, ' ').trimStart();

export default function AddVehicleScreen() {
    const theme = Colors.light;
    const router = useRouter();

    const [photo, setPhoto] = useState<Photo | null>(null);
    const [make, setMake] = useState('');
    const [model, setModel] = useState('');
    const [registration, setRegistration] = useState('');
    const [colour, setColour] = useState('');
    const [seats, setSeats] = useState(DEFAULT_SEATS);
    const [errors, setErrors] = useState<Errors>({});
    const [formError, setFormError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [justAdded, setJustAdded] = useState<string | null>(null);

    const clearError = (field: VehicleField) => {
        setJustAdded(null);
        setErrors(prev => ({ ...prev, [field]: undefined }));
    };

    const pickPhoto = async () => {
        const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!permission.granted) {
            setErrors(prev => ({ ...prev, photo: 'Photo library permission is needed to add a photo.' }));
            return;
        }
        const result = await ImagePicker.launchImageLibraryAsync({
            mediaTypes: ['images'],
            allowsEditing: true,
            aspect: [4, 3],
            quality: 0.7,
        });
        const asset = result.canceled ? undefined : result.assets[0];
        if (asset) {
            setPhoto({ uri: asset.uri, mimeType: asset.mimeType ?? undefined });
            clearError('photo');
        }
    };

    const validate = (): Errors => {
        const next: Errors = {};
        if (!photo) next.photo = 'Add a photo of the vehicle.';
        if (!make.trim()) next.make = 'Enter the car make, e.g. Maruti Suzuki.';
        if (!model.trim()) next.model = 'Enter the car model, e.g. Swift.';
        if (!registration.trim()) next.registrationNumber = 'Enter the registration number.';
        else if (!isValidRegistration(registration))
            next.registrationNumber = 'Enter a valid registration number, e.g. MH 12 AB 1234 or 22 BH 1234 AA.';
        else if (getVehicles().some(v => v.registrationNumber === normalizeRegistration(registration)))
            next.registrationNumber = 'You have already added this vehicle.';
        if (!colour.trim()) next.colour = 'Enter the colour.';
        return next;
    };

    const onSubmit = async () => {
        setFormError(null);
        setJustAdded(null);
        const next = validate();
        setErrors(next);
        if (Object.keys(next).length > 0 || !photo) return;

        setSaving(true);
        try {
            const vehicle = await addVehicle({ photo, make, model, registrationNumber: registration, colour, seatCapacity: seats });
            setJustAdded(vehicleLabel(vehicle));
            setPhoto(null);
            setMake('');
            setModel('');
            setRegistration('');
            setColour('');
            setSeats(DEFAULT_SEATS);
        } catch (e) {
            if (e instanceof VehicleError) {
                if (e.sessionExpired) {
                    router.replace('/login');
                    return;
                }
                if (e.field) setErrors(prev => ({ ...prev, [e.field!]: e.message }));
                else setFormError(e.message);
            } else {
                setFormError('Something went wrong. Please try again.');
            }
        } finally {
            setSaving(false);
        }
    };

    return (
        <Screen title="Add a vehicle" subtitle="Add each vehicle you'll offer rides in. You can add as many as you like.">
            {justAdded && (
                <View style={[styles.success, { backgroundColor: theme.successBg }]}>
                    <Text style={[styles.successText, { color: theme.success }]}>
                        {justAdded} added. Add another, or{' '}
                        <Link href="/vehicles" style={[styles.link, { color: theme.primary }]}>view my vehicles</Link>.
                    </Text>
                </View>
            )}

            <Card style={styles.form}>
                <View style={styles.group}>
                    <Text style={[styles.label, { color: theme.text }]}>Photo</Text>
                    <Pressable
                        onPress={pickPhoto}
                        disabled={saving}
                        accessibilityRole="button"
                        accessibilityLabel={photo ? 'Change vehicle photo' : 'Choose vehicle photo'}
                        style={({ pressed }) => [
                            styles.photoBox,
                            { borderColor: errors.photo ? theme.error : theme.border },
                            pressed && styles.pressed,
                        ]}
                    >
                        {photo ? (
                            <Image source={{ uri: photo.uri }} style={styles.photoPreview} />
                        ) : (
                            <View style={styles.photoEmpty}>
                                <Text style={[styles.photoPlus, { color: theme.primary }]}>+</Text>
                                <Text style={{ color: theme.muted }}>Tap to choose a photo</Text>
                                <Text style={[styles.hint, { color: theme.muted }]}>JPEG, PNG or WebP, up to 5 MB</Text>
                            </View>
                        )}
                    </Pressable>
                    {photo && !saving && (
                        <Pressable onPress={pickPhoto} accessibilityRole="button">
                            <Text style={[styles.link, { color: theme.primary }]}>Change photo</Text>
                        </Pressable>
                    )}
                    {errors.photo && <Text style={[styles.error, { color: theme.error }]}>{errors.photo}</Text>}
                </View>

                <View style={styles.row}>
                    <View style={styles.half}>
                        <TextField
                            label="Make"
                            value={make}
                            onChangeText={v => { setMake(v); clearError('make'); }}
                            placeholder="e.g. Maruti Suzuki"
                            autoCapitalize="words"
                            maxLength={MAX_MAKE_LENGTH}
                            error={errors.make}
                        />
                    </View>
                    <View style={styles.half}>
                        <TextField
                            label="Model"
                            value={model}
                            onChangeText={v => { setModel(v); clearError('model'); }}
                            placeholder="e.g. Swift"
                            autoCapitalize="words"
                            maxLength={MAX_MODEL_LENGTH}
                            error={errors.model}
                        />
                    </View>
                </View>

                <TextField
                    label="Registration number"
                    value={registration}
                    onChangeText={v => { setRegistration(formatRegistration(v)); clearError('registrationNumber'); }}
                    placeholder="e.g. MH 12 AB 1234"
                    autoCapitalize="characters"
                    maxLength={16}
                    style={styles.plate}
                    error={errors.registrationNumber}
                />

                <TextField
                    label="Colour"
                    value={colour}
                    onChangeText={v => { setColour(v); clearError('colour'); }}
                    placeholder="e.g. Pearl White"
                    autoCapitalize="words"
                    maxLength={MAX_COLOUR_LENGTH}
                    error={errors.colour}
                />

                <Stepper
                    label="Seat capacity"
                    value={seats}
                    min={MIN_SEATS}
                    max={MAX_SEATS}
                    onChange={n => { setSeats(n); clearError('seatCapacity'); }}
                    hint={errors.seatCapacity ?? `Seats available for passengers, ${MIN_SEATS}–${MAX_SEATS}.`}
                />

                <FormError message={formError} />
                <PrimaryButton title={saving ? 'Adding…' : 'Add vehicle'} onPress={onSubmit} loading={saving} />
            </Card>
        </Screen>
    );
}

const styles = StyleSheet.create({
    form: { padding: 20, gap: 18 },
    group: { gap: 6 },
    row: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
    half: { flexGrow: 1, flexBasis: 200 },
    label: { fontSize: 14, fontWeight: '600' },
    photoBox: {
        height: 180,
        borderWidth: 1.5,
        borderStyle: 'dashed',
        borderRadius: 12,
        overflow: 'hidden',
        alignItems: 'center',
        justifyContent: 'center',
    },
    photoEmpty: { alignItems: 'center', gap: 4 },
    photoPlus: { fontSize: 36, fontWeight: '300' },
    photoPreview: { width: '100%', height: '100%' },
    hint: { fontSize: 12 },
    link: { fontSize: 14, fontWeight: '700' },
    plate: { letterSpacing: 1, fontWeight: '600' },
    error: { fontSize: 13 },
    success: { borderRadius: 12, padding: 14 },
    successText: { fontSize: 15, fontWeight: '600' },
    pressed: { opacity: 0.75 },
});
