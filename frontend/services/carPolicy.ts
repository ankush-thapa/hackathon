// Car rules a driver sets when offering a ride.
// The rides API has no policy field yet (POST /v1/rides/offer rejects unknown fields), so the
// chosen rules are sent inside `notes` as a "Car policy: …" line. TODO: send as a real field
// once the backend adds one, and drop the notes encoding.

export const CAR_POLICIES = [
    { id: 'no_smoking', label: 'No smoking' },
    { id: 'no_pets', label: 'No pets' },
    { id: 'no_food', label: 'No food or drinks' },
    { id: 'ac', label: 'AC on' },
    { id: 'music', label: 'Music on' },
    { id: 'quiet', label: 'Quiet ride' },
    { id: 'luggage', label: 'Room for luggage' },
    { id: 'women_only', label: 'Women only' },
] as const;

export type CarPolicyId = (typeof CAR_POLICIES)[number]['id'];

export const DEFAULT_POLICIES: CarPolicyId[] = ['no_smoking'];

const POLICY_PREFIX = 'Car policy: ';

export function policyLine(ids: CarPolicyId[]) {
    const labels = CAR_POLICIES.filter(p => ids.includes(p.id)).map(p => p.label);
    return labels.length ? `${POLICY_PREFIX}${labels.join(', ')}` : '';
}

/** Combines the policy line and the driver's own note into the API's `notes` (max 500 chars). */
export function buildNotes(ids: CarPolicyId[], note: string) {
    return [policyLine(ids), note.trim()].filter(Boolean).join('\n') || undefined;
}
