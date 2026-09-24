"""Experimental one-call audit; frozen v1 Direct remains in answer_audit.py."""
from datetime import datetime, timezone
import re
import time
from typing import Literal
from uuid import uuid4

from pydantic import Field, model_validator

from .answer_audit import (
    Anchor, AuditSource, ClaimAudit, DIRECT_PROMPT,
    bind_claim, call_json, coverage, resolve_anchor, text_hash,
)
from .schema import Record


class AuditRequest(Record):
    answer: str = Field(min_length=1, max_length=12000)
    sources: list[AuditSource] = Field(min_length=1, max_length=40)
    strategy: Literal["direct", "split", "context"] = "direct"

    @model_validator(mode="after")
    def validate_texts(self):
        if not self.answer.strip() or any(not s.text.strip() for s in self.sources):
            raise ValueError("Answer and source texts must not be blank")
        if len({s.id for s in self.sources}) != len(self.sources):
            raise ValueError("Duplicate source IDs")
        if sum(len(s.text) for s in self.sources) > 80000:
            raise ValueError("Combined sources exceed 80000 characters; no automatic truncation")
        return self


class ContextClaim(ClaimAudit):
    context_id: str


class MetaText(Anchor):
    kind: Literal["word_count", "format", "introduction"]
    explanation: str = Field(min_length=1)


def answer_contexts(answer):
    # Newline-delimited paragraphs retain embedded attribution and multi-sentence referents.
    return [{"id": f"context-{i+1}", "start": match.start(), "end": match.end(),
             "text": match.group(), "offset_unit": "unicode_codepoint"}
            for i, match in enumerate(re.finditer(r"[^\r\n]+", answer)) if match.group().strip()]


CONTEXT_INSTRUCTION = """
The supplied answer_contexts are exact answer paragraphs, NOT evidence. Each claim must include
context_id identifying the paragraph containing its quote. Judge the assertion AS USED in that
whole paragraph and the complete answer, retaining attribution (allegations/reported opinions),
conditionality, negation, future/predicted/planned versus completed events, quantities and time.
An embedded allegation is not an assertion that the alleged event actually happened. A source
reporting a plan does not prove it happened. Do not add assumptions from world knowledge.
Keep the answer quote minimal enough to localize the specific assertion or unsupported portion;
the bound context supplies omitted referents/qualifiers. Do not drop hard assertions.
"""
META_INSTRUCTION = """
Also return meta_text: a list of {quote, occurrence, kind, explanation}. Route ONLY statements
about THIS RESPONSE's own presentation to it: nonfactual introductions (kind introduction),
format instructions (format), or self-declared word limits/counts (word_count). These do not need
source support. Never route source/document/study facts, reported quantities or uncertain claims
as meta_text. A factual assertion embedded in an introduction still belongs in claims. Keep
factual and meta quotes disjoint. Meta routing is visible and excluded only from source verdicts,
not from reference error denominators. Do not declare metatext true or verified.
"""


def prompt_for(variant):
    if variant not in ("context", "context_only", "meta_only"):
        raise ValueError("Unknown context experiment variant")
    context_on = variant != "meta_only"
    meta_on = variant != "context_only"
    prompt = DIRECT_PROMPT
    if context_on:
        prompt += CONTEXT_INSTRUCTION
    if meta_on:
        prompt += META_INSTRUCTION
    return prompt


def audit_context(item, llm, variant="context"):
    started = time.perf_counter()
    context_on, meta_on = variant != "meta_only", variant != "context_only"
    contexts = answer_contexts(item.answer)
    payload = {"answer": item.answer, "sources": [s.model_dump() for s in item.sources]}
    if context_on:
        payload["answer_contexts"] = contexts
    calls, claims, meta = [], [], []
    value, call = call_json(llm, prompt_for(variant), payload, variant, calls)
    if value is not None:
        try:
            expected = {"claims", "meta_text"} if meta_on else {"claims"}
            if not isinstance(value, dict) or set(value) != expected:
                raise ValueError("Unexpected audit keys")
            if not isinstance(value["claims"], list) or len(value["claims"]) > 24:
                raise ValueError("Invalid claims list")
            parsed = [(ContextClaim if context_on else ClaimAudit).model_validate(c) for c in value["claims"]]
            raw_meta = value.get("meta_text", [])
            if not isinstance(raw_meta, list) or len(raw_meta) > 24:
                raise ValueError("Invalid meta list")
            parsed_meta = [MetaText.model_validate(m) for m in raw_meta]
            by_context = {c["id"]: c for c in contexts}
            for i, c in enumerate(parsed):
                row = bind_claim(item, c, i)
                if context_on:
                    context = by_context.get(c.context_id)
                    row["context_span"] = context
                    span = row["answer_span"]
                    if not context or not span or not context["start"] <= span["start"] < span["end"] <= context["end"]:
                        row.update(status="invalid_reference", error_type="InvalidClaimContext")
                claims.append(row)
            for i, m in enumerate(parsed_meta):
                row = {"id": f"meta-{i+1}", **m.model_dump(), "status": "not_source_checked", "answer_span": None}
                try:
                    span = resolve_anchor(item.answer, m)
                    row["answer_span"] = span
                    if any(c["answer_span"] and max(span["start"], c["answer_span"]["start"]) < min(span["end"], c["answer_span"]["end"]) for c in claims):
                        raise ValueError("Meta overlaps a factual claim")
                except ValueError:
                    row.update(status="invalid_reference", error_type="InvalidMetaAnchorOrOverlap")
                meta.append(row)
        except (ValueError, TypeError):
            call.update(status="invalid_output", error_type="InvalidContextAuditSchema")
    checked = [c["answer_span"] for c in claims if c["status"] == "ok"]
    error = any(c["status"] != "ok" for c in calls + claims) or any(m["status"] == "invalid_reference" for m in meta)
    statuses = {name: sum(c["status"] == "ok" and c["relation"] == name for c in claims)
                for name in ("supported", "contradicted", "insufficient")}
    statuses["failed_or_unchecked"] = sum(c["status"] != "ok" for c in claims)
    return {"id": str(uuid4()), "created_utc": datetime.now(timezone.utc).isoformat(),
            "strategy": variant, "status": "partial_error" if error else "ok" if claims or meta else "no_claims",
            "answer_sha256": text_hash(item.answer), "source_hashes": {s.id: text_hash(s.text) for s in item.sources},
            "claims": claims, "meta_text": meta, "summary": statuses,
            "extraction_coverage": coverage(item.answer, [c["answer_span"] for c in claims if c["answer_span"]]),
            "checked_coverage": coverage(item.answer, checked),
            "meta_coverage": coverage(item.answer, [m["answer_span"] for m in meta if m["status"] == "not_source_checked"]),
            "presentation_counts": {"full_answer_whitespace_tokens": len(item.answer.split()),
                                    "rule": "Python str.split() on the full unchanged answer, including headings and metatext; not a linguistic word count or a verdict on the author's counting convention."},
            "claims_at_cap": len(claims) >= 24, "calls": calls,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "scope": "Experimental source support with visible context/metatext routing. No calibrated confidence or clinical grading."}
