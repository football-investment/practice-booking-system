"""
Contract tests — OpenAPI schema snapshot

Detects any unintentional API contract change: renamed/removed endpoints,
changed request/response schemas, or modified operation metadata.

No DB or server required — FastAPI generates the schema from registered
routes via app.openapi() without triggering lifespan or database connections.

When you intentionally change the API, run:
    python scripts/update_openapi_snapshot.py
Then commit the updated snapshot alongside your code changes.
"""

import json
from pathlib import Path

from app.main import app

SNAPSHOT_PATH = (
    Path(__file__).parent.parent.parent / "snapshots" / "openapi_snapshot.json"
)


class TestOpenAPISnapshot:
    """Contract: full API schema unchanged from committed snapshot."""

    def test_snapshot_file_exists(self):
        assert SNAPSHOT_PATH.exists(), (
            f"OpenAPI snapshot missing at {SNAPSHOT_PATH}. "
            "Run: python scripts/update_openapi_snapshot.py"
        )

    def test_api_contract_unchanged(self):
        current = app.openapi()
        snapshot = json.loads(SNAPSHOT_PATH.read_text())
        assert current == snapshot, (
            "API schema has changed since the last committed snapshot. "
            "If this change is intentional, update the snapshot:\n"
            "    python scripts/update_openapi_snapshot.py\n"
            "Then commit the updated tests/snapshots/openapi_snapshot.json."
        )

    def test_schema_has_paths(self):
        paths = app.openapi().get("paths", {})
        assert len(paths) > 0, "OpenAPI schema has no paths registered"

    def test_schema_has_version_info(self):
        info = app.openapi().get("info", {})
        assert "title" in info, "OpenAPI schema missing 'title' in info"
        assert "version" in info, "OpenAPI schema missing 'version' in info"

    def test_schema_has_minimum_route_count(self):
        # api-module-integrity gate requires ≥71 routes; actual count is 496
        path_count = len(app.openapi().get("paths", {}))
        assert path_count >= 71, (
            f"Route count dropped to {path_count} (minimum: 71). "
            "Check that all routers are still included in app/main.py."
        )
