// The signed-in session, kept in memory (lost on reload).
// TODO: persist with expo-secure-store (native) / localStorage (web) so users stay signed in.

export type Session = {
    userId: string; // string: snowflake IDs exceed JS safe-integer range
    accessToken: string;
    expiresAt: number; // epoch ms
    email?: string;
    phone?: string;
};

let current: Session | null = null;

export const getSession = () => (current && current.expiresAt > Date.now() ? current : null);
export const setSession = (s: Session | null) => { current = s; };
