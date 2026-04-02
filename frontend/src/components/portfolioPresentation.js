export const normalizeSecurityType = (row = {}) => {
    const rawType = row.security_type || row.asset_class || row.secType || row.sec_type || row.AssetClass;
    const normalized = String(rawType || '').trim().toUpperCase();
    if (normalized) return normalized;

    const contractHint = `${row.symbol || ''} ${row.local_symbol || row.localSymbol || ''}`.trim().toUpperCase();
    if (/\d{6}[CP]\d+/.test(contractHint)) return 'OPT';
    return 'STK';
};

export const resolveSecurityTypeLabel = (row = {}) => {
    const normalized = normalizeSecurityType(row);
    if (normalized === 'OPT' || normalized === 'FOP') return 'Option';
    if (normalized === 'STK') return 'Stock';
    return normalized || 'Stock';
};

export const getDisplaySymbol = (row = {}) =>
    row.display_symbol || row.description || row.local_symbol || row.localSymbol || row.symbol || '';

export const getVisibleRowCounterLabel = (rowCount) => `Rows: ${rowCount}`;
