# SciFact fixed-evidence pilot

This is **development data**, not a held-out clinical reliability estimate.
It uses public human annotations from [SciFact](https://github.com/allenai/scifact).
The original corpus is downloaded into the ignored `.benchmark-runtime/scifact/` cache;
it is not copied into this repository. SciFact source terms still apply to those files.

`selection.json` fixes 30 claim/document pairs before inference: 10 supported,
10 contradicted and 10 insufficient, sampled deterministically from official train.
Every known related document for a selected claim must be absent from official dev and
from other selected claims. These constraints concern known IDs, not guaranteed absence
of near duplicates or model pretraining exposure. We do not use the unlabelled official test.

Each model sees the claim, title and **all abstract sentences**, including their original
zero-based IDs. It never receives reference labels, rationale sets or split metadata.
An insufficient label refers only to the supplied abstract, not all published literature.

Run from the repository root using the Python environment described in the main README.
These commands do not run Qdrant, retrieval, the QA graph or local GPU inference.

```sh
python scripts/verification/prepare_scifact.py
python scripts/verification/report_fixed_evidence.py --run data/verification/scifact_pilot/run01_flash_direct
python scripts/verification/inspect_case.py scifact-train-1373-21003930 --run data/verification/scifact_pilot/run01_flash_direct
```

Preparation downloads a pinned official archive; a changed download fails rather than
silently changing the benchmark. Reporting and inspection are offline after preparation.
Inspection reconstructs exact quotes, source hashes and Unicode codepoint offsets from
the cached corpus. Published predictions contain references and offsets, not full abstracts.

To run a **new paid experiment**, configure the ignored `.env` for the documented Flash
profile, then use a fresh directory. No Pro fallback or repair calls are made.

```sh
python scripts/verification/run_fixed_evidence.py --output .benchmark-runtime/scifact_flash_repeat --workers 3
python scripts/verification/report_fixed_evidence.py --run .benchmark-runtime/scifact_flash_repeat
```

Each run saves `run.json` (prompt, configuration, normalized code hashes and provenance),
`predictions.jsonl` (every returned result or error) and `metrics.json` (offline scoring).
One logical call is made per case; the SDK may retry a failed transport request once.
Missing usage stays unavailable. API errors and invalid references are not counted as
insufficient evidence. An interrupted run retains completed records and can be reported
offline; unstarted cases remain `not_run`. Never overwrite a run to hide failures.

Exact agreement with one annotated rationale is measured separately from label agreement:
a different sentence set can be defensible. Programmatic quote binding proves source
location, not semantic support. Do not turn this small balanced sample into a confidence
percentage on a medical answer.

See [technical route](../../../docs/verification-roadmap.md),
[implementation plan](../../../docs/plans/v0.5-text-verification.md) and
[pilot report](../../../docs/verification-v0.5-pilot.md).
