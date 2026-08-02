from pydantic import BaseModel, ConfigDict


class PricesRefreshResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    updated: int
    failed: list[str]
    incomplete: bool


class SyncResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    holdings_count: int
    trades_appended: int
    last_sync_at: str
    prices: PricesRefreshResponse
