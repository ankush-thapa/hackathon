import React from 'react';
import { StyleSheet, View } from 'react-native';

// A handful of icons drawn with Views, so we don't need an icon library yet.
// Swap for @expo/vector-icons later if the team adds it.

export type IconName = 'menu' | 'close' | 'bell' | 'logout' | 'chevron' | 'plus' | 'back';

type Props = { name: IconName; color: string; size?: number };

export const Icon = ({ name, color, size = 24 }: Props) => {
    const s = size / 24; // all shapes are drawn on a 24×24 grid
    const bar = (w: number, h = 2.2) => ({ width: w * s, height: h * s, borderRadius: h * s, backgroundColor: color });

    let content: React.ReactNode = null;
    switch (name) {
        case 'menu':
            content = (
                <View style={{ gap: 4.5 * s }}>
                    <View style={bar(18)} /><View style={bar(18)} /><View style={bar(18)} />
                </View>
            );
            break;
        case 'close':
        case 'plus': {
            const rotate = name === 'close' ? 45 : 0;
            content = (
                <View style={{ width: 18 * s, height: 18 * s, alignItems: 'center', justifyContent: 'center' }}>
                    <View style={[bar(name === 'close' ? 20 : 16), styles.abs, { transform: [{ rotate: `${rotate}deg` }] }]} />
                    <View style={[bar(name === 'close' ? 20 : 16), styles.abs, { transform: [{ rotate: `${rotate + 90}deg` }] }]} />
                </View>
            );
            break;
        }
        case 'bell':
            content = (
                <View style={{ alignItems: 'center' }}>
                    <View style={{ width: 3 * s, height: 2 * s, borderTopLeftRadius: 2 * s, borderTopRightRadius: 2 * s, backgroundColor: color }} />
                    <View
                        style={{
                            width: 14 * s, height: 12 * s, borderWidth: 2 * s, borderBottomWidth: 0, borderColor: color,
                            borderTopLeftRadius: 7 * s, borderTopRightRadius: 7 * s,
                        }}
                    />
                    <View style={bar(19)} />
                    <View style={{ width: 6 * s, height: 3 * s, marginTop: 1.2 * s, borderBottomLeftRadius: 3 * s, borderBottomRightRadius: 3 * s, backgroundColor: color }} />
                </View>
            );
            break;
        case 'logout':
            content = (
                <View style={{ width: 20 * s, height: 18 * s, justifyContent: 'center' }}>
                    {/* door */}
                    <View
                        style={{
                            position: 'absolute', left: 0, top: 0, width: 10 * s, height: 18 * s, borderWidth: 2 * s, borderRightWidth: 0,
                            borderColor: color, borderTopLeftRadius: 2.5 * s, borderBottomLeftRadius: 2.5 * s,
                        }}
                    />
                    {/* arrow */}
                    <View style={[bar(12), { position: 'absolute', left: 6 * s }]} />
                    <View style={[styles.chevron, { position: 'absolute', left: 12 * s, width: 7 * s, height: 7 * s, borderColor: color, borderTopWidth: 2.2 * s, borderRightWidth: 2.2 * s }]} />
                </View>
            );
            break;
        case 'chevron':
        case 'back':
            content = (
                <View
                    style={[
                        styles.chevron,
                        {
                            width: 8 * s, height: 8 * s, borderColor: color, borderTopWidth: 2.2 * s, borderRightWidth: 2.2 * s,
                            transform: [{ rotate: name === 'back' ? '-135deg' : '45deg' }],
                            marginLeft: name === 'back' ? 4 * s : -3 * s,
                        },
                    ]}
                />
            );
            break;
    }

    return (
        <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }} pointerEvents="none">
            {content}
        </View>
    );
};

const styles = StyleSheet.create({
    abs: { position: 'absolute' },
    chevron: { transform: [{ rotate: '45deg' }] },
});
