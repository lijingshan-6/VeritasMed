# v0.8: traceable qualifiers do not establish better semantic reliability

**English** | [简体中文](../../reports/verification-v0.8-report.md)

v0.8 delivers conversations, parent-constrained location and qualifier diagnostics.
**Direct / Flash remains default.** Atomic v2 reconnects more conditions to text while adding
extraction states requiring review. There is no new expert gold; constructions or character
co-presence do not establish improved medical verification accuracy.

This report is recomputed from saved outputs. Inspect the
[protocol/manifests](../../../data/verification/v08/r2/README.md),
[full summary](../../../data/verification/v08/r2/summary.json) and
[six-case AI development review (Chinese)](../../reports/verification-v0.8-extraction-review.md).

## Research layers and default decision

- R1: 167 historical audits / 1,203 facts; locatable 1,097 → 1,179, 82 recovered,
  0 regressions, 24 unresolved. Location replay only, with no model calls or new semantic decisions.
  [Localization record (Chinese)](../../reports/verification-v0.8-localization.md).
- R2: 24 previously unused source groups × 4 variants = 96 constructed answers, including
  24 deliberate numeric errors. 12 groups development / 12 final; separately 12 RAGTruth train
  natural answers and three Direct/v2 runs on 6 preselected inputs.
- R3: inventory left only 1 unexposed public SciFact pair, labelled insufficient. Too few for a new
  three-way semantic generalization comparison; deferred without AI-generated gold.
  [Exposure inventory (Chinese)](../../reports/verification-v0.8-exposure.md).

Six sources contain explicit negation targets. The author saw constructed inputs; final model
outputs were generated after candidate freezing. This is not an external test blinded to developers.
Sources are separated by linked-paper groups; four variants are not four independent papers.
Natural samples contain six marked and six unmarked answers, not a natural error prevalence sample.
60 official test sources remain reserved.

Only one v2 candidate was developed; there was no second prompt round or relaxed conditions to
obtain positive results. Every call/failure remains. Direct permits one call, Atomic at most three
and 48 facts; Flash only, concurrency at most three, SDK retries zero. Original v1/historical outputs
remain. After freezing model, data and rules, final data were run only the scheduled once.

## Mechanical diagnostics on constructed answers

**Columns describe different measures.** Anchor coverage locates preannotated phrases. Joint
co-presence requires all target anchors within one claim's fragments/qualifiers. Numeric retention
also requires the original number in that item's explanation, conditional on joint co-presence;
it is not independent numeric-recognition accuracy. Direct may quote a longer passage; v2 returns
extra qualifiers by design. Such structural gains do not establish correct group–value semantic mapping.

Full completion means returned verification items all completed, not that extraction is exhaustive.
Reaching the declared fact ceiling does not prove completeness. Extraction contracts differ; v2 marks
some unanchored or nonliteral-number items `needs_review`. Completion therefore also measures
review burden from added rules, not a semantic accuracy ranking.

### Development

| Method | Fully completed answers | Anchor coverage | Joint co-presence targets | Completed and joint | Number + conditions retained |
|---|---|---|---|---|---|
| Direct | 37/48 | 320/320 | 68/112 | 68/112 | 52/96 |
| Atomic v1 | 26/48 | 304/320 | 61/112 | 56/112 | 45/96 |
| Atomic v2 | 24/48 | 320/320 | 98/112 | 77/112 | 80/96 |

| Method | Negation co-presence | Error controls: full-anchor alarm | Only supported under same conditions | Incomplete conditions or execution |
|---|---|---|---|---|
| Direct | 16/16 | 6/12 | 0/12 | 6/12 |
| Atomic v1 | 16/16 | 1/12 | 0/12 | 11/12 |
| Atomic v2 | 16/16 | 8/12 | 0/12 | 4/12 |

### Frozen final partition

| Method | Fully completed answers | Anchor coverage | Joint co-presence targets | Completed and joint | Number + conditions retained |
|---|---|---|---|---|---|
| Direct | 47/48 | 284/284 | 91/104 | 91/104 | 83/96 |
| Atomic v1 | 26/48 | 263/284 | 81/104 | 78/104 | 71/96 |
| Atomic v2 | 26/48 | 284/284 | 101/104 | 80/104 | 93/96 |

| Method | Negation co-presence | Error controls: full-anchor alarm | Only supported under same conditions | Incomplete conditions or execution |
|---|---|---|---|---|
| Direct | 8/8 | 10/12 | 0/12 | 2/12 |
| Atomic v1 | 8/8 | 5/12 | 0/12 | 7/12 |
| Atomic v2 | 8/8 | 11/12 | 0/12 | 1/12 |

Error controls also require all target anchors in one completed fact. The final column may include
Direct outputs already warning about the wrong number but omitting another sentence's condition;
it does not mean the model entirely missed the error. Alarms may be contradicted or insufficient.
Expected outcomes derive from the author's text transformations, not independent clinical labels.

## Paired source-group intervals

Final candidate minus Direct, in percentage points. 10,000 fixed-seed source-group bootstrap
resamples keep each group's four variants together and weight groups equally. Intervals describe
this small sample; there is no multiple-comparison correction.

| Candidate | Anchor difference [95% interval] | Joint difference | Completed-and-joint difference | Number + conditions difference | Full-completion difference |
|---|---|---|---|---|---|
| Atomic v1 | -6.8 [-11.5, -2.7] | -10.4 [-26.0, +5.2] | -13.5 [-30.2, +3.1] | -12.5 [-29.2, +4.2] | -43.8 [-58.3, -29.2] |
| Atomic v2 | +0.0 [+0.0, +0.0] | +9.4 [+0.0, +22.9] | -9.0 [-25.7, +6.9] | +10.4 [+0.0, +25.0] | -43.8 [-58.3, -31.2] |

Co-presence cannot satisfy upgrade criteria of fewer false accepts with non-inferior correct support
recall. Without a qualified new semantic comparison, no mechanical score justifies default promotion.

## Natural-answer development

| Method | Fully completed | Alarm on marked answer | Marked spans overlapped by alarms | Alarm on unmarked answer |
|---|---|---|---|---|
| Direct | 12/12 | 5/6 | 8/12 | 5/6 |
| Atomic v1 | 8/12 | 4/6 | 6/12 | 5/6 |
| Atomic v2 | 3/12 | 5/6 | 8/12 | 5/6 |

Overlap may result from longer quotes or qualifier coverage and does not establish specific-error
identification. Alarms on unmarked answers are not automatically false positives. These are development
diagnostics, not independent final reliability scores. Additional AI reading records shared disagreements
about police attribution, occupation generalization and onscreen characters; public labels and
denominators remain unchanged. See [development review (Chinese)](../../reports/verification-v0.8-extraction-review.md).
Model agreement cannot replace annotation adjudication.

## Repetition and actual resources

Six inputs were fixed before initial outputs; each method ran three times. Completion and target-level
joint alarm changes remain, without majority-vote gold. Complete sequences are in the summary JSON.

| Input | Method | Three statuses | Consistent completed target relations? |
|---|---|---|---|
| v08-21-original | Direct | ok / partial_error / ok | Changed |
| v08-21-original | Atomic v2 | partial_error / partial_error / partial_error | Changed |
| v08-06-paraphrase | Direct | partial_error / partial_error / partial_error | Consistent |
| v08-06-paraphrase | Atomic v2 | partial_error / partial_error / partial_error | Changed |
| v08-05-cross_context | Direct | ok / ok / ok | Consistent |
| v08-05-cross_context | Atomic v2 | ok / ok / ok | Consistent |
| v08-12-repeated_error | Direct | ok / ok / ok | Consistent |
| v08-12-repeated_error | Atomic v2 | ok / ok / ok | Consistent |
| v08-10-original | Direct | ok / ok / ok | Consistent |
| v08-10-original | Atomic v2 | partial_error / partial_error / partial_error | Changed |
| v08-07-paraphrase | Direct | ok / ok / ok | Consistent |
| v08-07-paraphrase | Atomic v2 | partial_error / ok / partial_error | Changed |

| Stage | Method | Calls | Calls with usage | Reported tokens | Median seconds / audit | Answers reaching fact ceiling |
|---|---|---|---|---|---|---|
| development | Direct | 48 | 48 | 230,531 | 16.3 | 0/48 |
| development | Atomic v1 | 96 | 96 | 545,068 | 37.6 | 0/48 |
| development | Atomic v2 | 96 | 96 | 807,988 | 52.7 | 0/48 |
| natural | Direct | 12 | 12 | 180,209 | 54.8 | 0/12 |
| natural | Atomic v1 | 25 | 25 | 382,962 | 120.4 | 0/12 |
| natural | Atomic v2 | 24 | 24 | 425,951 | 120.2 | 0/12 |
| repeat | Direct | 12 | 12 | 64,309 | 17.5 | 0/12 |
| repeat | Atomic v2 | 24 | 24 | 217,738 | 60.3 | 0/12 |
| final | Direct | 48 | 48 | 218,800 | 14.8 | 0/48 |
| final | Atomic v1 | 96 | 96 | 610,884 | 43.1 | 0/48 |
| final | Atomic v2 | 96 | 96 | 845,490 | 53.9 | 0/48 |

Total: 577 audit-internal model calls, 4,529,930 provider-reported tokens. This excludes context
diagnostics and medical Ask demos, and is not a monetary invoice. Missing usage is not zero usage.
Audit latency includes sequential calls; summed durations under parallel execution are not wall time.

## Delivered and still unproven

The product retains conversations, answer versions, sources and individual audits. Atomic v2 parent
sentences, fragments and qualifiers support linked inspection. Literal-number rules can add unnecessary
review, such as predictors omitting a shared age range after splitting a statistical model; no alarm
can still hide missing conditions. Six-case reading describes this, without independent expert labels.

Three real medical conversations are saved separately, with questions fixed before inference. The
second conversation missed clarification for a singular reference and answered durations for both
studies. The third final turn cited duration without fully answering the mortality subquestion and
retained partial coverage. The second also treated “do not compare efficacy” as an evidence gap,
creating an unnecessary partial-coverage label. These remain unchanged and are excluded from R2.
A passing Direct audit does not establish that the entire question was answered.

New semantic labels and explicit failure tasks are needed before comparing extraction fidelity,
additional retrieval and repair. There is no calibrated confidence percentage, automatic cross-study
conflict adjudication, or proof of repair from the verifier's own decisions.

[Conversation guide](../conversation-guide.md) · [Original release note](../../releases/v0.8.0.md) ·
[Reproduction](../research-reproduction.md)
