export const getNumericValue = (value) => {
    if (value === null || value === undefined || value === '') return null;
    const numeric = typeof value === 'number' ? value : Number(value);
    return Number.isFinite(numeric) ? numeric : null;
};

export const formatCurrency = (value, options = {}) => {
    const numeric = getNumericValue(value);
    if (numeric === null) return '-';
    return `$${numeric.toLocaleString(undefined, options)}`;
};

export const formatPercent = (value, digits = 2) => {
    const numeric = getNumericValue(value);
    if (numeric === null) return '-';
    return `${(numeric * 100).toFixed(digits)}%`;
};
