"""Replay controlled workflow comparisons; optional live use of the shared tools."""

import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException

from medrag.agent.research_workflow import LiteratureTask, run_research
from medrag.verification.gateway import FlashGateway
from medrag.verification.scifact import object_hash
from .audit import _slots

ROOT = Path(__file__).resolve().parents[4]
DATA = ROOT / "data/demo/research"
router = APIRouter(prefix="/api/research", tags=["research comparison"])


class ResearchRequest(LiteratureTask):
    method: Literal["direct_reader", "autonomous_tools", "structured_workflow"] = (
        "structured_workflow"
    )


@router.get("/examples")
def examples():
    path = DATA / "catalogue.json"
    return {
        "examples": json.loads(path.read_text(encoding="utf8")) if path.exists() else [],
        "scope": "Named-paper fact queries in a fixed candidate corpus; model judgments are evaluated against public annotations.",
    }


@router.get("/examples/{case_id}")
def replay(case_id: str):
    catalogue = examples()["examples"]
    if case_id not in {e["id"] for e in catalogue}:
        raise HTTPException(404, "Unknown saved comparison")
    record = json.loads((DATA / f"{case_id}.json").read_text(encoding="utf8"))
    if record["provenance"]["input_sha256"] != object_hash(record["input"]) or record["provenance"][
        "results_sha256"
    ] != object_hash(record["results"]):
        raise HTTPException(409, "Saved comparison does not match its original input/results.")
    return record


@router.get("/results")
def results():
    path = DATA / "results.json"
    if not path.exists():
        return {
            "status": "not_published",
            "note": "Experiments are not complete; no scores published yet.",
        }
    return json.loads(path.read_text(encoding="utf8"))


@router.post("")
def live(request: ResearchRequest):
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, "Three research/audit requests are already running")
    try:
        try:
            model = FlashGateway()
        except Exception:
            raise HTTPException(503, "Configure the Flash profile in local .env") from None
        task = LiteratureTask.model_validate(request.model_dump(exclude={"method"}))
        return {
            "input": task.model_dump(),
            "result": run_research(task, model, request.method),
            "mode": "live",
            "note": "Only provided documents/tools; six model-call budget includes verification. Not saved on server.",
        }
    finally:
        _slots.release()
