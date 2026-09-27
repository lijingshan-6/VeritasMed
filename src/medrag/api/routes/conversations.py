"""Bundled actual Ask conversations; no retrieval or model call during replay."""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[4] / "data/demo/conversations"
router = APIRouter(prefix="/api/conversations", tags=["saved conversations"])


@router.get("/examples")
def examples():
    path = ROOT / "catalogue.json"
    return {"examples": json.loads(path.read_text(encoding="utf-8")) if path.exists() else [],
            "mode": "saved_inference"}


@router.get("/examples/{example_id}")
def replay(example_id: str):
    entry = next((e for e in examples()["examples"] if e["id"] == example_id), None)
    if entry is None:
        raise HTTPException(404, "No bundled conversation with this ID.")
    path = (ROOT / entry["file"]).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise HTTPException(409, "Saved conversation file unavailable.")
    return FileResponse(path, media_type="application/json")
