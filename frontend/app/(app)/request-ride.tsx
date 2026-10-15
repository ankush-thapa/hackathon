import React, { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { PrimaryButton } from '../../components/PrimaryButton';
import { TextField } from '../../components/TextField';
import { Badge, Card, EmptyState, FormError, Screen, SecondaryButton, SectionTitle, Stepper, TextLink } from '../../components/ui';
import { Colors } from '../../constants/Colors';
import { dayLabel, nextDays, timeLabel } from '../../services/format';
import { useProfile } from '../../services/profile';
import { CURRENCY } from '../../constants/Currency';
import {
    DaySearch,
    RideSearchError,
    SearchParams,
    SearchRide,
    Station,
    bookRide,
    fetchStations,
    hasMore,
    searchMore,
    searchRides,
} from '../../services/rideSearch';
import { notifyDriverOfRequest } from '../../services/rideRequests';
import { getSession } from '../../services/session';

const theme = Colors.light;
const DAYS = nextDays(7);

const money = (v: string | number) => {
    const n = Number(v);
    return Number.isInteger(n) ? String(n) : n.toFixed(2);
};

/** Find an offered ride between two stations on a day, then request seats on it. */
export default function RequestRideScreen() {
    const router = useRouter();
    const [stations, setStations] = useState<Station[] | null>(null);
    const [stationsError, setStationsError] = useState<string | null>(null);

    const [from, setFrom] = useState<Station | null>(null);
    const [to, setTo] = useState<Station | null>(null);
    const [day, setDay] = useState<Date>(DAYS[0]);
    const [seats, setSeats] = useState(1);
    const [formError, setFormError] = useState<string | null>(null);

    // The search that produced the current results (so editing the form doesn't change what Book uses).
    const [query, setQuery] = useState<{ params: SearchParams; day: Date; from: Station; to: Station } | null>(null);
    const [results, setResults] = useState<DaySearch | null>(null);
    const [searching, setSearching] = useState(false);
    const [loadingMore, setLoadingMore] = useState(false);
    const [searchError, setSearchError] = useState<string | null>(null);

    const handleAuth = (e: unknown) => {
        if (e instanceof RideSearchError && e.status === 401) router.replace('/login');
    };

    const loadStations = async () => {
        setStationsError(null);
        try {
            setStations(await fetchStations());
        } catch (e) {
            handleAuth(e);
            setStationsError(e instanceof RideSearchError ? e.message : 'Could not load stations.');
        }
    };
    useEffect(() => { loadStations(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const swap = () => { setFrom(to); setTo(from); };

    const onSearch = async () => {
        setFormError(null);
        if (!from || !to) return setFormError('Choose where you’re leaving from and going to');
        if (from.id_station === to.id_station) return setFormError('Pick two different stations');
        const q = { params: { from: from.id_station, to: to.id_station, seats }, day, from, to };
        setQuery(q);
        setSearching(true);
        setSearchError(null);
        setResults(null);
        try {
            setResults(await searchRides(q.params, q.day));
        } catch (e) {
            handleAuth(e);
            setSearchError(e instanceof RideSearchError ? e.message : 'Search failed. Please try again.');
        } finally {
            setSearching(false);
        }
    };

    const onLoadMore = async () => {
        if (!query || !results) return;
        setLoadingMore(true);
        try {
            setResults(await searchMore(query.params, query.day, results));
        } catch (e) {
            handleAuth(e);
            setSearchError(e instanceof RideSearchError ? e.message : 'Could not load more rides.');
        } finally {
            setLoadingMore(false);
        }
    };

    if (!stations) {
        return (
            <Screen title="Request a ride" subtitle="Find a colleague going your way.">
                <View style={styles.center}>
                    {stationsError ? (
                        <>
                            <Text style={styles.error}>{stationsError}</Text>
                            <SecondaryButton title="Try again" onPress={loadStations} />
                        </>
                    ) : (
                        <ActivityIndicator color={theme.primary} />
                    )}
                </View>
            </Screen>
        );
    }

    return (
        <Screen title="Request a ride" subtitle="Find a colleague going your way.">
            <Card style={{ gap: 16 }}>
                <View style={{ gap: 10 }}>
                    <StationPicker label="From" value={from} onChange={setFrom} stations={stations} exclude={to} />
                    <Pressable onPress={swap} accessibilityRole="button" accessibilityLabel="Swap from and to" hitSlop={8} style={styles.swap}>
                        <Text style={styles.swapText}>⇅ Swap</Text>
                    </Pressable>
                    <StationPicker label="To" value={to} onChange={setTo} stations={stations} exclude={from} />
                </View>

                <View style={{ gap: 8 }}>
                    <Text style={styles.label}>Day</Text>
                    <View style={styles.chips} accessibilityRole="radiogroup" accessibilityLabel="Day">
                        {DAYS.map(d => {
                            const selected = d.getTime() === day.getTime();
                            return (
                                <Pressable
                                    key={d.toISOString()}
                                    onPress={() => setDay(d)}
                                    accessibilityRole="radio"
                                    accessibilityState={{ selected }}
                                    style={[styles.chip, selected && styles.chipActive]}
                                >
                                    <Text style={[styles.chipText, selected && { color: '#FFFFFF' }]}>{dayLabel(d)}</Text>
                                </Pressable>
                            );
                        })}
                    </View>
                </View>

                <Stepper label="Seats" value={seats} min={1} max={8} onChange={setSeats} />

                <FormError message={formError} />
                <PrimaryButton title="Search rides" onPress={onSearch} loading={searching} />
            </Card>

            {query && !searching ? (
                <>
                    <SectionTitle title={`${query.from.station_name} → ${query.to.station_name}`} />
                    <Text style={styles.meta}>
                        {dayLabel(query.day)} · {query.params.seats} seat{query.params.seats === 1 ? '' : 's'}
                    </Text>
                    {searchError && !results ? (
                        <View style={styles.center}>
                            <Text style={styles.error}>{searchError}</Text>
                            <SecondaryButton title="Try again" onPress={onSearch} />
                        </View>
                    ) : results && !results.rides.length ? (
                        <EmptyState
                            title="No rides found"
                            body="Nobody is offering this route yet. Try another day or fewer seats."
                        />
                    ) : results ? (
                        <>
                            {results.rides.map(r => (
                                <ResultCard key={r.idRide} ride={r} seats={query.params.seats} onAuthError={handleAuth} />
                            ))}
                            {searchError ? <Text style={[styles.error, { textAlign: 'center' }]}>{searchError}</Text> : null}
                            {hasMore(results) ? (
                                loadingMore ? (
                                    <ActivityIndicator color={theme.primary} />
                                ) : (
                                    <SecondaryButton title="Load more" onPress={onLoadMore} />
                                )
                            ) : null}
                        </>
                    ) : null}
                </>
            ) : null}
        </Screen>
    );
}

/** Type-to-filter station field with a short suggestion list. */
function StationPicker({ label, value, onChange, stations, exclude }: {
    label: string; value: Station | null; onChange: (s: Station | null) => void; stations: Station[]; exclude: Station | null;
}) {
    const [text, setText] = useState(value?.station_name ?? '');
    const [open, setOpen] = useState(false);

    // Keep the text in sync when the value changes from outside (e.g. Swap).
    useEffect(() => { setText(value?.station_name ?? ''); }, [value]);

    const matches = useMemo(() => {
        const q = text.trim().toLowerCase();
        return stations
            .filter(s => s.id_station !== exclude?.id_station)
            .filter(s => !q || s.station_name.toLowerCase().includes(q))
            .slice(0, 6);
    }, [text, stations, exclude]);

    return (
        <View>
            <TextField
                label={label}
                value={text}
                placeholder="Search stations"
                autoCapitalize="words"
                onChangeText={t => { setText(t); setOpen(true); if (value) onChange(null); }}
                onFocus={() => setOpen(true)}
                onBlur={() => setTimeout(() => setOpen(false), 150)} // let a suggestion tap land first
            />
            {open && !value ? (
                <View style={styles.suggestions} accessibilityRole="menu">
                    {matches.length ? (
                        matches.map(s => (
                            <Pressable
                                key={s.id_station}
                                onPress={() => { onChange(s); setText(s.station_name); setOpen(false); }}
                                accessibilityRole="menuitem"
                                style={({ pressed }) => [styles.suggestion, pressed && { backgroundColor: theme.primarySoft }]}
                            >
                                <Text style={styles.suggestionText}>{s.station_name}</Text>
                            </Pressable>
                        ))
                    ) : (
                        <Text style={[styles.meta, { padding: 12 }]}>No stations match “{text.trim()}”</Text>
                    )}
                </View>
            ) : null}
        </View>
    );
}

function ResultCard({ ride, seats, onAuthError }: { ride: SearchRide; seats: number; onAuthError: (e: unknown) => void }) {
    const router = useRouter();
    const profile = useProfile();
    const [step, setStep] = useState<'idle' | 'confirm' | 'done'>('idle');
    const [note, setNote] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const total = Number(ride.pricePerSeat) * seats;
    const car = ride.vehicle ? `${ride.vehicle.color} ${ride.vehicle.make} ${ride.vehicle.model}` : null;
    const driver = ride.driver.fullName || 'Driver';

    const book = async () => {
        setBusy(true);
        setError(null);
        try {
            const booking = await bookRide(ride.idRide, seats, note);
            setStep('done');
            const s = getSession();
            notifyDriverOfRequest({
                idDriver: ride.driver.userId,
                idRide: ride.idRide,
                idBooking: booking.id_booking,
                departureTime: ride.departureTime,
                seats,
                riderName: profile.fullName || s?.email?.split('@')[0] || 'A rider',
                note,
            });
        } catch (e) {
            onAuthError(e);
            setError(e instanceof RideSearchError ? e.message : 'Could not send your request. Please try again.');
        } finally {
            setBusy(false);
        }
    };

    return (
        <Card>
            <View style={styles.cardTop}>
                <Text style={styles.time}>{timeLabel(new Date(ride.departureTime))}</Text>
                <Text style={styles.price}>{CURRENCY}{money(ride.pricePerSeat)}<Text style={styles.meta}>/seat</Text></Text>
            </View>
            <View style={styles.route}>
                <View style={styles.dots}>
                    <View style={[styles.dot, { borderColor: theme.primary }]} />
                    <View style={[styles.line, { backgroundColor: theme.border }]} />
                    <View style={[styles.dot, { backgroundColor: theme.primary, borderColor: theme.primary }]} />
                </View>
                <View style={{ flex: 1, gap: 14 }}>
                    <Text style={styles.place} numberOfLines={1}>{ride.source.name}</Text>
                    <Text style={styles.place} numberOfLines={1}>
                        {ride.destination.name}
                        {ride.estimatedArrivalTime ? <Text style={styles.meta}>  · arrives {timeLabel(new Date(ride.estimatedArrivalTime))}</Text> : null}
                    </Text>
                </View>
            </View>
            <Text style={styles.meta}>
                {driver}{car ? ` · ${car}` : ''} · {ride.availableSeats} seat{ride.availableSeats === 1 ? '' : 's'} left
            </Text>
            {ride.notes ? <Text style={styles.note}>“{ride.notes}”</Text> : null}

            {step === 'done' ? (
                <View style={styles.doneBox} accessibilityLiveRegion="polite">
                    <Badge label="Request sent" tone="success" />
                    <Text style={styles.meta}>{driver} will confirm your {seats === 1 ? 'seat' : `${seats} seats`}.</Text>
                    <TextLink label="View in My rides" onPress={() => router.push('/my-rides')} />
                </View>
            ) : step === 'confirm' ? (
                <View style={{ gap: 10, marginTop: 8 }}>
                    <TextField
                        label="Note for the driver (optional)"
                        value={note}
                        onChangeText={setNote}
                        placeholder="e.g. I'll wait at gate 2"
                        autoCapitalize="sentences"
                        autoCorrect
                        maxLength={255}
                    />
                    <FormError message={error} />
                    <PrimaryButton title={`Request ${seats} seat${seats === 1 ? '' : 's'} · ${CURRENCY}${money(total)}`} onPress={book} loading={busy} />
                    {!busy ? <TextLink label="Cancel" onPress={() => { setStep('idle'); setError(null); }} /> : null}
                </View>
            ) : (
                <View style={{ marginTop: 8 }}>
                    <SecondaryButton title={`Book ${seats} seat${seats === 1 ? '' : 's'} · ${CURRENCY}${money(total)}`} onPress={() => setStep('confirm')} />
                </View>
            )}
        </Card>
    );
}

const styles = StyleSheet.create({
    center: { alignItems: 'center', paddingVertical: 40, gap: 12 },
    error: { fontSize: 14, color: theme.error },
    label: { fontSize: 14, fontWeight: '600', color: theme.text },
    meta: { fontSize: 14, color: theme.muted },
    note: { fontSize: 14, color: theme.text, fontStyle: 'italic' },
    swap: { alignSelf: 'flex-end', marginVertical: -4 },
    swapText: { fontSize: 14, fontWeight: '700', color: theme.primary },
    chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
    chip: { paddingVertical: 7, paddingHorizontal: 14, borderRadius: 20, borderWidth: 1, borderColor: theme.border, backgroundColor: theme.card },
    chipActive: { backgroundColor: theme.primary, borderColor: theme.primary },
    chipText: { fontSize: 14, fontWeight: '600', color: theme.text },
    suggestions: {
        marginTop: 6, borderWidth: 1, borderColor: theme.border, borderRadius: 12, backgroundColor: theme.card, overflow: 'hidden',
    },
    suggestion: { paddingVertical: 12, paddingHorizontal: 14, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: theme.border },
    suggestionText: { fontSize: 15, color: theme.text },
    cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
    time: { fontSize: 20, fontWeight: '800', color: theme.text },
    price: { fontSize: 17, fontWeight: '800', color: theme.text },
    route: { flexDirection: 'row', gap: 12, alignItems: 'stretch', marginVertical: 4 },
    dots: { alignItems: 'center', paddingVertical: 5, width: 12 },
    dot: { width: 12, height: 12, borderRadius: 6, borderWidth: 2.5 },
    line: { flex: 1, width: 2, marginVertical: 3 },
    place: { fontSize: 16, fontWeight: '700', color: theme.text },
    doneBox: { gap: 6, marginTop: 8, padding: 12, borderRadius: 12, backgroundColor: theme.successBg, alignItems: 'flex-start' },
});
