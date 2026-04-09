const normalizeHelpKey = (value) => {
    if (!value) return '';
    return String(value)
        .toLowerCase()
        .replace(/\s+/g, ' ')
        .trim();
};

const HEADER_HELP_BY_KEY = {
    account: 'Broker account identifier for this row.',
    'date/time': 'Execution timestamp in local time.',
    ticker: 'Tradable symbol. Click ticker for detail modal.',
    'order ticker': 'Order symbol or combo descriptor.',
    coverage: 'Coverage state of shares vs short calls.',
    dte: 'Days to expiration for the option contract.',
    'ntm %': 'Near-the-money distance between strike and underlying price.',
    qty: 'Position quantity (shares or contracts).',
    quantity: 'Filled trade size (absolute quantity).',
    price: 'Latest market or execution price.',
    value: 'Current market value of the position.',
    basis: 'Cost basis used for P&L calculations.',
    'unrealized p&l': 'Open profit/loss for current holdings.',
    divs: 'Dividends received for this position.',
    'total return': 'Unrealized P&L plus dividends.',
    'true yield': 'Position return percentage including dividends.',
    '% nav': 'Position size as percent of total NAV.',
    type: 'Security class (Stock, Option, or Combo).',
    'sub type': 'Option subtype, usually CALL or PUT.',
    'p.btc': 'Pending buy-to-close contracts from open orders.',
    action: 'Buy/Sell side or inferred trade direction.',
    comm: 'Commission and fees for this trade.',
    'realized p&l': 'Closed trade profit/loss.',
    source: 'Primary data origin (TWS live, Flex history, etc).',
    status: 'Current broker order status.',
    remaining: 'Open quantity still working in the order.',
    'total qty': 'Original order quantity submitted.',
    filled: 'Quantity already filled by broker.',
    'order type': 'Broker order type (LMT, MKT, etc).',
    tif: 'Time-in-force instruction for the order.',
    limit: 'Limit price or net debit/credit value.',
    last: 'Most recent underlying last price.',
    '1d %': 'One-day percent change of the underlying.',
    skew: 'Call/put skew indicator from analysis model.',
    'tsmom 60': '60-day time-series momentum score.',
    '200 ma': '200-day moving average level.',
    'ema 20': '20-day exponential moving average.',
    'hma 20': '20-day hull moving average.',
    'last update': 'Timestamp when this row was last refreshed.',
    'as of': 'Snapshot timestamp for this recommendation.',
    strategy: 'Strategy template used for the recommendation.',
    bucket: 'Timeframe bucket (daily, weekly, monthly).',
    strike: 'Option strike price.',
    premium: 'Option premium per contract.',
    'yield %': 'Expected yield as percentage.',
    'ann %': 'Annualized yield percentage.',
    vol: 'Recent option contract volume.',
    oi: 'Open interest for the option contract.',
    liq: 'Liquidity grade for execution quality.',
    score: 'Composite ranking score.',
    reason: 'Short explanation for why row ranked here.',
    'create date': 'When this opportunity row was first persisted.',
};

const CONTROL_HELP_RULES = [
    [/^all$/i, 'Show all rows and clear focus filters.'],
    [/^uncovered$/i, 'Show positions with uncovered shares.'],
    [/^naked$/i, 'Show positions where short calls exceed share coverage.'],
    [/^covered$/i, 'Show fully covered-call positions only.'],
    [/^pending cover$/i, 'Show rows with pending orders that improve coverage.'],
    [/^pending btc$/i, 'Show rows with pending buy-to-close intent.'],
    [/^pending roll$/i, 'Show rows with pending roll intent.'],
    [/^expiring/i, 'Toggle positions with options expiring within selected DTE.'],
    [/^near money/i, 'Toggle options near the money by strike distance %.'],
    [/^show "stk \?"$/i, 'Include related stock rows in option-focused views.'],
    [/^export csv$/i, 'Download currently visible portfolio rows as CSV.'],
    [/^my portfolio$/i, 'Open portfolio positions and coverage focus view.'],
];

export const resolveHeaderTooltip = (headerName, fieldName = '') => {
    const headerKey = normalizeHelpKey(headerName);
    const fieldKey = normalizeHelpKey(fieldName);
    return (
        HEADER_HELP_BY_KEY[headerKey] ||
        HEADER_HELP_BY_KEY[fieldKey] ||
        null
    );
};

export const withHeaderTooltips = (colDefs) =>
    (colDefs || []).map((def) => {
        if (!def || typeof def !== 'object') return def;
        if (def.headerTooltip) return def;
        const help = resolveHeaderTooltip(def.headerName, def.field);
        if (!help) return def;
        return { ...def, headerTooltip: help };
    });

export const resolveControlTooltip = (label, fallback = null) => {
    const normalized = normalizeHelpKey(label);
    for (const [pattern, text] of CONTROL_HELP_RULES) {
        if (pattern.test(normalized)) return text;
    }
    return fallback;
};

export const resolveQuickLinkTooltip = (kind, ticker) => {
    const symbol = ticker || 'ticker';
    if (kind === 'google') return `Open ${symbol} on Google Finance`;
    if (kind === 'yahoo') return `Open ${symbol} option chain on Yahoo Finance`;
    return `Open ${symbol} details`;
};

export const UI_HELP_HEADER_KEYS = Object.freeze(Object.keys(HEADER_HELP_BY_KEY));
