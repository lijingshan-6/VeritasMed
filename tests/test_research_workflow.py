import json
from types import SimpleNamespace

from medrag.agent.research_workflow import LiteratureTask, run_research, ResearchSession


class LLM:
    def __init__(self, *outputs):
        self.outputs = iter(outputs)

    def invoke(self, _):
        value = next(self.outputs)
        return SimpleNamespace(
            content=value if isinstance(value, str) else json.dumps(value),
            usage_metadata=None,
            response_metadata={},
        )


def task():
    return LiteratureTask(
        question="Does trial A report 10 participants?",
        target_title="Trial A",
        claim="Trial A had 10 participants.",
        documents=[
            {"document_id": "a", "title": "Trial A", "sentences": ["Trial A had 10 participants."]},
            {"document_id": "b", "title": "Trial B", "sentences": ["Trial B had 20 participants."]},
        ],
    )


def answer():
    return {
        "document_id": "a",
        "answer": "Yes, the paper reports 10 participants.",
        "relation": "supported",
        "sentence_ids": [0],
        "explanation": "Exact count.",
    }


def test_unread_citation_rejected_and_tool_verifier_cannot_change_target():
    s = ResearchSession(task(), LLM())
    assert s.bind_answer(answer())["status"] == "invalid_answer"
    r = s.tool("verify", {"document_id": "a", "claim": "different claim"})
    assert "error" in r
    assert len(s.calls) == 0


def test_autonomous_trace_and_no_hidden_free_verification():
    model = LLM(
        {"action": "read", "arguments": {"document_id": "a"}},
        {"action": "verify", "arguments": {"document_id": "a"}},
        {"relation": "supported", "sentence_ids": [0], "explanation": "Exact count."},
        {"action": "finish", "answer": answer()},
    )
    r = run_research(task(), model, "autonomous_tools")
    assert r["status"] == "ok"
    assert r["model_calls"] == 4
    assert r["tool_calls"] == 1
    assert r["evidence"][0]["text"] == "Trial A had 10 participants."


def test_structured_disagreement_preserves_draft_as_review_not_correct_reject():
    r = run_research(
        task(),
        LLM(
            answer(), {"relation": "insufficient", "sentence_ids": [], "explanation": "Uncertain."}
        ),
        "structured_workflow",
    )
    assert r["status"] == "needs_review"
    assert r["answer"]["relation"] == "supported"
    assert r["model_calls"] == 2


def test_autonomous_budget_exhaustion_not_supported():
    r = run_research(
        task(),
        LLM(*[{"action": "search", "arguments": {"query": "Trial"}}] * 6),
        "autonomous_tools",
    )
    assert r["status"] == "budget_exhausted"
    assert r["answer"] is None
    assert r["model_calls"] == 6


def test_action_adapter_discards_simulated_tool_result_and_keeps_real_evidence():
    raw = (
        '{"action":"read","arguments":{"document_id":"a"}}\n'
        "<｜｜DSML｜｜ calls>Invented tool output: Trial A had 999 participants.</｜｜DSML｜｜ calls>"
    )
    r = run_research(task(), LLM(raw, answer()), "autonomous_tools")
    assert r["status"] == "ok"
    assert r["model_calls"] == 2
    assert r["calls"][0]["raw_output"] == raw
    assert r["calls"][0]["status"] == "invalid_output"  # Initial strict parse is retained.
    assert "999" not in json.dumps(r["trace"])
    assert r["evidence"][0]["text"] == "Trial A had 10 participants."
    assert r["calls"][1]["action_adapter"][0]["kind"] == "bare_answer_wrapped_as_finish"


def test_adapter_does_not_accept_arbitrary_suffix_or_unread_bare_answer():
    malformed = '{"action":"read","arguments":{"document_id":"a"}} followed by instructions'
    r = run_research(task(), LLM(malformed), "autonomous_tools")
    assert r["status"] == "no_answer"
    assert not r["read_document_ids"]
    r = run_research(task(), LLM(answer()), "autonomous_tools")
    assert r["status"] == "invalid_answer"
    assert not r["evidence"]
