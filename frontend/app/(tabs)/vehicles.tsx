import React, { useState } from 'react';
import { Image, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Colors } from '../../constants/Colors';
import { PrimaryButton } from '../../components/PrimaryButton';
import { TextField } from '../../components/TextField';
import { VehicleCard } from '../../components/VehicleCard';
import { Vehicle, compactRegistration, isValidRegistration } from '../../types/vehicle';

type Errors = Partial<Record<'name' | 'number' | 'color' | 'photo', string>>;

const normalizeNumber = (value: string) => value.toUpperCase().replace(/\s+/g, ' ').trimStart();

export default function VehiclesScreen() {
    const theme = Colors.light;

    // Frontend only: vehicles live in memory until a backend endpoint exists.
    const [vehicles, setVehicles] = useState<Vehicle[]>([]);
    const [name, setName] = useState('');
    const [number, setNumber] = useState('');
    const [color, setColor] = useState('');
    const [photoUri, setPhotoUri] = useState<string | null>(null);
    const [errors, setErrors] = useState<Errors>({});

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
        if (!result.canceled && result.assets[0]) {
            setPhotoUri(result.assets[0].uri);
            setErrors(prev => ({ ...prev, photo: undefined }));
        }
    };

    const validate = (): Errors => {
        const next: Errors = {};
        if (!name.trim()) next.name = 'Enter the car name.';
        const cleaned = number.trim();
        if (!cleaned) next.number = 'Enter the vehicle number.';
        else if (!isValidRegistration(cleaned)) next.number = 'Enter a valid registration number, e.g. MH 12 AB 1234 or 22 BH 1234 AA.';
        else if (vehicles.some(v => compactRegistration(v.number) === compactRegistration(cleaned)))
            next.number = 'This vehicle is already added.';
        if (!color.trim()) next.color = 'Enter the colour.';
        if (!photoUri) next.photo = 'Add a photo of the vehicle.';
        return next;
    };

    const addVehicle = () => {
        const next = validate();
        setErrors(next);
        if (Object.keys(next).length > 0 || !photoUri) return;

        setVehicles(prev => [
            ...prev,
            {
                id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
                name: name.trim(),
                number: number.trim(),
                color: color.trim(),
                photoUri,
            },
        ]);
        setName('');
        setNumber('');
        setColor('');
        setPhotoUri(null);
    };

    const deleteVehicle = (id: string) => setVehicles(prev => prev.filter(v => v.id !== id));

    return (
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
            <View style={styles.main}>
                <Text style={[styles.title, { color: theme.text }]}>My vehicles</Text>
                <Text style={[styles.subtitle, { color: theme.muted }]}>Add the vehicles you'll offer rides in.</Text>

                {/* Add form */}
                <View style={[styles.form, { backgroundColor: theme.card, borderColor: theme.border }]}>
                    <View style={styles.photoGroup}>
                        <Text style={[styles.label, { color: theme.text }]}>Photo</Text>
                        <Pressable
                            onPress={pickPhoto}
                            accessibilityLabel="Choose vehicle photo"
                            style={({ pressed }) => [
                                styles.photoBox,
                                { borderColor: errors.photo ? theme.error : theme.border },
                                pressed && styles.pressed,
                            ]}
                        >
                            {photoUri ? (
                                <Image source={{ uri: photoUri }} style={styles.photoPreview} />
                            ) : (
                                <View style={styles.photoEmpty}>
                                    <Text style={[styles.photoPlus, { color: theme.primary }]}>+</Text>
                                    <Text style={{ color: theme.muted }}>Tap to choose a photo</Text>
                                </View>
                            )}
                        </Pressable>
                        {photoUri && (
                            <Pressable onPress={pickPhoto}>
                                <Text style={[styles.link, { color: theme.primary }]}>Change photo</Text>
                            </Pressable>
                        )}
                        {errors.photo && <Text style={[styles.error, { color: theme.error }]}>{errors.photo}</Text>}
                    </View>

                    <TextField
                        label="Car name"
                        value={name}
                        onChangeText={v => { setName(v); setErrors(p => ({ ...p, name: undefined })); }}
                        placeholder="e.g. Maruti Swift"
                        autoCapitalize="words"
                        maxLength={40}
                        error={errors.name}
                    />

                    <TextField
                        label="Vehicle number"
                        value={number}
                        onChangeText={v => { setNumber(normalizeNumber(v)); setErrors(p => ({ ...p, number: undefined })); }}
                        placeholder="e.g. MH 12 AB 1234"
                        autoCapitalize="characters"
                        maxLength={16}
                        style={styles.plate}
                        error={errors.number}
                    />

                    <TextField
                        label="Colour"
                        value={color}
                        onChangeText={v => { setColor(v); setErrors(p => ({ ...p, color: undefined })); }}
                        placeholder="e.g. Pearl White"
                        autoCapitalize="words"
                        maxLength={30}
                        error={errors.color}
                    />

                    <View style={styles.submit}>
                        <PrimaryButton title="Add vehicle" onPress={addVehicle} />
                    </View>
                </View>

                {/* List */}
                <Text style={[styles.sectionTitle, { color: theme.text }]}>
                    Added vehicles {vehicles.length > 0 ? `(${vehicles.length})` : ''}
                </Text>
                {vehicles.length === 0 ? (
                    <Text style={{ color: theme.muted }}>No vehicles yet. Add one above.</Text>
                ) : (
                    vehicles.map(v => <VehicleCard key={v.id} vehicle={v} onDelete={deleteVehicle} />)
                )}
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    scroll: {
        flexGrow: 1,
        paddingBottom: 32,
    },
    main: {
        width: '100%',
        maxWidth: 600,
        alignSelf: 'center',
        paddingHorizontal: 24,
        paddingTop: 32,
        gap: 12,
    },
    title: {
        fontSize: 28,
        fontWeight: '800',
        letterSpacing: -0.5,
    },
    subtitle: {
        fontSize: 15,
        marginBottom: 8,
    },
    form: {
        borderWidth: 1,
        borderRadius: 16,
        padding: 20,
        gap: 18,
    },
    photoGroup: {
        gap: 6,
    },
    label: {
        fontSize: 14,
        fontWeight: '600',
    },
    photoBox: {
        height: 180,
        borderWidth: 1.5,
        borderStyle: 'dashed',
        borderRadius: 12,
        overflow: 'hidden',
        alignItems: 'center',
        justifyContent: 'center',
    },
    photoEmpty: {
        alignItems: 'center',
        gap: 4,
    },
    photoPlus: {
        fontSize: 36,
        fontWeight: '300',
    },
    photoPreview: {
        width: '100%',
        height: '100%',
    },
    link: {
        fontSize: 14,
        fontWeight: '600',
    },
    plate: {
        letterSpacing: 1,
        fontWeight: '600',
    },
    error: {
        fontSize: 13,
    },
    submit: {
        marginTop: 6,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: '700',
        marginTop: 16,
    },
    pressed: {
        opacity: 0.75,
    },
});
