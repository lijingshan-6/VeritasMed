"""Local, source-bound auditing and replay of actual saved research calls."""
from functools import lru_cache
import json
from pathlib import Path
from threading import BoundedSemaphore
from typing import Literal

from fastapi import APIRouter, HTTPException

from medrag.verification.answer_audit import AuditInput, audit_answer, text_hash
from medrag.verification.gateway import FlashGateway
from medrag.verification.ragtruth import prepare
from medrag.verification.scifact import object_hash

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "data/verification/ragtruth_v1/run01"
CACHE = ROOT / ".benchmark-runtime/ragtruth"
router = APIRouter(prefix="/api/audit", tags=["answer audit"])
_slots = BoundedSemaphore(3)


def saved_rows():
    path = RUN / "predictions.jsonl"
    if not path.exists():
        return []
    # A benchmark can still be appending its current row. Expose complete records only.
    lines = path.read_text(encoding="utf8").splitlines(keepends=True)
    return [json.loads(line) for line in lines if line.endswith("\n")]


@lru_cache(maxsize=1)
def saved_cases():
    try:
        cases, manifest = prepare(CACHE)
        expected = json.loads((RUN / "manifest.json").read_text(encoding="utf8"))
    except FileNotFoundError:
        raise HTTPException(409, "Download the pinned sources first: python scripts/verification/answer_benchmark.py download") from None
    except ValueError:
        raise HTTPException(409, "Source cache failed its content check; restore the pinned files.") from None
    if object_hash(manifest) != object_hash(expected):
        raise HTTPException(409, "Saved research inputs do not match the source cache.")
    return {case["id"]: case for case in cases}


@router.get("/examples")
def examples():
    rows = saved_rows()
    grouped = {}
    for row in rows:
        case_id = row["case_id"]
        entry = grouped.setdefault(case_id, {"id": case_id, "strategies": {}})
        entry["strategies"][row["strategy"]] = row["audit"]["status"]
    return {"examples": sorted(grouped.values(), key=lambda r: int(r["id"])),
            "sources_downloaded": all((CACHE / name).exists() for name in ("response.jsonl", "source_info.jsonl")),
            "description": "Actual saved Flash calls on RAGTruth training answers; public nonmedical development data."}


@router.get("/examples/{response_id}")
def replay(response_id: str, strategy: Literal["direct", "split"] = "direct"):
    row = next((r for r in saved_rows() if r["case_id"] == response_id and r["strategy"] == strategy), None)
    if row is None:
        raise HTTPException(404, "No saved audit for this answer and strategy.")
    case = saved_cases().get(response_id)
    if case is None:
        raise HTTPException(409, "Unknown research answer.")
    item = case["input"].model_copy(update={"strategy": strategy})
    result = row["audit"]
    if result["answer_sha256"] != text_hash(item.answer) or result["source_hashes"] != {s.id: text_hash(s.text) for s in item.sources}:
        raise HTTPException(409, "Audit anchors belong to different input texts.")
    return {"input": item.model_dump(), "audit": result, "mode": "saved",
            "provenance": {"dataset": "RAGTruth", "split": "train", "response_id": response_id,
                           "run": "ragtruth_v1/run01", "note": "Saved inference, no new model call. Human error labels are not model inputs."}}


@router.post("")
def live_audit(item: AuditInput):
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, "Three audits are already running; try again after one finishes.")
    try:
        try:
            gateway = FlashGateway()
        except Exception:
            raise HTTPException(503, "Configure the Flash profile and key in the local .env before running a live audit.") from None
        return {"input": item.model_dump(), "audit": audit_answer(item, gateway), "mode": "live",
                "provenance": {"note": "New Flash inference on the supplied texts. Input and output are not saved on the server."}}
    finally:
        _slots.release()
