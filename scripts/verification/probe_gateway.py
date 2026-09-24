"""Record raw streamed model metadata, without persisting credentials or hidden reasoning."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from time import perf_counter

from medrag.config import load_project_env
from medrag.verification.scifact import prepare_pilot, object_hash
from medrag.verification.verifier import SYSTEM_PROMPT, prompt_payload


def main():
    from openai import OpenAI

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    load_project_env()
    model = os.environ["OPENHUB_MODEL"]
    if model.lower() != "deepseek-v4.1-flash":
        raise ValueError("Flash profile required")
    args.output.mkdir(parents=True, exist_ok=False)
    client = OpenAI(base_url=os.environ["OPENHUB_BASE_URL"], api_key=os.environ["OPENHUB_API_KEY"],
                    timeout=240, max_retries=1,
                    default_headers={"User-Agent": "Mozilla/5.0 MedRAG-Agent"})
    cases, _ = prepare_pilot(Path(".benchmark-runtime/scifact"))
    item = cases[0].input
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt_payload(item)}]
    report = {"created_utc": datetime.now(timezone.utc).isoformat(),
              "requested_model": model, "endpoint": os.environ["OPENHUB_BASE_URL"],
              "prompt_sha256": object_hash(messages), "case_id": item.case_id,
              "purpose": "Six identical already-exposed pilot prompts; metadata diagnosis only",
              "probes": []}
    try:
        report["advertised_flash_ids"] = sorted(m.id for m in client.models.list()
                                                if "flash" in m.id.lower())
    except Exception as exc:
        report["models_list_error"] = type(exc).__name__

    def probe(index):
        started = perf_counter()
        record = {"probe": index, "status": "ok", "chunk_models": {}, "usage": [],
                  "finish_reasons": [], "content_characters": 0, "reasoning_characters": 0}
        models = Counter()
        try:
            with client.chat.completions.create(
                model=model, messages=messages, stream=True, stream_options={"include_usage": True},
                max_tokens=32768, reasoning_effort="high", response_format={"type": "json_object"},
                extra_body={"thinking": {"type": "enabled"}},
            ) as stream:
                for chunk in stream:
                    models[chunk.model or "missing"] += 1
                    if chunk.usage is not None:
                        record["usage"].append(chunk.usage.model_dump())
                    for choice in chunk.choices:
                        record["content_characters"] += len(choice.delta.content or "")
                        record["reasoning_characters"] += len(getattr(choice.delta, "reasoning_content", None) or "")
                        if choice.finish_reason:
                            record["finish_reasons"].append(choice.finish_reason)
        except Exception as exc:
            record.update(status="execution_error", error_type=type(exc).__name__,
                          http_status=getattr(exc, "status_code", None))
        record["chunk_models"] = dict(models)
        record["elapsed_seconds"] = round(perf_counter() - started, 3)
        return record

    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(probe, range(1, 7)):
            report["probes"].append(result)
            print(json.dumps(result), flush=True)
    (args.output / "probe.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
