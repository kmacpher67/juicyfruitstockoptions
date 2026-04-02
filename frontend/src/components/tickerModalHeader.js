const toFiniteNumber = (value) => {
    if (value === null || value === undefined || value === '') return null;
    const numeric = typeof value === 'number' ? value : Number(String(value).replace('%', '').trim());
    return Number.isFinite(numeric) ? numeric : null;
};

const toIsoDateTimeText = (value) => {
    if (!value) return 'Last update unavailable';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return `Last update: ${value}`;
    return `Last update: ${parsed.toLocaleString()}`;
};

const summarizeDescription = (description) => {
    if (!description) return '';
    const compact = String(description).trim().replace(/\s+/g, ' ');
    if (!compact) return '';
    return compact.length > 96 ? `${compact.slice(0, 93)}...` : compact;
};

export const buildTickerHeaderModel = ({ ticker, tickerData }) => {
    const data = tickerData?.data || {};
    const profile = tickerData?.profile || {};
    const companyName = tickerData?.company_name || profile?.company_name || '';
    const descriptor = companyName || summarizeDescription(profile?.description);
    const change = toFiniteNumber(data['1D % Change']);
    const price = toFiniteNumber(data['Current Price']);
    const lastUpdate = data['Last Update'] || tickerData?.last_update || profile?.last_update;

    return {
        ticker: String(ticker || '').trim().toUpperCase(),
        descriptor,
        priceText: price === null ? null : `$${price.toFixed(2)}`,
        changeText: change === null ? null : `${change.toFixed(2)}%`,
        changeTone: change === null ? 'text-gray-400' : (change >= 0 ? 'text-green-400' : 'text-red-400'),
        lastUpdateText: toIsoDateTimeText(lastUpdate),
    };
};
