"""Mechanical, versioned localization; no extraction or semantic judgments."""

from copy import deepcopy

from .quote_audit import locate_quote

BINDING_VERSION = "parent-exact-v1"


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
