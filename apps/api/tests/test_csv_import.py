from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import Instrument, Transaction
from portfolio_tracker.modules import csv_import

FIXTURES = Path(__file__).parent / "fixtures"


def test_import_equity_tradebook_inserts_rows():
    text = (FIXTURES / "equity_tradebook.csv").read_text()
    Session = get_session_factory()

    with Session() as session:
        result = csv_import.import_csv(session, text)
        session.commit()

        assert result["format"] == "console_tradebook"
        assert result["new"] == 2
        assert result["existing"] == 0
        assert result["segment_counts"] == {"EQ": 2}
        assert result["flagged_rows"] == []
        assert result["date_min"] == "2024-01-15"
        assert result["date_max"] == "2024-02-01"
        assert session.query(Transaction).count() == 2


def test_reimport_is_idempotent():
    text = (FIXTURES / "equity_tradebook.csv").read_text()
    Session = get_session_factory()

    with Session() as session:
        csv_import.import_csv(session, text)
        session.commit()
        result = csv_import.import_csv(session, text)
        session.commit()

        assert result["new"] == 0
        assert result["existing"] == 2
        assert session.query(Transaction).count() == 2


def test_unknown_format_rejected():
    with pytest.raises(csv_import.CsvFormatError):
        csv_import.detect_format(["foo", "bar"])


def test_headers_are_normalized_for_detection():
    headers = [" Symbol ", "Trade Date", "Trade Type", "Quantity", "Price"]

    assert csv_import.detect_format(headers) == "console_tradebook"


def test_mf_tradebook_import():
    text = (FIXTURES / "mf_tradebook.csv").read_text()
    Session = get_session_factory()

    with Session() as session:
        result = csv_import.import_csv(session, text)
        session.commit()

        assert result["format"] == "console_tradebook"
        assert result["segment_counts"] == {"MF": 1}
        assert result["new"] == 1
        assert session.query(Instrument).one().instrument_type == "mf"


def test_unexpected_segment_is_imported_and_flagged():
    text = """symbol,trade_date,exchange,segment,trade_type,quantity,price,order_id
NIFTY24AUGFUT,2024-08-01,NFO,FO,buy,1,25000,O4
"""
    Session = get_session_factory()

    with Session() as session:
        result = csv_import.import_csv(session, text)
        session.commit()

        assert result["new"] == 1
        assert result["segment_counts"] == {"FO": 1}
        assert result["flagged_rows"] == ["row 2: NIFTY24AUGFUT unexpected segment FO"]
        assert session.query(Transaction).count() == 1


def test_parse_error_writes_nothing():
    text = """symbol,trade_date,segment,trade_type,quantity,price,order_id
RELIANCE,2024-01-15,EQ,buy,10,2500,O1
INFY,2024-02-01,EQ,buy,not-a-number,1500,O2
"""
    Session = get_session_factory()

    with Session() as session:
        with pytest.raises(csv_import.CsvParseError) as error:
            csv_import.import_csv(session, text)

        assert error.value.errors == ["row 3: invalid quantity 'not-a-number'"]
        assert session.query(Instrument).count() == 0
        assert session.query(Transaction).count() == 0


def test_eq_symbol_with_etf_name_is_classified_as_etf():
    text = """symbol,trade_date,exchange,segment,series,trade_type,quantity,price,order_id
NIFTYBEES,2024-01-15,NSE,EQ,EQ,buy,10,250,O5
"""
    Session = get_session_factory()

    with Session() as session:
        csv_import.import_csv(session, text)
        session.commit()

        assert session.query(Instrument).one().instrument_type == "etf"


def test_csv_endpoint_imports_multipart_file():
    from portfolio_tracker.main import create_app

    text = (FIXTURES / "equity_tradebook.csv").read_text()
    with TestClient(create_app()) as client:
        response = client.post(
            "/import/csv",
            files={"file": ("equity_tradebook.csv", text, "text/csv")},
        )

    assert response.status_code == 200
    assert response.json()["new"] == 2
