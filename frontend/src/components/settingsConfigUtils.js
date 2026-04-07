export const DEFAULT_DATA_FRESHNESS_CONFIG = {
    price_open_min: 15,
    price_closed_min: 12 * 60,
    mixed_open_min: 30,
    mixed_closed_min: 24 * 60,
    profile_open_min: 24 * 60,
    profile_closed_min: 24 * 60 * 7,
};

const toPositiveInt = (value, fallback) => {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return fallback;
    return Math.max(1, Math.floor(parsed));
};

export const normalizeDataFreshnessConfig = (raw) => {
    const source = raw || {};
    return {
        price_open_min: toPositiveInt(source.price_open_min, DEFAULT_DATA_FRESHNESS_CONFIG.price_open_min),
        price_closed_min: toPositiveInt(source.price_closed_min, DEFAULT_DATA_FRESHNESS_CONFIG.price_closed_min),
        mixed_open_min: toPositiveInt(source.mixed_open_min, DEFAULT_DATA_FRESHNESS_CONFIG.mixed_open_min),
        mixed_closed_min: toPositiveInt(source.mixed_closed_min, DEFAULT_DATA_FRESHNESS_CONFIG.mixed_closed_min),
        profile_open_min: toPositiveInt(source.profile_open_min, DEFAULT_DATA_FRESHNESS_CONFIG.profile_open_min),
        profile_closed_min: toPositiveInt(source.profile_closed_min, DEFAULT_DATA_FRESHNESS_CONFIG.profile_closed_min),
    };
};

export const buildDataFreshnessPayload = (config) => normalizeDataFreshnessConfig(config);
