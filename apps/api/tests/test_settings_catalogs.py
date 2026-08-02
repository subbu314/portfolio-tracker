from fastapi.testclient import TestClient

from portfolio_tracker.main import create_app
from portfolio_tracker.modules.benchmarks import DEFAULT_BY_CATEGORY
from portfolio_tracker.modules.index_tickers import INDEX_TICKERS


def test_settings_catalogs_match_backend_constants():
    client = TestClient(create_app())
    response = client.get("/settings/catalogs")
    assert response.status_code == 200
    body = response.json()
    assert body["mf_categories"] == list(DEFAULT_BY_CATEGORY.keys())
    assert body["benchmark_indexes"] == list(INDEX_TICKERS.keys())
