"""Run the production Agent: Flash development by default, other runs explicitly selected."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import logging
import os
import time
from threading import RLock
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

from run_agent import _git_provenance, _read_questions, _save, _summary


class CallTrace(BaseCallbackHandler):
    """Keep node outputs/usage, without API headers, secrets or reasoning transcripts."""

    def __init__(self):
        self.pending = {}
        self.calls = []

    def on_chat_model_start(self, serialized, messages, *, run_id: UUID, **kwargs):
        params = kwargs.get("invocation_params", {})
        self.pending[run_id] = {
            "began": time.perf_counter(),
            "node": (kwargs.get("metadata") or {}).get("langgraph_node"),
            "input_characters": sum(len(str(m.content)) for batch in messages for m in batch),
            "request_settings": {key: params[key] for key in (
                "model", "model_name", "max_tokens", "max_completion_tokens", "reasoning_effort",
                "response_format", "extra_body", "temperature",
            ) if key in params},
        }

    def on_llm_end(self, response, *, run_id: UUID, **kwargs):
        row = self.pending.pop(run_id, {"began": time.perf_counter()})
        row["latency_seconds"] = time.perf_counter() - row.pop("began")
        generation = response.generations[0][0]
        message = getattr(generation, "message", None)
        row["output"] = generation.text
        row["response_metadata"] = getattr(message, "response_metadata", {})
        row["usage"] = getattr(message, "usage_metadata", None)
        extra = getattr(message, "additional_kwargs", {})
        row["reasoning_characters_exposed_by_client"] = len(extra.get("reasoning_content") or "")
        self.calls.append(row)

    def on_llm_error(self, error, *, run_id: UUID, **kwargs):
        row = self.pending.pop(run_id, {"began": time.perf_counter()})
        row["latency_seconds"] = time.perf_counter() - row.pop("began")
        row["error_type"] = type(error).__name__
        self.calls.append(row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path,
                        default=Path(".benchmark-runtime/flash-baseline"))
    parser.add_argument("--models", nargs="+", choices=("flash", "pro"), default=["flash"],
                        help="Models to run (default: flash); use --models pro flash for a paid paired comparison")
    parser.add_argument("--split", choices=("development", "test"), default="development",
                        help="Use test only after freezing the implementation")
    parser.add_argument("--ids", nargs="*", help="Optional subset within the selected split")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    output_dir = root / args.output_dir
    os.environ.update({
        "LLM_BACKEND": "openhub", "OPENHUB_REASONING_EFFORT": "high",
        "OPENHUB_MAX_TOKENS": "32768", "LLM_TIMEOUT_SECONDS": "240",
        "QDRANT_PATH": str(root / ".benchmark-runtime/qdrant"),
        "QDRANT_COLLECTION": "veritasmed_benchmark_v1_1",
        "EMBEDDER_DEVICE": "cuda", "RERANKER_DEVICE": "cuda",
        "MEDRAG_DATA_DIR": str(root / ".benchmark-runtime/openhub-checkpoints"),
    })
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    logging.getLogger("medrag.agent.nodes").setLevel(logging.INFO)

    # Preserve the existing Windows native-library import order.
    import pyarrow  # noqa: F401
    import sentence_transformers  # noqa: F401
    from medrag.agent.graph import app
    from medrag.agent.nodes.retrieval import _get_retriever, _get_reranker
    from medrag.benchmark.agent_runner import run_agent_question
    from medrag.config import get_qdrant_client

    question_path = root / "data/benchmark/veritasmed_v1_1/questions.jsonl"
    questions = _read_questions(question_path, args.split)
    if args.ids:
        unknown = set(args.ids) - {q.id for q in questions}
        if unknown:
            raise SystemExit("IDs must belong to the selected split: " + ", ".join(sorted(unknown)))
        questions = [q for q in questions if q.id in args.ids]
    provenance = _git_provenance(root)
    provenance["runtime_file_sha256"]["scripts/benchmark/compare_agent_models.py"] = (
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    )
    common = {
        "schema_version": "1.0", "answer_source": "production_agent_graph",
        "split": args.split, "test_split_executed": args.split == "test",
        "questions_sha256": hashlib.sha256(question_path.read_bytes()).hexdigest(),
        "question_ids": [q.id for q in questions],
        "collection": "veritasmed_benchmark_v1_1",
        "runtime_config": {
            "backend": "openhub", "base_url": os.environ["OPENHUB_BASE_URL"],
            "thinking": "enabled", "reasoning_effort": "high", "max_output_tokens": 32768,
            "streaming_transport": True,
            "request_timeout_seconds": 240, "sdk_max_retries": 1,
            "embedder": "BAAI/bge-m3", "embedder_device": "cuda",
            "reranker": "BAAI/bge-reranker-v2-m3", "reranker_device": "cuda",
            "structured_outputs": "JSON object mode; unchanged checker schema in prompt",
            "max_active_requests": 3,
            "selected_models": list(dict.fromkeys(args.models)),
            "question_order": "alternate selected model order between questions",
            "shared_gpu_operations": "serialized, unchanged retrieval inputs and algorithms",
            "latency_excludes_shared_model_initialization": True,
        },
        **provenance,
    }
    # Gateway model IDs can be case-sensitive. Keep the configured Flash ID in
    # both the actual requests and the saved artifact rather than normalizing it.
    available_models = {
        "pro": "DeepSeek-v4-pro",
        "flash": os.environ.get("OPENHUB_MODEL", "deepseek-v4.1-flash").strip(),
    }
    models = {label: available_models[label] for label in args.models}
    artifacts = {}
    for label, model in models.items():
        path = output_dir / f"{label}_raw.json"
        if path.exists():
            if not args.resume:
                raise SystemExit(f"Refusing to overwrite existing run: {path}")
            saved = json.loads(path.read_text(encoding="utf-8"))
            for key in ("runtime_config", "runtime_file_sha256", "questions_sha256", "question_ids"):
                if saved[key] != common[key]:
                    raise SystemExit(f"Cannot resume after changing {key}")
            if saved["model"] != model:
                raise SystemExit("Cannot resume a different model")
            artifacts[label] = saved
        else:
            artifacts[label] = {**common, "model": model,
                                "created_at": datetime.now(timezone.utc).isoformat(), "results": []}
    # Retain the exact implementation even when the checkout has local changes.
    for relative in provenance["runtime_file_sha256"]:
        snapshot = output_dir / "runtime_code" / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        if not snapshot.exists():
            snapshot.write_bytes((root / relative).read_bytes())
    print("[setup] loading shared retrieval models", flush=True)
    began = time.perf_counter()
    reranker = _get_reranker()
    retriever = _get_retriever()
    gpu_lock = RLock()

    def serialize_gpu(method):
        def wrapped(*a, **kw):
            with gpu_lock:
                return method(*a, **kw)
        return wrapped

    # Share one set of weights; only remote calls overlap. Avoid simultaneous
    # tokenization/forward passes changing resource requirements or model state.
    retriever.retrieve = serialize_gpu(retriever.retrieve)
    reranker.rank_groups = serialize_gpu(reranker.rank_groups)
    reranker.rerank = serialize_gpu(reranker.rerank)
    print(f"[setup] ready in {time.perf_counter() - began:.1f}s", flush=True)

    def evaluate(index, question, label):
        trace = CallTrace()
        print(f"[compare] {index + 1}/{len(questions)} {question.id} {label} starting", flush=True)
        result = run_agent_question(app, question_id=question.id, query=question.question,
                                    callbacks=[trace], model=models[label])
        result.update({"split": args.split, "task_type": question.task_type.value,
                       "answerability": question.answerability.value, "category": question.category,
                       "api_calls": trace.calls})
        print(f"[compare] {question.id} {label} done: faithful={result['faithful']} "
              f"regen={result['regen_count']} seconds={result['latency_seconds']:.1f} "
              f"calls={len(trace.calls)} error={bool(result.get('error'))}", flush=True)
        return label, result

    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            jobs = []
            for index, question in enumerate(questions):
                order = list(models) if index % 2 == 0 else list(reversed(models))
                for label in order:
                    if not any(row["id"] == question.id for row in artifacts[label]["results"]):
                        jobs.append(pool.submit(evaluate, index, question, label))
            for future in as_completed(jobs):
                label, result = future.result()
                artifact = artifacts[label]
                artifact["results"].append(result)
                artifact["results"].sort(key=lambda row: common["question_ids"].index(row["id"]))
                artifact["summary"] = _summary(artifact["results"])
                _save(output_dir / f"{label}_raw.json", artifact)
    finally:
        get_qdrant_client().close()
    for label, artifact in artifacts.items():
        print(json.dumps({"model": label, **artifact["summary"]}), flush=True)


if __name__ == "__main__":
    main()
