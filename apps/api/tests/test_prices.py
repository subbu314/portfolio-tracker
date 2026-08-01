import json
from pathlib import Path
from unittest.mock import MagicMock, call

from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import BenchmarkPrice, Instrument, Price
from portfolio_tracker.modules.prices import service as price_service
from portfolio_tracker.modules.prices.amfi import AmfiNavProvider
from portfolio_tracker.modules.prices.yahoo import INDEX_TICKERS, YahooFinanceProvider


FIXTURES = Path(__file__).parent / "fixtures"


def test_index_tickers_single_source():
    from portfolio_tracker.modules.index_tickers import INDEX_TICKERS as a
    from portfolio_tracker.modules.prices.yahoo import INDEX_TICKERS as b

    assert a is b
    assert "Nifty 500" in a


def test_yahoo_provider_maps_history():
    provider = YahooFinanceProvider(client=MagicMock())
    provider._fetch_history = MagicMock(  # type: ignore[method-assign]
        return_value=[("2024-01-15", 2500.0), ("2024-01-16", 2510.0)]
    )

    rows = provider.get_history("RELIANCE.NS", "2024-01-15", "2024-01-16")

    assert rows == [("2024-01-15", 2500.0), ("2024-01-16", 2510.0)]


def test_amfi_provider_resolves_isin_and_filters_history():
    sample = json.loads((FIXTURES / "amfi_sample.json").read_text())
    http_get = MagicMock(side_effect=[[{"schemeCode": "123"}], sample])
    provider = AmfiNavProvider(http_get=http_get)

    rows = provider.get_history_by_isin("INF090I01239", "2024-03-01", "2024-03-01")

    assert rows == [("2024-03-01", 99.50)]
    assert http_get.call_args_list == [
        call("https://api.mfapi.in/mf/search?q=INF090I01239"),
        call("https://api.mfapi.in/mf/123"),
    ]


def test_amfi_provider_resolves_isin_via_scheme_list_when_search_empty():
    sample = json.loads((FIXTURES / "amfi_sample.json").read_text())
    scheme_list = [
        {
            "schemeCode": 120828,
            "schemeName": "quant Small Cap Fund - Growth Option - Direct Plan",
            "isinGrowth": "INF966L01689",
            "isinDivReinvestment": None,
        }
    ]
    http_get = MagicMock(side_effect=[[], scheme_list, sample])
    provider = AmfiNavProvider(http_get=http_get)

    rows = provider.get_history_by_isin("INF966L01689", "2024-03-01", "2024-03-01")

    assert rows == [("2024-03-01", 99.50)]
    assert http_get.call_args_list == [
        call("https://api.mfapi.in/mf/search?q=INF966L01689"),
        call("https://api.mfapi.in/mf"),
        call("https://api.mfapi.in/mf/120828"),
    ]


def test_amfi_provider_resolves_flexi_cap_category():
    sample = json.loads((FIXTURES / "amfi_sample.json").read_text())
    provider = AmfiNavProvider(
        http_get=MagicMock(side_effect=[[{"schemeCode": "123"}], sample])
    )

    assert provider.resolve_category("INF090I01239") == ("Flexi Cap", "123")


def test_refresh_prices_caches_equity_and_mf():
    Session = get_session_factory()
    with Session() as session:
        equity = Instrument(
            symbol="RELIANCE",
            isin="INE002A01018",
            instrument_type="equity",
            exchange="NSE",
            yahoo_symbol="RELIANCE.NS",
        )
        mutual_fund = Instrument(
            symbol="INF090I01239",
            isin="INF090I01239",
            instrument_type="mf",
            exchange=None,
        )
        session.add_all([equity, mutual_fund])
        session.commit()

        yahoo = MagicMock(spec=YahooFinanceProvider)
        yahoo.get_ltp.return_value = 2600.0
        yahoo.get_history.return_value = [("2024-01-15", 2500.0)]
        amfi = MagicMock(spec=AmfiNavProvider)
        amfi.get_history_by_isin.return_value = [("2024-03-01", 99.5)]
        amfi.resolve_category.return_value = ("Flexi Cap", "123")

        result = price_service.refresh_prices(
            session,
            as_of="2024-06-01",
            yahoo=yahoo,
            amfi=amfi,
            history_start="2024-01-01",
            benchmark_names=[],
        )
        session.commit()

        prices = session.query(Price).order_by(Price.symbol, Price.price_date).all()
        assert result == {"updated": 3, "failed": [], "incomplete": False}
        assert [(row.symbol, row.price_date, row.close, row.source) for row in prices] == [
            ("INF090I01239", "2024-03-01", 99.5, "amfi"),
            ("RELIANCE.NS", "2024-01-15", 2500.0, "yahoo"),
            ("RELIANCE.NS", "2024-06-01", 2600.0, "yahoo"),
        ]
        assert mutual_fund.scheme_code == "123"
        assert mutual_fund.mf_category == "Flexi Cap"
        assert mutual_fund.mf_category_source == "amfi"
        assert mutual_fund.needs_category == 0


def test_refresh_prices_tries_bse_after_empty_nse_history():
    Session = get_session_factory()
    with Session() as session:
        instrument = Instrument(
            symbol="RELIANCE",
            isin="INE002A01018",
            instrument_type="equity",
            exchange="NSE",
        )
        session.add(instrument)
        session.commit()
        yahoo = MagicMock(spec=YahooFinanceProvider)
        yahoo.get_history.side_effect = [[], [("2024-01-15", 2490.0)]]
        yahoo.get_ltp.return_value = 2500.0

        result = price_service.refresh_prices(
            session,
            as_of="2024-01-16",
            yahoo=yahoo,
            amfi=MagicMock(spec=AmfiNavProvider),
            history_start="2024-01-01",
            benchmark_names=[],
        )

        assert result["incomplete"] is False
        assert yahoo.get_history.call_args_list == [
            call("RELIANCE.NS", "2024-01-01", "2024-01-16"),
            call("RELIANCE.BO", "2024-01-01", "2024-01-16"),
        ]
        assert instrument.yahoo_symbol == "RELIANCE.BO"


def test_refresh_prices_falls_back_when_nse_ltp_is_missing():
    Session = get_session_factory()
    with Session() as session:
        instrument = Instrument(
            symbol="RELIANCE",
            isin="INE002A01018",
            instrument_type="equity",
            exchange="NSE",
        )
        session.add(instrument)
        session.commit()
        yahoo = MagicMock(spec=YahooFinanceProvider)
        yahoo.get_history.side_effect = [
            [("2024-01-15", 2490.0)],
            [("2024-01-15", 2500.0)],
        ]
        yahoo.get_ltp.side_effect = [None, 2510.0]

        result = price_service.refresh_prices(
            session,
            as_of="2024-01-16",
            yahoo=yahoo,
            amfi=MagicMock(spec=AmfiNavProvider),
            history_start="2024-01-01",
            benchmark_names=[],
        )

        assert result["incomplete"] is False
        assert instrument.yahoo_symbol == "RELIANCE.BO"
        assert yahoo.get_ltp.call_args_list == [call("RELIANCE.NS"), call("RELIANCE.BO")]


def test_refresh_prices_uses_latest_cached_date_for_incremental_history():
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
        session.add(
            Price(
                symbol="RELIANCE.NS",
                price_date="2024-05-31",
                close=2550.0,
                source="yahoo",
            )
        )
        session.commit()
        yahoo = MagicMock(spec=YahooFinanceProvider)
        yahoo.get_history.return_value = [("2024-06-01", 2600.0)]
        yahoo.get_ltp.return_value = 2600.0

        price_service.refresh_prices(
            session,
            as_of="2024-06-01",
            yahoo=yahoo,
            amfi=MagicMock(spec=AmfiNavProvider),
            history_start="2018-01-01",
            benchmark_names=[],
        )

        yahoo.get_history.assert_called_once_with(
            "RELIANCE.NS", "2024-05-31", "2024-06-01"
        )
        assert session.query(Price).count() == 2


def test_refresh_prices_updates_ltp_when_same_day_history_is_empty():
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
        session.add(
            Price(
                symbol="RELIANCE.NS",
                price_date="2024-06-01",
                close=2550.0,
                source="yahoo",
            )
        )
        session.commit()
        yahoo = MagicMock(spec=YahooFinanceProvider)
        yahoo.get_history.return_value = []
        yahoo.get_ltp.return_value = 2600.0

        result = price_service.refresh_prices(
            session,
            as_of="2024-06-01",
            yahoo=yahoo,
            amfi=MagicMock(spec=AmfiNavProvider),
            history_start="2018-01-01",
            benchmark_names=[],
        )

        assert result == {"updated": 1, "failed": [], "incomplete": False}
        yahoo.get_history.assert_called_once_with(
            "RELIANCE.NS", "2024-06-01", "2024-06-01"
        )
        yahoo.get_ltp.assert_called_once_with("RELIANCE.NS")
        price = session.query(Price).one()
        assert price.close == 2600.0


def test_refresh_prices_tries_bse_after_stored_nse_symbol_fails():
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
        session.commit()
        yahoo = MagicMock(spec=YahooFinanceProvider)
        yahoo.get_history.side_effect = [[], [("2024-01-15", 2490.0)]]
        yahoo.get_ltp.side_effect = [None, 2500.0]

        result = price_service.refresh_prices(
            session,
            as_of="2024-01-16",
            yahoo=yahoo,
            amfi=MagicMock(spec=AmfiNavProvider),
            history_start="2024-01-01",
            benchmark_names=[],
        )

        assert result["incomplete"] is False
        assert yahoo.get_history.call_args_list == [
            call("RELIANCE.NS", "2024-01-01", "2024-01-16"),
            call("RELIANCE.BO", "2024-01-01", "2024-01-16"),
        ]
        assert yahoo.get_ltp.call_args_list == [
            call("RELIANCE.NS"),
            call("RELIANCE.BO"),
        ]
        assert instrument.yahoo_symbol == "RELIANCE.BO"


def test_refresh_prices_reuses_stored_amfi_scheme_code():
    Session = get_session_factory()
    with Session() as session:
        instrument = Instrument(
            symbol="INF090I01239",
            isin="INF090I01239",
            instrument_type="mf",
            exchange=None,
            scheme_code="123",
        )
        session.add(instrument)
        session.commit()
        amfi = MagicMock(spec=AmfiNavProvider)
        amfi.get_history.return_value = [("2024-03-01", 99.5)]
        amfi.resolve_category.return_value = ("Flexi Cap", "123")

        result = price_service.refresh_prices(
            session,
            as_of="2024-03-01",
            yahoo=MagicMock(spec=YahooFinanceProvider),
            amfi=amfi,
            history_start="2024-01-01",
            benchmark_names=[],
        )

        assert result == {"updated": 1, "failed": [], "incomplete": False}
        amfi.get_history.assert_called_once_with("123", "2024-01-01", "2024-03-01")
        amfi.find_scheme_code_by_isin.assert_not_called()
        amfi.resolve_category.assert_called_once_with("INF090I01239", "123")
        assert instrument.scheme_code == "123"
        assert instrument.mf_category == "Flexi Cap"


def test_refresh_prices_caches_locked_benchmark_ticker():
    Session = get_session_factory()
    with Session() as session:
        yahoo = MagicMock(spec=YahooFinanceProvider)
        yahoo.get_history.return_value = [("2024-01-15", 21000.0)]

        result = price_service.refresh_prices(
            session,
            as_of="2024-01-16",
            yahoo=yahoo,
            amfi=MagicMock(spec=AmfiNavProvider),
            history_start="2024-01-01",
            benchmark_names=["Nifty 50"],
        )

        yahoo.get_history.assert_called_once_with(
            INDEX_TICKERS["Nifty 50"], "2024-01-01", "2024-01-16"
        )
        benchmark = session.query(BenchmarkPrice).one()
        assert result["updated"] == 1
        assert (benchmark.index_symbol, benchmark.close) == ("Nifty 50", 21000.0)


def test_refresh_prices_reports_missing_amfi_nav_as_failed():
    Session = get_session_factory()
    with Session() as session:
        session.add(
            Instrument(
                symbol="SOME MF",
                isin="INF000000001",
                instrument_type="mf",
            )
        )
        session.commit()

        amfi = MagicMock(spec=AmfiNavProvider)
        amfi.get_history_by_isin.return_value = []
        amfi.resolve_category.return_value = (None, None)
        yahoo = MagicMock(spec=YahooFinanceProvider)

        result = price_service.refresh_prices(
            session,
            as_of="2026-08-01",
            yahoo=yahoo,
            amfi=amfi,
            benchmark_names=[],
        )

        assert result["updated"] == 0
        assert result["incomplete"] is True
        assert any("INF000000001" in row or "SOME MF" in row for row in result["failed"])
        assert any(
            "AMFI" in row or "amfi" in row.lower() or "NAV" in row
            for row in result["failed"]
        )


def test_refresh_prices_uses_yahoo_alias_for_renamed_equity():
    Session = get_session_factory()
    with Session() as session:
        session.add(
            Instrument(
                symbol="ZOMATO",
                isin="INE758T01015",
                instrument_type="equity",
                exchange="NSE",
            )
        )
        session.commit()

        yahoo = MagicMock(spec=YahooFinanceProvider)

        def history(symbol, start, end):
            if symbol == "ETERNAL.NS":
                return [("2026-08-01", 250.0)]
            return []

        def ltp(symbol):
            return 255.0 if symbol == "ETERNAL.NS" else None

        yahoo.get_history.side_effect = history
        yahoo.get_ltp.side_effect = ltp
        amfi = MagicMock(spec=AmfiNavProvider)

        result = price_service.refresh_prices(
            session,
            as_of="2026-08-01",
            yahoo=yahoo,
            amfi=amfi,
            history_start="2026-01-01",
            benchmark_names=[],
        )

        instrument = session.query(Instrument).one()
        assert result["incomplete"] is False
        assert result["failed"] == []
        assert instrument.yahoo_symbol == "ETERNAL.NS"
        assert session.query(Price).filter(Price.symbol == "ETERNAL.NS").count() >= 1
