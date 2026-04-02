export const normalizeAccountScopeParam = (selectedAccount) => {
    const normalized = String(selectedAccount || '').trim();
    if (!normalized || normalized.toLowerCase() === 'all') {
        return {};
    }
    return { account_id: normalized };
};

const formatShortDate = (value) => {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return null;
    return parsed.toLocaleDateString(undefined, { month: '2-digit', day: '2-digit' });
};

const formatShortTimeEt = (value) => {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return null;
    return parsed.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
        timeZone: 'America/New_York',
    });
};

export const buildTimeframeSubtitle = (timeframeKey, timeframeMeta) => {
    const meta = timeframeMeta?.[timeframeKey] || {};
    const endDate = meta.end_date;
    const endDateSource = meta.end_date_source;

    if (!endDate) {
        return timeframeKey === '1d' ? 'as of COB --/--' : null;
    }

    const shortDate = formatShortDate(endDate);
    if (timeframeKey === '1d') {
        return shortDate ? `as of COB ${shortDate}` : 'as of COB --/--';
    }

    if (endDateSource === 'tws_rt') {
        const shortTime = formatShortTimeEt(endDate);
        return shortTime ? `as of ${shortTime} ET` : (shortDate ? `as of ${shortDate}` : null);
    }

    return shortDate ? `as of ${shortDate}` : null;
};
