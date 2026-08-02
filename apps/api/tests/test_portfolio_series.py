import pytest
from fastapi.testclient import TestClient

from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import (
    BenchmarkMap,
    BenchmarkPrice,
    Instrument,
    Price,
    Transaction,
)
from portfolio_tracker.main import create_app
from portfolio_tracker.modules import portfolio


def _seed_series(session):
    instrument = Instrument(
        symbol="RELIANCE",
        isin="INE002A01018",
        instrument_type="equity",
        exchange="NSE",
        yahoo_symbol="RELIANCE.NS",
    )
    session.add(instrument)
    session.flush()
    session.add_all(
        [
            Transaction(
                instrument_id=instrument.id,
                trade_date="2022-01-03",
                side="buy",
                quantity=10,
                price=2000.0,
                fees=0,
                source="csv",
                dedupe_key="s1",
            ),
            Price(
                symbol="RELIANCE.NS",
                price_date="2022-01-03",
                close=2000.0,
                source="yahoo",
            ),
            Price(
                symbol="RELIANCE.NS",
                price_date="2023-06-02",
                close=2200.0,
                source="yahoo",
            ),
            Price(
                symbol="RELIANCE.NS",
                price_date="2024-06-01",
                close=2600.0,
                source="yahoo",
            ),
            BenchmarkMap(
                instrument_id=instrument.id,
                benchmark_index="Nifty 500",
                source="default",
            ),
            BenchmarkPrice(
                index_symbol="Nifty 500",
                price_date="2022-01-03",
                close=10000.0,
            ),
            BenchmarkPrice(
                index_symbol="Nifty 500",
                price_date="2023-06-02",
                close=11000.0,
            ),
            BenchmarkPrice(
                index_symbol="Nifty 500",
                price_date="2024-06-01",
                close=12000.0,
            ),
        ]
    )
    session.commit()
    return instrument


def test_portfolio_series_itd_absolute():
    Session = get_session_factory()
    with Session() as session:
        _seed_series(session)
        result = portfolio.get_portfolio_series(
            session, as_of="2024-06-01", window="ITD"
        )
    assert result["available"] is True
    assert result["metric"] == "absolute"
    assert result["start"] == "2022-01-03"
    by_date = {p["date"]: p for p in result["points"]}
    assert by_date["2022-01-03"]["portfolio_return"] == 0.0
    assert abs(by_date["2024-06-01"]["portfolio_return"] - 0.3) < 1e-9
    assert abs(by_date["2024-06-01"]["benchmark_return"] - 0.2) < 1e-9


@pytest.mark.parametrize("has_as_of_quote", [False, True])
def test_portfolio_series_uses_window_start_with_forward_filled_price(
    has_as_of_quote,
):
    Session = get_session_factory()
    with Session() as session:
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
                dedupe_key="window-start-forward-fill",
            )
        )
        prices = [
            Price(
                symbol="RELIANCE.NS",
                price_date="2023-06-01",
                close=2000.0,
                source="yahoo",
            ),
            Price(
                symbol="RELIANCE.NS",
                price_date="2023-12-01",
                close=2200.0,
                source="yahoo",
            ),
        ]
        if has_as_of_quote:
            prices.append(
                Price(
                    symbol="RELIANCE.NS",
                    price_date="2024-06-01",
                    close=2400.0,
                    source="yahoo",
                )
            )
        session.add_all(prices)
        session.commit()

        result = portfolio.get_portfolio_series(
            session, as_of="2024-06-01", window="1Y"
        )

    assert result["start"] == "2023-06-02"
    assert result["points"][0]["date"] == "2023-06-02"
    assert result["points"][0]["portfolio_return"] == 0.0


def test_portfolio_series_http_and_unavailable_window():
    client = TestClient(create_app())
    Session = get_session_factory()
    with Session() as session:
        _seed_series(session)

    ok = client.get("/portfolio/series", params={"window": "ITD"})
    assert ok.status_code == 200
    assert ok.json()["metric"] == "absolute"
    assert len(ok.json()["points"]) >= 2

    # Holding starts 2022; as_of today may make 5Y available — force via service:
    Session = get_session_factory()
    with Session() as session:
        # inception 2022-01-03; window 5Y from 2022-06-01 starts 2017 → N/A
        result = portfolio.get_portfolio_series(
            session, as_of="2022-06-01", window="5Y"
        )
    assert result["available"] is False
    assert result["points"] == []


def test_portfolio_series_rejects_bad_window():
    client = TestClient(create_app())
    response = client.get("/portfolio/series", params={"window": "YTD"})
    assert response.status_code == 400
