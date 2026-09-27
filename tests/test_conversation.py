"""Context contract checks, not a claim of model/medical correctness."""
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from medrag.agent.conversation import ContextTurn, resolve_context
from medrag.api.models import AskRequest


def previous(answer="The discussion concerns Study A."):
    return ContextTurn(turn_id="t1", revision_id="r1", question="Describe Study A.", answer=answer, source_titles=["Study A"])


class FakeLLM:
    def __init__(self, decision):
        self.decision = decision

    def invoke(self, messages):
        assert "NEVER evidence" in messages[0].content
        return SimpleNamespace(content=json.dumps(self.decision), response_metadata={"model_name": "test-only"}, usage_metadata={"total_tokens": 10})


def decision(mode="follow_up", **kwargs):
    return dict(mode=mode, reference_context="Study A", context_turn_ids=["t1"], referent_entities=["Study A"], clarification="", **kwargs)


def test_follow_up_preserves_exact_new_conditions_and_records_cost():
    query = "What about patients WITHOUT diabetes, at 12 rather than 24 months?"
    result = resolve_context(query, [previous()], llm=FakeLLM(decision()))
    assert result.resolved_query.startswith(query + "\n\n")
    assert result.context_turn_ids == ["t1"]
    assert result.usage == {"total_tokens": 10}
    assert result.model == "test-only"
    assert "discussion concerns" not in result.resolved_query


def test_topic_switch_does_not_inherit_study():
    result = resolve_context("Describe Study B.", [previous()], llm=FakeLLM(dict(mode="independent", reference_context="", context_turn_ids=[], referent_entities=[], clarification="")))
    assert result.resolved_query == "Describe Study B."
    assert result.context_turn_ids == []


def test_ambiguous_reference_returns_clarification_not_medical_answer():
    result = resolve_context("What is its sample size?", [previous("Study A and Study B were discussed.")], llm=FakeLLM(dict(mode="clarify", reference_context="", context_turn_ids=["t1"], referent_entities=[], clarification="Do you mean Study A or Study B?")))
    assert result.needs_clarification
    assert result.resolved_query == ""
    assert "Study A or Study B" in result.clarification


@pytest.mark.parametrize("bad", [{}, {**decision(), "context_turn_ids": ["unknown"]}, {**decision(), "mode": "independent"}])
def test_invalid_resolution_cannot_silently_fall_back_to_guessing(bad):
    result = resolve_context("Its sample?", [previous()], llm=FakeLLM(bad))
    assert result.status == "invalid_resolution"
    assert result.needs_clarification and result.raw_output


def test_no_context_needs_no_model_and_omitted_context_requires_clarification():
    assert resolve_context("Study A?", []).resolved_query == "Study A?"
    assert resolve_context("Its sample?", [], omitted=1).needs_clarification


def test_context_caps_reject_overflow_instead_of_truncating():
    with pytest.raises(ValidationError):
        AskRequest(query="Question", context=[previous("x" * 12000)])
    with pytest.raises(ValidationError):
        AskRequest(query="Question", context=[previous(), previous()])
