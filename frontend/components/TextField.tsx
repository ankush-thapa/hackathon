import React, { forwardRef, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, TextInputProps, View } from 'react-native';
import { Colors } from '../constants/Colors';

type Props = TextInputProps & {
    label: string;
    error?: string;
    /** Helper text shown under the field when there is no error. */
    hint?: string;
    /** Adds a Show/Hide toggle and masks the value. */
    password?: boolean;
};

export const TextField = forwardRef<TextInput, Props>(({ label, error, hint, password, style, onFocus, onBlur, ...rest }, ref) => {
    const theme = Colors.light;
    const [focused, setFocused] = useState(false);
    const [hidden, setHidden] = useState(true);
    const borderColor = error ? theme.error : focused ? theme.primary : theme.border;

    return (
        <View style={styles.wrapper}>
            <Text style={[styles.label, { color: theme.text }]}>{label}</Text>
            <View style={[styles.inputRow, { borderColor, backgroundColor: theme.card }]}>
                <TextInput
                    ref={ref}
                    style={[styles.input, { color: theme.text }, style]}
                    placeholderTextColor={theme.muted}
                    secureTextEntry={password && hidden}
                    autoCapitalize="none"
                    autoCorrect={false}
                    onFocus={e => { setFocused(true); onFocus?.(e); }}
                    onBlur={e => { setFocused(false); onBlur?.(e); }}
                    accessibilityLabel={label}
                    {...rest}
                />
                {password && (
                    <Pressable
                        onPress={() => setHidden(h => !h)}
                        hitSlop={8}
                        accessibilityRole="button"
                        accessibilityLabel={hidden ? 'Show password' : 'Hide password'}
                    >
                        <Text style={[styles.toggle, { color: theme.primary }]}>{hidden ? 'Show' : 'Hide'}</Text>
                    </Pressable>
                )}
            </View>
            {error ? (
                <Text style={[styles.error, { color: theme.error }]}>{error}</Text>
            ) : hint ? (
                <Text style={[styles.error, { color: theme.muted }]}>{hint}</Text>
            ) : null}
        </View>
    );
});

const styles = StyleSheet.create({
    wrapper: { gap: 6 },
    label: { fontSize: 14, fontWeight: '600' },
    inputRow: {
        flexDirection: 'row',
        alignItems: 'center',
        borderWidth: 1.5,
        borderRadius: 12,
        paddingHorizontal: 14,
        minHeight: 52,
    },
    input: { flex: 1, fontSize: 16, paddingVertical: 12, outlineStyle: 'none' } as any,
    toggle: { fontSize: 14, fontWeight: '700', paddingLeft: 12 },
    error: { fontSize: 13 },
});
