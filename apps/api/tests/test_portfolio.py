from fastapi.testclient import TestClient

from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import (
    BenchmarkMap,
    BenchmarkPrice,
    HoldingsSnapshot,
    Instrument,
    Price,
    Transaction,
)
from portfolio_tracker.modules import portfolio
from portfolio_tracker.main import create_app


def _seed_itd(session):
    instrument = Instrument(
        symbol="RELIANCE",
        isin="INE002A01018",
        instrument_type="equity",
        exchange="NSE",
        yahoo_symbol="RELIANCE.NS",
    )
    session.add(instrument)
    session.flush()
    session.add(
        Transaction(
            instrument_id=instrument.id,
            trade_date="2022-01-03",
            side="buy",
            quantity=10,
            price=2000.0,
            fees=0,
            source="csv",
            dedupe_key="t1",
        )
    )
    session.add(
        HoldingsSnapshot(
            instrument_id=instrument.id,
            quantity=10,
            avg_price=2000.0,
            as_of="2024-06-01",
        )
    )
    session.add(
        Price(
            symbol="RELIANCE.NS",
            price_date="2022-01-03",
            close=2000.0,
            source="yahoo",
        )
    )
    session.add(
        Price(
            symbol="RELIANCE.NS",
            price_date="2024-06-01",
            close=2600.0,
            source="yahoo",
        )
    )
    session.add(
        BenchmarkMap(
            instrument_id=instrument.id,
            benchmark_index="Nifty 500",
            source="default",
        )
    )
    session.add(
        BenchmarkPrice(
            index_symbol="Nifty 500",
            price_date="2022-01-03",
            close=10000.0,
        )
    )
    session.add(
        BenchmarkPrice(
            index_symbol="Nifty 500",
            price_date="2024-06-01",
            close=12000.0,
        )
    )
    session.commit()
    return instrument


def test_overview_itd_core_metrics():
    Session = get_session_factory()
    with Session() as session:
        _seed_itd(session)

        overview = portfolio.get_overview(session, as_of="2024-06-01")

        assert overview["total_value"] == 26000.0
        assert overview["absolute"]["gain_inr"] == 6000.0
        assert overview["xirr"] is not None
        assert overview["cagr"] is not None
        assert overview["absolute_excess_pp"] is not None
        assert overview["xirr_excess_pp"] is not None
        assert overview["cagr_excess_pp"] is not None
        assert overview["windows"]["ITD"] is not None


def test_holdings_itd_xirr_excess_uses_benchmark_xirr():
    Session = get_session_factory()
    with Session() as session:
        _seed_itd(session)

        rows = portfolio.get_holdings(session, as_of="2024-06-01")

        assert len(rows) == 1
        holding = rows[0]
        assert holding["xirr"] is not None
        assert holding["xirr_excess_pp"] is not None
        assert abs(holding["xirr_excess_pp"]) < 50.0


def test_portfolio_http_endpoints_expose_itd_data():
    Session = get_session_factory()
    with Session() as session:
        _seed_itd(session)
    client = TestClient(create_app())

    overview_response = client.get("/portfolio/overview")
    holdings_response = client.get("/portfolio/holdings")

    assert overview_response.status_code == 200
    assert overview_response.json()["windows"]["ITD"] is not None
    assert holdings_response.status_code == 200
    holding = holdings_response.json()["holdings"][0]
    assert holding["windows"]["ITD"] is not None
    assert "_benchmark_cagr" not in holding
