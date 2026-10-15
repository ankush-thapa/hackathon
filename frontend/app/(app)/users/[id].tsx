import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Image, StyleSheet, Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Avatar } from '../../../components/Avatar';
import { Card, EmptyState, Screen, SecondaryButton, SectionTitle, TextLink } from '../../../components/ui';
import { Colors } from '../../../constants/Colors';
import { ApiError } from '../../../services/api';
import { TIME_ZONE } from '../../../services/format';
import { PublicProfile, fetchPublicProfile } from '../../../services/users';

const theme = Colors.light;

const GENDER: Record<string, string> = { male: 'Male', female: 'Female', other: 'Other', prefer_not_to_say: '' };
const VEHICLE_TYPE: Record<string, string> = { car: 'Car', hatchback: 'Hatchback', sedan: 'Sedan', suv: 'SUV', bike: 'Bike' };

/** A driver's or rider's public profile. Opened by tapping their photo or name. No phone number, ever. */
export default function UserProfileScreen() {
    const router = useRouter();
    const { id, name: hintName, photo: hintPhoto, role } = useLocalSearchParams<{ id: string; name?: string; photo?: string; role?: string }>();
    const [profile, setProfile] = useState<PublicProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<{ notFound: boolean; message: string } | null>(null);
    const [photoFailed, setPhotoFailed] = useState(false);

    const load = useCallback(async () => {
        if (!id) return;
        setLoading(true);
        setError(null);
        try {
            setProfile(await fetchPublicProfile(id));
        } catch (e) {
            if (e instanceof ApiError && e.status === 401) return router.replace('/login');
            setError({
                notFound: e instanceof ApiError && e.status === 404,
                message: e instanceof ApiError ? e.message : 'Something went wrong. Please try again.',
            });
        } finally {
            setLoading(false);
        }
    }, [id, router]);

    useEffect(() => { load(); }, [load]);

    const back = () => (router.canGoBack() ? router.back() : router.replace('/my-rides'));
    const backLink = <View style={{ paddingTop: 8 }}><TextLink label="Back" onPress={back} /></View>;

    const name = profile?.fullName || hintName || (role === 'Driver' ? 'Driver' : role === 'Passenger' ? 'Rider' : 'Hopr member');
    const photo = profile?.photoUrl ?? hintPhoto ?? null;

    if (error && !profile) {
        return (
            <Screen title="Profile" action={backLink}>
                <EmptyState
                    title={error.notFound ? 'Profile not available' : 'Couldn’t load this profile'}
                    body={error.notFound ? 'You can see someone’s profile once you share a ride, or while they’re offering one.' : error.message}
                    action={error.notFound ? undefined : <SecondaryButton title="Try again" onPress={load} />}
                />
            </Screen>
        );
    }

    const facts = profile
        ? [
            profile.age != null ? `${profile.age} years` : null,
            profile.gender ? GENDER[profile.gender] || null : null,
        ].filter(Boolean).join(' · ')
        : '';
    const since = profile
        ? new Date(profile.memberSince).toLocaleDateString('en-GB', { month: 'long', year: 'numeric', timeZone: TIME_ZONE })
        : null;

    return (
        <Screen title="Profile" action={backLink}>
            {/* Header: photo, name, role */}
            <Card style={styles.hero}>
                {photo && !photoFailed ? (
                    <Image source={{ uri: photo }} style={styles.photo} onError={() => setPhotoFailed(true)} accessibilityLabel={`Photo of ${name}`} />
                ) : (
                    <Avatar name={name} size={96} />
                )}
                <View style={{ alignItems: 'center', gap: 4 }}>
                    {role ? <Text style={styles.role}>{role}</Text> : null}
                    <Text style={styles.name} accessibilityRole="header">{name}</Text>
                    {facts ? <Text style={styles.meta}>{facts}</Text> : null}
                    {since ? <Text style={styles.meta}>Member since {since}</Text> : null}
                </View>
                {loading && !profile ? <ActivityIndicator color={theme.primary} /> : null}
            </Card>

            {profile ? (
                <>
                    {/* About */}
                    <SectionTitle title="About" />
                    <Card>
                        <Text style={profile.about ? styles.about : styles.meta}>
                            {profile.about || `${profile.fullName ? profile.fullName.split(' ')[0] : 'They'} hasn’t written anything yet.`}
                        </Text>
                    </Card>

                    {/* Vehicle */}
                    {profile.vehicle ? (
                        <>
                            <SectionTitle title="Vehicle" />
                            <Card style={{ gap: 4 }}>
                                <Text style={styles.vehicleName}>{profile.vehicle.make} {profile.vehicle.model}</Text>
                                <Text style={styles.meta}>
                                    {profile.vehicle.color} · {VEHICLE_TYPE[profile.vehicle.vehicleType] ?? profile.vehicle.vehicleType}
                                </Text>
                            </Card>
                        </>
                    ) : null}

                    {!profile.fullName ? (
                        <Text style={[styles.meta, { textAlign: 'center' }]}>This member hasn’t completed their profile yet.</Text>
                    ) : null}
                    <Text style={styles.privacy}>
                        Phone numbers and email addresses are never shown on profiles.
                    </Text>
                </>
            ) : null}
        </Screen>
    );
}

const styles = StyleSheet.create({
    hero: { alignItems: 'center', gap: 14, paddingVertical: 24 },
    photo: { width: 96, height: 96, borderRadius: 48, backgroundColor: theme.primarySoft },
    role: { fontSize: 12, fontWeight: '700', color: theme.muted, textTransform: 'uppercase', letterSpacing: 0.6 },
    name: { fontSize: 24, fontWeight: '800', color: theme.text, textAlign: 'center' },
    meta: { fontSize: 14, color: theme.muted },
    about: { fontSize: 15, color: theme.text, lineHeight: 22 },
    vehicleName: { fontSize: 16, fontWeight: '700', color: theme.text },
    privacy: { fontSize: 12, color: theme.muted, textAlign: 'center', marginTop: 4 },
});
