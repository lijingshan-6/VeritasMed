# Text-verification annotation policy v1

**English** | [简体中文](../verification-label-policy.md)

Applies to specified, fixed-version text views, not medical truth or evidence grades.
Fixed before new diagnostic model calls; official SciFact labels are not changed by this policy.

## Three relations

- **Support:** text establishes all material content with consistent subject, comparator, numbers,
  time, negation and qualifications.
- **Contradiction:** the same subject, conditions and event have an explicitly incompatible fact;
  missing support alone is not contradiction.
- **Insufficient:** facts needed for support/contradiction are not established in the supplied view.
  Execution errors are separate, not this label.

Ordinary synonyms, explicit references, thousands separators, exact conversions and simple
arithmetic are allowed, preserving denominator, subject and precision. Two years equals 24 months,
but not always 730 days. Abbreviations established in the source are allowed; unstated professional
aliases, external mechanisms and reverse causal inference cannot become verified evidence silently.
Flag gaps for a later source-backed entity-mapping module when needed.

“Not significant” does not mean “no effect”; an association does not establish intervention benefit.
The first stage checks explicitly stated statistical/design wording, not methodological grading or
clinical usability. Different results across papers are not automatically contradictions; this stage
uses one supplied text at a time.

## Sources and label limits

| Data | Labels | Can address | Cannot directly address |
|---|---|---|---|
| SciFact original labels | Public human annotation by the authors | Agreement with the existing verification task | Every strict-text boundary or unseen clinical generalization |
| controlled-v1 | Source anchors, construction rules and AI review | Sensitivity to traceable changes/deletions | Independent expert confirmation or natural-distribution accuracy |
| Agent observations | Actual output and AI diagnosis | Omission, aliases and inference failures | Independent correctness of the verifier itself |

AI review is not independent human review; model consensus does not change provenance. Preserve
original labels, output and doubts when models disagree; do not relabel or delete hard cases automatically.

## controlled-v1 construction

Select 12 SciFact train cited papers, excluding known dev and initial 30-pair pilot papers. Curate
for transparency rather than natural random sampling; construct four items per paper, 48 development
diagnostics. Full abstracts remain in the official local cache; IDs, hashes, sentence numbers,
transformations and rationale are retained in the repository.

1. Correct statement: directly readable fact and fixed source anchor.
2. Equivalent paraphrase: preserve fact with wording/number formatting/exact conversion changes.
3. Single contradiction: change one value, direction, arm or qualification, preserving the rest.
4. Insufficient evidence: preserve the correct claim and remove all directly supporting sentences.

Remove equally many irrelevant sentences from the first three views to reduce a short-abstract cue.
Keep sentence order. Balanced deletion counts do not guarantee equal lengths, language or semantic
cues; inspect titles and remaining context for leakage. Evidence deletion is a narrow diagnostic.
Programs check anchors/hashes, retention/deletion, grouping and fixed samples; semantic labels still
depend on the declared construction review.

All variants share one source group, never across splits. All 12 groups are development. A new
reserved set needs new groups and preregistered rules; this set cannot be renamed independent test.

## Comparison and interpretation

Methods share each claim, view, Flash configuration, token ceiling and one logical-call budget:

- `direct`: initial fixed-evidence prompt, relation and sentence IDs.
- `structured`: per-content relation, evidence and explanation, explicitly checking subject,
  numbers, units, time and qualifiers.
- `structured_no_fields`: same output/aggregation without explicit field-check instructions.

Retain model final and per-item judgments. Program aggregation: any contradiction → contradiction;
otherwise any insufficient → insufficient; otherwise support. Also report the model final judgment
as an aggregation ablation of the same output, not a new call. Model-generated item lists do not
prove complete decomposition; omissions require separate measurement. Prompts/formats and actual
tokens differ; equal computation is not claimed.

Primary measures: three-class results, class recall and non-support false acceptance. Also report
all-four-correct groups, paraphrase retention, post-deletion judgments, citation completeness,
execution errors and missing usage. Sentence binding proves location only. Pair by paper; 12 groups
do not support clinical reliability, significance or Agent superiority claims. Retain all results
rather than selecting a winner by returned provider model identifiers.

Shuffle/interleave requests in advance, concurrency at most 3. Matching gateway identifiers do not
prove stable weights. Different identifiers retain attribution limits without silent relabelling/model changes.
