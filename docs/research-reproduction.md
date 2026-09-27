# Reproduce the audit and workflow research

UI replay needs only the main README's lightweight setup. Research inference is optional,
uses the configured Flash account, and can make hundreds of paid calls. There is no Pro fallback.
Use the published raw results first; re-running an exposed evaluation is a repeat, not a new test.

## Restore source inputs

From the repository root, using the lightweight Python environment:

```sh
python scripts/verification/prepare_scifact.py
python scripts/verification/answer_benchmark.py download
```

These download pinned upstream data into `.benchmark-runtime`, verify the pinned input,
and leave the published experiment records intact. The original old medical corpus is not
needed to use frozen v0.6/v0.7 partitions. `v06_prepare.py` rebuilds the historical exposure
inventory and requires that old local corpus; it is not a fresh-clone startup requirement.

## Recompute saved results without model calls

```sh
python scripts/verification/v06_report.py pilot
python scripts/verification/v06_report.py final
python scripts/verification/v06_whole_report.py
python scripts/verification/v06_ablation_report.py
python scripts/verification/v06_budget.py report
python scripts/verification/v06_medical_review.py
python scripts/verification/v07_report.py development
python scripts/verification/v07_report.py development --run-dir data/verification/v07/development-original
python scripts/verification/v07_report.py final
python scripts/verification/v07_cases.py
python scripts/verification/v07_export.py export
```

Calibration uses NumPy/scikit-learn in the [separate research environment](minicheck-research.md).
Once its dependencies are installed, these commands also make no model calls:

```sh
python scripts/verification/v06_report.py calibrate
python scripts/verification/v06_report.py calibration_final
python scripts/verification/v07_figures.py
python scripts/verification/v07_release_reports.py
```

Labels and raw outputs are not overwritten. Metric JSON files are deterministic derivatives.
Published runs can include failures; inspect all planned denominators, not only successful calls.
Natural-answer matching measures error-span localization; it is not full semantic accuracy.
`v06_medical_review.py` reproduces a separately labelled post-hoc sensitivity view for the
documented source-view issue. It does not edit the frozen labels or replace primary scores.

## v0.8 offline development results

After restoring the pinned datasets above, replay the saved Atomic extractions with no model calls:

~~~sh
python scripts/verification/v08_rebind.py --output output/v08-r1-replay
~~~

This produces all old/new bindings and a table of recovered/unresolved positions. It includes
the three distinct GRADE demo audits, with repeats and ablations reported separately.
It does not change old judgments or count recovered positions as checked facts.
See the [localization report](verification-v0.8-localization.md).

The separate [source inventory](verification-v0.8-exposure.md) requires the old local medical
corpora as well as the pinned datasets. Fresh clones can inspect its saved snapshots;
rebuilding that local inventory is not required to run the app or the localization replay.

## A separately recorded paid repeat

Create a new ignored output directory, retaining the original results:

```sh
python scripts/verification/v06_fixed.py prepare --split pilot --method flash --run-dir .benchmark-runtime/my-fixed-repeat
python scripts/verification/v06_fixed.py run --split pilot --method flash --run-dir .benchmark-runtime/my-fixed-repeat

python scripts/verification/v06_whole.py prepare --dataset medical_development --run-dir .benchmark-runtime/my-answer-repeat
python scripts/verification/v06_whole.py run --dataset medical_development --run-dir .benchmark-runtime/my-answer-repeat

python scripts/verification/v07_benchmark.py prepare --split development --run-dir .benchmark-runtime/my-workflow-repeat
python scripts/verification/v07_benchmark.py run --split development --run-dir .benchmark-runtime/my-workflow-repeat
```

Each run has a frozen schedule and input/source hashes. Resuming skips existing attempts;
failed outputs remain failures rather than being silently retried. Provider access/balance/rate
errors stop new batches. Repeating failed cases requires a separately identified experiment.
Do not run several API runners simultaneously: each uses up to three requests internally.
Later milestone stages use a bounded continuous queue: jobs launch in frozen order when a
slot is free and are saved on completion. Earlier attempts used groups of three with a barrier;
the `dispatch` field records the new policy. This changes waiting time, not inference settings
or case selection. Already in-flight results are retained if a provider block stops dispatch.

## Reading the source snapshots

`data/verification/v06/frozen-source.json` preserves exact inference code used when protocols
were prepared. Release formatting was accepted only where Python ASTs were identical, including
prompt string values. Runners map format-equivalent code to that original fingerprint; actual
behavior/prompt changes fail the frozen-protocol comparison. Published runtime versions are in
`environment-flash.json` and `environment-minicheck.json`.

The workflow comparator required a development-only protocol correction before final inference:
its finish instructions conflicted, and some received replies mixed JSON with DSML. All 60 first
development records remain in `v07/development-original`. A complete second round uses explicit
finish instructions and recorded format normalization; no final question was used to repair it.
`v07/frozen-source-v2.json` preserves that exact revised source. A DSML suffix is retained in the
raw reply but never executed, included in model history, or treated as source evidence. Complete
bare answer objects may be wrapped as finish; read/citation validation and budgets still apply.

Raw JSONL records use actual file newlines. Unicode paragraph/line separators inside JSON
strings are preserved by the reader; they must not be treated as record boundaries.

The optional `run_v06_v07.py` dispatcher was used to continue the original experiment schedule.
It requires a completed medical development run and provider configuration; it is **not** a
no-key report command. The offline commands above are the appropriate reproduction entry.

The v0.7 comparison uses a bounded research workflow sharing tools with its autonomous comparator.
It does not run the historical Ask graph with dense/sparse retrieval, rewrite and answer repair.
The corpus, named-paper task, model-call budgets and this limitation are part of the protocol,
not conclusions inferred from a good score.


## v0.8 saved conversations and qualifier diagnostics

The following commands make no model calls:

```sh
python scripts/prepare_conversation_demo.py
node --experimental-strip-types frontend/scripts/package-conversation-demo.mjs
python scripts/verification/v08_r2_report.py --markdown docs/verification-v0.8-report.md
```

The first rebuilds the 15 original abstract passages from attributed snapshots. The second
packages unchanged saved Ask and audit responses using the browser's own export/import
contract. The third summarizes every recorded R2 attempt, retaining failures; intervals
resample source groups with all four variants together. Natural answers, artificial errors,
mechanical anchors and semantic development observations are separate.

`python scripts/run_showcase.py` opens the no-key conversation replay. The raw nine-question
protocol, WebSocket streams and returned audits are in `data/demo/conversations/`.

**Paid inference:** `scripts/record_conversation_demo.py` calls the running full Ask service;
`v08_r2_run.py run` calls Flash. Do not invoke them just to inspect a release. Their default
locations resume only unattempted jobs, so a deliberate independent run needs a separately
identified output directory and unchanged inputs/protocol. Do not overwrite historical failures
or replace the frozen final results. Run phases serially; maximum API concurrency is three.
R3 remains deferred because the unused public-label pool does not support a new semantic
comparison. Reusing exposed historical final cases is a regression exercise, not a new test.
