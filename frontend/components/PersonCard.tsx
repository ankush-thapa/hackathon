import React, { useState } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Colors } from '../constants/Colors';
import { profileHref } from '../services/users';
import { Avatar } from './Avatar';
import { Icon } from './Icon';

const theme = Colors.light;

type Props = {
    name: string;
    photoUrl?: string | null;
    /** Small label above the name, e.g. "Your driver" or "Passenger". */
    role?: string;
    /** Extra lines under the name, e.g. the car or "2 seats · ₹120". Falsy entries are skipped. */
    details?: (string | null | undefined | false)[];
    /** Something the person wrote, shown as a quote. */
    note?: string | null;
    size?: 'regular' | 'compact';
    right?: React.ReactNode;
    /** When set, tapping the card opens this user's profile page. */
    userId?: string | null;
};

/** Who you're riding with: photo (or initials), name and a few facts. Used for drivers and riders alike. */
export const PersonCard = ({ name, photoUrl, role, details = [], note, size = 'regular', right, userId }: Props) => {
    const router = useRouter();
    const [photoFailed, setPhotoFailed] = useState(false);
    const px = size === 'compact' ? 36 : 52;
    const lines = details.filter(Boolean) as string[];

    const label = [role, name, ...lines, note ? `Note: ${note}` : ''].filter(Boolean).join('. ');
    const content = (
        <>
            {photoUrl && !photoFailed ? (
                <Image
                    source={{ uri: photoUrl }}
                    style={{ width: px, height: px, borderRadius: px / 2, backgroundColor: theme.primarySoft }}
                    onError={() => setPhotoFailed(true)}
                    accessibilityIgnoresInvertColors
                />
            ) : (
                <Avatar name={name} size={px} />
            )}
            <View style={{ flex: 1, gap: 2 }}>
                {role ? <Text style={styles.role}>{role}</Text> : null}
                <Text style={[styles.name, size === 'compact' && { fontSize: 15 }]} numberOfLines={1}>{name}</Text>
                {lines.map((l, i) => <Text key={i} style={styles.meta}>{l}</Text>)}
                {note ? <Text style={styles.note}>“{note}”</Text> : null}
            </View>
            {right}
            {userId ? <Icon name="chevron" color={theme.muted} size={18} /> : null}
        </>
    );

    if (!userId) {
        return <View style={styles.row} accessible accessibilityLabel={label}>{content}</View>;
    }
    return (
        <Pressable
            onPress={() => router.push(profileHref(userId, { name, photo: photoUrl, role }))}
            accessibilityRole="button"
            accessibilityLabel={`${label}. View profile`}
            style={({ pressed }) => [styles.row, pressed && { opacity: 0.7 }]}
        >
            {content}
        </Pressable>
    );
};

const styles = StyleSheet.create({
    row: { flexDirection: 'row', alignItems: 'center', gap: 14 },
    role: { fontSize: 12, fontWeight: '700', color: theme.muted, textTransform: 'uppercase', letterSpacing: 0.5 },
    name: { fontSize: 17, fontWeight: '800', color: theme.text },
    meta: { fontSize: 14, color: theme.muted },
    note: { fontSize: 14, color: theme.text, fontStyle: 'italic', marginTop: 2 },
});
