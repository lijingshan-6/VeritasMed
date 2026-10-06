"""LLM factory for the Flash gateway (default) or a local Ollama model.

Backend selection via LLM_BACKEND (default: openhub):

  LLM_BACKEND=openhub → OpenAI-compatible gateway (Flash), reasoning enabled
  LLM_BACKEND=ollama  → ChatOllama pointing at the configured local model

Two graph roles; both use the same model for openhub:
  make_llm_fast()   → route, source identity selection, generate, summarize
  make_llm_think()  → grade, rewrite, check
  make_llm_think(reasoning=True) → optional Ollama reasoning, not used by default

There is no automatic fallback to another model.
"""
from __future__ import annotations

import logging
import os

from medrag.config import DEFAULT_OLLAMA_MODEL, ollama_base_url

logger = logging.getLogger(__name__)

_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)


def _make_llm(thinking: bool, *, reasoning: bool = False, structured: bool | dict = False):
    """Shared factory; both graph roles use the configured model."""
    backend = os.environ.get("LLM_BACKEND", "openhub").strip().lower()
    timeout = float(os.environ.get("LLM_TIMEOUT_SECONDS", "60"))
    if backend not in {"ollama", "openhub"}:
        raise ValueError("LLM_BACKEND must be openhub or ollama")
    if backend == "openhub":
        from langchain_openai import ChatOpenAI
        from langgraph.config import get_config

        base_url = os.environ.get("OPENHUB_BASE_URL", "").rstrip("/")
        api_key = os.environ.get("OPENHUB_API_KEY", "")
        try:
            run_config = get_config()
        except RuntimeError:  # Factory also supports calls outside a graph.
            run_config = {}
        selected_model = (run_config.get("configurable", {}).get("openhub_model")
                          or os.environ.get("OPENHUB_MODEL", "")).strip()
        if not base_url or not api_key or not selected_model:
            raise EnvironmentError("OpenHub requires OPENHUB_BASE_URL, OPENHUB_API_KEY and OPENHUB_MODEL")
        # Both tiers use the selected model with reasoning enabled.
        return ChatOpenAI(
            model=selected_model,
            base_url=base_url,
            api_key=api_key,
            temperature=None,
            timeout=timeout,
            max_retries=1,
            max_tokens=int(os.environ.get("OPENHUB_MAX_TOKENS", "32768")),
            reasoning_effort=os.environ.get("OPENHUB_REASONING_EFFORT", "high"),
            extra_body={"thinking": {"type": "enabled"}},
            model_kwargs={"response_format": {"type": "json_object"}} if structured else {},
            # This gateway rejects urllib's default UA before API dispatch.
            default_headers={"User-Agent": "Mozilla/5.0 VeritasMed"},
            use_responses_api=False,
            # Receive reasoning/output incrementally so a long completion does
            # not hit the gateway's 120s non-streaming proxy timeout. invoke()
            # still returns the assembled final message to the unchanged graph.
            streaming=True,
            stream_usage=True,
        )
    if backend == "ollama":
        from langchain_ollama import ChatOllama
        # Keep structured review direct: a reasoning-only response can consume
        # the output budget without returning a usable decision.
        logger.debug("[llm] %s → Ollama %s (reasoning=%s)",
                     "think" if thinking else "fast", _OLLAMA_MODEL, reasoning)
        return ChatOllama(
            model=_OLLAMA_MODEL,
            base_url=ollama_base_url(),
            client_kwargs={"timeout": timeout},
            reasoning=reasoning,
            format=structured if isinstance(structured, dict) else ("json" if structured else None),
            # Qwen's general thinking profile uses sampling. Greedy reasoning
            # exhausted the output budget without a final answer in development.
            temperature=1.0 if reasoning else (0.0 if thinking or structured else 0.2),
            top_p=0.95,
            top_k=20,
            repeat_penalty=1.0,
            num_ctx=8192,
            num_predict=4096,
        )


# ── Public factories ───────────────────────────────────────────────────────────

def make_llm_fast(*, structured: bool | dict = False):
    """Generation role: route, source matching, generate, summarize."""
    return _make_llm(False, structured=structured)


def make_llm_think(*, reasoning: bool = False, structured: bool | dict = False):
    """Review role: grade, rewrite, check."""
    return _make_llm(True, reasoning=reasoning, structured=structured)


__all__ = ["make_llm_fast", "make_llm_think"]
