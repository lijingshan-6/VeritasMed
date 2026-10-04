"""Regressions for failures recorded in the bundled v0.8 medical conversations.

These cases are already exposed development examples, not independent test results.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from medrag.agent.evidence import bind_components, preserve_result_context
from medrag.agent.utils import build_answer_from_claims
from medrag.retrieval.retriever import RetrievedChunk

RUN = Path(__file__).resolve().parents[1] / "data/demo/conversations/run01"


def saved_answer(name):
    for line in (RUN / f"{name}-events.jsonl").read_text(encoding="utf8").splitlines():
        event = json.loads(line)["event"]
        if event.get("event") == "done":
            return event["data"]
    raise AssertionError("No completed answer recorded")


def test_shared_source_sentence_keeps_the_second_requested_answer():
    # Evidence limits, turn 3: both components were bound to the same duration sentence.
    # Projecting it twice erased the mortality answer in all three regenerations.
    components = [{**c, "answer": ""} for c in saved_answer("v08-evidence-limits-turn-3")["answer_components"]]
    cite = components[0]["evidence"][0]["citation"]
    mortality = "That sentence does not report any five-year mortality result."
    claims = [{"component_id": "C1", "text": "Glucose fell for about 3 hours.", "cite": [cite]},
              {"component_id": "C2", "text": mortality, "cite": [cite]}]
    answer, _ = build_answer_from_claims(preserve_result_context(components, claims))
    assert "sustained for approximately 3 hours" in answer
    assert mortality.rstrip(".") in answer


def test_shared_sentence_is_not_reprojected_during_repair():
    # During repair only C2 is projected; C1's retained quotation is already rendered.
    components = [{**c, "answer": ""} for c in saved_answer("v08-evidence-limits-turn-3")["answer_components"]]
    cite = components[0]["evidence"][0]["citation"]
    retained = preserve_result_context(components[:1], [{"component_id": "C1", "text": "x", "cite": [cite]}])
    repair = {"component_id": "C2", "text": "No five-year mortality result is reported.", "cite": [cite]}
    assert preserve_result_context(components[1:], [*retained, repair]) == [repair]


def test_distinct_numeric_components_are_still_quoted():
    source = RetrievedChunk("pubmed:1:0", "Arm A improved by 5%. Arm B improved by 2%.", 0.9,
                            {"source": "pubmed", "doc_id": "1", "pmid": "1"})
    components = bind_components([
        {"requirement": "Arm A result", "status": "supported", "evidence_ids": ["E1"], "required_details": ["5%"]},
        {"requirement": "Arm B result", "status": "supported", "evidence_ids": ["E2"], "required_details": ["2%"]},
    ], [], [source])
    claims = [{"component_id": "C1", "text": "A was better.", "cite": ["PMID:1"]},
              {"component_id": "C2", "text": "B was smaller.", "cite": ["PMID:1"]}]
    texts = [c["text"] for c in preserve_result_context(components, claims)]
    assert texts == ['The study reports: "Arm A improved by 5%."', 'The study reports: "Arm B improved by 2%."']


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
