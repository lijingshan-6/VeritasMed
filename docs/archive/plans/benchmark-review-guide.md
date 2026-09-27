# VeritasMed Benchmark Review Guide

This guide defines how a candidate question becomes part of the VeritasMed
Evidence-Grounded Benchmark. Review the source passages before reading model opinions.
Model agreement never accepts an item automatically.

## Review roles

- `qwen3.5:9b` drafts the fresh candidate pool, reconstructs answers from only the
  proposed evidence, and performs a final independent audit of the frozen set.
- `medgemma1.5:4b` challenges medical ambiguity, omitted qualifiers, and unsupported
  implications.
- `llama3.1:8b` is the independent-family blind challenger. Its findings are treated
  as hypotheses to check, not labels to copy.
- The curator resolves every finding against the frozen source text and records the
  decision in `quality_audit.jsonl` and `model_adjudications.jsonl`.
- A later clinician review, if performed, is recorded as a separate role. It is never
  inferred from an AI review.

Models receive the question and selected evidence passages only. They do not receive the
proposed gold answer during independent reconstruction.

## Six required review dimensions

### Population

Confirm that age group, disease state, inclusion/exclusion criteria, sample size, and subgroup
are preserved. Reject answers that generalize a study population to all patients without support.

### Intervention or exposure

Confirm the exact drug, procedure, diagnostic method, policy, risk factor, dose, and duration.
Do not merge related interventions or silently substitute a class for a specific treatment.

### Comparator

Confirm what the reported outcome is compared with: placebo, baseline, another intervention,
another subgroup, or no comparator. A within-group change cannot become a between-group effect.

### Outcome

Confirm the endpoint, unit, direction, magnitude, and whether it is primary, secondary, surrogate,
or exploratory. Correlation, association, diagnostic performance, and treatment effect are distinct.

### Time point

Confirm follow-up duration and measurement time. Do not combine results from different time points
unless the question explicitly asks for a trajectory.

### Causal and uncertainty qualifier

Preserve study-design limits, confidence intervals, statistical uncertainty, confounding,
generalisability, and the authors' stated limitations. Observational association must not become
causation. Absence of evidence must not become evidence of no effect.

## Evidence labels

- `direct`: the quote explicitly states the claim.
- `derived`: the claim is a transparent calculation or comparison from quoted values. The
  calculation must be written in the review note.
- `context`: useful background that cannot satisfy a required claim alone.

Every required claim needs at least one `direct` or justified `derived` evidence span. Exact quote
matching ignores whitespace differences only.

## Candidate rejection rules

Reject or rewrite a candidate when any of these apply:

- The question joins unrelated domains merely to create difficulty.
- The answer needs general medical knowledge absent from the selected passages.
- Multiple materially different answers are equally reasonable.
- The question copies a rare phrase or exact measurement that makes retrieval trivial.
- A required claim has no exact source span.
- The evidence is truncated, retracted, duplicated, or missing a stable identifier.
- A comparative question lacks a common disease, intervention, diagnostic method, population,
  or outcome.
- The expected answer hides a limitation that changes interpretation.

## Review sequence

1. `draft`: source and evidence are selected before wording is final.
2. `evidence_checked`: every claim has been checked against exact source text.
3. `ambiguity_checked`: the question has one intended interpretation and plausible user intent.
4. `adversarial_checked`: both local model reviews are stored, including disagreement.
5. `adjudicated`: a curator resolves each finding from source evidence.
6. `frozen`: the item is assigned to a split and is immutable within benchmark v1.1.

Skipping a state is invalid. Any change to question text, gold claims, answerability, or required
evidence after adjudication returns the item to `evidence_checked` and appends a new review event.

## Answerability

- `complete`: all required claims can be answered from the frozen corpus.
- `partial`: at least one useful claim is supported and at least one requested material claim is
  absent. The missing evidence must be named.
- `unanswerable`: no source in the frozen corpus supports a responsible answer. The expected
  behavior is a concise refusal that states the evidence boundary without adding model knowledge.

## Acceptance record

An adjudication event records the question ID, prior state, next state, actor, UTC timestamp,
model tag when applicable, prompt version, findings, decision, evidence-based resolution, and
hash of the raw model output. Hidden reasoning is not stored.

The active records live under `data/benchmark/veritasmed_v1_1/`. The historical v1
directory is preserved as a separate snapshot and still names the models used for that
earlier run.
