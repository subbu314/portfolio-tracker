from fastapi.testclient import TestClient

from portfolio_tracker.main import create_app


def test_openapi_includes_portfolio_response_schemas():
    schema = TestClient(create_app()).get("/openapi.json").json()
    components = schema["components"]["schemas"]
    for name in (
        "OverviewResponse",
        "HoldingsResponse",
        "HoldingResponse",
        "PerformanceResponse",
        "AlertsResponse",
        "WindowMetrics",
        "AbsoluteReturn",
    ):
        assert name in components, name

    overview_path = schema["paths"]["/portfolio/overview"]["get"]
    assert "OverviewResponse" in overview_path["responses"]["200"]["content"][
        "application/json"
    ]["schema"].get("$ref", "") or overview_path["responses"]["200"]["content"][
        "application/json"
    ][
        "schema"
    ] == {
        "$ref": "#/components/schemas/OverviewResponse"
    }


def test_openapi_windows_map_has_fixed_properties():
    schema = TestClient(create_app()).get("/openapi.json").json()
    windows = schema["components"]["schemas"]["WindowsMap"]
    props = set(windows["properties"].keys())
    assert props == {"ITD", "1Y", "3Y", "5Y"}
    assert set(windows["required"]) == {"ITD", "1Y", "3Y", "5Y"}
    assert windows.get("additionalProperties") is False

    overview_windows = schema["components"]["schemas"]["OverviewResponse"]["properties"][
        "windows"
    ]
    assert overview_windows.get("$ref") == "#/components/schemas/WindowsMap"


def test_openapi_includes_holding_detail_paths():
    schema = TestClient(create_app()).get("/openapi.json").json()
    assert "/portfolio/holdings/{instrument_id}" in schema["paths"]
    assert "/portfolio/holdings/{instrument_id}/transactions" in schema["paths"]
    components = schema["components"]["schemas"]
    assert "HoldingTransactionsResponse" in components
    assert "TransactionRowResponse" in components
