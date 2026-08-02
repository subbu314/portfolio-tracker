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


def test_overlapping_reordered_imports_without_trade_ids_are_idempotent():
    first_file = """symbol,isin,trade_date,exchange,segment,trade_type,quantity,price,fees,order_execution_time
RELIANCE,INE002A01018,2024-01-15,NSE,EQ,buy,10,2500,12.5,2024-01-15 10:00:00
INFY,INE009A01021,2024-02-01,NSE,EQ,buy,5,1500,8,2024-02-01 11:00:00
"""
    overlapping_file = """symbol,isin,trade_date,exchange,segment,trade_type,quantity,price,fees,order_execution_time
TCS,INE467B01029,2024-03-05,NSE,EQ,buy,3,4000,7,2024-03-05 12:00:00
INFY,INE009A01021,2024-02-01,NSE,EQ,buy,5,1500,8,2024-02-01 11:00:00
RELIANCE,INE002A01018,2024-01-15,NSE,EQ,buy,10,2500,12.5,2024-01-15 10:00:00
"""
    Session = get_session_factory()

    with Session() as session:
        csv_import.import_csv(session, first_file)
        session.commit()
        result = csv_import.import_csv(session, overlapping_file)
        session.commit()

        assert result["new"] == 1
        assert result["existing"] == 2
        assert session.query(Transaction).count() == 3


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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("quantity", "0"),
        ("quantity", "-1"),
        ("price", "0"),
        ("price", "-1"),
        ("fees", "-0.01"),
    ],
)
def test_non_positive_trade_values_are_rejected_without_writes(field, value):
    row = {
        "quantity": "10",
        "price": "2500",
        "fees": "12.5",
    }
    row[field] = value
    text = f"""symbol,trade_date,segment,trade_type,quantity,price,fees,order_id
RELIANCE,2024-01-15,EQ,buy,{row["quantity"]},{row["price"]},{row["fees"]},O1
"""
    Session = get_session_factory()

    with Session() as session:
        with pytest.raises(csv_import.CsvParseError) as error:
            csv_import.import_csv(session, text)

        expected_rule = "must be non-negative" if field == "fees" else "must be positive"
        assert error.value.errors == [f"row 2: {field} {expected_rule}"]
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


def test_financial_year_label_uses_indian_fy():
    assert csv_import.financial_year_label("2024-03-31") == "FY2023-24"
    assert csv_import.financial_year_label("2024-04-01") == "FY2024-25"
    assert csv_import.financial_years_spanned("2024-01-04", "2024-03-28") == ["FY2023-24"]
    assert csv_import.financial_years_spanned("2024-04-02", "2025-03-11") == ["FY2024-25"]


def test_batch_import_accepts_multiple_files_and_skips_duplicates():
    eq = (FIXTURES / "equity_tradebook.csv").read_text()
    mf = (FIXTURES / "mf_tradebook.csv").read_text()
    Session = get_session_factory()
    with Session() as session:
        result = csv_import.import_csv_batch(
            session,
            [
                ("equity.csv", eq),
                ("mf.csv", mf),
                ("equity-again.csv", eq),
            ],
        )
        session.commit()
        assert result["summary"]["accepted"] == 3
        assert result["summary"]["rejected"] == 0
        assert result["summary"]["new"] == 3  # 2 equity + 1 mf; third file all existing
        assert result["summary"]["existing"] == 2
        assert result["files"][0]["ok"] is True
        assert result["files"][0]["financial_years"]
        assert session.query(Transaction).count() == 3


def test_batch_import_rejects_bad_file_keeps_good_files():
    eq = (FIXTURES / "equity_tradebook.csv").read_text()
    Session = get_session_factory()
    with Session() as session:
        result = csv_import.import_csv_batch(
            session,
            [
                ("equity.csv", eq),
                ("bad.csv", "not,a,tradebook\n1,2,3\n"),
            ],
        )
        session.commit()
        assert result["summary"]["accepted"] == 1
        assert result["summary"]["rejected"] == 1
        bad = result["files"][1]
        assert bad["ok"] is False
        assert bad["code"] == "csv_format"
        assert bad["action"] == csv_import.REIMPORT_ACTION
        assert "import this file again" in bad["action"].lower()
        assert session.query(Transaction).count() == 2


def test_import_route_multi_file_and_wrong_input_action():
    from portfolio_tracker.main import create_app

    client = TestClient(create_app())
    eq = (FIXTURES / "equity_tradebook.csv").read_bytes()
    bad = b"foo,bar\n1,2\n"
    response = client.post(
        "/import/csv",
        files=[
            ("files", ("equity.csv", eq, "text/csv")),
            ("files", ("bad.csv", bad, "text/csv")),
        ],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["accepted"] == 1
    assert body["summary"]["rejected"] == 1
    assert body["files"][1]["action"] == csv_import.REIMPORT_ACTION

    single_bad = client.post(
        "/import/csv",
        files={"file": ("bad.csv", bad, "text/csv")},
    )
    assert single_bad.status_code == 400
    detail = single_bad.json()["detail"]
    assert isinstance(detail, dict)
    assert detail["action"] == csv_import.REIMPORT_ACTION
