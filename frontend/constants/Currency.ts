// Stations are in Gurugram, so prices are in Indian rupees.
export const CURRENCY = '₹';
export const formatPrice = (amount: number) => (amount ? `${CURRENCY}${Number.isInteger(amount) ? amount : amount.toFixed(2)}` : 'Free');
