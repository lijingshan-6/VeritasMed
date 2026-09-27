# v0.7 controlled workflow comparison

Protocol: [v0.7 implementation plan](../../../docs/plans/v0.7-agent-comparison.md).
Interpretation: [research report](../../../docs/reports/verification-v0.7-report.md).
Every final case: [readable outputs](../../../docs/reports/verification-v0.7-cases.md).

## Task and grouping

One named-paper fact query per connected source group: 20 development, 40 final.
These source groups were reserved before v0.6 train/calibration partitioning. A question
includes the paper title and claim but not the correct document ID, gold relation or
rationale. Eight candidate abstracts are frozen per query: target plus seven development
distractors. Public SciFact labels evaluate the specified paper/claim relation only.

`manifest.json` records the source IDs, seeded selections, candidate order and budgets.
Each run directory contains its schedule/input/code hashes (`protocol.json`), actual
provider configuration and start/end metadata (`attempt-*.json`), and every result
including original drafts, failures and tool traces (`predictions.jsonl`).

`method-freeze.json` separates development from final. The final set is now exposed for
any reader: future repeats must not be described as new held-out tests. Public dataset
training contamination remains possible even with local source grouping.

The original 60 development records and their metrics are retained in `development-original/`.
Conflicting finish instructions and mixed JSON/DSML output made its autonomous arm unusable.
Before any final inference, a complete second development round in `development/` clarified
the prompt and added recorded format normalization. Only a leading JSON object is interpreted;
DSML suffixes are never tool results/evidence/model history. A valid bare answer may be wrapped
as finish, without relaxing read/citation checks or budgets. `frozen-source-v2.json` archives the
revised source. First-run failures are not used as evidence of superior Agent reasoning, and
the two rounds are not cherry-picked or pooled into a larger independent sample.

## Methods and meaning

- `direct_reader`: a single Flash call reads all eight complete abstracts.
- `autonomous_tools`: Flash decides search/read/verify/finish using validated JSON actions.
- `structured_workflow`: programmed search/read/draft/verify; disagreements preserve the
  original draft as needs-review. No automatic repair or model-as-gold scoring.

Both tool methods share the corpus/tool implementations and a six-model-call/eight-tool-call
ceiling; verification consumes model-call budget. The autonomous interface is application
JSON, not provider-native tool calling. Actual calls/tokens/latency differ and are reported.

This is a **bounded new research workflow**, not an evaluation of the historical Ask graph
with dense/sparse retrieval, query rewriting and answer repair. The known target title makes
search easier. No claim of broad medical Agent superiority follows from these results.

## Recompute and replay

Follow [research reproduction](../../../docs/research-reproduction.md) to download the pinned
source inputs and recompute saved metrics without model calls. `development-metrics.json`
and `final-metrics.json` are derived from all planned queries. Needs-review, wrong documents,
invalid answers and failed calls do not count as correct non-support. Original draft scores
and accepted-result scores are reported separately, with paired source-group uncertainty.

The three UI bundles in `data/demo/research` are development cases selected by seed **before**
workflow inference. They contain actual source text/tool traces for no-key replay. Such
third-party text retains its original terms; the repository code license does not relicense
the papers or [SciFact](https://github.com/allenai/scifact).
