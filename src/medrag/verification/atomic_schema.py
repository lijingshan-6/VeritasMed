"""Atomic audit contracts keep model interpretations separate from original text."""

from typing import Literal

from pydantic import Field

from .quote_audit import QuoteAuditRequest, QuoteReference
from .schema import Record, Relation


class AtomicAuditRequest(QuoteAuditRequest):
    strategy: Literal["direct", "split", "context", "quote_v2", "atomic_v1"] = "direct"


class FactSlots(Record):
    subject: str | None = None
    population: str | None = None
    intervention: str | None = None
    comparator: str | None = None
    outcome: str | None = None
    value_unit: str | None = None
    time: str | None = None
    qualifications: str | None = None


class AtomicFact(Record):
    parent_quote: str = Field(min_length=1)
    answer_quotes: list[str] = Field(min_length=1, max_length=8)
    normalized_claim: str = Field(min_length=1)
    slots: FactSlots
    decomposition_status: Literal["atomic", "still_compound", "uncertain"]


class AtomicExtraction(Record):
    facts: list[AtomicFact] = Field(max_length=48)
    completeness_note: str = Field(min_length=1)


class AtomicJudgment(Record):
    fact_id: str
    relation: Relation
    evidence: list[QuoteReference]
    explanation: str = Field(min_length=1)


class AtomicJudgments(Record):
    judgments: list[AtomicJudgment] = Field(max_length=48)
