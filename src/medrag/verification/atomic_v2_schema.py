"""Additive v0.8 contracts; historical atomic_v1 schemas remain unchanged."""

from typing import Literal

from pydantic import Field

from .atomic_schema import AtomicAuditRequest, AtomicFact
from .schema import Record


class AtomicV2Request(AtomicAuditRequest):
    strategy: Literal["direct", "split", "context", "quote_v2", "atomic_v1", "atomic_v2"] = "direct"


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


class AnchoredFact(AtomicFact):
    qualifiers: list[QualifierAnchor] = Field(max_length=24)


class AnchoredExtraction(Record):
    facts: list[AnchoredFact] = Field(max_length=48)
    completeness_note: str = Field(min_length=1)
