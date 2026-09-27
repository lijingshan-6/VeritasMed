# RAGTruth whole-answer development pilot

Protocol: [v0.5 answer audit](../../../docs/plans/v0.5-answer-audit.md).
Results: [experiment report](../../../docs/reports/verification-v0.5-answer-audit.md).
UI: [real audit panel](../../../docs/audit-demo.md).

## Provenance and scope

The [official RAGTruth repository](https://github.com/ParticleMedia/RAGTruth) provides human
hallucination spans in naturally generated answers. We pin commit
`c103204b9ce28d6bbad859304bf30de72b8ed8fe` and record both input file hashes.
Its repository license is MIT; original sources retain their own provenance. See the
[upstream license](https://github.com/ParticleMedia/RAGTruth/blob/c103204b9ce28d6bbad859304bf30de72b8ed8fe/LICENSE).
The upstream notice is preserved in [LICENSE-RAGTruth](LICENSE-RAGTruth).
We do not bundle the full news corpus; the download command obtains the pinned files locally.
Saved predictions contain model outputs and quoted evidence; the manifest preserves the selected
official error spans and comments without rewriting labels after seeing predictions.

24 distinct training source groups: 12 answers with annotated errors and 12 without annotated errors,
selected by a fixed hash ordering. Only Summary / quality=good is used; training candidates sharing
a source with official test are excluded. The protocol registers the exact 48-job schedule before calls.
60 official test source/response IDs are reserved by metadata only, not run or used to tune prompts.
These public data may have been seen in model pretraining. This is a nonmedical development pilot,
not expert medical validation, a representative prevalence estimate, or a final held-out score.

RAGTruth is not silently relabelled into our supported/contradicted/insufficient schema.
We compare binary error detection and error locations, keeping `implicit_true` spans as unsupported
by the provided source. Unextracted, failed and unrun errors remain in the gold denominator.
Character overlap is only a location proxy; broad claim flags can inflate recall and lower precision.

## Contents

- `run01/manifest.json`: selection, source IDs, human error spans, input hashes, reserved test IDs.
- `run01/protocol.json`: prompts, pre-run source hashes, schedule and comparison limits.
- `run01/run.json`: actual gateway settings and timestamps, no credentials.
- `run01/predictions.jsonl`: every completed attempt, including raw model JSON and failures.
- `run01/metrics.json`: all-answer metrics, per-answer scores, reported usage and model identifiers.
- `run01/environment.json`: relevant installed package versions captured during this run.

The protocol code hashes cover the audit engine, scorer, runner and transport. UI/API files are
outside this frozen research implementation. Direct uses one call; split uses extraction plus
per-claim calls. Inputs are equal; computation budgets are not equal. No Pro fallback is used.

## Replay and reproduce

From the repository root, in the configured Python environment:

```sh
python scripts/verification/answer_benchmark.py download
python scripts/verification/answer_benchmark.py report
python scripts/verification/answer_report.py
python scripts/run_audit_demo.py
```

`report` recomputes metrics from saved outputs without model calls and checks equality against the
saved metrics. The panel reconstructs exact input texts and checks their hashes before highlighting.
To run a new paid experiment, preserve the previous run and use a new directory:

```sh
python scripts/verification/answer_benchmark.py prepare --output data/verification/ragtruth_v1/run02
python scripts/verification/answer_benchmark.py run --output data/verification/ragtruth_v1/run02
python scripts/verification/answer_benchmark.py report --output data/verification/ragtruth_v1/run02
```

The run command requires the Flash `.env` profile documented in the project README. It freezes
the current code at preparation, executes at most three requests concurrently, and records access,
balance or rate-limit failures without overwriting earlier attempts. A failed run is not resumed
silently; a later attempt gets a new directory. The UI replays `run01` so demonstration examples remain stable.
