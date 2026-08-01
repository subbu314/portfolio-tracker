from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from portfolio_tracker.db.session import get_db
from portfolio_tracker.modules import portfolio, reconcile
from portfolio_tracker.schemas.portfolio import (
    AlertsResponse,
    HoldingsResponse,
    OverviewResponse,
    PerformanceResponse,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/overview", response_model=OverviewResponse)
def overview(session: Annotated[Session, Depends(get_db)]) -> dict:
    return portfolio.get_overview(session, as_of=date.today().isoformat())


@router.get("/holdings", response_model=HoldingsResponse)
def holdings(session: Annotated[Session, Depends(get_db)]) -> dict:
    rows = portfolio.get_holdings(session, as_of=date.today().isoformat())
    return {"holdings": rows}


@router.get("/alerts", response_model=AlertsResponse)
def alerts(session: Annotated[Session, Depends(get_db)]) -> dict:
    return reconcile.get_alerts(session, today=date.today().isoformat())


@router.get("/performance", response_model=PerformanceResponse)
def performance(session: Annotated[Session, Depends(get_db)]) -> dict:
    return portfolio.get_performance(session, as_of=date.today().isoformat())
