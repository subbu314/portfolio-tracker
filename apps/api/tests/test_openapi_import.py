from fastapi.testclient import TestClient

from portfolio_tracker.main import create_app


def test_openapi_includes_import_schemas():
    openapi = TestClient(create_app()).get("/openapi.json").json()
    components = openapi["components"]["schemas"]
    for name in (
        "ImportResultResponse",
        "BatchImportResultResponse",
        "FileImportOkResponse",
        "FileImportErrResponse",
        "ImportBadDetail",
        "ImportBadErrorResponse",
    ):
        assert name in components, name

    bad_response_schema = openapi["paths"]["/import/csv"]["post"]["responses"]["400"][
        "content"
    ]["application/json"]["schema"]
    assert bad_response_schema == {
        "$ref": "#/components/schemas/ImportBadErrorResponse"
    }
