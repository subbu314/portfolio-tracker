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


def test_portfolio_series_skips_incomplete_base_day_to_avoid_return_spike():
    Session = get_session_factory()
    with Session() as session:
        first = Instrument(
            symbol="FIRST",
            isin="FIRSTISIN",
            instrument_type="equity",
            exchange="NSE",
            yahoo_symbol="FIRST.NS",
        )
        second = Instrument(
            symbol="SECOND",
            isin="SECONDISIN",
            instrument_type="equity",
            exchange="NSE",
            yahoo_symbol="SECOND.NS",
        )
        session.add_all([first, second])
        session.flush()
        session.add_all(
            [
                Transaction(
                    instrument_id=first.id,
                    trade_date="2024-01-01",
                    side="buy",
                    quantity=1,
                    price=100.0,
                    fees=0,
                    source="csv",
                    dedupe_key="first-buy",
                ),
                Transaction(
                    instrument_id=second.id,
                    trade_date="2024-01-01",
                    side="buy",
                    quantity=1,
                    price=100.0,
                    fees=0,
                    source="csv",
                    dedupe_key="second-buy",
                ),
                Price(
                    symbol="FIRST.NS",
                    price_date="2024-01-01",
                    close=100.0,
                    source="yahoo",
                ),
                Price(
                    symbol="FIRST.NS",
                    price_date="2024-01-10",
                    close=100.0,
                    source="yahoo",
                ),
                Price(
                    symbol="SECOND.NS",
                    price_date="2024-01-10",
                    close=100.0,
                    source="yahoo",
                ),
            ]
        )
        session.commit()
        result = portfolio.get_portfolio_series(
            session, as_of="2024-01-10", window="ITD"
        )

    assert result["incomplete"] is True
    assert [point["date"] for point in result["points"]] == ["2024-01-10"]
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


def test_holding_series_itd_absolute():
    Session = get_session_factory()
    with Session() as session:
        instrument = _seed_series(session)
        result = portfolio.get_holding_series(
            session,
            instrument.id,
            as_of="2024-06-01",
            window="ITD",
        )
    assert result is not None
    assert result["available"] is True
    assert result["benchmark"] == "Nifty 500"
    by_date = {p["date"]: p for p in result["points"]}
    assert by_date["2022-01-03"]["holding_return"] == 0.0
    assert abs(by_date["2024-06-01"]["holding_return"] - 0.3) < 1e-9
    assert abs(by_date["2024-06-01"]["benchmark_return"] - 0.2) < 1e-9


@pytest.mark.parametrize("has_as_of_quote", [False, True])
def test_holding_series_uses_window_start_with_forward_filled_price(
    has_as_of_quote,
):
    Session = get_session_factory()
    with Session() as session:
        instrument = _seed_series(session)
        session.query(Price).filter(
            Price.symbol == "RELIANCE.NS",
            Price.price_date == "2023-06-02",
        ).update({"price_date": "2023-06-01"})
        if not has_as_of_quote:
            session.query(Price).filter(
                Price.symbol == "RELIANCE.NS",
                Price.price_date == "2024-06-01",
            ).delete()
        session.commit()
        result = portfolio.get_holding_series(
            session,
            instrument.id,
            as_of="2024-06-01",
            window="1Y",
        )

    assert result is not None
    assert result["start"] == "2023-06-02"
    assert result["points"][0]["date"] == "2023-06-02"
    assert result["points"][0]["holding_return"] == 0.0


def test_holding_series_http():
    client = TestClient(create_app())
    Session = get_session_factory()
    with Session() as session:
        instrument = _seed_series(session)
        instrument_id = instrument.id

    response = client.get(
        f"/portfolio/holdings/{instrument_id}/series",
        params={"window": "ITD"},
    )
    assert response.status_code == 200
    assert response.json()["instrument_id"] == instrument_id
    assert client.get("/portfolio/holdings/99999/series").status_code == 404
