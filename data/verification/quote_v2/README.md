# Quote-v2 development comparison

The frozen `run01` compares two different tasks on **8 new public train source groups**:

- Whole answer: original Direct and exact-quotes v2, 8 each; 4 answers have 5 public error spans,
  4 have no error marking (not a guarantee of correctness).
- Fixed target: frozen v1 verifier and quote-v2, 8 each. Four targets are the first public error
  spans with the full original answer as context; four are unique exact source sentence/line copies
  used as simple authored supported controls. This task supplies the target and measures no extraction.
- Four quote-v2 repetitions: whole/fixed for the first selected annotated and unmarked sources.

36 Flash calls total, at most three active requests; no Pro fallback. Before calling, the protocol
records ordered jobs, prompts, code/input hashes and non-secret model settings. No official test
source is used, and exact source-text duplicates of previous or test sources are excluded.

```sh
python scripts/verification/answer_benchmark.py download
# Offline, no API calls:
python scripts/verification/quote_benchmark.py report
python scripts/verification/quote_report.py
```

To run a new replication (billable), explicitly use a new output directory for both commands:

```sh
python scripts/verification/quote_benchmark.py prepare --output data/verification/quote_v2/run02
python scripts/verification/quote_benchmark.py run --output data/verification/quote_v2/run02
```

Never overwrite `run01` or replace failures with retries. Predictions include all raw final outputs,
usage, transport metadata and binding failures. Metadata cannot certify underlying model weights.
Fixed binary agreement is not a three-class or rationale score; exact-copy controls are easy and
neither task proves clinical reliability. Quote-v2 changes wording and output fields together, so
this comparison cannot isolate one prompt field's causal effect. Direct remains the default.

Completed: 36/36 audits, 294,320 reported tokens. Whole-answer error hits are 3/5 for both methods;
fixed binary agreement is 8/8 for each, with the easy controls and label-boundary limitations above.
See [full results](run01/results.md) and the [interpretation](../../../docs/verification-v0.5-specific-errors.md).
