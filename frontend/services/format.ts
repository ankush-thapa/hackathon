const DAY_MS = 86_400_000;

// ---- App time zone ------------------------------------------------------------------------------
// The app runs on Indian time (IST, UTC+05:30, no daylight saving) whatever the device is set to.
//
// Two kinds of Date are used:
//   • instants   – real moments (API timestamps, departure times). Shown with TIME_ZONE.
//   • calendar days – a Date used only for its year/month/day numbers (calendar, "Today").
//     Build them with today() / istDay() / addDays(); turn one into an instant with combine().
export const TIME_ZONE = 'Asia/Kolkata';
const IST_OFFSET_MS = 330 * 60_000;

/** IST year/month/day/hour/minute of an instant. */
export function istParts(instant: Date) {
    const shifted = new Date(instant.getTime() + IST_OFFSET_MS);
    return {
        y: shifted.getUTCFullYear(), m: shifted.getUTCMonth(), d: shifted.getUTCDate(),
        h: shifted.getUTCHours(), min: shifted.getUTCMinutes(),
    };
}

/** The IST calendar day an instant falls on. */
export const istDay = (instant: Date) => {
    const p = istParts(instant);
    return new Date(p.y, p.m, p.d);
};

/** Normalises a calendar day (drops any time part). */
export const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
/** Today in India. Always call it when needed, never once at import time. */
export const today = () => istDay(new Date());
export const addDays = (d: Date, n: number) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
export const sameDay = (a: Date, b: Date) => startOfDay(a).getTime() === startOfDay(b).getTime();
/** The instant a calendar day starts in IST (00:00 IST). */
export const dayStart = (day: Date) => new Date(Date.UTC(day.getFullYear(), day.getMonth(), day.getDate()) - IST_OFFSET_MS);
/** Current hour in India (0–23). */
export const istHour = () => istParts(new Date()).h;

/** For a calendar day: "Today", "Tomorrow" or e.g. "Fri 17 Oct". */
export function dayLabel(date: Date) {
    const diff = Math.round((startOfDay(date).getTime() - today().getTime()) / DAY_MS);
    if (diff === 0) return 'Today';
    if (diff === 1) return 'Tomorrow';
    return date.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
}

/** "Today, Thu 15 Oct" / "Tomorrow, Fri 16 Oct" / "Sat 17 Oct". */
export function fullDayLabel(date: Date) {
    const plain = date.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
    const rel = dayLabel(date);
    return rel === 'Today' || rel === 'Tomorrow' ? `${rel}, ${plain}` : plain;
}

/** For an instant: "09:00" in IST. */
export const timeLabel = (date: Date) => date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: TIME_ZONE });

export const departureLabel = (iso: string) => {
    const d = new Date(iso);
    return `${dayLabel(istDay(d))} · ${timeLabel(d)}`;
};

export function timeAgo(iso: string) {
    const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins} min ago`;
    const hours = Math.round(mins / 60);
    if (hours < 24) return `${hours} h ago`;
    return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: TIME_ZONE });
}

/** The next `count` days starting today, for date chips. */
export function nextDays(count: number) {
    const start = today();
    return Array.from({ length: count }, (_, i) => addDays(start, i));
}

/** Parses "HH:MM" (24h). */
export function parseTime(value: string): { h: number; m: number } | null {
    const match = /^([01]?\d|2[0-3]):([0-5]\d)$/.exec(value.trim());
    return match ? { h: Number(match[1]), m: Number(match[2]) } : null;
}

/** Calendar day + IST clock time → the real instant (e.g. 15 Oct 09:00 IST = 03:30 UTC). */
export function combine(day: Date, time: { h: number; m: number }) {
    return new Date(Date.UTC(day.getFullYear(), day.getMonth(), day.getDate(), time.h, time.m) - IST_OFFSET_MS);
}

/** Initials for an avatar from a name, email or phone. */
export function initials(source: string) {
    const name = source.includes('@') ? source.split('@')[0].replace(/[._-]+/g, ' ') : source;
    if (/^\+?\d/.test(name)) return '#';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    return ((parts[0]?.[0] ?? '') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase() || '?';
}
