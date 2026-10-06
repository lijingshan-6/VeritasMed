# Experiment A: grounded conclusions on PubMedQA

**English** | [简体中文](experiment-a.zh-CN.md)

Does VeritasMed answer biomedical research questions better than a plain retrieval-augmented
model, and is the difference worth its cost? This page reports the full experiment: the design,
every result (including those that went against the system), a withdrawn claim, and how to
reproduce it. Raw outputs for every answer, judgment and audit are in
[`experiments/pubmedqa/runs/`](../experiments/pubmedqa/runs/).

## Summary

1. **The difference is in the conclusion, not the facts.** A plain RAG answer restates the
   study's findings about as well as VeritasMed, but its first sentence - the yes/no conclusion -
   is uncited or unsupported by its own citation in **40%** of answers. VeritasMed: **16%**
   (paired difference -21.3 pp, 95% CI [-26.6, -16.1]). Handing the model the correct abstract
   does not fix it (36%), so the problem is generation, not retrieval.
2. **A stricter prompt alone grounds conclusions by declining to conclude.** A single-call RAG
   told to cite every sentence and never overstate matches VeritasMed on grounded conclusions,
   but its accuracy falls from 63.8% to **51.0%** - the closed-book level. VeritasMed keeps
   accuracy (63.6%) *and* grounds its conclusions. No other method tested does both.
3. **The audit catches errors.** On 200 answers with one planted error each it flags **97.9%**
   of material errors (95% CI [95, 99]) and wrongly flags **2.0%** of correct sentences
   ([1, 5]). On real plain-RAG answers it catches overstatements - e.g. "not significantly
   different" stated as "no difference" - that a general model judge accepted.
4. **Accuracy is not where VeritasMed wins.** It is level with plain RAG (63.6% vs 63.8%).
   PubMedQA labels come from the authors' conclusions, which the system never sees, so the
   label rewards confident inference; grounding a conclusion often means answering "maybe".
5. **The cost is real: about 1 cent and 50 seconds more per question** (4.7 model calls,
   59 s median, vs 1 call, 10 s).

One earlier result was withdrawn: an automatic checker (MiniCheck) suggested unsupported
sentences were "halved"; a blinded calibration showed that checker misjudges full abstracts,
and the claim was replaced by the numbers above ([section 5](#5-measurement-the-pre-registered-judge-failed-calibration)).

## 1. Setup

**Data.** [PubMedQA](https://github.com/pubmedqa/pubmedqa) (Jin et al., 2019, MIT licence): all
500 questions of the official expert-labelled test set (yes 276, no 169, maybe 55). Each question
is a paper title phrased as a question; the label is the authors' conclusion. The retrieval corpus
holds all 1,000 labelled abstracts plus 10,000 unlabelled PubMedQA abstracts as distractors
(36,550 passages). The conclusion section is never indexed.

**Methods.** Every method uses the same model (DeepSeek-V4.1-Flash through one gateway), the
same corpus and the same hybrid retriever (BGE-M3 dense + sparse, reranked, whole abstract of
the top paper).

| Arm | Method | Calls |
|---|---|---|
| A0 | Closed-book: the model answers from its own knowledge | 1 |
| A1 | **Plain RAG**: top 5 passages, one cited answer | 1 |
| A2 | **VeritasMed**: the full agent (grade evidence, bind each part of the question to source sentences, generate in plain words, self-check, repair) | 4.7 |
| A3 | VeritasMed with key facts pasted verbatim from the source (the v0.8 behaviour) | 4.4 |
| A4 | Gold abstract: the question's own abstract handed to the model (retrieval upper bound) | 1 |
| A5 | **Strict-prompt RAG** (follow-up E1): A1 with a prompt that requires a citation on every sentence and forbids overstating | 1 |

**Measures.**

- *Accuracy*: one fixed judge prompt maps each answer to yes/no/maybe; compared with the expert label.
- *Unsupported sentence*: a sentence without a citation, or one the cited passages do not
  support, judged by a Flash citation judge (chosen by calibration, [section 5](#5-measurement-the-pre-registered-judge-failed-calibration)).
- *Conclusion (bottom line)*: the answer's first sentence; every arm is asked to open with a
  one-sentence yes/no/insufficient conclusion. Sentences that only state what the evidence
  lacks are excluded.
- *Statistics*: paired question-level bootstrap (10,000 resamples) for differences between arms,
  Wilson intervals for proportions.

**Protocol.** Splits and seed were fixed before any model output existed. Prompts were revised
once on 50 development questions, then frozen; the test set was run once per arm (failed calls
retried, every attempt kept). The follow-ups E1 and E2 were
[registered](../experiments/pubmedqa/PREREGISTRATION-followup.md) in a commit before they ran.

## 2. Plain RAG overstates its conclusions; VeritasMed does not

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/experiment-a/bottom-lines-dark.png">
  <img alt="Share of answers whose first sentence fails: plain RAG 40%, gold abstract 36%, strict-prompt RAG 15%, VeritasMed 16%" src="assets/experiment-a/bottom-lines-light.png">
</picture>

| Conclusion sentence | Plain RAG | Gold abstract | Strict-prompt RAG | VeritasMed |
|---|---|---|---|---|
| Cited, but not supported by its passages | 20.3% | 19.4% | 14.7% | 10.9% |
| No citation at all | 19.8% | 17.0% | 0.4% | 4.9% |
| **Fails (either)** | **40.1%** | **36.3%** | **15.1%** | **15.8%** |

The rest of the answer differs much less. Among cited sentences after the first, Flash rejects
9.5% for plain RAG and 11.4% for VeritasMed: both restate findings well. The gap is concentrated
in the one sentence a reader is most likely to act on.

Two things these numbers do *not* say:

- An uncited conclusion is not necessarily false. When we audited 100 plain-RAG answers
  ([section 4](#4-the-audit-catches-planted-and-natural-errors)), most uncited conclusions were
  correct in content. They fail here because a reader cannot check them, which is the property
  this project is about. The two failure types are reported separately for that reason.
- The Flash judge is lenient on one kind of overstatement: it accepted "HFNC were not noisier"
  for a study that found "no evidence of a difference" (CI -4.0 to 0.9 dBA). VeritasMed's answer
  to that question made the same slip; the strict prompt wrote "not shown to be noisier". True
  conclusion-error rates are therefore somewhat higher for every arm, and this is the gap the audit covers.

## 3. A stricter prompt is not enough

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/experiment-a/tradeoff-dark.png">
  <img alt="Accuracy against grounded conclusions: plain RAG and gold abstract are accurate but poorly grounded; strict-prompt RAG is grounded but at closed-book accuracy; VeritasMed is both" src="assets/experiment-a/tradeoff-light.png">
</picture>

| | Accuracy | Macro-F1 | "maybe" answers | Correct when it commits | Conclusions grounded | Sentences unsupported | $ / question | Median time |
|---|---|---|---|---|---|---|---|---|
| Closed-book | 52.2% | 0.431 | 93 | 61.2% | - | - | $0.0014 | 7 s |
| Plain RAG | 63.8% | 0.580 | 160 | 85.9% | 59.9% | 21.8% | $0.0012 | 10 s |
| Gold abstract | 65.6% | 0.601 | 162 | 88.2% | 63.7% | 19.6% | $0.0009 | 7 s |
| Strict-prompt RAG | 51.0% | 0.465 | 196 | 76.6% | 84.9% | 8.9% | $0.0016 | 13 s |
| **VeritasMed** | **63.6%** | 0.565 | 137 | 81.3% | **84.2%** | 14.5% | $0.0105 | 59 s |

Paired differences (95% CI):

- VeritasMed vs plain RAG: accuracy -0.2 pp [-4.0, +3.6]; failed conclusions -21.3 pp [-26.6, -16.1];
  unsupported sentences -7.3 pp [-9.6, -4.9].
- Strict-prompt RAG vs VeritasMed: failed conclusions -2.4 pp [-6.7, +2.1]; accuracy -12.6 pp
  [-16.6, -8.4]; unsupported sentences -5.6 pp [-7.6, -3.6].

E1 was registered with one decision rule: if strict-prompt RAG is within 5 pp of VeritasMed on
failed conclusions, the multi-step generator is unnecessary. It is within the margin - but the
rule had no accuracy guard, and the strict prompt meets it by answering "maybe" to 196 of 500
questions and losing 12.6 points of accuracy. We report the rule's outcome and do not act on it:
a method that grounds its conclusions by withholding them does not do the job.

The strict prompt is better than VeritasMed on one measure: fewer unsupported sentences overall
(8.9% vs 14.5%). VeritasMed's answers are longer (4.3 vs 3.2 sentences) and include design
details, some of which the passages do not state - the audit flagged exactly these in
[planted-error review](#planted-errors).

## 4. The audit catches planted and natural errors

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/experiment-a/audit-dark.png">
  <img alt="Audit detection of planted errors: number 100%, direction 100%, population 96%, overstated conclusion 78%, all material errors after adjudication 98%" src="assets/experiment-a/audit-light.png">
</picture>

### Planted errors

200 VeritasMed answers, 50 per error type. In each, one cited sentence that MiniCheck
had accepted was rewritten by the model with one error; the answer was audited before and after.

| Error type | Flagged when planted | Same sentence flagged when correct |
|---|---|---|
| Changed number | 50/50 | 4/50 |
| Reversed direction or significance | 50/50 | 7/50 |
| Wrong population or comparator | 48/50 | 3/50 |
| Overstated conclusion | 39/50 | 6/50 |

Every flag on a correct sentence and every miss was then read against the abstract
([labels and reasons](../experiments/pubmedqa/runs/planted/adjudication.json)):

- Of 20 flags on unmodified sentences, 16 were right: 13 sentences asserted something the
  passages do not state (mostly study-design caveats VeritasMed had added) and 3 turned
  non-significance into "no effect". Two were wrong, one was due to a corrupted source
  character and one was debatable: **unwarranted flags 4/200 = 2.0% [1, 5]**.
- Of 13 misses, 4 plants were still correct after rewriting and 5 changed only wording
  strength ("showed" to "proved"). **Material errors detected: 187/191 = 97.9% [95, 99].**

### Natural errors (follow-up E2)

The audit was run on 100 plain-RAG answers and compared with the Flash citation judge:

| | Judge says unsupported | Judge says supported |
|---|---|---|
| Audit flags (cited sentences) | 26/37 = 70% | 20/253 = 8% |

All 27 disagreements on conclusion sentences were read against the abstract
([labels](../experiments/pubmedqa/runs/audit-natural/adjudication.json)). Of 19 "misses",
14 were correct sentences that only lacked a citation (the audit checks content, not
formatting), 4 were errors of the judge and 1 was debatable. Of 8 extra flags, 6 were right -
non-significance stated as "no difference", details the passages do not give - and 2 were pedantic.
On conclusions, the audit is the stricter and more often correct of the two checkers.

Limits: the adjudicator is the assistant that built the harness, not a blinded clinician, and
model-written plants are cleaner than real-world errors.

## 5. Measurement: the pre-registered judge failed calibration

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/experiment-a/judges-dark.png">
  <img alt="Agreement with blinded labels: MiniCheck 77.3%, Flash citation judge 94.0%" src="assets/experiment-a/judges-light.png">
</picture>

The plan named MiniCheck-Flan-T5-Large, a local fact-checking model, as the citation judge.
With it, VeritasMed appeared to halve unsupported sentences (44.5% to 21.5%). A pre-planned
second judge (Flash) agreed with MiniCheck on only 73% of 998 sentences (Cohen's kappa 0.19)
and found a much smaller gap.

To settle it, 150 cited sentences (50 per arm) were labelled with arm and judge outputs hidden
([items](../experiments/pubmedqa/runs/agreement/calibration-items.jsonl),
[labels and rubric](../experiments/pubmedqa/runs/agreement/calibration-labels.json)).
Flash agreed with the labels on 94.0%, MiniCheck on 77.3%. MiniCheck rejects even a sentence
copied word for word from the source once the document is a full abstract of about 230 words
(it accepts the same sentence against a two-sentence document), which penalises paraphrase and
favoured VeritasMed's closer-to-source wording. Flash became the primary judge; the MiniCheck
results remain in the files as a rejected measure, and the "halved" claim was withdrawn.

## 6. Other findings

**Pasting source sentences verbatim (A3) scores best and answers worst.** The v0.8 behaviour
reaches 67.6% accuracy (+4.0 pp vs VeritasMed [+0.8, +7.2]) and 3.4% unsupported sentences. Both
are artefacts. 60% of its sentences are near-copies of the source, which a citation judge accepts
by construction, and its accuracy gain comes almost entirely from answering "maybe" less often
(on 33 of the 43 questions only A3 got right, VeritasMed had answered "maybe"). Its answers read like this:

> The study reports: "There was no evidence of a difference in average noise levels…"
> The study reports: "At low frequency (500 Hz), HFNC was mean 3.0 dBA quieter…" …

That is a list of quotations, not an answer. VeritasMed keeps the plain-language answer and shows
the bound source sentences beside each claim instead; this result confirms that choice.

**Accuracy on PubMedQA measures willingness to conclude.** When the retrieval methods commit to yes or no
they are right 77-88% of the time; differences in accuracy come mainly from how often they answer
"maybe". Even the gold abstract reaches only 65.6%, because the label is the authors' conclusion,
which goes beyond the reported results.

**Retrieval is not the bottleneck here.** The correct abstract is among the passages used in
98% of questions for every retrieval arm.

## 7. Limitations

- PubMedQA questions are single-paper yes/no questions with near-perfect retrieval. It cannot test
  synthesis across studies, missing evidence or scope errors - the cases VeritasMed was designed
  for. Results on those would need a different benchmark.
- The conclusion metric was found in exploratory analysis of the main run. Follow-up E1 was
  registered with it as the primary measure, on new outputs, but the same 500 questions.
- Support is judged by a model (Flash, 94% agreement on 150 labelled sentences). The labels and all
  adjudications were made by the assistant that built the harness, not by clinicians.
- One model throughout. Flash also writes VeritasMed's answers; on the calibration set it was
  stricter on VeritasMed than the labels, not more lenient, but self-preference cannot be ruled out.
- The strict prompt was written after seeing the main results, which favours it; VeritasMed's
  conclusion advantage over plain RAG does not depend on it.

## 8. Cost and reproduction

Total model spend for the whole experiment, including development runs, the follow-ups and both
judges: **$25.18** (gateway list prices). VeritasMed answers cost $5.47 for 500 questions.

```sh
python experiments/pubmedqa/prepare.py                  # download, freeze splits, build corpus
python experiments/pubmedqa/index.py                    # index 36,550 passages (GPU, ~5 min)
python experiments/pubmedqa/run.py answer --split test_full --arms A0,A1,A2,A4,A5
python experiments/pubmedqa/run.py judge  --split test_full --arms A0,A1,A2,A4,A5
python experiments/pubmedqa/score.py --split test_full   # sentence split (+ MiniCheck, kept for the record)
python experiments/pubmedqa/agreement.py --n 500 --arms A1,A2,A4,A5   # Flash citation judge
python experiments/pubmedqa/planted.py --n 200          # planted-error audit
python experiments/pubmedqa/audit_natural.py            # E2
python experiments/pubmedqa/report.py --run main --split test_full
python experiments/pubmedqa/figures.py
```

A3 runs the same harness against the verbatim variant
([`a3-verbatim.patch`](../experiments/pubmedqa/a3-verbatim.patch)) with `MEDRAG_SRC` pointing at
that source tree. Every run writes one JSON line per question and resumes where it stopped; spend
is priced from reported token usage and capped per API key.

The original design is kept as written in [`docs/plans/experiment-a.zh-CN.md`](plans/experiment-a.zh-CN.md).
