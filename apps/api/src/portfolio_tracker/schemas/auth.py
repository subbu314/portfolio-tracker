from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str


class LoginUrlResponse(BaseModel):
    login_url: str


class ConnectedResponse(BaseModel):
    connected: bool


class AuthStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connected: bool
    credentials_configured: bool
    last_sync_at: str | None
    last_trade_append_at: str | None
