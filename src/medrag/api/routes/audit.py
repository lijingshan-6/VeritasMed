"""Live source-bound answer audit: Direct by default, Atomic v2 as an experiment."""
from threading import BoundedSemaphore

from fastapi import APIRouter, HTTPException

from medrag.verification.answer_audit import AuditRequest, audit_answer
from medrag.verification.atomic_v2 import audit_atomic_v2
from medrag.verification.gateway import FlashGateway

router = APIRouter(prefix="/api/audit", tags=["answer audit"])
_slots = BoundedSemaphore(3)


@router.post("")
def live_audit(item: AuditRequest):
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, "Three audits are already running; try again after one finishes.")
    try:
        try:
            gateway = FlashGateway()
        except Exception:
            raise HTTPException(503, "Configure the Flash profile and key in the local .env before running a live audit.") from None
        audit = audit_atomic_v2 if item.strategy == "atomic_v2" else audit_answer
        return {"input": item.model_dump(), "audit": audit(item, gateway), "mode": "live",
                "provenance": {"note": "New Flash inference on the supplied texts. Input and output are not saved on the server."}}
    finally:
        _slots.release()
