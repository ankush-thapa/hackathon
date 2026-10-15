import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { Colors } from '../constants/Colors';
import { ApiError } from '../services/api';
import { MAX_STATION_SEARCH, Station, searchStations } from '../services/stations';
import { TextField } from './TextField';

const theme = Colors.light;
const DEBOUNCE_MS = 250;
const MAX_RESULTS = 8;

type Props = {
    label: string;
    placeholder: string;
    value: Station | null;
    onChange: (station: Station | null) => void;
    /** e.g. the station already chosen on the other end of the route. */
    excludeId?: number;
    error?: string;
    onSessionExpired?: () => void;
};

/** Type to search GET /v1/stations; pick one from the list. */
export const StationPicker = ({ label, placeholder, value, onChange, excludeId, error, onSessionExpired }: Props) => {
    const inputRef = useRef<TextInput>(null);
    const [query, setQuery] = useState('');
    const [open, setOpen] = useState(false);
    const [results, setResults] = useState<Station[]>([]);
    const [loading, setLoading] = useState(false);
    const [loadError, setLoadError] = useState<string | null>(null);

    // Debounced search; aborts the previous request so stale results never win.
    useEffect(() => {
        if (!open) return;
        const controller = new AbortController();
        const timer = setTimeout(async () => {
            setLoading(true);
            setLoadError(null);
            try {
                const found = await searchStations(query, { limit: MAX_RESULTS + 1, signal: controller.signal });
                setResults(found);
            } catch (e) {
                if (controller.signal.aborted) return;
                if (e instanceof ApiError && e.status === 401) onSessionExpired?.();
                setLoadError(e instanceof ApiError ? e.message : 'Could not load stations');
                setResults([]);
            } finally {
                if (!controller.signal.aborted) setLoading(false);
            }
        }, query ? DEBOUNCE_MS : 0);
        return () => {
            clearTimeout(timer);
            controller.abort();
        };
    }, [query, open, onSessionExpired]);

    const choose = (s: Station) => {
        onChange(s);
        setOpen(false);
        setQuery('');
        inputRef.current?.blur();
    };

    if (value && !open) {
        return (
            <View style={{ gap: 6 }}>
                <Text style={styles.label}>{label}</Text>
                <Pressable
                    onPress={() => { setOpen(true); setTimeout(() => inputRef.current?.focus(), 0); }}
                    accessibilityRole="button"
                    accessibilityLabel={`${label}: ${value.name}. Change`}
                    style={[styles.selected, { borderColor: error ? theme.error : theme.border }]}
                >
                    <View style={[styles.pin, { backgroundColor: theme.primary }]} />
                    <Text style={styles.selectedText} numberOfLines={1}>{value.name}</Text>
                    <Text style={styles.change}>Change</Text>
                </Pressable>
                {error ? <Text style={styles.error}>{error}</Text> : null}
            </View>
        );
    }

    const visible = results.filter(s => s.id !== excludeId).slice(0, MAX_RESULTS);

    return (
        <View style={{ gap: 6 }}>
            <TextField
                ref={inputRef}
                label={label}
                placeholder={placeholder}
                value={query}
                onChangeText={t => { setQuery(t); setOpen(true); }}
                onFocus={() => setOpen(true)}
                error={error}
                autoCapitalize="words"
                maxLength={MAX_STATION_SEARCH}
                returnKeyType="search"
                onSubmitEditing={() => visible[0] && choose(visible[0])}
                accessibilityHint="Type to search stations, then pick one from the list"
            />
            {open ? (
                <View style={styles.list} accessibilityRole="list">
                    {loading ? (
                        <View style={styles.status}><ActivityIndicator color={theme.primary} /></View>
                    ) : loadError ? (
                        <Text style={[styles.statusText, { color: theme.error }]}>{loadError}</Text>
                    ) : visible.length === 0 ? (
                        <Text style={styles.statusText}>{query ? `No stations match “${query}”` : 'No stations available'}</Text>
                    ) : (
                        visible.map((s, i) => (
                            <Pressable
                                key={s.id}
                                onPress={() => choose(s)}
                                accessibilityRole="button"
                                accessibilityLabel={s.name}
                                style={({ pressed }) => [
                                    styles.option,
                                    i > 0 && { borderTopWidth: 1, borderTopColor: theme.border },
                                    pressed && { backgroundColor: theme.primarySoft },
                                ]}
                            >
                                <View style={[styles.pin, { backgroundColor: theme.muted }]} />
                                <Text style={styles.optionText} numberOfLines={1}>{s.name}</Text>
                            </Pressable>
                        ))
                    )}
                    {value ? (
                        <Pressable onPress={() => { setOpen(false); setQuery(''); }} style={[styles.option, styles.keep]}>
                            <Text style={styles.change}>Keep {value.name}</Text>
                        </Pressable>
                    ) : null}
                </View>
            ) : null}
        </View>
    );
};

const styles = StyleSheet.create({
    label: { fontSize: 14, fontWeight: '600', color: theme.text },
    selected: {
        flexDirection: 'row', alignItems: 'center', gap: 10, minHeight: 52, borderWidth: 1.5, borderRadius: 12,
        paddingHorizontal: 14, backgroundColor: theme.card,
    },
    selectedText: { flex: 1, fontSize: 16, fontWeight: '600', color: theme.text },
    change: { fontSize: 14, fontWeight: '700', color: theme.primary },
    pin: { width: 10, height: 10, borderRadius: 5 },
    list: { borderWidth: 1, borderColor: theme.border, borderRadius: 12, backgroundColor: theme.card, overflow: 'hidden' },
    option: { flexDirection: 'row', alignItems: 'center', gap: 10, minHeight: 48, paddingHorizontal: 14 },
    optionText: { flex: 1, fontSize: 15, color: theme.text },
    keep: { borderTopWidth: 1, borderTopColor: theme.border, justifyContent: 'center' },
    status: { padding: 14, alignItems: 'center' },
    statusText: { padding: 14, fontSize: 14, color: theme.muted },
    error: { fontSize: 13, color: theme.error },
});
