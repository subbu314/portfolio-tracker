from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from portfolio_tracker.db.session import get_db
from portfolio_tracker.modules import kite_auth, kite_sync
from portfolio_tracker.modules.prices import refresh_prices
from portfolio_tracker.schemas.sync import SyncResponse

router = APIRouter(tags=["sync"])
RECONNECT_MESSAGE = "Reconnect Zerodha — access token missing or expired"
SessionDep = Annotated[Session, Depends(get_db)]


@router.post(
    "/sync",
    response_model=SyncResponse,
    responses={401: {"description": "Kite reconnection required"}},
)
def sync(session: SessionDep) -> dict:
    if not kite_auth.is_token_valid(session):
        raise HTTPException(status_code=401, detail=RECONNECT_MESSAGE)
    try:
        result = kite_sync.sync_all(session)
    except kite_auth.KiteAuthError as exc:
        raise HTTPException(status_code=401, detail=RECONNECT_MESSAGE) from exc
    return {**result, "prices": refresh_prices(session)}
