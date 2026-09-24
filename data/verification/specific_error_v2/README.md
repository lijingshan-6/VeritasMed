# Specific-error development review v2

This is an **AI-authored, post-hoc diagnostic**, not new expert gold or independent semantic accuracy.
It covers all 33 original error spans in the existing 48 RAGTruth train answers. Official labels,
offsets, original scores and all saved model outputs remain unchanged.

- `review_notes.json`: 33 explicit reviews referring to actual claim IDs, with rationale and frozen
  saved-output text hashes. Semantic decisions were made by the development assistant after reading
  the public explanations and outputs. The script does not infer them from keyword matches.
- `report.json` / `report.md`: generated cards with public explanations, actual model reasons,
  evidence quotations and original position hits. JSON retains all claim judgments for both methods
  on all 48 answers, including unmarked answers. Raw calls remain in the linked original runs;
  their warnings are not independently adjudicated as false.
- `binding_replay.json`: a separate **software-only counterfactual** over 126 existing context-v1
  outputs. Drops only occurrence/context ID fields; keeps every quote, verdict and reason. It is not
  a new model run, and its success must not replace historical failures.

Review states: `identified` = the specific public issue was explicitly identified; `partial` = only
part of a compound issue; `overlap_only` = flags overlap but reasons address another issue;
`missed` = no specific detection; `unresolved` = rationale/reference/scope disagreement prevents
credit. Unresolved and partial rows stay in the 33-row inventory. Identification does not establish
three-class correctness, overall precision, all other claim judgments or clinical truth.

Reproduce from the repository root after the pinned source download; no key or model calls:

```sh
python scripts/verification/answer_benchmark.py download
python scripts/verification/specific_error_report.py
python scripts/verification/rebind_saved_quotes.py
```

Direct and Context each have 26 identified, 2 partial and 2 unresolved issues. Direct has 3 misses;
Context has 2 misses and 1 overlap-only. These review counts are not an independent correctness score.
The binding-only replay completes 125/126 versus historical 123/126, recovering cases 4492 and 736.
The inexact source quote in 2978 remains unresolved. No formerly complete audit becomes incomplete
on this finite sample; unique-only binding can still reject repeated quotations in other inputs.
