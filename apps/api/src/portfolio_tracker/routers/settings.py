from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from portfolio_tracker.db.models import Instrument
from portfolio_tracker.db.session import get_db
from portfolio_tracker.modules import benchmarks
from portfolio_tracker.modules.benchmarks import DEFAULT_BY_CATEGORY
from portfolio_tracker.modules.index_tickers import INDEX_TICKERS
from portfolio_tracker.schemas.settings import (
    BenchmarkBody,
    BenchmarkListResponse,
    BenchmarkUpdateResponse,
    CatalogsResponse,
    CategoryBody,
    CategoryUpdateResponse,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/catalogs", response_model=CatalogsResponse)
def catalogs() -> dict:
    return {
        "mf_categories": list(DEFAULT_BY_CATEGORY.keys()),
        "benchmark_indexes": list(INDEX_TICKERS.keys()),
    }


@router.get("/benchmarks", response_model=BenchmarkListResponse)
def list_benchmarks(
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    items = []
    for instrument in session.query(Instrument).all():
        row = benchmarks.ensure_benchmark_map(session, instrument)
        items.append(
            {
                "instrument_id": instrument.id,
                "symbol": instrument.symbol,
                "instrument_type": instrument.instrument_type,
                "mf_category": instrument.mf_category,
                "needs_category": bool(instrument.needs_category),
                "benchmark_index": row.benchmark_index,
                "source": row.source,
            }
        )
    return {"items": items}


@router.put(
    "/benchmarks/{instrument_id}",
    response_model=BenchmarkUpdateResponse,
    responses={
        400: {"description": "Unknown benchmark index"},
        404: {"description": "Instrument not found"},
    },
)
def put_benchmark(
    instrument_id: int,
    body: BenchmarkBody,
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    if session.get(Instrument, instrument_id) is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    try:
        row = benchmarks.set_benchmark_override(
            session,
            instrument_id,
            body.benchmark_index,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "instrument_id": instrument_id,
        "benchmark_index": row.benchmark_index,
        "source": row.source,
    }


@router.put(
    "/categories/{instrument_id}",
    response_model=CategoryUpdateResponse,
    responses={404: {"description": "Instrument not found"}},
)
def put_category(
    instrument_id: int,
    body: CategoryBody,
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    try:
        instrument = benchmarks.set_category_override(
            session,
            instrument_id,
            body.category,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "instrument_id": instrument.id,
        "mf_category": instrument.mf_category,
    }
