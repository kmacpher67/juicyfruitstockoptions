export const ANALYTICS_FIELD_GROUPS = [
    {
        title: 'Core Pricing',
        fields: [
            ['Current Price', 'Current Price'],
            ['1D % Change', '1D % Change'],
            ['YoY Price %', 'YoY Price %'],
            ['Market Cap (T$)', 'Market Cap (T$)'],
            ['P/E', 'P/E'],
            ['Last Update', 'Last Update'],
            ['Error', 'Error'],
        ],
    },
    {
        title: 'Trend & Technicals',
        fields: [
            ['EMA_20', 'EMA_20'],
            ['HMA_20', 'HMA_20'],
            ['TSMOM_60', 'TSMOM_60'],
            ['RSI_14', 'RSI_14'],
            ['ATR_14', 'ATR_14'],
            ['MA_30', 'MA_30'],
            ['MA_60', 'MA_60'],
            ['MA_120', 'MA_120'],
            ['MA_200', 'MA_200'],
            ['EMA_20_highlight', 'EMA_20_highlight'],
            ['HMA_20_highlight', 'HMA_20_highlight'],
            ['TSMOM_60_highlight', 'TSMOM_60_highlight'],
            ['MA_30_highlight', 'MA_30_highlight'],
            ['MA_60_highlight', 'MA_60_highlight'],
            ['MA_120_highlight', 'MA_120_highlight'],
            ['MA_200_highlight', 'MA_200_highlight'],
        ],
    },
    {
        title: 'Dividends & Fundamentals',
        fields: [
            ['Ex-Div Date', 'Ex-Div Date'],
            ['Div Yield', 'Div Yield'],
            ['Analyst 1-yr Target', 'Analyst 1-yr Target'],
        ],
    },
    {
        title: 'Options Metrics',
        fields: [
            ['1-yr 6% OTM PUT Price', '1-yr 6% OTM PUT Price'],
            ['Annual Yield Put Prem', 'Annual Yield Put Prem'],
            ['3-mo Call Yield', '3-mo Call Yield'],
            ['6-mo Call Yield', '6-mo Call Yield'],
            ['1-yr Call Yield', '1-yr Call Yield'],
            ['Annual Yield Call Prem', 'Annual Yield Call Prem'],
            ['Call/Put Skew', 'Call/Put Skew'],
            ['6-mo Call Strike', '6-mo Call Strike'],
            ['_PutExpDate_365', '_PutExpDate_365'],
            ['_CallExpDate_365', '_CallExpDate_365'],
            ['_CallExpDate_90', '_CallExpDate_90'],
            ['_CallExpDate_180', '_CallExpDate_180'],
        ],
    },
];

const parseNumeric = (value) => {
    if (value === null || value === undefined) return null;
    const normalized = String(value).replace('%', '').trim();
    if (!normalized || normalized.toLowerCase() === 'nan') return null;
    const parsed = Number.parseFloat(normalized);
    return Number.isFinite(parsed) ? parsed : null;
};

const scoreBands = {
    positive: { max: 100, min: 70, label: 'Strong' },
    neutral: { max: 69, min: 45, label: 'Watch' },
    weak: { max: 44, min: 0, label: 'Weak' },
};

export const computeTickerHealthScore = (row) => {
    if (!row || typeof row !== 'object') return null;

    const momentum = parseNumeric(row['TSMOM_60']);
    const skew = parseNumeric(row['Call/Put Skew']);
    const rsi = parseNumeric(row['RSI_14']);
    const oneDay = parseNumeric(row['1D % Change']);
    const yoy = parseNumeric(row['YoY Price %']);

    const components = [];

    if (momentum !== null) components.push(Math.max(-1, Math.min(1, momentum)) * 20);
    if (skew !== null) components.push(Math.max(-1, Math.min(2, skew - 1)) * 15);
    if (rsi !== null) components.push((50 - Math.abs(50 - rsi)) * 0.5);
    if (oneDay !== null) components.push(Math.max(-5, Math.min(5, oneDay)) * 2);
    if (yoy !== null) components.push(Math.max(-25, Math.min(25, yoy)) * 0.8);

    if (!components.length) return null;

    const raw = 50 + components.reduce((acc, current) => acc + current, 0);
    return Math.max(0, Math.min(100, Math.round(raw)));
};

export const getTickerHealthTone = (score) => {
    if (score === null || score === undefined) return 'text-slate-400';
    if (score >= scoreBands.positive.min) return 'text-green-400';
    if (score >= scoreBands.neutral.min) return 'text-yellow-400';
    return 'text-red-400';
};

export const getTickerHealthLabel = (score) => {
    if (score === null || score === undefined) return '-';
    if (score >= scoreBands.positive.min) return scoreBands.positive.label;
    if (score >= scoreBands.neutral.min) return scoreBands.neutral.label;
    return scoreBands.weak.label;
};
