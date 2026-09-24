# Context / metatext development experiment

See the [predeclared protocol](../../../docs/plans/v0.5-context-audit.md).
Flash only; 126 scheduled one-call audits: 72 regression ablations, 48 paired new-source audits,
and 6 repeated context audits. The old Direct control is reused for regression only; new-source
Direct and Context are interleaved within this run. No original official test source is used.

`run01/manifest.json` fixes public RAGTruth train IDs, input hashes and unchanged original error spans.
`protocol.json` fixes code hashes, prompts, settings (no key), execution order and the prior output hash.
The upstream RAGTruth revision/license is the same as [ragtruth_v1](../ragtruth_v1/README.md).
Original source texts are in the local ignored cache, not repeatedly copied into predictions.

From the repository root, in the audit Python environment:

```sh
python scripts/verification/answer_benchmark.py download
python scripts/verification/context_benchmark.py report
python scripts/verification/context_report.py
```

Reporting makes no model calls. It reproduces `metrics.json` and `results.md` from saved outputs.
The second command requires all scheduled attempts to be saved, reproduces `paired_cases.md` and
`paired_effects.json`, and evaluates the declared development promotion conditions. Its tables are
post-run presentation of the frozen scorer, not a new model judge.
The frozen protocol recorded the old control's native Windows byte hash. The reporting script accepts
only LF/CRLF equivalents so a Git checkout on another platform can reproduce it, and records the LF
canonical digest in `paired_effects.json`. JSON contents and record order must still match exactly;
the frozen protocol and original control records are not rewritten.
Unrun/failed cases remain in the fixed denominator. Metatext overlaps with gold errors are counted
separately and never removed from the reference. Character Jaccard measures repeat stability,
not correctness; two empty warning sets are defined to have Jaccard 1.

For a **new paid run**, use a fresh output directory; this repeats exposed development cases, not unseen testing:

```sh
python scripts/verification/context_benchmark.py prepare --output data/verification/context_v1/run02
python scripts/verification/context_benchmark.py run --output data/verification/context_v1/run02
python scripts/verification/context_benchmark.py report --output data/verification/context_v1/run02
```

Never overwrite a previous attempt or modify frozen code while it is running. HTTP access/balance/rate
errors stop new submissions and retain in-flight results. Raw final model outputs and provider-reported
usage/model names are saved; private chain-of-thought is not saved.

`prior_disagreement_ledger.json` / `.md` enumerate every previous warning and below-half/missed gold
span. They are mechanical reference comparisons with the original explanations and bound evidence,
**not expert adjudication, new gold labels, or proof that every unmatched warning is wrong**.
