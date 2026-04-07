import re


def normalize_ticker_symbol(raw_symbol: str | None) -> str:
    value = str(raw_symbol or "").strip().upper()
    if not value:
        return ""
    value = value.split()[0]
    occ_match = re.match(r"^([A-Z]{1,6})\d{6}[CP]\d+", value)
    if occ_match:
        return occ_match.group(1)
    return value


def canonical_instrument_key(
    *,
    ticker: str | None,
    sec_type: str | None = "STK",
    expiry: str | None = None,
    right: str | None = None,
    strike: float | int | str | None = None,
) -> str:
    symbol = normalize_ticker_symbol(ticker)
    security_type = str(sec_type or "STK").strip().upper() or "STK"
    if security_type in {"OPT", "FOP"}:
        expiry_norm = re.sub(r"[^0-9]", "", str(expiry or ""))[:8]
        right_norm = str(right or "").strip().upper()[:1]
        try:
            strike_norm = f"{float(strike):.3f}".rstrip("0").rstrip(".")
        except (TypeError, ValueError):
            strike_norm = ""
        return ":".join(
            [
                security_type,
                symbol or "UNKNOWN",
                expiry_norm or "UNKNOWN",
                right_norm or "U",
                strike_norm or "UNKNOWN",
            ]
        )
    return f"{security_type}:{symbol or 'UNKNOWN'}"
