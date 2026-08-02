import json
from pathlib import Path

from portfolio_tracker.main import create_app


def test_openapi_document_is_valid_json_with_paths():
    doc = create_app().openapi()
    assert doc["openapi"].startswith("3.")
    assert "/portfolio/overview" in doc["paths"]
    assert "/import/csv" in doc["paths"]
    assert "/sync" in doc["paths"]
    # round-trip serializable
    raw = json.dumps(doc)
    assert json.loads(raw)["info"]["title"] == "Portfolio Tracker API"
