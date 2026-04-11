export function formatTradeHistoryDate(date) {
    return date.toISOString().split('T')[0];
}

export function getLastCompletedTradingDay(now = new Date()) {
    const date = new Date(now);
    date.setHours(0, 0, 0, 0);

    const day = date.getDay();
    if (day === 0) {
        date.setDate(date.getDate() - 2);
        return date;
    }
    if (day === 6) {
        date.setDate(date.getDate() - 1);
        return date;
    }
    if (day === 1) {
        date.setDate(date.getDate() - 3);
        return date;
    }

    date.setDate(date.getDate() - 1);
    return date;
}

export function calculateTradeHistoryDateRange(range, now = new Date()) {
    let startDate = null;

    if (range === 'ALL') return { start: null, end: null };
    if (range === 'RT') {
        const today = formatTradeHistoryDate(now);
        return { start: today, end: today };
    }

    if (range === '1D') {
        const lastTradingDay = getLastCompletedTradingDay(now);
        const formatted = formatTradeHistoryDate(lastTradingDay);
        return { start: formatted, end: formatted };
    }

    if (range === 'MTD') {
        startDate = new Date(now.getFullYear(), now.getMonth(), 1);
    } else if (range === 'YTD') {
        startDate = new Date(now.getFullYear(), 0, 1);
    } else if (range === '1W') {
        startDate = new Date(now);
        startDate.setDate(now.getDate() - 7);
    } else if (range === '1M') {
        startDate = new Date(now);
        startDate.setMonth(now.getMonth() - 1);
    } else if (range === '3M') {
        startDate = new Date(now);
        startDate.setMonth(now.getMonth() - 3);
    } else if (range === '6M') {
        startDate = new Date(now);
        startDate.setMonth(now.getMonth() - 6);
    } else if (range === '1Y') {
        startDate = new Date(now);
        startDate.setFullYear(now.getFullYear() - 1);
    } else if (range === '5Y') {
        startDate = new Date(now);
        startDate.setFullYear(now.getFullYear() - 5);
    }

    const startStr = formatTradeHistoryDate(startDate);
    const endStr = formatTradeHistoryDate(now);
    return { start: startStr, end: endStr };
}

export function getTradeActionLabel(row = {}) {
    const explicitAction = String(
        row.raw_action || row.action || row.outcome_action || row.buy_sell || ''
    ).toUpperCase();

    if (explicitAction === 'DIVIDEND') return 'DIVIDEND';
    if (['EXPIRED', 'ASSIGNED', 'EXERCISED'].includes(explicitAction)) return explicitAction;
    if (explicitAction === 'BUY' || explicitAction === 'BOT') return 'BUY';
    if (explicitAction === 'SELL' || explicitAction === 'SLD') return 'SELL';

    const qty = row.quantity !== undefined ? row.quantity : row.Quantity;
    if (!qty) return '-';
    return qty > 0 ? 'BUY' : 'SELL';
}
