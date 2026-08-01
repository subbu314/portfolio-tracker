from typing import TypedDict


class HoldingPublic(TypedDict):
    instrument_id: int
    symbol: str
    instrument_type: str
    qty: float
    avg_price: float
    ltp: float | None
    value: float | None
    absolute_pct: float | None
    absolute_inr: float | None
    xirr: float | None
    cagr: float | None
    benchmark: str
    benchmark_return: float | None
    absolute_excess_pp: float | None
    xirr_excess_pp: float | None
    cagr_excess_pp: float | None
    incomplete: bool
    needs_category: bool
    windows: dict


class HoldingComputed(TypedDict):
    """Internal row used while assembling overview/performance."""

    public: HoldingPublic
    benchmark_cagr: float | None
