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


def _seed_with_window_prices(session):
    instrument = _seed_itd(session)
    session.add(
        Price(
            symbol="RELIANCE.NS",
            price_date="2023-06-02",
            close=2200.0,
            source="yahoo",
        )
    )
    session.add(
        BenchmarkPrice(
            index_symbol="Nifty 500",
            price_date="2023-06-02",
            close=11000.0,
        )
    )
    session.commit()
    return instrument


def test_overview_rolling_1y_available_3y_5y_null():
    Session = get_session_factory()
    with Session() as session:
        _seed_with_window_prices(session)

        overview = portfolio.get_overview(session, as_of="2024-06-01")

        assert overview["windows"]["1Y"] is not None
        assert abs(overview["windows"]["1Y"]["absolute_pct"] - (2 / 11)) < 1e-9
        assert abs(overview["windows"]["1Y"]["absolute_excess_pp"] - (100 / 11)) < 1e-9
        assert overview["windows"]["1Y"]["xirr"] is not None
        assert overview["windows"]["1Y"]["xirr_excess_pp"] is not None
        assert overview["windows"]["3Y"] is None
        assert overview["windows"]["5Y"] is None


def test_holdings_include_windows():
    Session = get_session_factory()
    with Session() as session:
        _seed_with_window_prices(session)

        rows = portfolio.get_holdings(session, as_of="2024-06-01")

        assert "windows" in rows[0]
        assert rows[0]["windows"]["ITD"] is not None
        assert rows[0]["windows"]["1Y"] is not None
        assert rows[0]["windows"]["3Y"] is None


def test_performance_has_contributors_and_windows():
    Session = get_session_factory()
    with Session() as session:
        _seed_with_window_prices(session)
        perf = portfolio.get_performance(session, as_of="2024-06-01")
        assert perf["default_window"] == "ITD"
        assert "1Y" in perf["windows_available"]
        assert len(perf["contributors"]) >= 1
        assert "windows" in perf["holdings"][0]
        assert perf["overview"]["windows"]["1Y"] is not None


def test_rolling_windows_are_null_when_opening_position_price_is_missing():
    Session = get_session_factory()
    with Session() as session:
        instrument = _seed_itd(session)
        session.query(Price).filter(Price.price_date < "2024-06-01").delete()
        session.query(HoldingsSnapshot).delete()
        session.add(
            Transaction(
                instrument_id=instrument.id,
                trade_date="2023-09-01",
                side="buy",
                quantity=1,
                price=2300.0,
                fees=0,
                source="csv",
                dedupe_key="missing-opening-price-buy",
            )
        )
        session.commit()

        holdings = portfolio.get_holdings(session, as_of="2024-06-01")
        overview = portfolio.get_overview(session, as_of="2024-06-01")

        assert holdings[0]["qty"] == 11
        assert holdings[0]["windows"]["1Y"] is None
        assert overview["windows"]["1Y"] is None


def test_rolling_windows_use_in_window_cost_when_opening_quantity_is_zero():
    Session = get_session_factory()
    with Session() as session:
        instrument = Instrument(
            symbol="NEW",
            isin="INE000000001",
            instrument_type="equity",
            exchange="NSE",
            yahoo_symbol="NEW.NS",
        )
        session.add(instrument)
        session.flush()
        for trade_date, side, quantity, price, dedupe_key in (
            ("2022-01-01", "buy", 1, 500.0, "zero-opening-old-buy"),
            ("2022-02-01", "sell", 1, 500.0, "zero-opening-old-sell"),
            ("2024-01-01", "buy", 10, 100.0, "zero-opening-current-buy"),
        ):
            session.add(
                Transaction(
                    instrument_id=instrument.id,
                    trade_date=trade_date,
                    side=side,
                    quantity=quantity,
                    price=price,
                    fees=0,
                    source="csv",
                    dedupe_key=dedupe_key,
                )
            )
        session.add(
            Price(
                symbol="NEW.NS",
                price_date="2024-06-01",
                close=120.0,
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
        session.add_all(
            [
                BenchmarkPrice(
                    index_symbol="Nifty 500",
                    price_date="2023-06-02",
                    close=100.0,
                ),
                BenchmarkPrice(
                    index_symbol="Nifty 500",
                    price_date="2024-01-01",
                    close=100.0,
                ),
                BenchmarkPrice(
                    index_symbol="Nifty 500",
                    price_date="2024-06-01",
                    close=110.0,
                ),
            ]
        )
        session.commit()

        holdings = portfolio.get_holdings(session, as_of="2024-06-01")
        overview = portfolio.get_overview(session, as_of="2024-06-01")

        assert abs(holdings[0]["windows"]["1Y"]["absolute_pct"] - 0.2) < 1e-9
        assert abs(overview["windows"]["1Y"]["absolute_pct"] - 0.2) < 1e-9


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


def test_benchmark_price_fallback_respects_as_of_cap():
    """Regression: on_or_after fallback must not use prices after as_of."""
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
                trade_date="2024-03-10",
                side="buy",
                quantity=10,
                price=2000.0,
                fees=0,
                source="csv",
                dedupe_key="future-bench-t1",
            )
        )
        session.add(
            Price(
                symbol="RELIANCE.NS",
                price_date="2024-03-12",
                close=2100.0,
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
                price_date="2024-03-20",
                close=12000.0,
            )
        )
        session.commit()

        rows = portfolio.get_holdings(session, as_of="2024-03-12")

        assert len(rows) == 1
        holding = rows[0]
        assert holding["incomplete"] is True
        assert holding["benchmark_return"] is None
        assert holding["windows"]["ITD"]["benchmark_return"] is None
        assert holding["xirr_excess_pp"] is None


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
