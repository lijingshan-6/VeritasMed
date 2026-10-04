"""Export FastAPI OpenAPI schema to openapi.json at project root.

Used when REST API models or routes change; then regenerate frontend types:

    python scripts/export_openapi.py
    cd frontend && npm run generate-types
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from medrag.api.app import app  # noqa: E402
from medrag.api.models import ChunkOut  # noqa: E402

OUT = ROOT / "openapi.json"


def main() -> None:
    schema = app.openapi()
    # ChunkOut travels inside the WebSocket answer, so no REST route references it.
    schema["components"]["schemas"]["ChunkOut"] = ChunkOut.model_json_schema(
        ref_template="#/components/schemas/{model}")
    OUT.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[openapi] wrote {OUT} ({len(schema.get('paths', {}))} paths)")


if __name__ == "__main__":
    main()
