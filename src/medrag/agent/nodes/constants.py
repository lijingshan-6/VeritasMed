"""Graph budgets and retrieval thresholds; no runtime resources."""
from __future__ import annotations




MAX_REWRITES = 2          # up to 3 retrieval attempts total


MAX_REGEN    = 2          # up to 2 regen attempts; no confidence-skip bypass


GRADE_THRESHOLD = 0.75    # raised from 0.6 — stricter pass so rewrite fires meaningfully


_GRADE_THRESHOLDS = {
    "factual":   0.6,   # raised from 0.5
    "synthesis": 0.75,  # raised from 0.6
    "multihop":  0.8,   # raised from 0.7
}


HISTORY_SUMMARIZE_EVERY = 10  # L2 compression after this many turns


CANDIDATE_K  = 20         # hybrid retrieval candidate pool


PER_QUERY_K  = 12         # bound multi-part retrieval before grouped reranking


TOP_K        = 5          # chunks passed to generator


MAX_EVIDENCE = 8          # cap after completing the leading document(s) with their other sections
