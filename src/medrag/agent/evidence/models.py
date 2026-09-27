"""Source-bound answer schemas and exact source sentence preparation."""
from __future__ import annotations

import html
import re
from typing import Literal
from pydantic import BaseModel, Field
from medrag.retrieval.retriever import RetrievedChunk


class EvidenceSpan(BaseModel):
    chunk_id: str
    citation: str = ""
    quote: str


class AnswerComponent(BaseModel):
    id: str = ""
    requirement: str
    question_span: str = ""
    source_hint: str = ""
    status: Literal["supported", "partial", "missing"] = "missing"
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    required_details: list[str] = Field(default_factory=list)
    missing_outcome: str = ""
    gap: str = ""
    answer: str = ""


def normalized(text: str) -> str:
    """Ignore presentation whitespace/HTML, preserving numbers and inequalities."""
    text = html.unescape(re.sub(r"</?[A-Za-z][^>]*>", "", text))
    return " ".join(text.split()).casefold()


def source_spans(chunks: list[RetrievedChunk]) -> dict[str, dict]:
    """Give source sentences stable local IDs so models need not transcribe quotes."""
    spans = {}
    for chunk in chunks:
        # A decimal or 'vs. 84%' is not a sentence break. All returned text is
        # still verbatim source material, including any original HTML markup.
        for quote in re.split(r"(?<=[.!?])\s+(?=[A-Z<])|\n{2,}", chunk.text):
            if quote.strip():
                spans[f"E{len(spans) + 1}"] = {
                    "chunk_id": chunk.chunk_id, "citation": chunk.citation, "quote": quote.strip(),
                }
    return spans
