const DAY_MS = 86_400_000;

const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());

/** "Today", "Tomorrow" or e.g. "Fri 17 Oct". */
export function dayLabel(date: Date) {
    const diff = Math.round((startOfDay(date).getTime() - startOfDay(new Date()).getTime()) / DAY_MS);
    if (diff === 0) return 'Today';
    if (diff === 1) return 'Tomorrow';
    return date.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
}

export const timeLabel = (date: Date) => date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

export const departureLabel = (iso: string) => {
    const d = new Date(iso);
    return `${dayLabel(d)} · ${timeLabel(d)}`;
};

export function timeAgo(iso: string) {
    const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins} min ago`;
    const hours = Math.round(mins / 60);
    if (hours < 24) return `${hours} h ago`;
    return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

/** The next `count` days starting today, for date chips. */
export function nextDays(count: number) {
    const today = startOfDay(new Date());
    return Array.from({ length: count }, (_, i) => new Date(today.getTime() + i * DAY_MS));
}

/** Parses "HH:MM" (24h). */
export function parseTime(value: string): { h: number; m: number } | null {
    const match = /^([01]?\d|2[0-3]):([0-5]\d)$/.exec(value.trim());
    return match ? { h: Number(match[1]), m: Number(match[2]) } : null;
}

export function combine(day: Date, time: { h: number; m: number }) {
    return new Date(day.getFullYear(), day.getMonth(), day.getDate(), time.h, time.m);
}

/** Initials for an avatar from a name, email or phone. */
export function initials(source: string) {
    const name = source.includes('@') ? source.split('@')[0].replace(/[._-]+/g, ' ') : source;
    if (/^\+?\d/.test(name)) return '#';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    return ((parts[0]?.[0] ?? '') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase() || '?';
}
