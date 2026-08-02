from fastapi.testclient import TestClient

from portfolio_tracker.main import create_app


def test_openapi_includes_auth_sync_settings_schemas():
    components = TestClient(create_app()).get("/openapi.json").json()["components"]["schemas"]
    for name in (
        "HealthResponse",
        "LoginUrlResponse",
        "ConnectedResponse",
        "AuthStatusResponse",
        "SyncResponse",
        "PricesRefreshResponse",
        "BenchmarkListResponse",
        "BenchmarkItem",
        "BenchmarkUpdateResponse",
        "CategoryUpdateResponse",
    ):
        assert name in components, name
