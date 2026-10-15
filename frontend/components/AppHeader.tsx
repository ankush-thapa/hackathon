import React from 'react';
import { Image, Platform, Pressable, StatusBar, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Colors } from '../constants/Colors';
import { useUnreadCount } from '../services/notifications';
import { useProfile } from '../services/profile';
import { clearSession, getSession } from '../services/session';
import { Avatar } from './Avatar';
import { Icon } from './Icon';
import { IconButton } from './IconButton';

type Props = { onMenuPress: () => void; showMenuButton: boolean };

/** Logged-in header: sidebar button on the left; notifications, profile and logout on the right. */
export const AppHeader = ({ onMenuPress, showMenuButton }: Props) => {
    const theme = Colors.light;
    const router = useRouter();
    const insets = useSafeAreaInsets();
    const unread = useUnreadCount();
    const profile = useProfile();
    const session = getSession();
    const displayName = profile.fullName || session?.email || session?.phone || 'Me';

    const logout = () => {
        clearSession();
        router.replace('/login');
    };

    return (
        <View
            style={[
                styles.wrapper,
                {
                    backgroundColor: theme.card,
                    borderBottomColor: theme.border,
                    paddingTop: Platform.OS === 'ios' ? insets.top : Platform.OS === 'android' ? StatusBar.currentHeight : 0,
                },
            ]}
        >
            <View style={styles.bar}>
                <View style={styles.left}>
                    {showMenuButton ? (
                        <IconButton onPress={onMenuPress} accessibilityLabel="Open menu">
                            <Icon name="menu" color={theme.text} />
                        </IconButton>
                    ) : null}
                    <Pressable
                        onPress={() => router.push('/dashboard')}
                        accessibilityRole="link"
                        accessibilityLabel="Carpool dashboard"
                        style={({ pressed }) => [styles.brand, pressed && { opacity: 0.7 }]}
                    >
                        <Image source={require('../assets/app_icon.png')} style={styles.logo} />
                        <Text style={[styles.brandName, { color: theme.text }]}>Carpool</Text>
                    </Pressable>
                </View>

                <View style={styles.right}>
                    <IconButton onPress={() => router.push('/notifications')} accessibilityLabel="Notifications" badge={unread}>
                        <Icon name="bell" color={theme.text} />
                    </IconButton>
                    <IconButton onPress={() => router.push('/profile')} accessibilityLabel="My profile">
                        <Avatar name={displayName} size={32} />
                    </IconButton>
                    <IconButton onPress={logout} accessibilityLabel="Log out">
                        <Icon name="logout" color={theme.text} />
                    </IconButton>
                </View>
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    wrapper: { borderBottomWidth: 1, zIndex: 10 },
    bar: {
        height: 60, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
        paddingHorizontal: 6, width: '100%', maxWidth: 1200, alignSelf: 'center',
    },
    left: { flexDirection: 'row', alignItems: 'center', gap: 2, flexShrink: 1 },
    right: { flexDirection: 'row', alignItems: 'center' },
    brand: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 6, paddingVertical: 6 },
    logo: { width: 28, height: 28, borderRadius: 7 },
    brandName: { fontSize: 19, fontWeight: '800', letterSpacing: -0.4 },
});
