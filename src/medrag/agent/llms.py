"""LLM factory for the configured gateway, Ollama or legacy MiMo backend.

Backend selection via environment variable LLM_BACKEND (default: mimo):

  LLM_BACKEND=mimo    → ChatOpenAI pointing at MiMo-V2.5 API
  LLM_BACKEND=ollama  → ChatOllama pointing at the configured local model
  LLM_BACKEND=openhub → OpenAI-compatible gateway, with thinking enabled

Two graph roles (not necessarily different models):
  make_llm_fast()   → route, source identity selection, generate, summarize
  make_llm_think()  → grade, rewrite, check
  make_llm_think(reasoning=True) → optional Ollama reasoning, not used by default

The current research profile uses openhub with Flash for both roles and enabled
reasoning. There is no automatic Pro fallback. Only the legacy MiMo adapter
selects separate fast/Pro names and disables internal reasoning on both.

MiMo env vars (read from .env):
  OPENAI_BASE_URL   — MiMo API base URL
  OPENAI_API_KEY    — MiMo API key
  MIMO_MODEL_FAST   — override fast model name  (default: mimo-v2.5)
  MIMO_MODEL_THINK  — override think model name (default: mimo-v2.5-pro)

Ollama env vars:
  OLLAMA_MODEL      — override model name (default: qwen3.5:9b)

See docs/decisions/2026-09-23-flash-research-baseline.md for the model decision.
"""
from __future__ import annotations

import logging
import os

from medrag.config import DEFAULT_OLLAMA_MODEL, ollama_base_url

logger = logging.getLogger(__name__)

# ── MiMo model names ───────────────────────────────────────────────────────────
_MIMO_FAST  = os.environ.get("MIMO_MODEL_FAST",  "mimo-v2.5")
_MIMO_THINK = os.environ.get("MIMO_MODEL_THINK", "mimo-v2.5-pro")

# ── Ollama model name ──────────────────────────────────────────────────────────
_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)


def _mimo_base_url() -> str:
    url = (
        os.environ.get("OPENAI_BASE_URL")
        or os.environ.get("OPENAI_API_BASE", "")
    ).rstrip("/")
    if not url:
        raise EnvironmentError(
            "MiMo backend requires OPENAI_BASE_URL (or OPENAI_API_BASE) in .env"
        )
    return url


def _mimo_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise EnvironmentError("MiMo backend requires OPENAI_API_KEY in .env")
    return key


# ── Internal factory ───────────────────────────────────────────────────────────

def _make_llm(thinking: bool, *, reasoning: bool = False, structured: bool | dict = False):
    """Shared factory; graph role selects a separate model only for legacy MiMo."""
    temp = 0.6 if thinking else 0.2
    model = _MIMO_THINK if thinking else _MIMO_FAST

    backend = os.environ.get("LLM_BACKEND", "mimo").strip().lower()
    timeout = float(os.environ.get("LLM_TIMEOUT_SECONDS", "60"))
    if backend not in {"mimo", "ollama", "openhub"}:
        raise ValueError("LLM_BACKEND must be mimo, ollama or openhub")
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
        # Both tiers use the selected model. Do not silently disable reasoning
        # or inherit MiMo's small final-output budget in a model comparison.
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
            default_headers={"User-Agent": "Mozilla/5.0 MedRAG-Agent"},
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

    # Default: mimo
    from langchain_openai import ChatOpenAI
    logger.debug("[llm] %s → MiMo %s", "think" if thinking else "fast", model)

    # MiMo models always reason internally unless explicitly disabled.
    # With thinking enabled and max_tokens=4096, the model burns 1000-5000+
    # reasoning tokens before producing content → 15-27 s for grade/check calls.
    # budget_tokens has no effect on this API; the only working control is
    # {"type": "disabled"}.  Grade/check quality stays high using the pro model
    # (mimo-v2.5-pro) even without explicit CoT; the fast model uses v2.5.
    return ChatOpenAI(
        model=model,
        base_url=_mimo_base_url(),
        api_key=_mimo_api_key(),
        temperature=temp,
        timeout=timeout,
        max_retries=1,
        max_tokens=4096 if thinking else 1024,
        extra_body={"thinking": {"type": "disabled"}},
    )


# ── Public factories ───────────────────────────────────────────────────────────

def make_llm_fast(*, structured: bool | dict = False):
    """Low-latency LLM — thinking OFF. Used by: route_query, generate_answer_node, summarize_history."""
    return _make_llm(False, structured=structured)


def make_llm_think(*, reasoning: bool = False, structured: bool | dict = False):
    """Pro-tier LLM (mimo-v2.5-pro, thinking disabled). Used by: grade_relevance, rewrite_query, check_faithfulness."""
    return _make_llm(True, reasoning=reasoning, structured=structured)


__all__ = ["make_llm_fast", "make_llm_think"]
