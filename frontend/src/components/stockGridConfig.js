export const STOCK_GRID_AVERAGE_FIELDS_ORDER = ['EMA_20', 'HMA_20', 'MA_30', 'MA_60', 'MA_120', 'MA_200'];

export const STOCK_GRID_REQUIRED_FIELDS = [
    'Ticker',
    'Current Price',
    'Call/Put Skew',
    '1D % Change',
    'YoY Price %',
    'TSMOM_60',
    'RSI_14',
    ...STOCK_GRID_AVERAGE_FIELDS_ORDER,
    'Annual Yield Put Prem',
    '3-mo Call Yield',
    '6-mo Call Yield',
    '1-yr Call Yield',
    'Div Yield',
];
