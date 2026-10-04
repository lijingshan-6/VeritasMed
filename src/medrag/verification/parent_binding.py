"""Mechanical, versioned localization; no extraction or semantic judgments."""

from copy import deepcopy

BINDING_VERSION = "parent-exact-v1"


def locate_quote(text: str, quote: str) -> dict:
    """Only unique exact text is bound. Include overlapping occurrences and never guess."""
    if not quote or not quote.strip():
        return {"status": "empty_quote", "match_count": 0, "span": None, "candidates": []}
    starts, cursor = [], 0
    while (start := text.find(quote, cursor)) >= 0:
        starts.append(start)
        cursor = start + 1
    spans = [{"start": s, "end": s + len(quote), "text": quote, "offset_unit": "unicode_codepoint"}
             for s in starts[:8]]
    return {"status": "unique" if len(starts) == 1 else "ambiguous" if starts else "not_found",
            "match_count": len(starts), "span": spans[0] if len(starts) == 1 else None,
            "candidates": spans, "candidates_truncated": len(starts) > len(spans)}


def bind_parent_fragments(answer: str, parent_quote: str, quotes: list[str]) -> dict:
    """Bind fragments only inside one exact parent; return global code-point offsets.

    Repeated/missing parents never authorize a global first-match fallback. A
    uniquely bound fragment demonstrates text location, not a faithful claim.
    """
    parent = locate_quote(answer, parent_quote)
    scope = parent["span"]
    fragments = []
    for quote in quotes:
        if scope is None:
            binding = {
                "status": "unresolved_parent",
                "span": None,
                "match_count": 0,
                "candidates": [],
                "candidates_truncated": False,
                "parent_status": parent["status"],
            }
        else:
            binding = deepcopy(locate_quote(scope["text"], quote))
            for candidate in binding["candidates"]:
                candidate["start"] += scope["start"]
                candidate["end"] += scope["start"]
            # locate_quote shares its unique span with candidates[0]. Deepcopy
            # preserves that identity: shift once, not twice.
            if binding["span"] is not None:
                assert answer[binding["span"]["start"] : binding["span"]["end"]] == quote
        fragments.append(
            {**binding, "quote": quote, "search_scope": scope, "binding_version": BINDING_VERSION}
        )
    return {
        "binding_version": BINDING_VERSION,
        "parent_binding": parent,
        "answer_bindings": fragments,
        "position_valid": bool(quotes)
        and scope is not None
        and all(b["status"] == "unique" for b in fragments),
    }
