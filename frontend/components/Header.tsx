import React from 'react';
import { View, Text, StyleSheet, Pressable, Platform, StatusBar, Image, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Colors } from '../constants/Colors';

const getMobileHeaderHeight = () => Platform.OS === 'ios' ? 60 : 64;

export const Header = () => {
    const theme = Colors.light;
    const router = useRouter();
    const insets = useSafeAreaInsets();
    const { width } = useWindowDimensions();
    const isLargeScreen = width > 768;

    return (
        <View style={[
            styles.headerWrapper,
            {
                backgroundColor: theme.card,
                borderBottomColor: theme.border,
                paddingTop: Platform.OS === 'ios' ? insets.top : (Platform.OS === 'android' ? StatusBar.currentHeight : 0)
            }
        ]}>
            <View style={[
                styles.headerContainer,
                {
                    paddingHorizontal: isLargeScreen ? 24 : 14,
                    height: isLargeScreen ? 72 : getMobileHeaderHeight(),
                }
            ]}>
                <Pressable
                    style={({ pressed }) => [styles.logoContainer, pressed && { opacity: 0.7 }]}
                    onPress={() => router.push('/')}
                >
                    <Image
                        source={require('../assets/app_icon.png')}
                        style={styles.logoImage}
                        resizeMode="contain"
                        accessibilityLabel="Hackathon Logo"
                    />
                    <Text style={[styles.logoBrandName, { color: theme.text }]}>Hackathon</Text>
                </Pressable>
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    headerWrapper: {
        borderBottomWidth: 1,
        zIndex: 100,
    },
    headerContainer: {
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        alignSelf: 'center',
        width: '100%',
        maxWidth: 1200,
    },
    logoContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    logoImage: {
        width: 32,
        height: 32,
    },
    logoBrandName: {
        fontSize: 22,
        fontWeight: '800',
        letterSpacing: -0.5,
        fontFamily: 'System',
    },
});
