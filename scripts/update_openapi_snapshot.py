"""
Update the committed OpenAPI snapshot when API changes are intentional.

Usage:
    python scripts/update_openapi_snapshot.py

Run this whenever you intentionally change the API (add/remove/rename endpoints,
change request/response schemas). Commit the updated snapshot alongside your code.

The snapshot is used by tests/unit/contract/test_openapi_snapshot.py to detect
unintentional API contract changes.
"""

import json
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app  # noqa: E402

SNAPSHOT_PATH = Path(__file__).parent.parent / "tests" / "snapshots" / "openapi_snapshot.json"


def main():
    SNAPSHOT_PATH.parent.mkdir(exist_ok=True)

    schema = app.openapi()

    SNAPSHOT_PATH.write_text(json.dumps(schema, indent=2, sort_keys=True))

    path_count = len(schema.get("paths", {}))
    component_count = len(schema.get("components", {}).get("schemas", {}))

    print(f"Updated: {SNAPSHOT_PATH}")
    print(f"  Routes    : {path_count}")
    print(f"  Components: {component_count}")
    print(f"  API title : {schema.get('info', {}).get('title', '?')}")
    print(f"  API version: {schema.get('info', {}).get('version', '?')}")


if __name__ == "__main__":
    main()
