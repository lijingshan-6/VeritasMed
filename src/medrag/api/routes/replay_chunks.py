"""Read adjacent original abstract passages without a vector database."""
import json

from fastapi import APIRouter, HTTPException, Query

from medrag.api.routes.conversations import ROOT

router = APIRouter()


@router.get("/api/chunk/{chunk_id:path}")
def chunk_context(chunk_id: str, context_window: int = Query(default=1, ge=0, le=3)):
    path = ROOT / "corpus.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf8").splitlines()]
    by_id = {r["chunk_id"]: r for r in rows}
    row = by_id.get(chunk_id)
    if row is None:
        raise HTTPException(404, "This passage is not in the bundled corpus.")
    key, index = chunk_id.rsplit(":", 1)

    def slim(index):
        source = by_id.get(f"{key}:{index}")
        return {"chunk_id": source["chunk_id"], "text": source["text"], "score": None} if source else None

    return {
        "chunk": slim(int(index)),
        "prev_chunk": slim(int(index) - 1) if context_window else None,
        "next_chunk": slim(int(index) + 1) if context_window else None,
        "document": {"title": row["title"], "citation": f"PMC:{row['doc_id']}",
                     "external_url": row["source_url"]},
    }
