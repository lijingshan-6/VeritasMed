# VeritasMed Evidence-Grounded Benchmark v1 — Baseline Report

## What this benchmark measures

This benchmark asks whether VeritasMed can find the passages needed for a medical-literature question, reconstruct only the supported claims, preserve study limitations, cite the evidence, and decline conclusions that the supplied literature cannot support.

It contains 50 manually curated questions tied to the frozen corpus snapshot `6dd1f367df9b3653`:

- 10 single-evidence questions
- 15 within-document synthesis questions
- 10 cross-document comparisons
- 10 limitations and safety questions
- 5 insufficient-evidence questions
- 40 complete, 5 partially answerable, and 5 unanswerable questions
- 15 development and 35 holdout questions
- 44 unique PubMed sources across 20 clinical or technical domains

The benchmark is an engineering artifact without clinician review. It is not a medical exam and cannot establish clinical safety.

## How the gold set was produced

Evidence was selected before question wording. An 80-item candidate pool was generated from exact source passages. `qwen3:8b` independently reconstructed answers, and `medgemma1.5:4b` challenged the candidates for population, exposure or intervention, comparator, outcome, time point, and uncertainty errors.

The model votes were retained as review evidence, not labels. The curator read all 80 question-claim-evidence bundles, rejected 30, and rewrote the selected 50. Every required claim resolves to a verbatim passage in the 44,768-chunk normalized snapshot. Derived limitations include their reasoning rule. The five unanswerable questions use same-topic passages that omit the requested intervention comparison or patient outcome.

The question set, rejection reasons, model reviews, curator decisions, model digests, and corpus hashes are committed as inspectable artifacts under `data/benchmark/veritasmed_v1/`.

## Retrieval baseline

P1 and P2 were run on all 50 questions from the frozen BGE-M3 dense and sparse cache. Retrieval metrics below use the 45 answerable questions; the five unanswerable questions have no positive evidence chunk. P3 was run on the 15-question development split because the CPU cross-encoder takes roughly 20 seconds per question on this host.

| Pipeline and scope | Answerable n | Required-claim recall@5 | All required found@5 | nDCG@5 | MRR@5 |
|---|---:|---:|---:|---:|---:|
| P1 dense, full set | 45 | 0.9222 | 0.9111 | 0.9060 | 0.9111 |
| P2 dense+sparse RRF, full set | 45 | **0.9889** | **0.9778** | **0.9549** | **0.9463** |
| P2 dense+sparse RRF, development | 13 | 0.9615 | 0.9231 | 0.9528 | 0.9615 |
| P3 P2+cross-encoder, development | 13 | 0.9615 | 0.9231 | **0.9702** | **1.0000** |

P2 found all required chunks for every holdout answerable question. Its one incomplete full-set result was development question VMG-011, a cross-document comparison between prostate-MRI triage and breast-ultrasound recurrence assessment: only the prostate source reached the top five. P3 moved relevant development results upward but did not recover the absent second source, so its gain is ranking quality rather than recall.

For the five unanswerable questions, the named same-topic hard-negative passage appeared in P2's top five for four questions. This rate is reported descriptively; retrieving a near-topic passage is useful only if the answer layer recognizes that the requested comparison is still absent.

## Local answer baseline

The current direct cited-answer path was run on all 15 development questions with P2 retrieval and local `qwen3:8b`. `medgemma1.5:4b` proposed claim-to-citation mappings. The curator corrected seven obvious assessment errors or duplicate mappings; the original judge output hash remains in each result.

| Metric | Development score |
|---|---:|
| Required-claim completeness | 0.9667 |
| Claim-support precision | 1.0000 |
| Citation coverage | 0.9667 |
| Answerability behavior | 0.9333 |
| Strict question pass | **12 / 15 (0.8000)** |

Strict pass requires every required claim, only valid claim citations, correct answerability behavior, and no unsupported or forbidden claim.

| Answerability group | n | Strict pass |
|---|---:|---:|
| Complete | 11 | 8 / 11 |
| Partial | 2 | 2 / 2 |
| Unanswerable | 2 | 2 / 2 |

The corrected result is more informative than the initial automatic judge score. MedGemma marked both explicit refusals as non-abstentions and missed both explicit evidence-boundary statements, which would have reduced strict pass to 10/15. This is why model judgments remain proposed mappings until a person accepts or corrects them.

## Representative cases

**Complete synthesis — VMG-002.** The answer correctly reported the opposing nine-month device-area and lumen-area changes and the 24-month adverse-event count from the single-arm DYNAMITE study, with the right PMID. This case passed all dimensions.

**Cross-document retrieval miss — VMG-011.** P2 retrieved the prostate-MRI AI source but not the breast-ultrasound SCAR-Net source. The answer accurately stated the first study and explicitly said evidence for the second was missing. It failed claim completeness, as intended; fluent partial coverage does not count as a complete comparison.

**Successful abstention — VMG-014.** The answer reported that the prostate study was a diagnostic simulation, refused to claim reduced biopsies or improved patient outcomes, and named the absent prospective clinical comparison. MedGemma initially misclassified this, and the curator corrected the visible mapping.

**Unsupported extra statement — VMG-016.** The answer correctly reported the adenomyosis imaging changes and correlations, then incorrectly claimed that no depression measure was reported despite having just cited the depression association. The required claims were present, but strict pass failed because the extra statement contradicted the source.

## Reproduce the artifacts

Use the locked Python environment described in the README.

```sh
python scripts/benchmark/validate_dataset.py \
  --questions data/benchmark/veritasmed_v1/questions.jsonl \
  --normalized-corpus-root .

python scripts/benchmark/score_retrieval.py \
  --split all --pipelines p1,p2

python scripts/benchmark/score_retrieval.py \
  --split development --pipelines p3 \
  --output data/benchmark/veritasmed_v1/baseline_retrieval_p3_dev.json

python scripts/benchmark/score_answers.py \
  --split development --pipeline p2 \
  --overrides data/benchmark/veritasmed_v1/answer_assessment_overrides_dev.jsonl
```

The retrieval runner scores directly from the frozen BGE cache and therefore does not require a running Qdrant service. P3 and answer generation require the model weights or Ollama tags documented in the repository. On a CPU-only host, P3 is intentionally shown on the development split rather than presented as a full-set number.

## What the baseline says

Hybrid retrieval is already strong on the frozen corpus, including the holdout split. The remaining product gap is answer discipline. The current local answerer can synthesize ordinary evidence and can abstain when prompted clearly, but it still adds unsupported explanatory text and can contradict a cited result in a trailing paragraph. The next improvement should target evidence-boundary enforcement and claim-level post-generation checking rather than another retrieval rewrite.
