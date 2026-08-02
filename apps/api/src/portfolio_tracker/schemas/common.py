from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RequestTokenBody(BaseModel):
    request_token: str


class AbsoluteReturn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gain_inr: float
    gain_pct: float | None
    invested_cost: float
    current_value: float


WindowKey = Literal["ITD", "1Y", "3Y", "5Y"]


class WindowMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    absolute_pct: float | None = None
    absolute_inr: float | None = None
    xirr: float | None = None
    cagr: float | None = None
    benchmark_return: float | None = None
    absolute_excess_pp: float | None = None
    xirr_excess_pp: float | None = None
    cagr_excess_pp: float | None = None


class WindowsMap(BaseModel):
    """Fixed window keys so OpenAPI/TS keep named properties (not string index)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    ITD: WindowMetrics | None
    y1: WindowMetrics | None = Field(alias="1Y")
    y3: WindowMetrics | None = Field(alias="3Y")
    y5: WindowMetrics | None = Field(alias="5Y")


class AllocationSlice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    weight: float
