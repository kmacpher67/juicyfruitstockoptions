from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class FRStatus(str, Enum):
    FOLLOWUP_REVIEW = "F-R"


class FRReviewState(str, Enum):
    ACTIVE = "Active"
    REVIEWED = "Reviewed"
    ASSIGNED = "Assigned"


class FRStrategyType(str, Enum):
    BULL_PUT_RATIO_SPREAD_1X2 = "BULL_PUT_RATIO_SPREAD_1X2"
    DEEP_ITM_CALL_SUBSTITUTION_PMCC = "DEEP_ITM_CALL_SUBSTITUTION_PMCC"


class FRLegSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class FRLegOptionType(str, Enum):
    PUT = "PUT"
    CALL = "CALL"


class FRLegMoneyness(str, Enum):
    ITM = "ITM"
    OTM = "OTM"
    ATM = "ATM"


class FRLeg(BaseModel):
    side: FRLegSide
    option_type: FRLegOptionType
    quantity: int = Field(default=1, ge=1)
    strike: float = Field(..., gt=0)
    expiration: date
    delta: float | None = Field(default=None, ge=-1.0, le=1.0)
    moneyness: FRLegMoneyness | None = None


class FRCreateRequest(BaseModel):
    status: FRStatus = FRStatus.FOLLOWUP_REVIEW
    review_state: FRReviewState = FRReviewState.ACTIVE
    ticker: str = Field(..., min_length=1, max_length=16)
    trade_date: date
    strategy_type: FRStrategyType
    legs: list[FRLeg] = Field(..., min_length=1)
    net_credit: float
    underlying_last_price: float | None = None
    last_mtm_sync_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def _validate_strategy_legs(self):
        validate_strategy_legs(self.strategy_type, self.legs)
        return self


class FRUpdateRequest(BaseModel):
    status: FRStatus | None = None
    review_state: FRReviewState | None = None
    ticker: str | None = Field(default=None, min_length=1, max_length=16)
    trade_date: date | None = None
    strategy_type: FRStrategyType | None = None
    legs: list[FRLeg] | None = None
    net_credit: float | None = None
    underlying_last_price: float | None = None
    last_mtm_sync_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)


class FRItem(BaseModel):
    fr_id: str
    status: FRStatus
    review_state: FRReviewState
    ticker: str
    trade_date: date
    strategy_type: FRStrategyType
    legs: list[FRLeg]
    net_credit: float
    effective_entry_price: float
    underlying_last_price: float | None = None
    last_mtm_sync_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class FRListResponse(BaseModel):
    count: int
    rows: list[FRItem]


def validate_strategy_legs(strategy_type: FRStrategyType, legs: list[FRLeg]) -> None:
    if strategy_type == FRStrategyType.BULL_PUT_RATIO_SPREAD_1X2:
        _validate_ratio_spread_1x2(legs)
        return

    if strategy_type == FRStrategyType.DEEP_ITM_CALL_SUBSTITUTION_PMCC:
        _validate_deep_itm_call_substitution(legs)
        return

    raise ValueError(f"Unsupported strategy_type: {strategy_type}")


def compute_effective_entry_price(strategy_type: FRStrategyType, legs: list[FRLeg], net_credit: float) -> float:
    if strategy_type == FRStrategyType.BULL_PUT_RATIO_SPREAD_1X2:
        short_put_strikes = {
            leg.strike
            for leg in legs
            if leg.option_type == FRLegOptionType.PUT and leg.side == FRLegSide.SHORT
        }
        if len(short_put_strikes) != 1:
            raise ValueError("Ratio spread requires a single short put strike for effective entry computation")
        entry_strike = next(iter(short_put_strikes))
        return float(entry_strike - net_credit)

    if strategy_type == FRStrategyType.DEEP_ITM_CALL_SUBSTITUTION_PMCC:
        long_call_strikes = {
            leg.strike
            for leg in legs
            if leg.option_type == FRLegOptionType.CALL and leg.side == FRLegSide.LONG
        }
        if len(long_call_strikes) != 1:
            raise ValueError("ITM substitution requires a single long call strike for effective entry computation")
        entry_strike = next(iter(long_call_strikes))
        return float(entry_strike - net_credit)

    raise ValueError(f"Unsupported strategy_type: {strategy_type}")


def _validate_ratio_spread_1x2(legs: list[FRLeg]) -> None:
    if not legs:
        raise ValueError("legs are required")

    if any(leg.option_type != FRLegOptionType.PUT for leg in legs):
        raise ValueError("Ratio spread requires PUT legs only")

    long_qty_itm = 0
    short_qty_otm = 0
    short_strikes = set()

    for leg in legs:
        if leg.moneyness is None:
            raise ValueError("Ratio spread requires moneyness for each leg")
        if leg.side == FRLegSide.LONG:
            if leg.moneyness != FRLegMoneyness.ITM:
                raise ValueError("Ratio spread long put leg must be ITM")
            long_qty_itm += leg.quantity
        elif leg.side == FRLegSide.SHORT:
            if leg.moneyness != FRLegMoneyness.OTM:
                raise ValueError("Ratio spread short put legs must be OTM")
            short_qty_otm += leg.quantity
            short_strikes.add(leg.strike)

    if long_qty_itm != 1:
        raise ValueError("Ratio spread requires exactly 1 long ITM put")
    if short_qty_otm != 2:
        raise ValueError("Ratio spread requires exactly 2 short OTM puts")
    if len(short_strikes) != 1:
        raise ValueError("Ratio spread requires short OTM puts at one strike")


def _validate_deep_itm_call_substitution(legs: list[FRLeg]) -> None:
    if not legs:
        raise ValueError("legs are required")

    if any(leg.option_type != FRLegOptionType.CALL for leg in legs):
        raise ValueError("ITM substitution requires CALL legs only")

    long_legs = [leg for leg in legs if leg.side == FRLegSide.LONG]
    short_legs = [leg for leg in legs if leg.side == FRLegSide.SHORT]

    long_qty = sum(leg.quantity for leg in long_legs)
    short_qty = sum(leg.quantity for leg in short_legs)
    if long_qty != 1:
        raise ValueError("ITM substitution requires exactly 1 long call")
    if short_qty != 1:
        raise ValueError("ITM substitution requires exactly 1 short OTM call")

    long_leg = long_legs[0]
    short_leg = short_legs[0]

    if long_leg.delta is None or long_leg.delta < 0.80:
        raise ValueError("ITM substitution long call requires delta >= 0.80")

    if short_leg.moneyness != FRLegMoneyness.OTM:
        raise ValueError("ITM substitution short call must be OTM")

    if short_leg.expiration >= long_leg.expiration:
        raise ValueError("ITM substitution short call must be shorter-term than long call")
