# Agent v0.4: source-bound answers, with unresolved scope and execution failures

The separate full development run passes **9/15** under the unchanged v1.1 rubric,
compared with **10/15** in v0.3. It finds all required evidence for **12/13** answerable
questions. There are **3 incorrectly scoped or unsupported
material additions** and **2 missing required qualifiers**.

**This remains a v0.4 candidate.** The 13/15 strict-pass target, zero-unsupported-additions condition
and 13/13 retrieval target are not met; structured output is also unstable on boundary questions.
The **35-question test split remains unused**.
The implemented evidence display and working demonstration do not imply reliable clinical answers.

## What changed

- Match named studies before drafting, then keep each requested component with its source,
  exact quotation, necessary details and evidence gap.
- Bind generation and targeted repair to that same outline. Preserve supported parts alongside
  unanswered parts; remove a rejected outcome even when the repair budget is exhausted.
- Restore omitted source-bound numbers as attributed quotations, normalizing HTML and thousands
  separators first. This can still produce repetitive wording.
- Expose complete, partial and insufficient coverage, expandable quotations and source navigation.
  Coverage and the model check are not accuracy scores.
- Accept Ollama server-binding addresses on Windows by connecting through loopback; preserve remote hosts.

## Independent runs and timing

All three runs used the fixed Agent implementation `a945a8f` and the same
`qwen3.5:9b` digest/configuration. Focus questions were 006, 010, 011, 013, 014 and 024.
Every question used isolated state. No focus answer was substituted into the full development run.

| Run | Strict passes | Unsupported additions | Execution errors | Mean latency | Slowest retained attempt | Logged rewrites / regenerations |
|---|---:|---:|---:|---:|---|---:|
| Focus A | 5/6 | 1 | 0 | 95.0 s | 195.9 s (VMG-014) | 0 / 3 |
| Focus B | 4/6 | 1 | 1 | 119.4 s | 381.2 s (VMG-014) | 1 / 0 |
| Full development | 9/15 | 3 | 1 | 84.8 s | 227.0 s (VMG-042) | 0 / 6 |

The full development sequence was paused at the user's request after six completed answers,
then resumed on the same implementation. Those six result objects are unchanged. The interrupted
VMG-012 attempt had no final answer; its partial time and the user pause are excluded. The resumed
sequence includes a second cold startup, so these are retained-attempt timings, not an uninterrupted
wall-clock benchmark. No completed failed answer was discarded.

Focus B's empty VMG-014 answer is an **execution failure**, not a correct refusal. Its 381.2 seconds
remain in the mean. Failure-row state counters default to zero; the table instead counts events
in the retained logs, which record one rewrite before that error. The web API has a 300-second
deadline, so that CLI attempt would time out earlier in the UI.

## Comparison with v0.3

| Metric | v0.3 | v0.4 candidate |
|---|---:|---:|
| Strict pass | 10/15 | 9/15 |
| All required evidence found@5, answerable questions | 13/13 | 12/13 |
| Required-claim Recall@5 | 100.0% | 96.2% |
| nDCG@5 / MRR@5 | 0.9546 / 0.9487 | 0.9467 / 0.9487 |
| Mapped core-claim completeness / citation coverage | 100.0% / 100.0% | 96.7% / 96.7% |
| Answerability score | 14/15 | 14/15 |
| Missing required qualifiers | 5 | 2 |
| Unsupported or incorrectly scoped additions | 2 | 3 |
| Mean retained-attempt latency | 91.3 s | 84.8 s |

Core-claim mapping measures the main requested findings; it does not judge every additional sentence.
Correct numbers can still be assigned to the wrong population or stage of a study. The model context
budget and sampling profile also changed, so this comparison does not isolate one architectural cause.

| Question | v0.3 | v0.4 | Change |
|---|---|---|---|
| [VMG-001](agent-v0.4-cases.md#vmg-001) | Pass | Pass | Retained pass |
| [VMG-002](agent-v0.4-cases.md#vmg-002) | Pass | Pass | Retained pass |
| [VMG-006](agent-v0.4-cases.md#vmg-006) | Fail | Pass | Improved |
| [VMG-009](agent-v0.4-cases.md#vmg-009) | Pass | Fail | Regressed |
| [VMG-010](agent-v0.4-cases.md#vmg-010) | Fail | Pass | Improved |
| [VMG-011](agent-v0.4-cases.md#vmg-011) | Fail | Fail | Still fails |
| [VMG-012](agent-v0.4-cases.md#vmg-012) | Pass | Pass | Retained pass |
| [VMG-013](agent-v0.4-cases.md#vmg-013) | Fail | Pass | Improved |
| [VMG-014](agent-v0.4-cases.md#vmg-014) | Fail | Fail | Still fails |
| [VMG-018](agent-v0.4-cases.md#vmg-018) | Pass | Fail | Regressed |
| [VMG-024](agent-v0.4-cases.md#vmg-024) | Pass | Pass | Retained pass |
| [VMG-032](agent-v0.4-cases.md#vmg-032) | Pass | Fail | Regressed |
| [VMG-034](agent-v0.4-cases.md#vmg-034) | Pass | Pass | Retained pass |
| [VMG-039](agent-v0.4-cases.md#vmg-039) | Pass | Pass | Retained pass |
| [VMG-042](agent-v0.4-cases.md#vmg-042) | Pass | Fail | Regressed |

## Remaining failures and conservative scope decisions

SCAR-Net's abstract says it **developed** the model using 34,376 images from 5,710 patients at
four hospitals. It separately reports multicenter validation improvements, without stating a
validation denominator. VMG-009 and the repeated VMG-011 answers attach the development counts
to validation/performance wording. Under the existing all-material-statements support rule, these
are counted conservatively as scope errors. The numbers are not invented; their asserted role is
not established. The original wording and source quotes are published in the case pages so readers
can assess this decision. Earlier preliminary passes were revised during sentence-level adjudication;
the final scores include the scope penalty.

The earlier third-study insertion in VMG-011 is absent from these runs, but binding sources has
not reliably preserved every within-paper role. Population count, development data, test subset
and outcome comparison need separate treatment in the next implementation iteration. This is
not evidence of an overall answer-quality improvement.

Two other full-run regressions matter: VMG-018 loses the anisotropic-diffusion study and omits
image-shift/Hadamard details from its supported fMRI component; VMG-032 omits the required
non-significant dialysis-vintage contrast. VMG-014 refuses the requested clinical-benefit inference,
but adds 'without real biopsies' even though the source explicitly lists histopathology and/or
follow-up as reference standards. A sensible refusal can still contain an unsupported rationale.

The model check also remains unreliable. It accepted these scope errors, and sometimes rejected
source-supported population details or requested clinical results that the paper did not measure.
In the full development run, false passes are **VMG-009, VMG-011, VMG-032**;
false rejections are **VMG-001**.
These labels come from the external source-first decisions, not a second model vote.

Strict failures in the full development run:

- **VMG-009**: The development cohort, network modules and all diagnostic before/after ranges with P values are correct. The extra sentence stating that the model was validated in a design involving 34,376 images and 5,710 patients reuses development counts as validation counts. The source does not report that validation denominator, so this is one incorrectly scoped material addition despite complete core-claim coverage.

- **VMG-011**: Both requested comparisons, intervals and P values are retained, and the source quotation distinguishes 400 test patients from 500 total prostate participants. However, 'Using 34,376 ultrasound images from 5,710 patients ... improved radiologists performance' attaches SCAR-Net development-data counts directly to the validation-performance result without identifying the development role. The abstract reports those counts for development, not a validation denominator. Conservatively count one incorrectly scoped material addition, consistently with both focus runs.

- **VMG-014**: The answer correctly refuses to infer biopsy reduction or patient-outcome benefits from the simulation. However, 'a simulation without real biopsies' is an unsupported description of the underlying data: the abstract explicitly uses histopathology and/or at least three years of follow-up as reference standards. No prospective biopsy-use comparison is not the same as no real biopsy data. Count one unsupported material addition even though the comparative-benefit boundary is acknowledged; the broad 'only' wording also overlooks the reported examinations-triaged endpoint.

- **VMG-018**: The answer retains the fMRI through-plane/in-plane acceleration and simulated/experimental scan-time, SNR and CNR results, so its main C1 finding is mapped. It omits the required image-shift/2D-Hadamard method detail (one missing qualifier) and entirely lacks C2's anisotropic-diffusion/Rician-noise filtering method and validation. PMID:41903663 was not retained in retrieval. The explicit gap is truthful about the retrieved evidence, but cannot replace the missing answerable study; no cross-study ranking or unsupported outcome is added.

- **VMG-032**: The main higher-flow/LVMI association, mean difference 22.83, 95% CI 0.37-45.29, P=0.046 and 241-patient cross-sectional population are correct. The causal/intervention boundary is correctly stated. However, C1 explicitly requires the contrast that dialysis vintage was not significantly associated; that contrast and its uncertainty are absent (one missing required qualifier). The core claims are mapped, but strict pass remains false.

- **VMG-042**: Execution failed when evidence planning returned unusable structured output after the bounded retry; no answer was saved. An empty technical failure does not acknowledge the missing nonadaptive comparator and is not a valid abstention. Retain the failed attempt and its 226.98-second latency in the denominator. The failure row resets intermediate state; its empty retrieved-chunk list does not prove that retrieval was never attempted.

## Demonstration and limits

A fresh Windows directory was installed using Python 3.12.7, the 163-package CPU lock, the editable
project and `npm ci`. The bundled three-passage index and API/frontend started successfully. A real
fastMRI+ question returned its supported annotation findings and diagnostic-accuracy gap in **57.48 s**,
with source and context navigation working. Model files were already cached; uncached download speed
was not measured. See the [Live screenshot](../assets/v04-live-partial.png) and [demo walkthrough](../configuration.md).

Guided screenshots remain clearly labelled authored fixtures. The Live fixture also uses authored
summaries; the benchmark instead uses its frozen research corpus. Docker, MiMo and macOS/Linux were
not exercised for this candidate. The API's 300-second limit and the structured-output failure are
operating limitations, not guarantees that every arbitrary question will finish.

All retained answers were read against the frozen claims and source passages by Codex. No independent
clinician adjudicated them. This small development-exposed 2026 snapshot does not establish general
medical reliability, unseen-test accuracy or superiority over plain RAG. Exact quote binding checks
provenance; it does not prove entailment, and number presence does not prove numeric reasoning.

## Inspect and reproduce

- [All 15 development answers and evidence](agent-v0.4-cases.md)
- [Focus A: all six answers](agent-v0.4-focus-a-cases.md) · [Focus B: all six attempts](agent-v0.4-focus-b-cases.md)
- [Raw full development run](../../data/benchmark/veritasmed_v1_1/agent_v04_dev_raw.json)
- [Full development assessments](../../data/benchmark/veritasmed_v1_1/answer_assessment_overrides_v04_dev.jsonl)
- [Full development scores](../../data/benchmark/veritasmed_v1_1/agent_v04_dev_scored.json)
- [Run manifest, settings and artifact hashes](../../data/benchmark/veritasmed_v1_1/agent_v04_manifest.json)
- [Focus A log](../../data/benchmark/veritasmed_v1_1/agent_v04_focus_a_log.txt) · [Focus B log](../../data/benchmark/veritasmed_v1_1/agent_v04_focus_b_log.txt) · [Development log, including resume](../../data/benchmark/veritasmed_v1_1/agent_v04_dev_log.txt)
- [Earlier interrupted two-answer attempt](../../data/benchmark/veritasmed_v1_1/agent_v04_earlier_interrupted_focus_raw.json), excluded from final summaries; [implementation record](../archive/worklogs/agent-v0.4-worklog.md)

Recompute saved decisions and arithmetic without Ollama, GPU, Qdrant or the raw corpus:

```sh
python -m pip install "pydantic>=2.7,<3"
python scripts/benchmark/recompute_saved_agent.py --version v0.4
```

Omit `--version` for the preserved v0.3 default. This recalculates published decisions, not semantic
correctness. Answer hashes bind each assessment to its exact answer. To produce new answers, obtain
the matching full corpus/index using the [benchmark instructions](benchmark-v1.1-report.md), then run:

```sh
python scripts/benchmark/run_agent.py --split development --output output/agent_dev_raw.json --model qwen3.5:9b --embedder-device cpu --reranker-device cuda --timeout 240
```

Use `--reranker-device cpu` without CUDA. New answers require new assessments. The tiny demo fixture
cannot substitute for the full benchmark corpus. The frozen questions and scorer are unchanged.

## Before using the held-out test

Correct the within-study cohort scope and refusal rationale, preserve required comparison details,
recover the missing second study, and make boundary planning return valid structured output within
its budget. Separate valid evidence gaps from requests for more retrieval. Repeat the declared
development protocol, retaining failures and wording defects. Only then decide whether the unchanged
35-question test split is ready to be used. This candidate does not lower the planned criteria.
