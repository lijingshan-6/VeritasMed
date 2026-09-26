"""Local, source-bound auditing and replay of actual saved research calls."""
from functools import lru_cache
import json
from pathlib import Path
from threading import BoundedSemaphore
from typing import Literal

from fastapi import APIRouter, HTTPException

from medrag.verification.answer_audit import AuditInput, audit_answer, text_hash
from medrag.verification.context_audit import audit_context
from medrag.verification.quote_audit import QuoteAuditRequest, audit_quotes
from medrag.verification.gateway import FlashGateway
from medrag.verification.ragtruth import prepare
from medrag.verification.scifact import object_hash, read_jsonl

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "data/verification/ragtruth_v1/run01"
CONTEXT_RUN = ROOT / "data/verification/context_v1/run01"
QUOTE_RUN = ROOT / "data/verification/quote_v2/run01"
CACHE = ROOT / ".benchmark-runtime/ragtruth"
MEDICAL = ROOT / "data/demo/medical/audit.json"
router = APIRouter(prefix="/api/audit", tags=["answer audit"])
_slots = BoundedSemaphore(3)


def saved_rows():
    path = RUN / "predictions.jsonl"
    if not path.exists():
        return []
    # A benchmark can still be appending its current row. Expose complete records only.
    lines = path.read_text(encoding="utf8").splitlines(keepends=True)
    rows = [json.loads(line) for line in lines if line.endswith("\n")]
    context_path = CONTEXT_RUN / "predictions.jsonl"
    if context_path.exists():
        rows.extend({**row, "run": "context_v1/run01"} for line in context_path.read_text(encoding="utf8").splitlines(keepends=True)
                    if line.endswith("\n") for row in [json.loads(line)]
                    if row["group"] != "repeat" and row["strategy"] in ("direct", "context"))
    quote_path = QUOTE_RUN / "predictions.jsonl"
    if quote_path.exists():
        rows.extend({**row, "run": "quote_v2/run01"} for line in quote_path.read_text(encoding="utf8").splitlines(keepends=True)
                    if line.endswith("\n") for row in [json.loads(line)]
                    if row["task"] == "whole" and row["attempt"] == 1)
    return rows


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
    by_id = {case["id"]: case for case in cases}
    if (CONTEXT_RUN / "manifest.json").exists():
        manifest = json.loads((CONTEXT_RUN / "manifest.json").read_text(encoding="utf8"))
        sources = {s["source_id"]: s for s in read_jsonl(CACHE / "source_info.jsonl")}
        responses = {r["id"]: r for r in read_jsonl(CACHE / "response.jsonl")}
        for case in manifest["groups"]["development"]:
            response, source = responses[case["response_id"]], sources[case["source_id"]]
            item = AuditInput(answer=response["response"], sources=[{"id": source["source_id"],
                              "title": f"RAGTruth {source['source']} · source {source['source_id']}", "text": source["source_info"]}])
            if object_hash(item.model_dump()) != case["input_sha256"]:
                raise HTTPException(409, "Context experiment inputs do not match the frozen manifest.")
            by_id[case["response_id"]] = {"input": item}
    if (QUOTE_RUN / "manifest.json").exists():
        manifest = json.loads((QUOTE_RUN / "manifest.json").read_text(encoding="utf8"))
        sources = {s["source_id"]: s for s in read_jsonl(CACHE / "source_info.jsonl")}
        responses = {r["id"]: r for r in read_jsonl(CACHE / "response.jsonl")}
        for case in manifest["whole"]:
            response, source = responses[case["case_id"]], sources[case["source_id"]]
            item = AuditInput(answer=response["response"], sources=[{"id": source["source_id"],
                              "title": f"RAGTruth {source['source']} · source {source['source_id']}", "text": source["source_info"]}])
            if object_hash(item.model_dump()) != case["input_sha256"]:
                raise HTTPException(409, "Quote experiment inputs do not match the frozen manifest.")
            by_id[case["case_id"]] = {"input": item}
    return by_id


@router.get("/examples")
def examples():
    rows = saved_rows()
    grouped = {}
    for row in rows:
        case_id = row["case_id"]
        entry = grouped.setdefault(case_id, {"id": case_id, "strategies": {}})
        entry["strategies"][row["strategy"]] = row["audit"]["status"]
    entries = sorted(grouped.values(), key=lambda r: int(r["id"]))
    for entry in entries:
        entry["label"] = f"RAGTruth #{entry['id']}"
        entry["requires_download"] = True
    if MEDICAL.exists():
        record = json.loads(MEDICAL.read_text(encoding="utf8"))
        entries.insert(0, {"id": "medical-grade", "label": "Medical · GRADE hypoglycemia trial",
                           "requires_download": False,
                           "strategies": {record["input"]["strategy"]: record["audit"]["status"]}})
    return {"examples": entries,
            "sources_downloaded": all((CACHE / name).exists() for name in ("response.jsonl", "source_info.jsonl")),
            "description": "Actual saved Flash inference: bundled original-paper medical demo and optional nonmedical RAGTruth development examples."}


@router.get("/examples/{response_id}")
def replay(response_id: str, strategy: Literal["direct", "split", "context", "quote_v2"] = "direct"):
    if response_id == "medical-grade" and MEDICAL.exists():
        record = json.loads(MEDICAL.read_text(encoding="utf8"))
        if record["input"]["strategy"] != strategy:
            raise HTTPException(404, "No saved medical audit for this strategy.")
        item = QuoteAuditRequest.model_validate(record["input"])
        if record["audit"]["answer_sha256"] != text_hash(item.answer) or record["audit"]["source_hashes"] != {s.id: text_hash(s.text) for s in item.sources}:
            raise HTTPException(409, "Medical demo anchors belong to different input texts.")
        return {**record, "mode": "saved", "provenance": {**record["provenance"],
                "note": "Saved actual Ask → Direct audit of the GRADE hypoglycemia trial abstract (Seaquist et al., 2024; CC0). No new model call. Single-paper software demonstration, not a reliability evaluation."}}
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
                           "run": row.get("run", "ragtruth_v1/run01"), "group": row.get("group", "original pilot"),
                           "note": "Saved inference, no new model call. Human error labels are not model inputs."}}


@router.post("")
def live_audit(item: QuoteAuditRequest):
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, "Three audits are already running; try again after one finishes.")
    try:
        try:
            gateway = FlashGateway()
        except Exception:
            raise HTTPException(503, "Configure the Flash profile and key in the local .env before running a live audit.") from None
        if item.strategy == "quote_v2":
            result = audit_quotes(item, gateway)
        elif item.strategy == "context":
            result = audit_context(item, gateway)
        else:
            result = audit_answer(item, gateway)
        return {"input": item.model_dump(), "audit": result, "mode": "live",
                "provenance": {"note": "New Flash inference on the supplied texts. Input and output are not saved on the server."}}
    finally:
        _slots.release()
