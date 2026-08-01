from fastapi.testclient import TestClient

from portfolio_tracker.main import create_app


def test_openapi_includes_import_schemas():
    components = TestClient(create_app()).get("/openapi.json").json()["components"]["schemas"]
    for name in (
        "ImportResultResponse",
        "BatchImportResultResponse",
        "FileImportOkResponse",
        "FileImportErrResponse",
        "ImportBadDetail",
    ):
        assert name in components, name
