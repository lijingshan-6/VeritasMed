# Agent v0.4 repair: actual answer results

The independent full development run passes **15/15**, compared with **9/15** in the first v0.4 candidate and **10/15** in v0.3.
All required evidence is retrieved for **13/13** answerable questions. The full run has **0 unsupported material additions**, **0 missing required qualifiers**, and **0 execution errors**.
The original development targets are **met**. The 35-question test split remains unused; this is still an unpublished development candidate.

## What was repaired

- Rank each component search before matching its study, then choose the final five passages. A broad review no longer automatically displaces a second requested study before matching.
- Build and check each study's outline separately, using its focused question and global source-sentence IDs. This reduces false gaps about the other study.
- Preserve complete selected numerical/method sentences with visible attribution: actor, development/test population role, comparator, uncertainty and null contrasts stay together. Design-limit explanations remain generated and checked.
- Distinguish an unmeasured outcome from a measured outcome without the requested comparison. Gaps do not invent absent patients or biopsies.
- Use direct JSON output and require every component's check through a JSON schema. This constrains format, not truth; self-check remains fallible.
- Require explicitly named alphanumeric targets/model codes to occur in candidate source text before study matching; references alone cannot identify the primary study.
- Let generation recover omitted result sentences from the same bound study, with global evidence IDs resolved to original text. Missing outcomes cannot be upgraded by this mechanism.
- State a concrete missing outcome and setting for open evidence-boundary questions; avoid echoing the planner's instruction as an answer.

## Separate runs

All three runs use implementation `46b2888` with unchanged gold questions and scoring rules.
Focus runs contain 006, 010, 011, 013, 014 and 024. The full 15-question run is separate; no best-of selection or answer substitution was used.

| Run | Strict content passes | Agent self-check passes | Unsupported additions | Missing qualifiers | Execution errors | Mean latency | Slowest |
|---|---:|---:|---:|---:|---:|---:|---|
| focus_a | 6/6 | 6/6 | 0 | 0 | 0 | 63.2 s | 92.4 s (VMG-006) |
| focus_b | 6/6 | 6/6 | 0 | 0 | 0 | 61.8 s | 79.7 s (VMG-006) |
| dev | 15/15 | 13/15 | 0 | 0 | 0 | 71.1 s | 110.0 s (VMG-009) |

These are locally observed end-to-end times including startup, with CPU BGE-M3 and CUDA reranking on an RTX 4060 Laptop GPU. The model is `qwen3.5:9b`, context 8,192, output limit 4,096, structured fast/review temperatures 0.0. The browser API retains its 300-second overall deadline.
The full run includes four unnecessary regenerations and one structured-output retry. All three
runs also retain a Qdrant destructor warning during interpreter shutdown after all answers were
saved; all processes exited with code 0. It is recorded separately from question errors.

An omitted core finding is recorded as an unmapped claim; an unnamed required evidence boundary is
recorded through the answerability decision. Either can fail strict scoring even when the separate
missing-qualifier count is zero. Model self-check disagreements are retained in the case reports.

## Every development answer

| Question | First candidate | Repaired run | Source-first decision |
|---|---|---|---|
| [VMG-001](agent-v0.4-repaired-cases.md#vmg-001) | Pass | Pass | Actual increased extracellular volume and lower right-heart MRI findings are complete, with 21 HIV veterans versus 20 controls and cautious interpretation. Higher GDF-15, demographics and the cross-sectional pilot/regression design match the source; association is not made causal. |
| [VMG-002](agent-v0.4-repaired-cases.md#vmg-002) | Pass | Pass | Now reports actual 9-month device/lumen area changes, absolute and relative differences, uncertainty and p values rather than only naming the endpoints. Correct 24-month four-patient MACE count/rate with one MI and four revascularization events. Added 55-patient enrollment and prospective observational single-arm design are source statements; no superiority claim. |
| [VMG-006](agent-v0.4-repaired-cases.md#vmg-006) | Pass | Pass | Contains actual higher GDF-15/increased ECV/lower MRI right-heart findings, 21 veterans with HIV versus 20 controls, cautious association and the unresolved longitudinal trajectory. Extra population demographics and regression detail are exact source text. Independently generated text and retrieved source IDs exactly match the reviewed focus_a answer; that semantic decision is reused, not its answer. |
| [VMG-009](agent-v0.4-repaired-cases.md#vmg-009) | Fail | Pass | Both requested claims are fully answered: development counts/modules and assisted-radiologist validation comparisons with p values, without a false validation denominator. The final answer additionally notes absent uncertainty/confidence intervals, which the supplied abstract indeed does not report. This unrequested gap and a false partial/self-check failure remain a presentation/control defect, not a missing required fact or an invented result. Two unnecessary regenerations are retained. |
| [VMG-010](agent-v0.4-repaired-cases.md#vmg-010) | Pass | Pass | Both required target-specific preclinical findings are present with the correct studies. Additional LGR5 uptake and tumor-to-muscle numbers retain the positive/negative models and match the source; no patient-accuracy or head-to-head claim. Independently generated text and retrieved source IDs exactly match the reviewed focus_a answer; that semantic decision is reused, not its answer. |
| [VMG-011](agent-v0.4-repaired-cases.md#vmg-011) | Fail | Pass | Both diagnostic changes retain original radiologist comparators, intervals and p values. Prostate 400-patient testing subset remains distinct from 500 included men; breast development counts remain a development statement. No cross-study superiority or unsupported denominator. Independently generated text and retrieved source IDs exactly match the reviewed focus_a answer; that semantic decision is reused, not its answer. |
| [VMG-012](agent-v0.4-repaired-cases.md#vmg-012) | Pass | Pass | Correct nomogram AUC and confidence interval, sensitivity and specificity. The 600-patient, single-center retrospective context is an exact source statement and is not presented as prospective proof of reduced thrombosis. |
| [VMG-013](agent-v0.4-repaired-cases.md#vmg-013) | Pass | Pass | Complete sensitivity/specificity tradeoff with actual radiologist baselines, intervals, p values and 400-test/500-cohort roles. The explicit gap names real-world deployment effects on patient outcomes and downstream care instead of repeating a task instruction. Independently generated text and retrieved source IDs exactly match the reviewed focus_a answer; that semantic decision is reused, not its answer. |
| [VMG-014](agent-v0.4-repaired-cases.md#vmg-014) | Fail | Pass | Correctly states that the source supplies no outcome data establishing reduced unnecessary biopsies or improved patient outcomes versus radiologist-only care. Does not misrepresent the available retrospective patient records or biopsies. Independently generated text and retrieved source IDs exactly match the reviewed focus_a answer; that semantic decision is reused, not its answer. |
| [VMG-018](agent-v0.4-repaired-cases.md#vmg-018) | Fail | Pass | Both actual methods and validation results are covered: through/in-plane fMRI acceleration, image shifts and Hadamard encoding with simulated/experimental scan-time and SNR/CNR findings; adaptive anisotropic diffusion, Rician estimation and PSO with synthetic/real-image noise reduction and detail preservation. The extra qualified activation-detection comparison and Bayesian voxel-wise estimates occur in the fMRI abstract verbatim in substance. No cross-study superiority. One structured-output retry is retained in the log. |
| [VMG-024](agent-v0.4-repaired-cases.md#vmg-024) | Pass | Pass | Correct brush-versus-plasma sensitivity comparison. Additional specificity, 187-patient population, reference-standard methods and control follow-up are direct source statements. No invented recurrence benefit or denominator. Independently generated text and retrieved source IDs exactly match the reviewed focus_a answer; that semantic decision is reused, not its answer. |
| [VMG-032](agent-v0.4-repaired-cases.md#vmg-032) | Fail | Pass | Both the flow-LVMI association and the nonsignificant dialysis-vintage contrast are explicitly present with estimates, confidence intervals and p values; the 241-patient count and extra flow/vintage summaries match the source. The answer explains that cross-sectional associations cannot prove causal benefit from lowering flow. The self-check falsely says the fully quoted null contrast is absent, leaving a partial label and two unnecessary regenerations; that defect is preserved separately from content scoring. |
| [VMG-034](agent-v0.4-repaired-cases.md#vmg-034) | Pass | Pass | All independent predictors and directions retain their odds ratios and confidence intervals. Population counts and the mid/low-pelvic versus perineal blood-loss, episiotomy and ultrasound comparisons match the source, including p values. No causal treatment benefit inferred. |
| [VMG-039](agent-v0.4-repaired-cases.md#vmg-039) | Pass | Pass | Complete target-coverage comparator and uncertainty, lack of significant OAR difference, treatment times, grade-3-or-higher absence and grade-2 rate. Source counts 41 patients/232 fractions/178 ASRT fractions and added workflow/background details are preserved without a comparative survival claim. The answer is unnecessarily repetitive, a readability limitation. |
| [VMG-042](agent-v0.4-repaired-cases.md#vmg-042) | Fail | Pass | Correctly refuses comparative local-control/survival benefit because the supplied study lacks the requested nonadaptive comparator. Does not falsely claim that local control or survival were never measured. |

## Read or recompute the evidence

- [All 15 answers and frozen source passages](agent-v0.4-repaired-cases.md)
- [Focus A](agent-v0.4-repaired-focus-a-cases.md) and [Focus B](agent-v0.4-repaired-focus-b-cases.md)
- [Run manifest](../../data/benchmark/veritasmed_v1_1/agent_v04_repaired_manifest.json), [repair worklog](../archive/worklogs/agent-v0.4-repair-worklog.md), [debugging probes](../../data/benchmark/veritasmed_v1_1/v04_repair_probes)
- [Original v0.4 report, preserved](agent-v0.4-report.md), [v0.3 baseline](agent-v0.3-report.md)
- [First independent repair round, preserved](../../data/benchmark/veritasmed_v1_1/v04_repair_round1): 11/15, with focus results 4/6 and 5/6. It exposed regressions that required another implementation change; none of its answers was substituted into the final run.

```sh
python -m pip install "pydantic>=2.7,<3"
python scripts/benchmark/recompute_saved_agent.py --version v0.4-repaired
```

`--version v0.4` still reproduces the first candidate; omitting the option still selects v0.3.
Recomputation checks saved answer hashes, mappings and arithmetic. The semantic decisions above were made by Codex against the frozen passages, without independent clinician review. It does not independently rejudge the answers.
Identical independently generated answers with the same retrieved source IDs reuse the same source-reviewed decision; that reuse is noted in the assessments. Their actual outputs and timings remain separate.

## Limits

The full-run SCAR-Net answer (009) contains all required facts but is still labelled partial by the
Agent. Its planner added an unrequested confidence-interval component; the source has p values but
does not supply those intervals. The final gap is not a fabricated result, yet the label and two
unnecessary regenerations are a real remaining control/presentation defect. Strict content scoring
does not score this coverage-label error, so a high strict score must not be read as a flawless UI
or perfect self-check.
The hemodialysis answer (032) also receives a false partial/self-check failure: its null
dialysis-vintage comparison is fully quoted, yet the checker says it is missing. That causes
two more unnecessary regenerations. Both label errors remain visible in the retained outputs.

These are development questions already used for debugging, not unseen generalization results. Exact quotation improves fidelity but makes some answers longer and repetitive. Source matching and semantic checking can still fail, and measured performance here does not establish clinical reliability. The first candidate's failures, first independent repair round and all seven debugging probes remain available.
