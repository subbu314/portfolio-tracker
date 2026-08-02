from typing import Literal

from pydantic import BaseModel, ConfigDict

from portfolio_tracker.schemas.common import (
    AbsoluteReturn,
    AllocationSlice,
    WindowKey,
    WindowsMap,
)


class HoldingResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

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
    mf_category: str | None
    windows: WindowsMap


class HoldingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    holdings: list[HoldingResponse]


class TransactionRowResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    trade_date: str
    side: str
    quantity: float
    price: float
    fees: float
    amount: float
    source: str


class HoldingTransactionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instrument_id: int
    transactions: list[TransactionRowResponse]


class OverviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: str
    total_value: float
    absolute: AbsoluteReturn
    xirr: float | None
    cagr: float | None
    benchmark_return: float | None
    absolute_excess_pp: float | None
    xirr_excess_pp: float | None
    cagr_excess_pp: float | None
    allocation: list[AllocationSlice]
    incomplete: bool
    windows: WindowsMap


class ContributorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    absolute_excess_pp: float | None
    xirr_excess_pp: float | None
    cagr_excess_pp: float | None
    value: float | None
    weight: float
    windows: WindowsMap


class PerformanceResponse(OverviewResponse):
    contributors: list[ContributorResponse]
    holdings: list[HoldingResponse]
    windows_available: list[WindowKey]
    default_window: WindowKey


class SeriesPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str
    portfolio_return: float | None = None
    benchmark_return: float | None = None
    holding_return: float | None = None


class PortfolioSeriesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window: WindowKey
    metric: Literal["absolute"]
    as_of: str
    start: str | None
    available: bool
    incomplete: bool
    points: list[SeriesPoint]


class HoldingSeriesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instrument_id: int
    window: WindowKey
    metric: Literal["absolute"]
    benchmark: str
    as_of: str
    start: str | None
    available: bool
    incomplete: bool
    points: list[SeriesPoint]


class ReconcileDiff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instrument_id: int
    symbol: str
    holdings_qty: float
    tx_qty: float
    delta: float


class GapAlert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suggested_from: str
    suggested_to: str
    message: str


class AlertsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token_connected: bool
    credentials_configured: bool
    reconcile: list[ReconcileDiff]
    reconcile_message: str | None = None
    gap: GapAlert | None
