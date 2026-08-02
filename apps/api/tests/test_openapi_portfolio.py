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
