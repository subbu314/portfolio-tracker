import json
from pathlib import Path

from portfolio_tracker.main import create_app

OPENAPI_PATH = Path(__file__).resolve().parents[2] / "web" / "openapi.json"


def test_openapi_document_is_valid_json_with_paths():
    doc = create_app().openapi()
    assert doc["openapi"].startswith("3.")
    assert "/portfolio/overview" in doc["paths"]
    assert "/import/csv" in doc["paths"]
    assert "/sync" in doc["paths"]
    # round-trip serializable
    raw = json.dumps(doc)
    assert json.loads(raw)["info"]["title"] == "Portfolio Tracker API"


def test_committed_openapi_matches_live_app():
    live = create_app().openapi()
    committed = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert committed == live, (
        "apps/web/openapi.json is stale. From repo root run: npm run generate:api"
    )
