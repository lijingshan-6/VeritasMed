# v0.6 audit reliability report (delivered with v0.7.0)

**English** | [简体中文](../../reports/verification-v0.6-report.md)

Fixed targets, medical constructions and natural answers are separate tasks. Public human labels
provide external references; constructed facts and AI development review are not independent
medical gold. All scheduled samples and failures remain available.

**Decision: Direct remains default; atomic-v1 and MiniCheck remain research options. Calibration
found no acceptance threshold meeting the predeclared conditions. No claim confidence percentage is published.**

## Data and freezing

| Purpose | Source groups / pairs or answers | Status |
|---|---|---|
| Fixed-target development pilot | 60 pairs | Excluded from final scores |
| Score fitting | 50 groups / 87 pairs | SciFact train |
| Independent threshold selection | 50 groups / 91 pairs | SciFact train |
| Fixed-target final | 247 groups / 339 pairs | Official dev, run once after freezing; not official test |
| Medical development | 15 groups / 60 answers | Original, paraphrase, single error, removed evidence |
| Medical transfer | 8 groups / 32 answers | Also constructed diagnostics, not clinical generalization |
| Natural-answer development | 36 sources / 36 answers | 18 with public errors, 18 without marked errors |
| Preselected repetition | 12 sources / 3 runs per method | Original plus two independent calls |
| Reserved natural-answer final | 60 sources | Unused: insufficient whole-answer semantic scoring and upgrade evidence |

P0 partitions connected groups of claims and all linked papers, excluding exposure from previous
pilots, constructions and medical corpora. The v0.7 sets of 20/40 groups were reserved separately.
The planned 24 medical groups became 23: abstract 42291761 had contradictory years and truncation;
it was not forced into an annotation. Public data may be in pretraining; source isolation does not
establish absence of training contamination.

[v06 artifacts](../../../data/verification/v06/README.md) retain protocols, label provenance,
per-run settings and exact inference code. Prompt changes did not overwrite first-run records.

## E1: fixed claim and complete abstract

Flash and pinned MiniCheck-Flan-T5-Large receive the same target and complete abstract, without
gold relations or rationale sentences. MiniCheck is binary; inputs exceeding 2048 tokens fail
explicitly rather than being silently truncated. Contradicted / Insufficient are merged as Non-supported.

Public labels may require domain aliases or implicit reasoning, while the Flash prompt limits
judgment to the supplied text. Identical inputs do not imply identical learned decision policies.
Labels are retained, not revised according to output; disagreements do not all measure medical ability.

| Method | Completed | Correct binary | Non-support accepted | Support recall | Support precision | Balanced accuracy |
|---|---|---|---|---|---|---|
| flash | 339/339 | 291/339 | 6/201 | 96/138 | 94.1% | 83.3% |
| minicheck | 339/339 | 279/339 | 14/201 | 92/138 | 86.8% | 79.9% |

Failures/incomplete items are not correct rejections. Denominators include all scheduled pairs;
the jointly successful subset in JSON cannot replace this table.

Flash requires valid rationale sentence IDs to complete; MiniCheck returns only a binary label,
with no equivalent citation contract. The table includes this additional output requirement;
invalid citations cannot all be interpreted as semantic classification errors.

A post hoc label diagnostic ignores only invalid Flash rationale references, retaining parsed
relation labels: completed 339/339, binary correct 291/339. It was registered after E2 citation
failures, during the fixed final run, and did not select methods, thresholds or defaults.
It does not replace the primary table or failures; JSON retains all denominators and details.

![Fixed verifier comparison](../../assets/v07-fixed-verifiers.png)

| MiniCheck − Flash | Paired difference and 95% source-group bootstrap interval |
|---|---|
| False acceptance (lower is better) | +4.0 pp [+0.5, +8.1] |
| Support recall (higher is better) | -2.9 pp [-12.2, +6.0] |

247 connected groups, 2,000 paired resamples, seed 260926. Zero observed errors or degenerate
intervals do not imply zero risk. Predeclared upgrade criteria require better false acceptance
with support recall falling by no more than 3 percentage points, rather than overall accuracy alone.

### Flash three-way labels and rationales

| Public label | Output | Count |
|---|---|---|
| contradicted | insufficient | 15 |
| insufficient | insufficient | 118 |
| supported | supported | 96 |
| supported | insufficient | 36 |
| insufficient | supported | 5 |
| contradicted | contradicted | 55 |
| supported | contradicted | 6 |
| insufficient | contradicted | 7 |
| contradicted | supported | 1 |

Rationale comparison: `{"annotated_pairs": 209, "exact_one_annotation": 85, "covers_one_annotation": 145, "correct_relation_and_covers": 141}`.
This measures matching public rationale sets; valid alternatives may be unannotated.
Valid text location does not establish a correct judgment.

| Method | Median seconds / pair | Total seconds | Reported API tokens | Records without token usage |
|---|---|---|---|---|
| flash | 3.945 | 2334.5 | 569,216 | 0 |
| minicheck | 0.155 | 59.0 | 0 | 339 |

MiniCheck used a local RTX 4060 Laptop / FP32; time excludes weight loading. Missing API usage
does not imply no compute cost. Flash's gateway-returned model name does not authenticate
underlying weights. Artifacts retain model versions, environment and response fields.

## Calibration: no publishable acceptance rule

A logistic mapping was fitted only on 87 pairs; a separate 91 pairs selected a threshold from
the predeclared grid: empirical error among accepted items ≤5%, at least 20 pairs across 10 groups.
**No threshold qualified.** The frozen mapping was still evaluated on final data: raw Brier=0.1395,
mapped=0.1306, completed 339/339.

![Reliability and risk-coverage](../../assets/v07-calibration.png)

Final curves describe distribution, not a new threshold search. With a null threshold, acceptance
risk is unestimable; accepting nothing is not zero risk. Preselected group representatives and risk
intervals are in `calibration-final.json`. Scores concern textual support, not medical truth probabilities.

## E3: whole answers and constructed facts

**The primary tables use original frozen construction labels. A recorded source-scope concern
affects medical-15; the following sensitivity analysis removes that group uniformly. Retaining
records does not endorse known questionable labels as infallible.**

Each medical answer has two predefined fact units. Extraction is associated by original answer
character positions: at least half a target's non-whitespace characters must overlap; conflicting
associated judgments produce no definite decision. Broad claims may combine adjacent facts;
faithful normalization may overlap fewer characters. These are **positional diagnostics, not semantic accuracy**.

### Development: 15 groups

| Method | Completed answers | Full fact-text coverage | Position-linked false accepts | Position-linked correct supports | Position-linked error alarms |
|---|---|---|---|---|---|
| direct | 55/60 | 115/120 | 3/45 | 70/75 | 38/45 |
| split | 58/60 | 119/120 | 0/45 | 71/75 | 44/45 |
| atomic_v1 | 54/60 | 94/120 | 1/45 | 71/75 | 43/45 |

### Transfer: 8 groups

| Method | Completed answers | Full fact-text coverage | Position-linked false accepts | Position-linked correct supports | Position-linked error alarms |
|---|---|---|---|---|---|
| direct | 23/32 | 60/64 | 1/24 | 34/40 | 18/24 |
| split | 26/32 | 63/64 | 0/24 | 33/40 | 23/24 |
| atomic_v1 | 23/32 | 47/64 | 0/24 | 35/40 | 18/24 |

Unextracted, incomplete and unassociable items stay in the original denominators.
Successfully split easy items cannot alone form the overall score.

### Construction-label erratum and sensitivity

After development outputs existed, re-reading sources for all 23 groups found that medical-15's
Natsal-3 identifier was absent from the supplied title/selected sentences. The count was supported,
but the complete named fact's Supported label needs qualification. Original labels, inputs,
inference and primary tables remain unchanged. Removing all four variants of that group from
every method is post hoc sensitivity analysis, not independent expert review or new confirmatory
performance. Other groups are not certified error-free either.

| Method | Sources / answers / facts | Position-linked false accepts | Position-linked correct supports |
|---|---|---|---|
| direct | 14 / 56 / 112 | 3/42 | 65/70 |
| split | 14 / 56 / 112 | 0/42 | 68/70 |
| atomic_v1 | 14 / 56 / 112 | 1/42 | 68/70 |

[Erratum](../../../data/verification/v06/medical-label-review.json) and
[sensitivity details](../../../data/verification/v06/medical-label-sensitivity.json) retain discovery
timing, sources and limitations. Future dataset revisions need new versions and freezing, not overwritten inputs.

### Natural answers: publicly annotated error spans

| Method | Completed answers | Any error overlap | At least half-error coverage | Alarm on unmarked answer |
|---|---|---|---|---|
| direct | 34/36 | 19/22 | 16/22 | 13/18 |
| split | 35/36 | 19/22 | 18/22 | 12/18 |
| atomic_v1 | 11/36 | 18/22 | 17/22 | 13/18 |

Legacy scoring fields remain reproducible: `false_positive` here means an alarm on an unmarked
answer, not a confirmed false alarm. Overlap does not prove identifying the specific error;
longer alarms also increase overlap. Natural answers are not a medical diagnostic set.

### Actual compute

| Partition | Method | Calls | Reported tokens | Mean seconds / answer | Calls without usage |
|---|---|---|---|---|---|
| medical_development | direct | 60 | 174,783 | 12.1 | 0 |
| medical_development | split | 228 | 328,040 | 24.5 | 0 |
| medical_development | atomic_v1 | 120 | 350,910 | 22.1 | 0 |
| medical_transfer | direct | 32 | 100,370 | 12.8 | 0 |
| medical_transfer | split | 121 | 191,559 | 26.7 | 0 |
| medical_transfer | atomic_v1 | 64 | 249,344 | 29.3 | 0 |
| natural | direct | 36 | 577,725 | 58.6 | 0 |
| natural | split | 425 | 1,481,342 | 140.3 | 0 |
| natural | atomic_v1 | 74 | 1,033,432 | 97.1 | 0 |

These are per-answer latencies, not parallel batch wall time. Direct usually makes 1 call; original
Split verifies each item, up to 25; atomic-v1 extracts then verifies in batches, up to 3.
Changes from extra compute cannot all be attributed to structure.

## E2 / E4 / E5: mechanism diagnostics

Seed selection chose all 4 variants of 3 sources: 12 answers. E2 compares both verifiers on the
same frozen independent fact table, with 30 targets: both complete 27, binary disagreements 3.
Per-item input hashes remain available. Original answers are not appended to evidence to certify
themselves. Parsing has no independent semantic gold; disagreement does not decide correctness.

E2 statuses: Flash `{"ok": 27, "invalid_evidence_reference": 3}`; MiniCheck `{"ok": 30}`.
The three incomplete Flash items are invalid rationale citations, not correct non-support decisions.
MiniCheck has no such citation contract.

All three belong to medical-06: several source sentences were packaged as one evidence unit
(ID 0), while Flash returned ID 1, triggering `SentenceOutOfRange`; its original supported label
and explanation remain. Input packaging/citation contracts need improvement. No patched IDs,
reruns or erased failures were used.

E4 removes explicit slots while preserving extraction, answer and source:
`{"planned_facts": 30, "both_completed": 29, "relation_changed": 0, "status_changed": 0}`.
A single development ablation may include randomness; added alarms would not establish slot efficacy.

E5 advisory numeric rules: `{"not_applicable": 22, "unresolved": 8}`. Disabling them removes hints;
semantic decisions changed 0 times. Multiple numbers, missing units, intervals or uncertain context
remain unresolved. Matching numbers by coincidence is not factual support.

### Substantive extraction-fidelity gaps

[AI development review of 12 preselected inputs](../../reports/verification-v0.6-extraction-review.md)
(original Chinese record) found an omitted quarterly denominator, numeric slots sometimes containing
only units, and repeated/compound facts self-labelled atomic. Text location exposes these issues
but does not repair semantics. This is not independent annotation or comprehensive fidelity validation.

Short fragments repeated in an answer are another bottleneck. Even with a unique parent, the
frozen locator requires fragment uniqueness throughout the answer. Unbound facts are not verified.
Natural Atomic binding counts:
`{"parent": {"unique": 505, "not_found": 5}, "answer_fragment": {"unique": 834, "not_found": 3, "ambiguous": 30}, "evidence": {"unique": 619, "not_found": 2, "ambiguous": 1}}`.
Parent-constrained location is a possible controlled improvement; this round did not rerun and
overwrite unchecked items.

## E6: repetition and call-budget control

| Method | Sources | Alarm presence changed across three runs | Alarm location set changed |
|---|---|---|---|
| direct | 12 | 2 | 7 |
| atomic_v1 | 12 | 4 | 10 |

Real independent calls used the same frozen inputs; no best run was selected. Agreement is not a gold label.

| Conservative answer-level control | Clear alarm | No alarm | Review required | Alarm on marked answer | Total calls |
|---|---|---|---|---|---|
| direct_three | 7 | 2 | 3 | 4/6 | 36 |
| atomic_first | 3 | 1 | 8 | 3/6 | 25 |

After small medical-development positional gains, before repeat outputs, this additional analysis
was planned on the same 12 sources. Direct retains a signal only when all three complete and
agree on alarm presence; otherwise review is required. Atomic uses its first run, at most three
calls. Only answer-level alarms are compared: spans are not pooled, majority votes are not truth,
and retention rates cannot conceal failures. See `budget-protocol.json` and complete details.

## Product and release decision

Atomic decomposition, qualifier slots, multiple source-text anchors, numeric hints and separate
MiniCheck outputs are in the real-record panel. Direct remains default; disagreements prompt review.
Three GRADE demonstrations distinguish actual Agent answers from constructed group swaps and
constructed evidence deletion.

There is insufficient evidence on whole-answer semantics, extraction fidelity and non-inferior
support recall to upgrade the default, automatically repair answers or use the 60-source natural
reserve. Evidence grading, clinical applicability and cross-study conflict adjudication remain
separate research tasks. v0.6 was released together with v0.7.0; no independent v0.6.0 release is invented.

[Original protocol (Chinese)](../../plans/v0.6-audit-reliability.md) ·
[Reproduction](../research-reproduction.md) · [MiniCheck](../minicheck-research.md) ·
[v0.7 workflow comparison](verification-v0.7-report.md)
