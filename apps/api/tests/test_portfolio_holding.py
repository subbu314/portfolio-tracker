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


def _seed_one(session):
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
                trade_date="2024-01-10",
                side="buy",
                quantity=5,
                price=2000.0,
                fees=10.0,
                source="csv",
                dedupe_key="h1",
            ),
            Transaction(
                instrument_id=instrument.id,
                trade_date="2024-02-01",
                side="buy",
                quantity=5,
                price=2100.0,
                fees=0.0,
                source="api",
                dedupe_key="h2",
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
                price_date="2024-06-01",
                close=12000.0,
            ),
        ]
    )
    session.commit()
    return instrument


def test_get_holding_and_transactions_http():
    client = TestClient(create_app())
    Session = get_session_factory()
    with Session() as session:
        instrument = _seed_one(session)
        instrument_id = instrument.id

    missing = client.get("/portfolio/holdings/99999")
    assert missing.status_code == 404

    holding = client.get(f"/portfolio/holdings/{instrument_id}")
    assert holding.status_code == 200
    body = holding.json()
    assert body["instrument_id"] == instrument_id
    assert body["symbol"] == "RELIANCE"
    assert body["qty"] == 10

    txs = client.get(f"/portfolio/holdings/{instrument_id}/transactions")
    assert txs.status_code == 200
    rows = txs.json()["transactions"]
    assert len(rows) == 2
    assert rows[0]["trade_date"] == "2024-01-10"
    assert rows[0]["side"] == "buy"
    assert rows[0]["quantity"] == 5
    assert rows[0]["price"] == 2000.0
    assert rows[0]["fees"] == 10.0
    assert rows[0]["amount"] == 10000.0
    assert rows[0]["source"] == "csv"
    assert rows[1]["source"] == "api"


def test_transactions_404_unknown_instrument():
    client = TestClient(create_app())
    assert client.get("/portfolio/holdings/99999/transactions").status_code == 404


def test_transactions_same_trade_date_ordered_by_id():
    """Two txs on same trade_date must sort by id asc (not side/source)."""
    client = TestClient(create_app())
    Session = get_session_factory()
    with Session() as session:
        instrument = Instrument(
            symbol="TCS",
            isin="INE467B01029",
            instrument_type="equity",
            exchange="NSE",
            yahoo_symbol="TCS.NS",
        )
        session.add(instrument)
        session.flush()
        # Insert higher-id row first so API must apply id tie-break.
        session.add(
            Transaction(
                instrument_id=instrument.id,
                trade_date="2024-03-15",
                side="sell",
                quantity=3,
                price=3500.0,
                fees=5.0,
                source="api",
                dedupe_key="same-day-2",
            )
        )
        session.add(
            Transaction(
                instrument_id=instrument.id,
                trade_date="2024-03-15",
                side="buy",
                quantity=10,
                price=3400.0,
                fees=0.0,
                source="csv",
                dedupe_key="same-day-1",
            )
        )
        session.commit()
        instrument_id = instrument.id

    rows = client.get(f"/portfolio/holdings/{instrument_id}/transactions").json()[
        "transactions"
    ]
    assert len(rows) == 2
    assert rows[0]["trade_date"] == rows[1]["trade_date"] == "2024-03-15"
    assert rows[0]["id"] < rows[1]["id"]
    assert rows[0]["side"] == "sell"
    assert rows[0]["source"] == "api"
    assert rows[1]["side"] == "buy"
    assert rows[1]["source"] == "csv"
