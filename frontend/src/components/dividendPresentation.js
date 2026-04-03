const toFiniteNumber = (value) => {
    if (value === null || value === undefined || value === '') return null;
    const numeric = typeof value === 'number' ? value : Number(value);
    return Number.isFinite(numeric) ? numeric : null;
};

export const formatDividendCurrency = (value, digits = 2) => {
    const numeric = toFiniteNumber(value);
    if (numeric === null) return '-';
    return `$${numeric.toFixed(digits)}`;
};

export const formatDividendPercent = (value, digits = 2) => {
    const numeric = toFiniteNumber(value);
    if (numeric === null) return '-';
    return `${numeric.toFixed(digits)}%`;
};

export const formatAccountsHeldLines = (value) => {
    const raw = String(value || '').trim();
    if (!raw || raw === '-') return [];
    return raw
        .split(',')
        .map((line) => line.trim())
        .filter(Boolean);
};

export const resolvePredictedPrice = (opportunity) => {
    const predicted = toFiniteNumber(opportunity?.predicted_price);
    if (predicted !== null) return predicted;
    return toFiniteNumber(opportunity?.current_price);
};

export const resolveAnalystTarget = (opportunity) => {
    const target = toFiniteNumber(opportunity?.analyst_target);
    if (target === null || target <= 0) return null;
    return target;
};

export const resolveQuarterlyReturnPct = (opportunity) => {
    const explicit = toFiniteNumber(opportunity?.return_pct);
    if (explicit !== null) return explicit;

    const dividendAmount = toFiniteNumber(opportunity?.dividend_amount);
    const currentPrice = toFiniteNumber(opportunity?.current_price);
    if (dividendAmount === null || currentPrice === null || currentPrice <= 0) return null;
    return (dividendAmount / currentPrice) * 100;
};
