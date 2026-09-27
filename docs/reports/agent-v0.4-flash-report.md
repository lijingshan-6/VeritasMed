# v0.4 Flash: answer quality and release evidence

Completed on 2026-09-23 as the **v0.4 research showcase milestone**, published as source tag
[`v0.4.0`](https://github.com/lijingshan-6/medrag-agent/tree/v0.4.0). Final development
passes **15/15**, independent repetition **10/10**, and the first held-out evaluation **31/35
(88.6%)** under the unchanged frozen rubric. All requests in these three runs completed.
Four held-out failures remain visible; publication does not establish clinical reliability.

## Frozen implementation

| Run | Strict answer passes | Unsupported additions | Required evidence | Coverage-label disagreements | Mean seconds |
|---|---:|---:|---:|---:|---:|
| [Development](agent-v0.4-flash-development-cases.md) | 15/15 | 0 | 13/13 answerable | 0 | 51.9 |
| [Independent repetition](agent-v0.4-flash-repeat-cases.md) | 10/10 | 0 | 8/8 answerable | 1 | 57.0 |
| [First held-out evaluation](agent-v0.4-flash-test-cases.md) | 31/35 | 0 | 32/32 answerable | 6 | 72.5 |

The repeated original seven cases pass 7/7; the additional 002/006/011 diagnostics pass 3/3.
There are no execution errors or missing required qualifiers in these two runs. Repetition's
006 correctly states the longitudinal evidence limit but displays complete coverage. These
content scores therefore do not establish fully reliable UI labels.

The [freeze manifest](../../data/benchmark/veritasmed_v1_1/v04_flash_release/freeze_manifest.json)
records exact code, configuration, input hashes and the 65-file source snapshot. The question
hash and scorer remain unchanged. No code or prompts were tuned using held-out outputs for this release.
The freeze preceded held-out inference at **09:50:05 UTC**. The test split was run once;
there was no best-of selection or replacement of failed answers. These 35 questions are now
exposed and cannot serve as unseen confirmation for subsequent fixes.

The selected model is Flash for all Agent roles. Earlier attempts used OpenHub
`deepseek-v4.1-flash`; after a billing interruption, the user supplied a new compatible
gateway, `https://www.cun.ai/v1`, listing `DeepSeek-V4.1-Flash`. These provider identifiers
do not establish identical underlying weights. The final three runs all use the new gateway;
their scores are not a controlled comparison of providers or models.
The production graph
retrieves real literature, matches the requested studies, binds an evidence outline, generates
a cited answer and reviews the complete answer together with its gaps. The frozen gold
contract and scorer are unchanged. Source-first assessments remain engineering reviews,
not independent clinician reviews or evidence of clinical reliability.

## What the held-out failures mean

All 32 answerable questions retrieved their required source chunks. The four failures therefore
show that source retrieval and literal quotations do not ensure a complete answer:

| Case | Retained failure |
|---|---|
| [023](agent-v0.4-flash-test-cases.md#vmg-023) | Diagnostic metrics and further-study needs are present, but the declared gap about real clinical adoption and patient outcomes is missing. |
| [037](agent-v0.4-flash-test-cases.md#vmg-037) | Risk-group survival rates replace the required independent MVI-risk and AFP-L3 associations, omitting their hazard ratios and intervals. |
| [041](agent-v0.4-flash-test-cases.md#vmg-041) | The composite endpoint is called only “primary outcome”, losing its distinction from mortality alone; the required causal-design limitation is also absent. |
| [049](agent-v0.4-flash-test-cases.md#vmg-049) | The gap concerns test performance and muscle activation instead of guided rehabilitation versus usual care and pain/disability outcomes. |

There were **zero unsupported material additions observed**, **one omitted endpoint qualifier**,
and omitted claims/boundaries as described above. The internal model check passed **35/35**,
including all four failed answers. It is not an independent correctness assessment.

## Coverage labels and judgment limits

Held-out coverage disagrees with the frozen labels in 007, 021, 023, 041, 047 and 048. These are
**disagreements, not six equivalent factual errors**. In particular, 021 asks broadly about three
groups while its gold claims cover narrower findings; 047's wording can request an additional
fracture count versus X-ray that the gold does not require; 048 calls detection performance
“image quality” while the source lacks direct image-quality metrics for one method. The model's
extra gaps in these three cases are defensible and expose annotation-scope ambiguities.
The questions and classifications were not revised during scoring. A later dataset version
should clarify this wording without retrospectively inflating this run's score.

030 is another explicit judgment choice: the answer preserves P=0.21 and the interval crossing
zero, which was accepted as retaining nonsignificance even without a plain-language yes/no.
The case notes preserve that reasoning so another reviewer can challenge it. All assessments
are AI source-first engineering judgments; no independent clinician adjudication was performed.

The independent 006 repeat and the real fastMRI+ browser answer also display complete coverage
while correctly explaining an unestablished outcome. Read the answer and passages, not just the label.

## Runtime and presentation

All Agent roles request `DeepSeek-V4.1-Flash`, thinking enabled, reasoning effort `high`, an
output ceiling of 32,768 tokens per call, streaming transport and a 240-second client timeout.
There is no Pro fallback. Research uses BGE-M3/BGE reranking on CUDA against the frozen
44,768-chunk index; at most three questions run at once, sharing serialized GPU operations.
The three-passage CPU demo is separate and is not benchmark evidence.

Held-out median latency was **62.3 seconds**, maximum **254.8 seconds**, excluding shared model
initialization. No CLI answer exceeded the browser's 300-second deadline, but 007 needed two
retrieval rewrites and came close. Four answer regenerations occurred. A whole-set browser run
was not performed. The separate actual Flash browser example completed in 49.30 seconds;
see [screenshots, downloaded answer and source page](../configuration.md#current-flash-browser-run--2026-09-23).

The provider supplied usage for **0/77** development calls, **0/53** repeat calls and only
**2/194** held-out calls. The latter report 668 input and 2,938 output tokens for those two calls
only; these are **not run totals or a cost estimate**.

Critical-fact source projection appears in 13/15 development answers, 8/10 repeats and 33/35
held-out answers (including adjacent prognostic context in one refusal). Mean answer lengths
are 155, 185 and 193 words respectively, with some much longer, repetitive answers. The
cross-sectional design-scope repair is implemented but triggered in none of these three runs;
the observed score change is not evidence of that rule's causal contribution. There is no
ablation against plain RAG, no independent model judge, and no proof of broader medical accuracy.

## Preserved development work

See the [worklog](../archive/worklogs/agent-v0.4-flash-worklog.md). Every completed attempt is retained. These reused development questions do not provide independent generalization evidence.

| Run | Strict passes | Unsupported additions | Missing qualifiers | Mean seconds |
|---|---:|---:|---:|---:|
| [Probe 1](agent-v0.4-flash-probe1-cases.md) | 4/7 | 4 | 0 | 141.1 |
| [Probe 2](agent-v0.4-flash-probe2-cases.md) | 5/7 | 1 | 1 | 89.8 |
| [Probe 3](agent-v0.4-flash-probe3-cases.md) | 4/7 | 0 | 1 | 105.2 |
| [First full development](agent-v0.4-flash-development-first-cases.md) | 12/15 | 1 | 1 | 73.7 |
| [Second full development](agent-v0.4-flash-development-round2-cases.md) | 13/15 | 1 | 0 | 82.5 |
| [Third full development](agent-v0.4-flash-development-round3-cases.md) | 13/15 | 1 | 1 | 86.0 |
| [Fourth full development, billing interrupted](agent-v0.4-flash-billing-blocked-cases.md) | 10/15 | 0 in completed answers | 0 in completed answers | 63.3* |
| [First full development on the new gateway](agent-v0.4-flash-cun-first-cases.md) | 14/15 | 1 | 0 | 51.8 |
| [Final full development](agent-v0.4-flash-development-cases.md) | 15/15 | 0 | 0 | 51.9 |

The second and third complete runs still contained an unsupported assertion, so neither met
the unchanged zero-addition criterion. The current implementation renders critical numerical,
population and method components from selected exact source sentences; requested design
explanations remain generative. This trades some fluency for factual fidelity.

The fourth run completed ten answers that passed source-first assessment, then OpenHub returned
HTTP 403 `insufficient balance` for 024, 032, 034, 039 and 042. All five execution failures remain
in the denominator; **10/15 is not a completed quality result or a release pass**. The mean marked
with an asterisk includes failed requests and is not a successful-answer speed comparison.
The original artifact and recorded runtime files are preserved. That interrupted attempt is
separate from the subsequent complete runs on the new endpoint.

The first complete new-gateway run still invented measurement timing in 032 ("concurrently
measured"). It therefore also misses the zero-addition criterion, despite 15/15 internal
self-checks. The final implementation explicitly repairs that narrow case with the bound
cross-sectional design and an association-versus-intervention limitation; safe explanations
and other study designs retain normal model review. See the worklog for the scope of this rule.

All earlier Qwen and Pro/Flash comparisons remain historical results under their own settings;
they are linked from the [documentation index](../README.md) and are not pooled into the current score.

## Offline inspection

Saved cases can be read without API access, a GPU or the full research index. To recalculate
the final runs' already reviewed decisions, install the small offline dependency and run:

```sh
python -m pip install "pydantic>=2.7,<3"
python scripts/benchmark/report_flash_release.py --directory data/benchmark/veritasmed_v1_1/v04_flash_development_final --case-name agent-v0.4-flash-development-cases
python scripts/benchmark/report_flash_release.py --directory data/benchmark/veritasmed_v1_1/v04_flash_repeat --case-name agent-v0.4-flash-repeat-cases
python scripts/benchmark/report_flash_release.py --directory data/benchmark/veritasmed_v1_1/v04_flash_test --case-name agent-v0.4-flash-test-cases
```

This recomputes mappings and arithmetic; it does not generate new answers or independently
verify the semantic judgments. A new run requires its own source-reviewed assessment file.
The raw answers, hash-bound assessments, scored results and summaries live in the corresponding
folders under `data/benchmark/veritasmed_v1_1/`; the freeze manifest identifies the exact inputs.

The next iteration should address missing outcome/endpoint requirements, concise presentation
and coverage-label meaning. Use these exposed cases for development, and obtain new independent
questions or external review before making another claim about unseen performance.
