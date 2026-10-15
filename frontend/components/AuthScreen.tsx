import React from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Colors } from '../constants/Colors';

type Props = { title: string; subtitle?: string; children: React.ReactNode };

/** Mobile-first shell for auth forms: centred column, keyboard-safe, capped width on large screens. */
export const AuthScreen = ({ title, subtitle, children }: Props) => {
    const theme = Colors.light;
    return (
        <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
            <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
                <View style={styles.column}>
                    <Text style={[styles.title, { color: theme.text }]}>{title}</Text>
                    {subtitle ? <Text style={[styles.subtitle, { color: theme.muted }]}>{subtitle}</Text> : null}
                    <View style={styles.form}>{children}</View>
                </View>
            </ScrollView>
        </KeyboardAvoidingView>
    );
};

const styles = StyleSheet.create({
    flex: { flex: 1 },
    scroll: { flexGrow: 1, justifyContent: 'center', paddingVertical: 32 },
    column: { width: '100%', maxWidth: 420, alignSelf: 'center', paddingHorizontal: 24 },
    title: { fontSize: 28, fontWeight: '800', letterSpacing: -0.5 },
    subtitle: { fontSize: 15, marginTop: 6 },
    form: { marginTop: 28, gap: 18 },
});
