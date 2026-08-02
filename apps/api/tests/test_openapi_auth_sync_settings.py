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


def test_openapi_includes_settings_catalogs():
    schema = TestClient(create_app()).get("/openapi.json").json()
    assert "/settings/catalogs" in schema["paths"]
    assert "CatalogsResponse" in schema["components"]["schemas"]
