from app.services.instrument_identity import canonical_instrument_key, normalize_ticker_symbol


def test_normalize_ticker_symbol_handles_occ_style_option_symbol():
    assert normalize_ticker_symbol("amd260620C00180000") == "AMD"


def test_canonical_instrument_key_for_stock():
    assert canonical_instrument_key(ticker=" aapl ", sec_type="stk") == "STK:AAPL"


def test_canonical_instrument_key_for_option():
    key = canonical_instrument_key(
        ticker="AMD",
        sec_type="OPT",
        expiry="2026-06-20",
        right="c",
        strike=180,
    )
    assert key == "OPT:AMD:20260620:C:180"
