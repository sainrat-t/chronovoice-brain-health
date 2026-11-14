"""Write the OpenAPI description of the API for the frontend types.

The frontend types are generated from it, so they mirror the backend models exactly
(CLAUDE.md, TypeScript rules). Run from backend/, then `npm run gen:api` in frontend/:

    uv run python -m scripts.export_openapi
"""

from __future__ import annotations

import json
from pathlib import Path

from app.main import create_app

TARGET = Path(__file__).resolve().parents[2] / "frontend" / "src" / "api" / "openapi.json"


def main() -> None:
    schema = create_app().openapi()
    TARGET.write_text(json.dumps(schema, indent=1, sort_keys=True) + "\n")
    print(f"OpenAPI written to {TARGET}")


if __name__ == "__main__":
    main()
