from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import BenchmarkPrice, Price
from portfolio_tracker.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"


def test_import_then_overview(monkeypatch):
    monkeypatch.setattr(
        "portfolio_tracker.modules.kite_auth.authenticated_kite",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Kite must not be called")
        ),
    )
    client = TestClient(create_app())
    csv_text = (FIXTURES / "equity_tradebook.csv").read_text()

    response = client.post(
        "/import/csv",
        files={"file": ("equity.csv", csv_text, "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["new"] == 2

    as_of = date.today().isoformat()
    Session = get_session_factory()
    with Session() as session:
        session.add_all(
            [
                Price(
                    symbol="RELIANCE.NS",
                    price_date="2024-01-15",
                    close=2500.0,
                    source="yahoo",
                ),
                Price(
                    symbol="RELIANCE.NS",
                    price_date=as_of,
                    close=3000.0,
                    source="yahoo",
                ),
                Price(
                    symbol="INFY.NS",
                    price_date="2024-02-01",
                    close=1500.0,
                    source="yahoo",
                ),
                Price(
                    symbol="INFY.NS",
                    price_date=as_of,
                    close=1800.0,
                    source="yahoo",
                ),
                BenchmarkPrice(
                    index_symbol="Nifty 500",
                    price_date="2024-01-15",
                    close=10000.0,
                ),
                BenchmarkPrice(
                    index_symbol="Nifty 500",
                    price_date=as_of,
                    close=12000.0,
                ),
            ]
        )
        session.commit()

    overview = client.get("/portfolio/overview")

    assert overview.status_code == 200
    body = overview.json()
    assert body["total_value"] > 0
    assert body["absolute"]["gain_inr"] > 0
    assert body["windows"]["ITD"] is not None

    alerts = client.get("/portfolio/alerts")
    assert alerts.status_code == 200


def test_settings_routes_manage_benchmark_and_category_overrides():
    client = TestClient(create_app())
    csv_text = (FIXTURES / "equity_tradebook.csv").read_text()
    client.post(
        "/import/csv",
        files={"file": ("equity.csv", csv_text, "text/csv")},
    )

    listed = client.get("/settings/benchmarks")

    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 2
    instrument_id = items[0]["instrument_id"]
    assert items[0]["benchmark_index"] == "Nifty 500"

    benchmark = client.put(
        f"/settings/benchmarks/{instrument_id}",
        json={"benchmark_index": "Nifty 50"},
    )
    category = client.put(
        f"/settings/categories/{instrument_id}",
        json={"category": "Large Cap"},
    )

    assert benchmark.status_code == 200
    assert benchmark.json()["source"] == "user"
    assert category.status_code == 200
    assert category.json()["mf_category"] == "Large Cap"


def test_settings_reject_unknown_benchmark_name():
    client = TestClient(create_app())
    csv_text = (FIXTURES / "equity_tradebook.csv").read_text()
    client.post(
        "/import/csv",
        files={"file": ("equity.csv", csv_text, "text/csv")},
    )
    instrument_id = client.get("/portfolio/holdings").json()["holdings"][0][
        "instrument_id"
    ]

    response = client.put(
        f"/settings/benchmarks/{instrument_id}",
        json={"benchmark_index": "Imaginary Index"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown benchmark index: Imaginary Index"
