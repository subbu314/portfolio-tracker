from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from portfolio_tracker.db.session import get_db
from portfolio_tracker.modules import portfolio, reconcile
from portfolio_tracker.schemas.portfolio import (
    AlertsResponse,
    HoldingResponse,
    HoldingsResponse,
    HoldingTransactionsResponse,
    OverviewResponse,
    PerformanceResponse,
    PortfolioSeriesResponse,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/overview", response_model=OverviewResponse)
def overview(session: Annotated[Session, Depends(get_db)]) -> dict:
    return portfolio.get_overview(session, as_of=date.today().isoformat())


@router.get("/holdings", response_model=HoldingsResponse)
def holdings(session: Annotated[Session, Depends(get_db)]) -> dict:
    rows = portfolio.get_holdings(session, as_of=date.today().isoformat())
    return {"holdings": rows}


@router.get(
    "/series",
    response_model=PortfolioSeriesResponse,
    responses={400: {"description": "Invalid window"}},
)
def portfolio_series(
    session: Annotated[Session, Depends(get_db)],
    window: Annotated[
        str,
        Query(json_schema_extra={"enum": ["ITD", "1Y", "3Y", "5Y"]}),
    ] = "ITD",
) -> dict:
    try:
        return portfolio.get_portfolio_series(
            session, as_of=date.today().isoformat(), window=window
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/holdings/{instrument_id}",
    response_model=HoldingResponse,
    responses={404: {"description": "Holding not found"}},
)
def holding_detail(
    instrument_id: int,
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    row = portfolio.get_holding(
        session, instrument_id, as_of=date.today().isoformat()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Holding not found")
    return row


@router.get(
    "/holdings/{instrument_id}/transactions",
    response_model=HoldingTransactionsResponse,
    responses={404: {"description": "Instrument not found"}},
)
def holding_transactions(
    instrument_id: int,
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    rows = portfolio.list_transactions(session, instrument_id)
    if rows is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return {"instrument_id": instrument_id, "transactions": rows}


@router.get("/alerts", response_model=AlertsResponse)
def alerts(session: Annotated[Session, Depends(get_db)]) -> dict:
    return reconcile.get_alerts(session, today=date.today().isoformat())


@router.get("/performance", response_model=PerformanceResponse)
def performance(session: Annotated[Session, Depends(get_db)]) -> dict:
    return portfolio.get_performance(session, as_of=date.today().isoformat())
