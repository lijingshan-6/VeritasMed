"""Record the prespecified nine questions through the real Ask WebSocket and audit API."""
import hashlib
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import time

import httpx
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/demo/conversations"


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(value.encode("utf8")).hexdigest()


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=OUT / "run01")
    args = parser.parse_args()
    protocol = json.loads((OUT / "protocol.json").read_text(encoding="utf8"))
    run = args.run_dir
    run.mkdir(parents=True, exist_ok=True)
    identity = {
        "protocol_sha256": digest((OUT / "protocol.json").read_text(encoding="utf8")),
        "corpus_sha256": digest((OUT / "corpus.jsonl").read_text(encoding="utf8")),
        "scope": "Saved actual Ask output. One request per scheduled question; no output-selected retry.",
    }
    if (run / "identity.json").exists():
        if json.loads((run / "identity.json").read_text(encoding="utf8")) != identity:
            raise ValueError("Recording inputs changed")
    else:
        save(run / "identity.json", identity)
    for spec in protocol["conversations"]:
        path = run / (spec["id"] + ".json")
        conversation = json.loads(path.read_text(encoding="utf8")) if path.exists() else {
            "schema": 1, "id": spec["id"], "title": spec["label"], "created_at": now(),
            "updated_at": now(), "turns": [],
        }
        for i, question in enumerate(spec["questions"]):
            turn_id = spec["id"] + f"-turn-{i + 1}"
            revision_id = turn_id + "-revision-1"
            existing = next((t for t in conversation["turns"] if t["id"] == turn_id), None)
            if existing is None:
                previous = conversation["turns"][-1] if conversation["turns"] else None
                context = []
                omitted = 0
                if previous:
                    previous_revision = previous["revisions"][-1]
                    context = list(previous_revision["context"])
                    omitted = previous_revision["omitted_context"]
                    result = previous_revision["result"]
                    if result and previous_revision["status"] in {"complete", "clarification"}:
                        context.append({
                            "turn_id": previous["id"], "revision_id": previous_revision["id"],
                            "question": previous["question"], "answer": result["answer"],
                            "source_titles": [f"{c['citation']} · {c['title']}" for c in result["chunks"]],
                        })
                bounded, size = [], 0
                for item in reversed(context):
                    length = len(item["question"] + item["answer"] + "".join(item["source_titles"]))
                    if len(bounded) >= 6 or size + length > 12000:
                        break
                    bounded.insert(0, item)
                    size += length
                omitted += len(context) - len(bounded)
                revision = {
                    "id": revision_id, "created_at": now(), "status": "running", "origin": "live",
                    "context": bounded, "omitted_context": omitted, "result": None,
                    "timeline": [], "liveChunks": [], "error": None, "audits": [],
                }
                turn = {"id": turn_id, "question": question,
                        "parent_turn_id": previous["id"] if previous else None, "revisions": [revision]}
                conversation["turns"].append(turn)
                save(path, conversation)  # Interrupted requests remain visible, never silently repeated.
                events = run / (turn_id + "-events.jsonl")
                print(f"Ask {turn_id}", flush=True)
                try:
                    with connect("ws://127.0.0.1:8000/api/ask", open_timeout=20) as ws:
                        ws.send(json.dumps({"query": question, "thread_id": spec["id"],
                                            "context": bounded, "omitted_context": omitted}))
                        with events.open("a", encoding="utf8") as stream:
                            while True:
                                event = json.loads(ws.recv(timeout=340))
                                stamp = round(time.time() * 1000)
                                stream.write(json.dumps({"received_at": stamp, "event": event}, ensure_ascii=False) + "\n")
                                stream.flush()
                                if event["event"] == "node_start":
                                    revision["timeline"].append({
                                        "name": event["node"], "label": event["node"].replace("_", " ").title(),
                                        "status": "running", "summary": "", "timestamp": stamp,
                                    })
                                elif event["event"] == "node_end":
                                    node = next((n for n in reversed(revision["timeline"])
                                                 if n["name"] == event["node"] and n["status"] == "running"), None)
                                    if node:
                                        node.update(status="done", summary="Recorded node output",
                                                    detail=event["data"], elapsed_ms=stamp - node["timestamp"])
                                elif event["event"] == "done":
                                    result = event["data"]
                                    revision.update(
                                        result=result,
                                        status="clarification" if (result.get("conversation_context") or {}).get("needs_clarification") else "complete",
                                        answer_sha256=digest(result["answer"]),
                                        source_hashes={c["chunk_id"]: digest(c["text"]) for c in result["chunks"]},
                                    )
                                    break
                                elif event["event"] == "error":
                                    revision.update(status="failed", error=event["data"]["message"])
                                    break
                except Exception as exc:
                    revision.update(status="failed", error=f"Recorded transport failure: {type(exc).__name__}")
                conversation["updated_at"] = now()
                save(path, conversation)
            else:
                revision = existing["revisions"][0]
                if revision["status"] == "running":
                    revision.update(status="failed", error="Recording interrupted before completion; request not repeated.")
                    save(path, conversation)
            result = revision["result"]
            if revision["status"] != "complete" or not result["chunks"]:
                continue
            eligible = [t for t in conversation["turns"]
                        if t["revisions"][0]["status"] == "complete"
                        and t["revisions"][0]["result"]["chunks"]]
            methods = ["direct", "atomic_v2"] if eligible[0]["id"] == turn_id else ["direct"]
            for method in methods:
                audit_path = run / (turn_id + "-" + method + ".json")
                if audit_path.exists():
                    continue
                # Same hand-off as the browser (format v2): title line, blank line, passage.
                item = {"answer": result["answer"], "strategy": method, "sources": [
                    {"id": f"evidence-{j + 1}", "title": f"{c['citation']} · {c['title']}",
                     "text": f"{c['citation']} · {c['title']}\n\n{c['text']}"}
                    for j, c in enumerate(result["chunks"])
                ]}
                save(audit_path, {"status": "started", "input": item, "created_utc": now()})
                print(f"Audit {turn_id} {method}", flush=True)
                try:
                    response = httpx.post("http://127.0.0.1:8000/api/audit", json=item, timeout=400)
                    response.raise_for_status()
                    record = response.json()
                    record["mode"] = "saved"
                    record["provenance"] = {
                        **record["provenance"],
                        "note": "Saved actual Ask → audit. Three-paper abstract demonstration, not independent clinical gold.",
                        "run": run.resolve().relative_to(ROOT).as_posix() if run.resolve().is_relative_to(ROOT) else run.name,
                        "conversation_id": spec["id"],
                        "turn_id": turn_id, "revision_id": revision_id,
                        "handoff": {
                            "kind": "live_ask", "question": question, "thread_id": spec["id"],
                            "citations": result["citations"], "input": {**item, "strategy": "direct"},
                            "source_map": [
                                {"id": f"evidence-{j + 1}", "chunk_id": c["chunk_id"],
                                 "citation": c["citation"], "external_url": c["external_url"],
                                 "section": c.get("section")}
                                for j, c in enumerate(result["chunks"])
                            ],
                        },
                    }
                    save(audit_path, record)
                    print(f"Saved {method}: {record['audit']['status']}", flush=True)
                except Exception as exc:
                    save(audit_path, {"status": "failed", "input": item,
                                      "error": type(exc).__name__, "created_utc": now()})
        print(f"Saved conversation {spec['id']}", flush=True)


if __name__ == "__main__":
    main()
