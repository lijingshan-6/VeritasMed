"""Fresh graph inputs shared by the web and MCP entry points.

Each public request also needs a new checkpoint ID: passing empty lists does
not clear LangGraph's additive history, rewrite or repair reducers.
"""


def build_initial_state(query: str) -> dict:
    return {
        "query": query,
        "original_query": "",
        "answer_components": [],
        "answer_claims": [],
        "binding_issues": [],
        "repair_component_ids": [],
        "repair_history": [],
        "rewritten_queries": [],
        "retrieved_chunks": [],
        "relevance_score": 0.0,
        "relevant": False,
        "grade_reason": "",
        "rewrite_hint": "",
        "iterations": 0,
        "answer": "",
        "citations": [],
        "confidence": 0.0,
        "faithful": False,
        "faithfulness_issues": "",
        "regen_count": 0,
        "history": [],
        "summary": "",
    }
