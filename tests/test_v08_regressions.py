"""Regressions for failures recorded in the bundled v0.8 medical conversations.

These cases are already exposed development examples, not independent test results.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch


RUN = Path(__file__).resolve().parents[1] / "data/demo/conversations/run01"


def saved_answer(name):
    for line in (RUN / f"{name}-events.jsonl").read_text(encoding="utf8").splitlines():
        event = json.loads(line)["event"]
        if event.get("event") == "done":
            return event["data"]
    raise AssertionError("No completed answer recorded")








def test_writing_instruction_is_dropped_instead_of_reported_as_missing_evidence():
    # Diet/exercise, turn 1: "Do not rank their clinical effectiveness" became component C3
    # with an evidence gap, although the checker itself said it was only an instruction.
    from medrag.agent.nodes import check_faithfulness

    saved = saved_answer("v08-diet-exercise-turn-1")
    components = saved["answer_components"]
    assert components[2]["status"] == "missing"
    supported = [c for c in components if c["status"] == "supported"]
    claims = [{"component_id": c["id"], "text": f'The study reports: "{span["quote"]}"', "cite": [span["citation"]]}
              for c in supported for span in c["evidence"]]
    checks = {c["id"]: {"passed": True, "correction": "", "unsupported_source_inference": False,
                        "evidence_status": c["status"], "gap": "", "missing_outcome": "",
                        "requirement_requested": True, "answer_constraint": c["id"] == "C3"} for c in components}
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=json.dumps({
        "supported": True, "complete": True, "boundary_correct": True, "issues": "", "component_checks": checks}))
    with patch("medrag.agent.nodes.checking.make_llm_think", return_value=llm):
        result = check_faithfulness({"query": saved["conversation_context"]["original_query"],
            "answer_components": components, "answer_claims": claims, "retrieved_chunks": [],
            "answer": saved["answer"], "evidence_status": "partial", "evidence_gap": saved["evidence_gap"]})
    assert [c["id"] for c in result["answer_components"]] == ["C1", "C2"]
    assert result["evidence_status"] == "complete" and result["evidence_gap"] == ""
    assert "does not establish" not in result["answer"]
    assert result["faithful"] is True
