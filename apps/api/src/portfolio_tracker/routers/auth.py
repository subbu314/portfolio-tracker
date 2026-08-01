from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from portfolio_tracker.db.session import get_db
from portfolio_tracker.modules import kite_auth
from portfolio_tracker.schemas.common import RequestTokenBody

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login-url")
def login_url() -> dict[str, str]:
    try:
        return {"login_url": kite_auth.get_login_url()}
    except kite_auth.KiteConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/callback")
def callback(body: RequestTokenBody, session: Session = Depends(get_db)) -> dict[str, bool]:
    try:
        return kite_auth.exchange_request_token(session, body.request_token)
    except kite_auth.KiteConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except kite_auth.KiteAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/status")
def status(session: Session = Depends(get_db)) -> dict:
    return kite_auth.get_auth_status(session)


@router.post("/logout")
def logout(session: Session = Depends(get_db)) -> dict[str, bool]:
    kite_auth.clear_token(session)
    return {"connected": False}
