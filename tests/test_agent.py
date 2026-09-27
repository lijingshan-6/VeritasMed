"""Graph structure and unit tests for the LangGraph agentic loop.

These tests do NOT require Qdrant or Ollama — they mock all external calls
and only verify:
  1. Graph topology (all expected nodes present, edges correct)
  2. Conditional routing logic (_after_grade, _after_check)
  3. State transformations for rewrite_query, increment_regen, route_query
  4. SqliteSaver checkpointer wires up without error

Run with:
    pytest tests/test_agent.py -v
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from medrag.retrieval.retriever import RetrievedChunk


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sample_state():
    """Minimal AgentState-compatible dict for testing."""
    return {
        "query": "What is the mechanism of aspirin?",
        "original_query": "",
        "query_type": "factual",
        "source_scope": "general",
        "answer_mode": "direct",
        "search_queries": [],
        "answer_requirements": [],
        "rewritten_queries": [],
        "retrieved_chunks": [],
        "retrieval_groups": [],
        "relevance_score": 0.0,
        "relevant": False,
        "grade_reason": "No relevant context found.",
        "rewrite_hint": "Try expanding to include COX inhibition.",
        "iterations": 0,
        "answer": "",
        "citations": [],
        "confidence": 0.0,
        "evidence_status": "complete",
        "evidence_gap": "",
        "faithful": False,
        "faithfulness_issues": "",
        "regen_count": 0,
        "history": [],
        "summary": "",
    }


# ── Test 1: Graph topology ─────────────────────────────────────────────────────

class TestGraphTopology:
    """Verify the compiled graph contains all expected nodes."""

    def test_all_nodes_present(self):
        from medrag.agent.graph import app

        nodes = set(app.nodes.keys())
        expected = {
            "__start__",
            "route", "retrieve", "rerank", "grade",
            "rewrite", "generate", "check", "inc_regen",
            "append_history", "summarize_gate", "summarize",
        }
        missing = expected - nodes
        assert not missing, f"Missing nodes: {missing}"

    def test_graph_type(self):
        from langgraph.graph.state import CompiledStateGraph
        from medrag.agent.graph import app

        assert isinstance(app, CompiledStateGraph)

    def test_checkpointer_attached(self):
        from medrag.agent.graph import app

        assert app.checkpointer is not None


# ── Test 2: Conditional routing ───────────────────────────────────────────────

class TestConditionalRouting:
    """Unit tests for _after_grade and _after_check edge functions."""

    def test_after_grade_relevant(self, sample_state):
        from medrag.agent.graph import _after_grade

        state = {**sample_state, "relevance_score": 0.8, "iterations": 0}
        assert _after_grade(state) == "generate"

    def test_after_grade_rewrite(self, sample_state):
        from medrag.agent.graph import _after_grade

        state = {**sample_state, "relevance_score": 0.3, "iterations": 0}
        assert _after_grade(state) == "rewrite"

    def test_after_grade_max_rewrites_hit(self, sample_state):
        from medrag.agent.graph import _after_grade

        state = {**sample_state, "relevance_score": 0.2, "iterations": 2}
        assert _after_grade(state) == "generate"   # cap hit → generate anyway

    def test_after_grade_exact_threshold(self, sample_state):
        from medrag.agent.graph import _after_grade

        state = {**sample_state, "relevance_score": 0.75, "iterations": 0}
        assert _after_grade(state) == "generate"   # default synthesis threshold reached

    def test_after_check_faithful(self, sample_state):
        from medrag.agent.graph import _after_check

        state = {**sample_state, "faithful": True, "regen_count": 0}
        assert _after_check(state) == "end"

    def test_after_check_unfaithful_first_regen(self, sample_state):
        from medrag.agent.graph import _after_check

        state = {**sample_state, "faithful": False, "regen_count": 0}
        assert _after_check(state) == "regenerate"

    def test_after_check_unfaithful_cap_hit(self, sample_state):
        from medrag.agent.graph import _after_check

        state = {**sample_state, "faithful": False, "regen_count": 2}
        assert _after_check(state) == "end"   # regeneration cap reached

    def test_after_check_confidence_does_not_bypass_evidence_check(self, sample_state):
        from medrag.agent.graph import _after_check

        # first-gen, unfaithful, but has citations + confidence ≥ threshold
        state = {
            **sample_state,
            "faithful": False,
            "regen_count": 0,
            "citations": ["PMID:12345", "PMC:doc196"],
            "confidence": 0.99,
        }
        assert _after_check(state) == "regenerate"

    def test_after_check_regen_fires_without_citations(self, sample_state):
        from medrag.agent.graph import _after_check

        # first-gen, unfaithful, no citations → smart gate does not fire
        state = {**sample_state, "faithful": False, "regen_count": 0, "citations": [], "confidence": 0.9}
        assert _after_check(state) == "regenerate"


# ── Test 3: Node state transformations ────────────────────────────────────────

class TestNodeTransformations:
    """Unit tests for node functions with mocked LLM."""

    def test_rewrite_increments_counter(self, sample_state):
        from medrag.agent.nodes import rewrite_query

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="aspirin COX inhibitor prostaglandin synthesis"
        )

        with patch("medrag.agent.nodes.planning.make_llm_think", return_value=mock_llm):
            state = {**sample_state, "iterations": 1}
            result = rewrite_query(state)

        assert result["iterations"] == 2
        assert result["query"] == "aspirin COX inhibitor prostaglandin synthesis"
        assert len(result["rewritten_queries"]) == 1

    def test_increment_regen_increments_counter(self, sample_state):
        from medrag.agent.nodes import increment_regen

        state = {**sample_state, "regen_count": 0}
        result = increment_regen(state)
        assert result["regen_count"] == 1

        state2 = {**sample_state, "regen_count": 1}
        result2 = increment_regen(state2)
        assert result2["regen_count"] == 2

    def test_route_query_initialises_counters(self, sample_state):
        from medrag.agent.nodes import route_query

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='{"type": "factual", "reason": "single fact requested"}'
        )

        with patch("medrag.agent.nodes.planning.make_llm_fast", return_value=mock_llm):
            result = route_query(sample_state)

        assert result["iterations"] == 0
        assert result["regen_count"] == 0

    def test_route_query_preserves_original_query(self, sample_state):
        from medrag.agent.nodes import route_query

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='{"type": "factual", "reason": "single fact"}'
        )

        with patch("medrag.agent.nodes.planning.make_llm_fast", return_value=mock_llm):
            result = route_query(sample_state)

        assert result["original_query"] == sample_state["query"]

    def test_route_query_extracts_search_plan_and_answer_requirements(self, sample_state):
        from medrag.agent.nodes import route_query

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=(
                '{"type":"synthesis","reason":"two studies",'
                '"source_scope":"multi_source",'
                '"answer_mode":"compare",'
                '"search_queries":["prostate MRI AI triage performance",'
                '"breast ultrasound SCAR-Net radiologist performance"],'
                '"answer_requirements":["Report the prostate result with comparator",'
                '"Report the breast result with all performance measures"]}'
            )
        )

        with patch("medrag.agent.nodes.planning.make_llm_fast", return_value=mock_llm):
            result = route_query(sample_state)

        assert result["search_queries"] == [
            "prostate MRI AI triage performance",
            "breast ultrasound SCAR-Net radiologist performance",
        ]
        assert result["answer_requirements"] == [
            "Report the prostate result with comparator",
            "Report the breast result with all performance measures",
        ]
        assert result["source_scope"] == "multi_source"
        assert result["answer_mode"] == "compare"

    def test_route_retries_invalid_json_once(self, sample_state):
        from medrag.agent.nodes import route_query

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content='{"type":"synthesis"'),
            MagicMock(
                content=(
                    '{"type":"factual","reason":"one fact",'
                    '"source_scope":"single_study","search_queries":["aspirin mechanism"],'
                    '"answer_requirements":["Report the mechanism"]}'
                )
            ),
        ]

        with patch("medrag.agent.nodes.planning.make_llm_fast", return_value=mock_llm):
            result = route_query(sample_state)

        assert mock_llm.invoke.call_count == 2
        assert result["source_scope"] == "single_study"

    def test_route_detects_evidence_boundary_question(self, sample_state):
        from medrag.agent.nodes import route_query

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=(
                '{"type":"factual","source_scope":"single_study","reason":"one study",'
                '"search_queries":["AI triage biopsies outcomes"],'
                '"answer_requirements":["Does the study reduce unnecessary biopsies?",'
                '"Does the study improve patient outcomes?"]}'
            )
        )
        state = {
            **sample_state,
            "query": "Does the supplied study establish fewer biopsies or better outcomes?",
        }

        with patch("medrag.agent.nodes.planning.make_llm_fast", return_value=mock_llm):
            result = route_query(state)

        assert result["answer_mode"] == "evidence_boundary"

    def test_route_does_not_accept_boundary_mode_for_what_question(self, sample_state):
        from medrag.agent.nodes import route_query

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=(
                '{"type":"synthesis","source_scope":"single_study",'
                '"answer_mode":"evidence_boundary","reason":"incorrect model label",'
                '"search_queries":["DYNAMITE structural changes"],'
                '"answer_requirements":["Report structural changes"]}'
            )
        )
        state = {
            **sample_state,
            "query": "What structural changes did the DYNAMITE study report?",
        }

        with patch("medrag.agent.nodes.planning.make_llm_fast", return_value=mock_llm):
            result = route_query(state)

        assert result["answer_mode"] == "direct"

    def test_route_keeps_one_named_model_with_build_and_validation_in_one_source(
        self, sample_state
    ):
        from medrag.agent.nodes import route_query

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=(
                '{"type":"synthesis","source_scope":"multi_source",'
                '"answer_mode":"compare","reason":"build and performance",'
                '"search_queries":["SCAR-Net architecture","SCAR-Net validation"],'
                '"answer_requirements":["How SCAR-Net was built",'
                '"How SCAR-Net changed radiologist performance"]}'
            )
        )
        state = {
            **sample_state,
            "query": (
                "How was SCAR-Net built and validated for distinguishing postoperative "
                "breast scars from recurrent lesions, and how much did it change "
                "radiologist performance?"
            ),
        }

        with patch("medrag.agent.nodes.planning.make_llm_fast", return_value=mock_llm):
            result = route_query(state)

        assert result["source_scope"] == "single_study"

    def test_route_keeps_unanswered_effect_with_the_named_workflow(self, sample_state):
        from medrag.agent.nodes import route_query

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=(
                '{"type":"synthesis","source_scope":"multi_source",'
                '"answer_mode":"compare","reason":"result and gap",'
                '"search_queries":["prostate MRI AI triage performance",'
                '"prostate MRI real-world effect"],'
                '"answer_requirements":["Report sensitivity and specificity",'
                '"State what remains untested"]}'
            )
        )
        state = {
            **sample_state,
            "query": (
                "What sensitivity-specificity tradeoff did simulated prostate-MRI AI "
                "triage show, and what real-world clinical effect remains untested?"
            ),
        }

        with patch("medrag.agent.nodes.planning.make_llm_fast", return_value=mock_llm):
            result = route_query(state)

        assert result["source_scope"] == "single_study"

    def test_hybrid_retrieve_runs_each_planned_query_and_merges_chunks(self, sample_state):
        from medrag.agent.nodes import hybrid_retrieve

        chunks = {
            "original": RetrievedChunk("pubmed:1:0", "one", 0.9, {"source": "pubmed", "doc_id": "1"}),
            "component a": RetrievedChunk("pubmed:2:0", "two", 0.8, {"source": "pubmed", "doc_id": "2"}),
            "component b": RetrievedChunk("pubmed:3:0", "three", 0.7, {"source": "pubmed", "doc_id": "3"}),
        }
        retriever = MagicMock()
        retriever.retrieve.side_effect = lambda query, k: [chunks[query]]
        state = {
            **sample_state,
            "query": "original",
            "original_query": "original",
            "search_queries": ["component a", "component b"],
        }

        with patch("medrag.agent.nodes.retrieval._get_retriever", return_value=retriever):
            result = hybrid_retrieve(state)

        assert [call.args[0] for call in retriever.retrieve.call_args_list] == [
            "original",
            "component a",
            "component b",
        ]
        assert [chunk.chunk_id for chunk in result["retrieved_chunks"]] == [
            "pubmed:1:0",
            "pubmed:2:0",
            "pubmed:3:0",
        ]
        assert [group["query"] for group in result["retrieval_groups"]] == [
            "original",
            "component a",
            "component b",
        ]

    def test_rerank_keeps_candidates_until_study_identity_is_assessed(self, sample_state):
        from medrag.agent.nodes import rerank_chunks

        target = RetrievedChunk(
            "pubmed:1:0", "target", 0.9, {"source": "pubmed", "doc_id": "1"}
        )
        adjacent = RetrievedChunk(
            "pubmed:2:0", "adjacent", 0.8, {"source": "pubmed", "doc_id": "2"}
        )
        reranker = MagicMock()
        reranker.rank_groups.return_value = [[adjacent, target]]
        selector = MagicMock()
        selector.invoke.return_value = MagicMock(content='{"source_ids":["PMID:1"]}')
        state = {
            **sample_state,
            "original_query": "What did the supplied study establish?",
            "source_scope": "single_study",
            "retrieved_chunks": [target, adjacent],
            "retrieval_groups": [
                {"query": "target study", "chunks": [target, adjacent]},
            ],
        }

        with patch("medrag.agent.nodes.retrieval._get_reranker", return_value=reranker), patch(
            "medrag.agent.nodes.retrieval.make_llm_fast", return_value=selector,
        ):
            result = rerank_chunks(state)

        assert "PMID:2" in selector.invoke.call_args.args[0][1].content
        assert reranker.rank_groups.call_args.args[0] == [("target study", [target, adjacent])]
        assert result["retrieved_chunks"] == [target]

    def test_append_history_records_original_query_and_answer(self, sample_state):
        from medrag.agent.nodes import append_history

        state = {
            **sample_state,
            "original_query": "original question about aspirin",
            "answer": "Aspirin inhibits COX.",
        }
        result = append_history(state)
        assert len(result["history"]) == 1
        assert result["history"][0]["query"] == "original question about aspirin"
        assert result["history"][0]["answer"] == "Aspirin inhibits COX."

    def test_append_history_falls_back_to_query_when_original_missing(self, sample_state):
        from medrag.agent.nodes import append_history

        state = {**sample_state, "original_query": "", "answer": "Some answer."}
        result = append_history(state)
        assert result["history"][0]["query"] == sample_state["query"]

    def test_generate_falls_back_on_json_parse_error(self, sample_state):
        from medrag.agent.nodes import generate_answer_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="Aspirin inhibits COX-1 and COX-2 enzymes."   # plain text, not JSON
        )

        with patch("medrag.agent.nodes.generation.make_llm_fast", return_value=mock_llm):
            result = generate_answer_node(sample_state)

        # Should not raise; uncited claims are dropped → disclaimer
        assert "do not contain sufficient cited evidence" in result["answer"]
        assert result["citations"] == []
        assert result["confidence"] == 0.0

    def test_generate_answers_the_original_question_after_rewrite(self, sample_state):
        from medrag.agent.nodes import generate_answer_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='{"claims":[],"confidence":0,"evidence_status":"insufficient","evidence_gap":"The retrieved documents do not establish the requested comparison."}'
        )
        state = {
            **sample_state,
            "query": "narrow rewritten retrieval query",
            "original_query": "full user question with both comparison arms",
            "answer_requirements": ["Cover both comparison arms"],
        }

        with patch("medrag.agent.nodes.generation.make_llm_fast", return_value=mock_llm):
            result = generate_answer_node(state)

        messages = mock_llm.invoke.call_args.args[0]
        assert "full user question with both comparison arms" in messages[1].content
        assert "Cover both comparison arms" in messages[1].content
        assert result["evidence_status"] == "insufficient"
        assert result["evidence_gap"] in result["answer"]

    def test_evidence_boundary_mode_discards_adjacent_partial_claims(self, sample_state):
        from medrag.agent.nodes import generate_answer_node

        chunk = RetrievedChunk(
            "pubmed:1:0",
            "The simulation improved specificity but did not measure patient outcomes.",
            0.9,
            {"source": "pubmed", "doc_id": "1"},
        )
        gap = "The study does not establish fewer biopsies or improved patient outcomes."
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=(
                '{"claims":[{"text":"Specificity improved.","cite":["PMID:1"]}],'
                '"confidence":0.7,"evidence_status":"partial",'
                f'"evidence_gap":"{gap}"}}'
            )
        )
        state = {
            **sample_state,
            "answer_mode": "evidence_boundary",
            "retrieved_chunks": [chunk],
        }

        with patch("medrag.agent.nodes.generation.make_llm_fast", return_value=mock_llm):
            result = generate_answer_node(state)

        assert result["evidence_status"] == "insufficient"
        assert result["answer"] == gap
        assert result["citations"] == []

    def test_faithfulness_check_requires_complete_answer_and_correct_boundary(self, sample_state):
        from medrag.agent.nodes import check_faithfulness

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=(
                '{"supported":true,"complete":false,"boundary_correct":true,'
                '"issues":"The answer omits the comparator and confidence interval."}'
            )
        )
        state = {
            **sample_state,
            "query": "rewritten query",
            "original_query": "What were the effect, comparator, and confidence interval?",
            "answer_requirements": ["Include effect, comparator, and confidence interval"],
            "answer": "The treatment was associated with improvement [PMID:1].",
        }

        with patch("medrag.agent.nodes.checking.make_llm_think", return_value=mock_llm):
            result = check_faithfulness(state)

        messages = mock_llm.invoke.call_args.args[0]
        assert "What were the effect, comparator, and confidence interval?" in messages[1].content
        assert result["faithful"] is False
        assert "omits the comparator" in result["faithfulness_issues"]

    def test_regen_prompt_repeats_the_json_contract(self):
        from medrag.agent.prompts import REGEN_SYSTEM

        assert '"claims"' in REGEN_SYSTEM
        assert '"cite"' in REGEN_SYSTEM
        assert '"confidence"' in REGEN_SYSTEM
        rendered = REGEN_SYSTEM.format(faithfulness_issues="unsupported claim")
        assert '"claims"' in rendered

    def test_grade_relevance_trusts_boolean_over_score(self, sample_state):
        from medrag.agent.nodes import grade_relevance

        mock_llm = MagicMock()
        # LLM says relevant=true but score=0.4 (below threshold)
        mock_llm.invoke.return_value = MagicMock(
            content='{"relevant": true, "score": 0.4, "reason": "partial", "rewrite_hint": ""}'
        )

        with patch("medrag.agent.nodes.grading.make_llm_think", return_value=mock_llm):
            result = grade_relevance(sample_state)

        # relevant=true should bump score to at least GRADE_THRESHOLD
        assert result["relevance_score"] >= 0.6

    def test_grade_preserves_original_requirements_when_outline_is_missing(self, sample_state):
        from medrag.agent.nodes import grade_relevance
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content='{"relevant":true,"score":0.95}')
        requirements = ["Report treatment time", "Report toxicity"]
        with patch("medrag.agent.nodes.grading.make_llm_think", return_value=mock_llm):
            result = grade_relevance({**sample_state, "answer_requirements": requirements})
        assert result["answer_requirements"] == requirements
        assert [c["requirement"] for c in result["answer_components"]] == requirements
        assert all(c["status"] == "missing" for c in result["answer_components"])

    def test_requirement_filter_drops_details_unrelated_to_question(self):
        from medrag.agent.nodes.planning import _filter_requirements_for_query

        result = _filter_requirements_for_query(
            "How did AI change prostate MRI and breast ultrasound diagnostic performance?",
            [
                "Prostate MRI sensitivity and specificity changed with AI",
                "Breast ultrasound AUC changed with AI",
                "Generalizability limitations and evidence gaps",
            ],
        )

        assert result == [
            "Prostate MRI sensitivity and specificity changed with AI",
            "Breast ultrasound AUC changed with AI",
        ]

    def test_requirement_filter_drops_unasked_generic_evidence_boundary(self):
        from medrag.agent.nodes.planning import _filter_requirements_for_query

        result = _filter_requirements_for_query(
            "In the cross-sectional pilot, what cardiac MRI findings were reported?",
            [
                "Report the cardiac MRI findings from the pilot",
                "Evidence boundaries regarding the pilot study's conclusions",
            ],
        )

        assert result == ["Report the cardiac MRI findings from the pilot"]







# ── Test 4: Memory helpers ────────────────────────────────────────────────────

class TestMemoryHelpers:
    """Test L2 summarisation trigger logic."""

    def test_maybe_summarize_triggers_at_10(self):
        from medrag.agent.graph import _maybe_summarize

        state_10 = {"history": [{}] * 10}
        assert _maybe_summarize(state_10) == "summarize"

    def test_maybe_summarize_skips_at_9(self):
        from medrag.agent.graph import _maybe_summarize

        state_9 = {"history": [{}] * 9}
        assert _maybe_summarize(state_9) == "end"

    def test_maybe_summarize_triggers_at_20(self):
        from medrag.agent.graph import _maybe_summarize

        state_20 = {"history": [{}] * 20}
        assert _maybe_summarize(state_20) == "summarize"

    def test_maybe_summarize_empty_history(self):
        from medrag.agent.graph import _maybe_summarize

        state_empty = {"history": []}
        assert _maybe_summarize(state_empty) == "end"
