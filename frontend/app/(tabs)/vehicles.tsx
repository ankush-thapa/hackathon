import React, { useState } from 'react';
import { Image, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Colors } from '../../constants/Colors';
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

                    <Text style={[styles.label, { color: theme.text }]}>Car name</Text>
                    <TextInput
                        value={name}
                        onChangeText={v => { setName(v); setErrors(p => ({ ...p, name: undefined })); }}
                        placeholder="e.g. Maruti Swift"
                        placeholderTextColor={theme.muted}
                        maxLength={40}
                        style={[styles.input, { color: theme.text, borderColor: errors.name ? theme.error : theme.border }]}
                    />
                    {errors.name && <Text style={[styles.error, { color: theme.error }]}>{errors.name}</Text>}

                    <Text style={[styles.label, { color: theme.text }]}>Vehicle number</Text>
                    <TextInput
                        value={number}
                        onChangeText={v => { setNumber(normalizeNumber(v)); setErrors(p => ({ ...p, number: undefined })); }}
                        placeholder="e.g. MH 12 AB 1234"
                        placeholderTextColor={theme.muted}
                        autoCapitalize="characters"
                        autoCorrect={false}
                        maxLength={16}
                        style={[
                            styles.input,
                            { color: theme.text, borderColor: errors.number ? theme.error : theme.border },
                        ]}
                    />
                    {errors.number && <Text style={[styles.error, { color: theme.error }]}>{errors.number}</Text>}

                    <Text style={[styles.label, { color: theme.text }]}>Colour</Text>
                    <TextInput
                        value={color}
                        onChangeText={v => { setColor(v); setErrors(p => ({ ...p, color: undefined })); }}
                        placeholder="e.g. Pearl White"
                        placeholderTextColor={theme.muted}
                        maxLength={30}
                        style={[styles.input, { color: theme.text, borderColor: errors.color ? theme.error : theme.border }]}
                    />
                    {errors.color && <Text style={[styles.error, { color: theme.error }]}>{errors.color}</Text>}

                    <Pressable
                        onPress={addVehicle}
                        style={({ pressed }) => [styles.addBtn, { backgroundColor: theme.primary }, pressed && styles.pressed]}
                    >
                        <Text style={styles.addBtnText}>Add vehicle</Text>
                    </Pressable>
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
    },
    subtitle: {
        fontSize: 15,
        marginBottom: 8,
    },
    form: {
        borderWidth: 1,
        borderRadius: 12,
        padding: 16,
        gap: 8,
    },
    label: {
        fontSize: 15,
        fontWeight: '600',
        marginTop: 6,
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
    input: {
        borderWidth: 1,
        borderRadius: 10,
        paddingHorizontal: 12,
        paddingVertical: 10,
        fontSize: 16,
        letterSpacing: 0.5,
    },
    error: {
        fontSize: 13,
    },
    addBtn: {
        marginTop: 12,
        paddingVertical: 12,
        borderRadius: 24,
        alignItems: 'center',
    },
    addBtnText: {
        color: '#FFFFFF',
        fontSize: 16,
        fontWeight: '700',
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
