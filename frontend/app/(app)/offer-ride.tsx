import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { DeparturePicker, validateDeparture } from '../../components/DeparturePicker';
import { PrimaryButton } from '../../components/PrimaryButton';
import { StationPicker } from '../../components/StationPicker';
import { TextField } from '../../components/TextField';
import { Card, ChipGroup, FormError, Screen, SecondaryButton, Stepper, TextLink } from '../../components/ui';
import { Colors } from '../../constants/Colors';
import { CURRENCY, formatPrice } from '../../constants/Currency';
import { ApiError } from '../../services/api';
import { CAR_POLICIES, CarPolicyId, DEFAULT_POLICIES, buildNotes } from '../../services/carPolicy';
import { departureLabel } from '../../services/format';
import { OfferError, OfferField, Ride, offerRide } from '../../services/rides';
import { clearSession } from '../../services/session';
import { Station } from '../../services/stations';
import { MAX_SEATS, VehicleListNotReady, fetchMyVehicles, useVehicles, vehicleLabel } from '../../services/vehicles';

const theme = Colors.light;
const MAX_PRICE = 10000;
const MAX_NOTE = 300; // leaves room for the car-policy line inside the API's 500-char notes

type Errors = Partial<Record<OfferField, string>>;

function validatePrice(value: string): string | undefined {
    if (!value.trim()) return 'Enter a rate per seat (0 for free)';
    if (!/^\d+(\.\d{1,2})?$/.test(value.trim())) return 'Use numbers only, up to 2 decimals';
    if (Number(value) > MAX_PRICE) return `Keep it under ${CURRENCY}${MAX_PRICE}`;
}

export default function OfferRideScreen() {
    const router = useRouter();
    const vehicles = useVehicles();
    const [vehiclesState, setVehiclesState] = useState<'loading' | 'ready' | 'fallback' | 'error'>('loading');
    const [vehiclesError, setVehiclesError] = useState<string | null>(null);

    const [vehicleId, setVehicleId] = useState<string | null>(null);
    const [source, setSource] = useState<Station | null>(null);
    const [destination, setDestination] = useState<Station | null>(null);
    const [dayIndex, setDayIndex] = useState(0);
    const [time, setTime] = useState('');
    const [seats, setSeats] = useState(1);
    const [price, setPrice] = useState('');
    const [policies, setPolicies] = useState<CarPolicyId[]>(DEFAULT_POLICIES);
    const [note, setNote] = useState('');

    const [submitted, setSubmitted] = useState(false);
    const [serverErrors, setServerErrors] = useState<Errors>({});
    const [formError, setFormError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [created, setCreated] = useState<Ride | null>(null);

    const sessionExpired = useCallback(() => {
        clearSession();
        router.replace('/login');
    }, [router]);

    const loadVehicles = useCallback(async () => {
        setVehiclesState('loading');
        setVehiclesError(null);
        try {
            await fetchMyVehicles();
            setVehiclesState('ready');
        } catch (e) {
            if (e instanceof VehicleListNotReady) return setVehiclesState('fallback');
            if (e instanceof ApiError && e.status === 401) return sessionExpired();
            setVehiclesError(e instanceof Error ? e.message : 'Could not load your vehicles');
            setVehiclesState('error');
        }
    }, [sessionExpired]);

    useEffect(() => { loadVehicles(); }, [loadVehicles]);

    // Pre-select the default vehicle once the list arrives.
    useEffect(() => {
        if (!vehicleId && vehicles.length) setVehicleId((vehicles.find(v => v.isDefault) ?? vehicles[0]).id);
    }, [vehicles, vehicleId]);

    const vehicle = vehicles.find(v => v.id === vehicleId);
    const maxSeats = vehicle?.seatCapacity ?? MAX_SEATS;

    const local: Errors = submitted
        ? {
            vehicle: vehicle ? undefined : 'Choose a vehicle',
            source: source ? undefined : 'Choose a pickup station',
            destination: !destination
                ? 'Choose a drop-off station'
                : source && destination.id === source.id ? 'Drop-off must be different from pickup' : undefined,
            departure: validateDeparture(dayIndex, time).error,
            price: validatePrice(price),
        }
        : {};
    const err = (f: OfferField) => local[f] ?? serverErrors[f];
    const clear = (f: OfferField) => setServerErrors(prev => ({ ...prev, [f]: undefined }));

    const onSubmit = async () => {
        setSubmitted(true);
        setFormError(null);
        setServerErrors({});
        const d = validateDeparture(dayIndex, time);
        const missing = [
            !source && 'source',
            (!destination || (source && destination.id === source.id)) && 'destination',
            !d.date && 'departure time',
            !vehicle && 'vehicle',
            validatePrice(price) && 'rate',
        ].filter(Boolean);
        if (missing.length || !vehicle || !source || !destination || !d.date) {
            // Errors are shown on each field; this line by the button says why nothing was sent.
            setFormError(`Please check: ${missing.join(', ')}.`);
            return;
        }

        setSaving(true);
        try {
            const ride = await offerRide({
                vehicleId: vehicle.id,
                source,
                destination,
                departAt: d.date,
                seats: Math.min(seats, maxSeats),
                pricePerSeat: Number(price),
                notes: buildNotes(policies, note),
            });
            setCreated(ride);
        } catch (e) {
            if (e instanceof OfferError && e.sessionExpired) return sessionExpired();
            if (e instanceof OfferError && e.field) setServerErrors({ [e.field]: e.message });
            else setFormError(e instanceof Error ? e.message : 'Something went wrong. Please try again.');
        } finally {
            setSaving(false);
        }
    };

    const reset = () => {
        setCreated(null); setSubmitted(false); setSource(null); setDestination(null);
        setTime(''); setSeats(1); setPrice(''); setNote(''); setPolicies(DEFAULT_POLICIES);
    };

    // --- Success ----------------------------------------------------------------------------
    if (created) {
        return (
            <Screen title="Ride offered" subtitle="Riders going your way can now book a seat.">
                <Card style={styles.summary}>
                    <Text style={styles.summaryRoute}>{created.from} → {created.to}</Text>
                    <Text style={styles.meta}>{departureLabel(created.departAt)}</Text>
                    <Text style={styles.meta}>
                        {created.seats} seat{created.seats === 1 ? '' : 's'} · {created.pricePerSeat ? `${formatPrice(created.pricePerSeat)} per seat` : 'Free'}
                    </Text>
                    {vehicle ? <Text style={styles.meta}>{vehicleLabel(vehicle)} · {vehicle.registrationNumber}</Text> : null}
                    {created.note ? <Text style={styles.noteText}>{created.note}</Text> : null}
                </Card>
                <PrimaryButton title="Back to dashboard" onPress={() => router.replace('/dashboard')} />
                <SecondaryButton title="Offer another ride" onPress={reset} />
            </Screen>
        );
    }

    // --- Form ------------------------------------------------------------------------------------
    return (
        <Screen title="Offer a ride" subtitle="Share your empty seats with people going your way.">
            <StationPicker
                label="Source"
                placeholder="Search pickup station"
                value={source}
                onChange={s => { setSource(s); clear('source'); }}
                excludeId={destination?.id}
                error={err('source')}
                onSessionExpired={sessionExpired}
            />
            <StationPicker
                label="Destination"
                placeholder="Search drop-off station"
                value={destination}
                onChange={s => { setDestination(s); clear('destination'); }}
                excludeId={source?.id}
                error={err('destination')}
                onSessionExpired={sessionExpired}
            />

            <DeparturePicker
                dayIndex={dayIndex}
                onDayChange={i => { setDayIndex(i); clear('departure'); }}
                time={time}
                onTimeChange={t => { setTime(t); clear('departure'); }}
                timeError={err('departure')}
            />

            <View style={{ gap: 8 }}>
                {vehiclesState === 'loading' && !vehicles.length ? (
                    <>
                        <Text style={styles.label}>Vehicle</Text>
                        <View style={styles.inlineStatus} accessibilityLiveRegion="polite">
                            <ActivityIndicator color={theme.primary} size="small" />
                            <Text style={styles.hint}>Loading your vehicles…</Text>
                        </View>
                    </>
                ) : vehiclesState === 'error' && !vehicles.length ? (
                    <>
                        <Text style={styles.label}>Vehicle</Text>
                        <View style={[styles.inlineBox, { borderColor: theme.error }]}>
                            <Text style={[styles.hint, { color: theme.error, flex: 1 }]}>{vehiclesError ?? 'Could not load your vehicles'}</Text>
                            <TextLink label="Try again" onPress={loadVehicles} />
                        </View>
                    </>
                ) : !vehicles.length ? (
                    <>
                        <Text style={styles.label}>Vehicle</Text>
                        <View style={[styles.inlineBox, { borderColor: err('vehicle') ? theme.error : theme.border }]}>
                            <Text style={[styles.hint, { flex: 1 }]}>You haven’t added a vehicle yet.</Text>
                            <TextLink label="+ Add a vehicle" onPress={() => router.push('/vehicles/add')} />
                        </View>
                        {err('vehicle') ? <Text style={styles.errorText}>{err('vehicle')}</Text> : null}
                    </>
                ) : (
                    <ChipGroup
                        label="Vehicle"
                        value={vehicleId}
                        error={err('vehicle')}
                        onChange={id => {
                            setVehicleId(id);
                            clear('vehicle');
                            const v = vehicles.find(x => x.id === id);
                            if (v) setSeats(s => Math.min(s, v.seatCapacity));
                        }}
                        options={vehicles.map(v => ({ value: v.id, label: `${vehicleLabel(v)} · ${v.registrationNumber}` }))}
                    />
                )}
                {vehiclesState === 'fallback' && vehicles.length ? (
                    <Text style={styles.hint}>Showing vehicles added on this device — the full list will load once the vehicles API is live.</Text>
                ) : null}
            </View>

            <Stepper
                label="Seats to offer"
                value={Math.min(seats, maxSeats)}
                min={1}
                max={maxSeats}
                onChange={n => { setSeats(n); clear('seats'); }}
                hint={err('seats') ?? (vehicle ? `${vehicleLabel(vehicle)} has ${vehicle.seatCapacity} passenger seat${vehicle.seatCapacity === 1 ? '' : 's'}` : 'Limited to your vehicle’s seats once you pick one')}
            />

            <TextField
                label={`Rate per seat (${CURRENCY})`}
                placeholder="e.g. 80"
                value={price}
                onChangeText={v => { setPrice(v); clear('price'); }}
                error={err('price')}
                hint="Enter 0 to offer the ride for free"
                keyboardType="decimal-pad"
                maxLength={8}
            />

            <View style={{ gap: 8 }}>
                <Text style={styles.label}>Car policy</Text>
                <Text style={styles.hint}>Let riders know your rules. Pick all that apply.</Text>
                <View style={styles.chips}>
                    {CAR_POLICIES.map(p => {
                        const on = policies.includes(p.id);
                        return (
                            <Pressable
                                key={p.id}
                                onPress={() => setPolicies(list => (on ? list.filter(x => x !== p.id) : [...list, p.id]))}
                                accessibilityRole="checkbox"
                                accessibilityState={{ checked: on }}
                                style={[styles.chip, on && { backgroundColor: theme.primary, borderColor: theme.primary }]}
                            >
                                <Text style={[styles.chipText, { color: on ? '#FFFFFF' : theme.text }]}>{on ? '✓ ' : ''}{p.label}</Text>
                            </Pressable>
                        );
                    })}
                </View>
            </View>

            <TextField
                label="Anything else? (optional)"
                placeholder="e.g. Pickup from the main gate"
                value={note}
                onChangeText={v => { setNote(v); clear('notes'); }}
                error={err('notes')}
                hint={`${note.length}/${MAX_NOTE}`}
                maxLength={MAX_NOTE}
                multiline
                style={{ minHeight: 72, textAlignVertical: 'top' }}
                autoCapitalize="sentences"
            />

            <FormError message={formError} />
            <PrimaryButton title="Offer ride" onPress={onSubmit} loading={saving} />
        </Screen>
    );
}

const styles = StyleSheet.create({
    label: { fontSize: 14, fontWeight: '600', color: theme.text },
    hint: { fontSize: 13, color: theme.muted },
    inlineStatus: { flexDirection: 'row', alignItems: 'center', gap: 10, minHeight: 48 },
    inlineBox: {
        flexDirection: 'row', alignItems: 'center', gap: 12, minHeight: 52, borderWidth: 1.5, borderStyle: 'dashed',
        borderRadius: 12, paddingHorizontal: 14, backgroundColor: theme.card,
    },
    errorText: { fontSize: 13, color: theme.error },
    chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
    chip: { minHeight: 40, borderWidth: 1.5, borderColor: theme.border, borderRadius: 999, paddingHorizontal: 14, justifyContent: 'center', backgroundColor: theme.card },
    chipText: { fontSize: 14, fontWeight: '600' },
    summary: { gap: 6 },
    summaryRoute: { fontSize: 18, fontWeight: '800', color: theme.text },
    meta: { fontSize: 14, color: theme.muted },
    noteText: { fontSize: 14, color: theme.text, marginTop: 4 },
});
