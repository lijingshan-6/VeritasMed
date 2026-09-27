"""Run the production Ask graph on a benchmark split with isolated state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from statistics import fmean
from typing import Any


_RUNTIME_FILES = (
    "scripts/benchmark/run_agent.py",
    "src/medrag/agent/graph.py",
    "src/medrag/agent/llms.py",
    "src/medrag/agent/prompts.py",
    "src/medrag/agent/state.py",
    "src/medrag/agent/utils.py",
    "src/medrag/benchmark/agent_runner.py",
    "src/medrag/config.py",
    "src/medrag/index/embedder.py",
    "src/medrag/retrieval/hybrid.py",
    "src/medrag/retrieval/reranker.py",
) + tuple(
    path.relative_to(Path(__file__).resolve().parents[2]).as_posix()
    for package in ("nodes", "evidence")
    for path in sorted(
        (Path(__file__).resolve().parents[2] / "src/medrag/agent" / package).glob("*.py")
    )
)


def _read_questions(path: Path, split: str) -> list[Any]:
    from medrag.benchmark.schema import BenchmarkQuestion

    with path.open(encoding="utf-8") as handle:
        rows = [
            BenchmarkQuestion.model_validate_json(line)
            for line in handle
            if line.strip()
        ]
    return [row for row in rows if split == "all" or row.split.value == split]


def _save(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "questions": len(rows),
        "errors": sum(bool(row.get("error")) for row in rows),
        "mean_latency_seconds": fmean(row["latency_seconds"] for row in rows)
        if rows
        else 0.0,
        "agent_faithful_rate": fmean(float(row["faithful"]) for row in rows)
        if rows
        else 0.0,
        "mean_confidence": fmean(row["confidence"] for row in rows)
        if rows
        else 0.0,
        "mean_rewrites": fmean(row["iterations"] for row in rows)
        if rows
        else 0.0,
        "mean_regenerations": fmean(row["regen_count"] for row in rows)
        if rows
        else 0.0,
    }


def _git_provenance(root: Path) -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    diff = subprocess.run(
        ["git", "diff", "--binary", "HEAD"],
        cwd=root,
        capture_output=True,
        check=True,
    ).stdout
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {
        "code_commit": commit,
        "working_tree_dirty": bool(status),
        "tracked_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "runtime_file_sha256": {
            relative_path: hashlib.sha256((root / relative_path).read_bytes()).hexdigest()
            for relative_path in _RUNTIME_FILES
        },
    }


def run(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    runtime_path = (root / args.qdrant_path).resolve()
    checkpoint_path = (root / ".benchmark-runtime/checkpoints").resolve()
    os.environ.update(
        {
            "QDRANT_PATH": str(runtime_path),
            "QDRANT_COLLECTION": args.collection,
            "LLM_BACKEND": "ollama",
            "OLLAMA_MODEL": args.model,
            "OLLAMA_HOST": args.ollama_host,
            "LLM_TIMEOUT_SECONDS": str(args.timeout),
            "EMBEDDER_DEVICE": args.embedder_device,
            "RERANKER_DEVICE": args.reranker_device,
            "MEDRAG_DATA_DIR": str(checkpoint_path),
        }
    )

    # Load the PyTorch stack before Qdrant's native gRPC runtime on Windows.
    # The inverse order can terminate a CUDA process before Python can emit an
    # exception, which is why build_runtime_index applies the same guard.
    import pyarrow  # noqa: F401 -- load Arrow before the ML/native runtime on Windows
    import sentence_transformers  # noqa: F401

    # Imports must follow the environment contract because the production graph
    # binds backend and collection settings at import time.
    from medrag.agent.graph import app as agent_app
    from medrag.benchmark.agent_runner import run_agent_question

    questions = _read_questions(root / args.questions, args.split)
    questions_sha256 = hashlib.sha256((root / args.questions).read_bytes()).hexdigest()
    output_path = root / args.output
    if args.resume and output_path.exists():
        prior = json.loads(output_path.read_text(encoding="utf-8"))
        existing = {row["id"]: row for row in prior.get("results", [])}
    else:
        existing = {}
    results: list[dict[str, Any]] = []
    provenance = _git_provenance(root)
    from medrag.agent.llms import make_llm_fast, make_llm_think
    fast_llm = make_llm_fast(structured=True)
    review_llm = make_llm_think(structured=True)
    runtime_config = {
        "embedder": "BAAI/bge-m3",
        "embedder_device": args.embedder_device,
        "reranker": "BAAI/bge-reranker-v2-m3",
        "reranker_device": args.reranker_device,
        "ollama_fast_reasoning": False,
        "ollama_review_reasoning": False,
        "structured_outputs": "Ollama JSON mode for route, study matching, outline and generation; per-component JSON Schema for check",
        "fast_num_predict": fast_llm.num_predict,
        "review_num_predict": review_llm.num_predict,
        "fast_context_tokens": fast_llm.num_ctx,
        "review_context_tokens": review_llm.num_ctx,
        "fast_temperature": fast_llm.temperature,
        "review_temperature": review_llm.temperature,
        "boundary_outline_temperature": review_llm.temperature,
        "top_p": fast_llm.top_p,
        "top_k": fast_llm.top_k,
        "repeat_penalty": fast_llm.repeat_penalty,
        "model_default_presence_penalty": 1.5,
        "request_timeout_seconds": args.timeout,
    }

    for offset, question in enumerate(questions, start=1):
        if question.id in existing:
            results.append(existing[question.id])
            print(f"[resume] {offset}/{len(questions)} {question.id}", flush=True)
            continue
        print(f"[agent] starting {offset}/{len(questions)} {question.id}", flush=True)
        result = run_agent_question(
            agent_app,
            question_id=question.id,
            query=question.question,
        )
        result.update(
            {
                "split": question.split.value,
                "task_type": question.task_type.value,
                "answerability": question.answerability.value,
                "category": question.category,
            }
        )
        results.append(result)
        payload = {
            "schema_version": "1.0",
            "answer_source": "production_agent_graph",
            "split": args.split,
            "model": args.model,
            "collection": args.collection,
            "questions_sha256": questions_sha256,
            "runtime_config": runtime_config,
            **provenance,
            "summary": _summary(results),
            "results": results,
        }
        _save(output_path, payload)
        print(
            f"[agent] {offset}/{len(questions)} {question.id} "
            f"faithful={result['faithful']} latency={result['latency_seconds']:.1f}s",
            flush=True,
        )

    payload = {
        "schema_version": "1.0",
        "answer_source": "production_agent_graph",
        "split": args.split,
        "model": args.model,
        "collection": args.collection,
        "questions_sha256": questions_sha256,
        "runtime_config": runtime_config,
        **provenance,
        "summary": _summary(results),
        "results": results,
    }
    _save(output_path, payload)
    print(json.dumps(payload["summary"], indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path("data/benchmark/veritasmed_v1_1/questions.jsonl"),
    )
    parser.add_argument("--split", choices=["development", "test", "all"], default="development")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/benchmark/veritasmed_v1_1/baseline_agent_dev_raw.json"),
    )
    parser.add_argument(
        "--qdrant-path",
        type=Path,
        default=Path(".benchmark-runtime/qdrant"),
    )
    parser.add_argument("--collection", default="veritasmed_benchmark_v1_1")
    parser.add_argument("--model", default="qwen3.5:9b")
    parser.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--embedder-device", choices=["cpu", "cuda", "auto"], default="cpu")
    parser.add_argument("--reranker-device", choices=["cpu", "cuda", "auto"], default="cpu")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
