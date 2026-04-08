const DATE_LABEL_PATTERN = /(date|update|captured at|expiration|as of)/i;
const PERCENT_LABEL_PATTERN = /(%|yield|skew|confidence|change|rank)/i;
const CURRENCY_LABEL_PATTERN = /(price|premium|strike|value|target|cost|basis|credit)/i;

const parseNumeric = (value) => {
    if (value === null || value === undefined || value === '') return null;
    if (typeof value === 'number') return Number.isFinite(value) ? value : null;
    const trimmed = String(value).trim();
    if (!trimmed) return null;
    const normalized = trimmed.endsWith('%') ? trimmed.slice(0, -1) : trimmed;
    const parsed = Number.parseFloat(normalized.replace(/,/g, ''));
    return Number.isFinite(parsed) ? parsed : null;
};

const toIsoIfDateLike = (value) => {
    if (typeof value !== 'string' && typeof value !== 'number') return null;
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return null;
    return parsed.toISOString();
};

export const formatDisplayValue = (label, value) => {
    if (value === undefined || value === null || value === '') return '-';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (Array.isArray(value)) return value.length ? value.map((item) => formatDisplayValue(label, item)).join(', ') : '-';
    if (typeof value === 'object') return JSON.stringify(value);

    const dateLike = DATE_LABEL_PATTERN.test(label);
    if (dateLike) {
        const iso = toIsoIfDateLike(value);
        if (iso) {
            if (label.toLowerCase() === 'ex-div date') {
                return iso.split('T')[0];
            }
            return iso;
        }
        return String(value);
    }

    const numeric = parseNumeric(value);
    if (numeric !== null) {
        if (PERCENT_LABEL_PATTERN.test(label)) return `${numeric.toFixed(2)}%`;
        if (CURRENCY_LABEL_PATTERN.test(label)) return numeric.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        if (Number.isInteger(numeric)) return numeric.toLocaleString('en-US');
        return numeric.toLocaleString('en-US', { maximumFractionDigits: 4 });
    }

    return String(value);
};

export const getAnalyticsSummaryCards = (stock) => {
    const currentPrice = parseNumeric(stock?.['Current Price']);
    const oneDayChange = parseNumeric(stock?.['1D % Change']);
    const skew = parseNumeric(stock?.['Call/Put Skew']);
    const momentum = parseNumeric(stock?.['TSMOM_60']);
    const dividendYield = parseNumeric(stock?.['Div Yield']);
    const rsi = parseNumeric(stock?.['RSI_14']);

    return [
        {
            label: 'Price',
            value: formatDisplayValue('Current Price', currentPrice),
            tone: 'text-blue-300',
        },
        {
            label: '1D Change',
            value: formatDisplayValue('1D % Change', oneDayChange),
            tone: oneDayChange > 0 ? 'text-emerald-300' : oneDayChange < 0 ? 'text-rose-300' : 'text-gray-200',
        },
        {
            label: 'Skew',
            value: formatDisplayValue('Call/Put Skew', skew),
            tone: skew >= 1 ? 'text-emerald-300' : 'text-amber-300',
        },
        {
            label: 'TSMOM 60',
            value: formatDisplayValue('TSMOM_60', momentum),
            tone: momentum > 0 ? 'text-emerald-300' : momentum < 0 ? 'text-rose-300' : 'text-gray-200',
        },
        {
            label: 'Div Yield',
            value: formatDisplayValue('Div Yield', dividendYield),
            tone: 'text-cyan-300',
        },
        {
            label: 'RSI 14',
            value: formatDisplayValue('RSI_14', rsi),
            tone: rsi > 70 ? 'text-rose-300' : rsi < 30 ? 'text-emerald-300' : 'text-gray-200',
        },
    ];
};

export const buildSectionLines = (title, rows) => {
    const lines = [title];
    for (const [label, value] of rows) {
        lines.push(`${label}: ${formatDisplayValue(label, value)}`);
    }
    lines.push('');
    return lines;
};

export const buildTickerNotFoundLogPayload = ({ ticker, activeTab }) => ({
    level: 'warning',
    source: 'frontend',
    boundary: 'ticker_modal_detail_lookup',
    message: `Ticker detail lookup returned found=false for ${ticker || 'unknown'}`,
    ticker: ticker || null,
    active_tab: activeTab || null,
    timestamp: new Date().toISOString(),
    path: typeof window !== 'undefined' ? window.location?.pathname || null : null,
    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent || null : null,
});
