# R2 protocol, fixed before inference

This study diagnoses extraction from supplied text. It is not independent clinical gold
or the unavailable R3 public-label generalization evaluation. Direct / Flash remains default.

## Inputs and source separation

The manifest contains 24 previously unused SciFact source groups, split by a fixed
document hash into 12 development and 12 final groups. Each has four variants: selected
original abstract sentences, authored paraphrase, shared context in a separate paragraph,
and a deliberately changed first quantity that repeats the second target quantity.
The 24 numerical error controls are included in the 96 answers, not extra samples.
Six sources also have explicit negation targets. All sources are complete pinned abstracts.

The authoring AI inspected the first 28 hash-ranked eligible sources, recorded four
input-only exclusions, and annotated these targeted constraints before any candidate call.
This is not independent expert review. Final inputs were visible during construction;
their model outputs must remain unseen until the development candidate is frozen.
All four variants of a source stay in the same split.

Natural development uses 12 preselected, disjoint RAGTruth **train** sources: six with
marked errors, six without. No official-test source or label is used. Natural and constructed
results are separate. Source and target annotations are never passed to inference; only
the answer and original source text are model inputs.

## Methods and bounded schedule

Direct, unchanged atomic_v1, and qualifier-anchored atomic_v2 receive the same inputs.
Direct has one call; Atomic has at most three calls and 48 extracted facts. At most three
API requests run concurrently; Flash only, SDK retries disabled, failures retained.

There are 144 development audits, 36 natural audits and 144 final audits. Six development
case IDs are fixed for Direct/v2 repetition: first run plus two further attempts, adding
24 audits. Repetitions measure variability and do not vote on truth. At most two candidate
development revisions are allowed; no revision is required just to obtain a positive result.
Freeze code, manifest and scoring before one final pass. Do not retry final failures for a
better score. Infrastructure continuations retain original failures and run identity.

## Measurements fixed before inference

The scoring implementation is v08_r2_metrics.py, fingerprinted with each run.

- **Target anchor coverage:** fraction of preannotated literal phrases covered by exact
  answer/qualifier spans. Multiple occurrences are explicitly retained as acceptable spans.
  This is targeted phrase coverage, not exhaustive extraction recall.
- **Single-claim anchor co-presence:** at least one parsed claim contains all required
  anchors for that target. Direct can quote a compound passage; co-presence alone does
  not establish that group and value are interpreted correctly.
- **Literal preservation:** the target quantity appears in the normalized interpretation
  (or Direct's original quote) of such a claim. Exact wording is strict; spelled-out/
  converted quantities can fail it without being semantically wrong.
- **Constructed error controls:** separately report whether the deliberately wrong
  quantity survives extraction, gets a completed warning, is accepted, or is unassessed.
  Completed relations are model outputs on authored controls, not clinical truth rates.
- **Negation targets:** report phrase coverage/co-presence separately. No negation
  keyword test is called proof of semantic equivalence.
- **Execution:** all planned answers, full completion, unassessed claims, compound/uncertain
  parsing, declared exact duplicates, calls, reported tokens and recorded latency.
- **Natural:** marked error-span overlap with completed warnings, completion and warning
  frequency in unmarked answers. Unmarked warnings are not automatically false positives.

Paired summaries resample source groups, never treat the four variants as four independent
papers. Any small-sample interval is descriptive. Six prespecified repeat inputs also
receive a separately labelled AI development review of actual group/qualifier interpretation;
this review cannot convert constructions to expert gold or inform final input relabelling.
Mechanical results and semantic development observations are reported separately.

## Reproduction

Use saved outputs first. Running v08_r2_run.py calls the paid Flash service. The input
manifest and failed attempts must remain unchanged; a new invocation resumes only unattempted
jobs under an identical protocol. Prepare and run one phase at a time.

The inference Python/library versions are recorded in `environment-flash.json`; endpoint,
exact model name, generation settings and dispatch time are in each phase's dispatch file.
This protocol was written before inference. The generated [report](../../../../docs/reports/verification-v0.8-report.md)
and `summary.json` describe the completed run without changing its inputs or labels.

Completion: all 348 scheduled audit records are retained across the four phases, including
partial results. The saved records contain 577 model calls. Direct / Flash remains default;
there is no new semantic generalization claim and no final-case retry selected for its score.
