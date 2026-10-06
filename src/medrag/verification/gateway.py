"""Flash-only streaming transport for research; preserve all response model identifiers."""
import os
from types import SimpleNamespace
from urllib.parse import urlsplit


class FlashGateway:
    def __init__(self):
        from medrag.config import load_project_env
        from openai import OpenAI

        load_project_env()
        self.model = os.environ["OPENHUB_MODEL"]
        endpoint = urlsplit(os.environ["OPENHUB_BASE_URL"])
        if os.environ.get("LLM_BACKEND", "").lower() != "openhub" or self.model.lower() != "deepseek-v4.1-flash":
            raise ValueError("This research run requires the configured Flash profile")
        if endpoint.username or endpoint.password or endpoint.query:
            raise ValueError("Do not embed credentials in the endpoint")
        self.settings = {"model": self.model, "base_url": endpoint.geturl(),
                         "reasoning_effort": os.environ.get("OPENHUB_REASONING_EFFORT", "high"),
                         "max_tokens": int(os.environ.get("OPENHUB_MAX_TOKENS", "32768")),
                         "timeout_seconds": float(os.environ.get("LLM_TIMEOUT_SECONDS", "240")),
                         "streaming": True, "sdk_max_retries": 1, "transport": "openai_sdk_raw_stream"}
        self.client = OpenAI(api_key=os.environ["OPENHUB_API_KEY"], base_url=endpoint.geturl(),
                             timeout=self.settings["timeout_seconds"], max_retries=1,
                             default_headers={"User-Agent": "Mozilla/5.0 VeritasMed"})

    def invoke(self, messages):
        roles = {"system": "system", "human": "user", "ai": "assistant"}
        payload = [{"role": roles[m.type], "content": m.content} for m in messages]
        text, models, usage_snapshots, finish_reasons = [], set(), [], []
        reasoning_characters = 0
        with self.client.chat.completions.create(
            model=self.model, messages=payload, stream=True, stream_options={"include_usage": True},
            reasoning_effort=self.settings["reasoning_effort"], max_tokens=self.settings["max_tokens"],
            response_format={"type": "json_object"}, extra_body={"thinking": {"type": "enabled"}},
        ) as stream:
            for chunk in stream:
                if chunk.model:
                    models.add(chunk.model)
                if chunk.usage is not None:
                    usage_snapshots.append({"input_tokens": chunk.usage.prompt_tokens,
                                            "output_tokens": chunk.usage.completion_tokens,
                                            "total_tokens": chunk.usage.total_tokens})
                for choice in chunk.choices:
                    if choice.delta:
                        if choice.delta.content:
                            text.append(choice.delta.content)
                        reasoning_characters += len(getattr(choice.delta, "reasoning_content", None) or "")
                    if choice.finish_reason:
                        finish_reasons.append(choice.finish_reason)
        usage = usage_snapshots[-1] if usage_snapshots else None
        return SimpleNamespace(content="".join(text), usage_metadata=usage,
                               response_metadata={"model": next(iter(models)) if len(models) == 1 else None,
                                                  "model_identifiers": sorted(models),
                                                  "finish_reason": finish_reasons[-1] if finish_reasons else None,
                                                  "usage_snapshots": usage_snapshots,
                                                  "reasoning_characters": reasoning_characters})
