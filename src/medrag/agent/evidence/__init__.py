"""Public evidence API. Implementations are separated by responsibility."""

from .models import (
    EvidenceSpan as EvidenceSpan,
    AnswerComponent as AnswerComponent,
    normalized as normalized,
    source_spans as source_spans,
)
from .scope import (
    population_scope_issue as population_scope_issue,
    component_gap as component_gap,
    protocol_scope_issue as protocol_scope_issue,
    repair_design_scope as repair_design_scope,
)
from .binding import (
    bind_components as bind_components,
    outline_status as outline_status,
    repair_gaps as repair_gaps,
    bind_claims as bind_claims,
    bind_additional_evidence as bind_additional_evidence,
)
from .restoration import (
    missing_numeric_details as missing_numeric_details,
)
