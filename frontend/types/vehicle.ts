export type Vehicle = {
    id: string;
    name: string;
    number: string;
    color: string;
    photoUri: string;
};

// Indian vehicle registration numbers. Spaces/hyphens between parts are optional.
//  - Standard: state code, RTO district, 0–3 series letters, 4 digits  → MH 12 AB 1234, DL 3C AB 1234, KA 05 1234
//  - Bharat (BH) series: year, "BH", 4 digits, 1–2 letters             → 22 BH 1234 AA
const STANDARD_REG = /^[A-Z]{2}[ -]?[0-9]{1,2}[A-Z]?[ -]?(?:[A-Z]{1,3}[ -]?)?[0-9]{4}$/;
const BH_REG = /^[0-9]{2}[ -]?BH[ -]?[0-9]{4}[ -]?[A-Z]{1,2}$/;

export const isValidRegistration = (value: string) => {
    const v = value.trim().toUpperCase();
    return STANDARD_REG.test(v) || BH_REG.test(v);
};

// Used for duplicate checks: "MH 12 AB 1234" and "MH12AB1234" are the same vehicle.
export const compactRegistration = (value: string) => value.toUpperCase().replace(/[\s-]/g, '');
