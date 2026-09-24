# Controlled textual diagnostics v1

48 **development** cases in 12 document groups, constructed from the pinned SciFact corpus.
These are source-anchored minimal edits and evidence-deletion controls, reviewed by AI.
They are **not independent expert annotations** and do not replace SciFact's original labels.

`families.json` contains all authored claims, source sentence IDs, the changed slot,
equivalence rationale and annotation rationale. Every family contains:

1. A supported fact with a nonessential-sentence deletion control.
2. An equivalent wording or exact unit conversion under the same evidence view.
3. One conflicting fact under that same view.
4. The original supported claim with the necessary source evidence removed, labelled insufficient.

Both evidence views remove the same number of sentences. This reduces one length cue but
does not eliminate all artifacts. The input is an intentionally modified source view, not
an unmodified full abstract. Original sentence order is preserved and view IDs map back to
original sentence IDs. Neither variant labels nor gold rationale reach the model prompt.

All documents are known SciFact train sources, disjoint by known document IDs from official
dev and the previous 30-case pilot. All four variants stay in one source group. No group in
this batch is a held-out evaluation group. Source selection was curated for interpretability,
not sampled to represent medical questions in natural use.

## Reproduce

Use the project Python environment and run from the repository root. The official external
corpus remains in ignored local cache; none of these commands starts Qdrant or local GPU inference.

```sh
python scripts/verification/prepare_scifact.py
python scripts/verification/compare_diagnostics.py report --output data/verification/controlled_v1/run01
python scripts/verification/inspect_diagnostic.py controlled-cbf7066acbffe873 --run data/verification/controlled_v1/run01
```

Reporting and inspecting are offline after the data download. Inspection shows source
sentences, original sentence IDs, construction rationale and every arm's actual response.
Do not publish the source-deleted version as an unedited paper excerpt.

For a **new paid run**, configure the ignored `.env` for the documented Flash profile and
choose a new output directory. Prepare freezes source and code hashes, labels, prompts and
schedule before inference. Run refuses an existing attempt or changed inference code.

```sh
python scripts/verification/compare_diagnostics.py prepare --output .benchmark-runtime/controlled_repeat
python scripts/verification/compare_diagnostics.py run --output .benchmark-runtime/controlled_repeat
python scripts/verification/compare_diagnostics.py report --output .benchmark-runtime/controlled_repeat
```

The three arms each make one logical call per case: `direct`, `structured`, and
`structured_no_fields`, with a maximum of three simultaneous requests. The same-output
reducer ablation uses saved component judgments and makes no additional calls. The raw
streaming SDK records response model identifiers and usage; no Pro fallback is available.
The SDK can retry transport errors once. Results and execution errors are retained as they
finish; unstarted cases are counted as `not_run` if an interrupted run is reported offline.

`protocol.json` contains the predeclared schedule and inference code hashes; `manifest.json`
binds all cases to source versions and view mappings; `predictions.jsonl` preserves every
logical outcome; `run.json` records the execution settings; `metrics.json` is recomputable.
API errors never become insufficient evidence. Exact quote binding does not prove support.
Runtime is measured; equal per-call token caps do not mean equal actual computation.

See [label policy](../../../docs/verification-label-policy.md),
[technical route](../../../docs/verification-roadmap.md), and
[comparison report](../../../docs/verification-v0.5-diagnostics.md).
