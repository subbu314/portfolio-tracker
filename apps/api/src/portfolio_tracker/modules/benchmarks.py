from __future__ import annotations

from sqlalchemy.orm import Session

from portfolio_tracker.db.models import BenchmarkMap, Instrument
from portfolio_tracker.modules.index_tickers import INDEX_TICKERS

DEFAULT_BY_CATEGORY: dict[str, str] = {
    "Flexi Cap": "Nifty 500",
    "Large Cap": "Nifty 100",
    "Mid Cap": "Nifty Midcap 150",
    "Small Cap": "Nifty Smallcap 250",
}

MF_CATEGORY_CHOICES: list[str] = list(DEFAULT_BY_CATEGORY.keys())


def default_benchmark_for(instrument: Instrument) -> str:
    if instrument.instrument_type == "mf":
        if instrument.mf_category and instrument.mf_category in DEFAULT_BY_CATEGORY:
            return DEFAULT_BY_CATEGORY[instrument.mf_category]
        return "Nifty 500"
    # stocks / unknown ETFs
    if instrument.instrument_type == "etf" and instrument.mf_category:
        # optional: underlying index name stored in mf_category for index ETFs
        return instrument.mf_category
    return "Nifty 500"


def ensure_benchmark_map(session: Session, instrument: Instrument) -> BenchmarkMap:
    row = session.get(BenchmarkMap, instrument.id)
    if row is None:
        row = BenchmarkMap(
            instrument_id=instrument.id,
            benchmark_index=default_benchmark_for(instrument),
            source="default",
        )
        session.add(row)
        session.flush()
        if instrument.instrument_type == "mf" and not instrument.mf_category:
            instrument.needs_category = 1
        return row
    if row.source != "user":
        row.benchmark_index = default_benchmark_for(instrument)
        row.source = "default"
    return row


def set_benchmark_override(session: Session, instrument_id: int, benchmark_index: str) -> BenchmarkMap:
    if benchmark_index not in INDEX_TICKERS:
        raise ValueError(f"Unknown benchmark index: {benchmark_index}")
    row = session.get(BenchmarkMap, instrument_id)
    if row is None:
        row = BenchmarkMap(instrument_id=instrument_id, benchmark_index=benchmark_index, source="user")
        session.add(row)
    else:
        row.benchmark_index = benchmark_index
        row.source = "user"
    session.flush()
    return row


def set_category_override(session: Session, instrument_id: int, category: str) -> Instrument:
    inst = session.get(Instrument, instrument_id)
    if inst is None:
        raise ValueError(f"Instrument {instrument_id} not found")
    inst.mf_category = category
    inst.mf_category_source = "user"
    inst.needs_category = 0
    ensure_benchmark_map(session, inst)
    return inst


def portfolio_blended_benchmark_return(weights_and_returns: list[tuple[float, float]]) -> float:
    if not weights_and_returns:
        return 0.0
    return sum(w * r for w, r in weights_and_returns)
