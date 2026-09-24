"""Text-only contracts. Gold annotations never belong to VerificationInput."""
from __future__ import annotations

import hashlib
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Relation(StrEnum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT = "insufficient"


class EvidenceDocument(Record):
    document_id: str
    title: str
    sentences: list[str] = Field(min_length=1)

    @property
    def canonical_text(self) -> str:
        return "\n".join(self.sentences)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_text.encode("utf-8")).hexdigest()


class VerificationInput(Record):
    case_id: str
    claim: str = Field(min_length=1)
    document: EvidenceDocument


class GoldCase(Record):
    input: VerificationInput
    relation: Relation
    rationale_sets: list[list[int]]
    original_split: str
    claim_id: int
    related_document_ids: list[str]


class Decision(Record):
    relation: Relation
    sentence_ids: list[StrictInt]
    explanation: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_ids(self):
        if len(set(self.sentence_ids)) != len(self.sentence_ids):
            raise ValueError("Duplicate sentence IDs")
        if any(i < 0 for i in self.sentence_ids):
            raise ValueError("Sentence IDs must be nonnegative")
        if self.relation == Relation.INSUFFICIENT and self.sentence_ids:
            raise ValueError("Insufficient decisions must not assert an evidence rationale")
        if self.relation != Relation.INSUFFICIENT and not self.sentence_ids:
            raise ValueError("Support/contradiction requires evidence sentence IDs")
        return self


class EvidenceSpan(Record):
    document_id: str
    document_sha256: str
    sentence_id: int
    start: int
    end: int
    offset_unit: str = "unicode_codepoint"
    text: str


def bind_evidence(document: EvidenceDocument, decision: Decision) -> list[EvidenceSpan]:
    """Resolve IDs, not model-generated quotes; preserve duplicate sentence positions."""
    offsets = []
    cursor = 0
    for sentence in document.sentences:
        offsets.append(cursor)
        cursor += len(sentence) + 1
    spans = []
    for i in decision.sentence_ids:
        if i >= len(document.sentences):
            raise ValueError(f"Sentence ID {i} is outside document {document.document_id}")
        text = document.sentences[i]
        spans.append(EvidenceSpan(
            document_id=document.document_id, document_sha256=document.sha256,
            sentence_id=i, start=offsets[i], end=offsets[i] + len(text), text=text,
        ))
    return spans
