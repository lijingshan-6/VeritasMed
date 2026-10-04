"""Atomic v2 contracts: model interpretations stay separate from exact original text."""

from typing import Literal

from pydantic import Field

from .schema import Record, Relation


class FactSlots(Record):
    subject: str | None = None
    population: str | None = None
    intervention: str | None = None
    comparator: str | None = None
    outcome: str | None = None
    value_unit: str | None = None
    time: str | None = None
    qualifications: str | None = None


class QualifierAnchor(Record):
    kind: Literal[
        "population",
        "group_comparison",
        "outcome",
        "value_unit",
        "time_denominator",
        "negation_attribution",
    ]
    quote: str = Field(min_length=1)
    parent_quote: str = Field(min_length=1)


class AnchoredFact(Record):
    parent_quote: str = Field(min_length=1)
    answer_quotes: list[str] = Field(min_length=1, max_length=8)
    normalized_claim: str = Field(min_length=1)
    slots: FactSlots
    decomposition_status: Literal["atomic", "still_compound", "uncertain"]
    qualifiers: list[QualifierAnchor] = Field(max_length=24)


class AnchoredExtraction(Record):
    facts: list[AnchoredFact] = Field(max_length=48)
    completeness_note: str = Field(min_length=1)


class QuoteReference(Record):
    source_id: str
    quote: str = Field(min_length=1)


class AtomicJudgment(Record):
    fact_id: str
    relation: Relation
    evidence: list[QuoteReference]
    explanation: str = Field(min_length=1)


class AtomicJudgments(Record):
    judgments: list[AtomicJudgment] = Field(max_length=48)
