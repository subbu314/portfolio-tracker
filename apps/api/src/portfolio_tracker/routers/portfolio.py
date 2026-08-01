from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from portfolio_tracker.db.session import get_db
from portfolio_tracker.modules import portfolio, reconcile

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/overview")
def overview(session: Annotated[Session, Depends(get_db)]) -> dict:
    return portfolio.get_overview(session, as_of=date.today().isoformat())


@router.get("/holdings")
def holdings(session: Annotated[Session, Depends(get_db)]) -> dict:
    rows = portfolio.get_holdings(session, as_of=date.today().isoformat())
    return {"holdings": rows}


@router.get("/alerts")
def alerts(session: Annotated[Session, Depends(get_db)]) -> dict:
    return reconcile.get_alerts(session, today=date.today().isoformat())


@router.get("/performance")
def performance(session: Annotated[Session, Depends(get_db)]) -> dict:
    return portfolio.get_performance(session, as_of=date.today().isoformat())
