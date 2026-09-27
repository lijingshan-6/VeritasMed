# v0.6 audit reliability research

The planned fixed-claim, calibration, constructed medical, natural-development, repeat and
ablation runs are complete. See the [research report](../../../docs/reports/verification-v0.6-report.md).
Read each `attempt-*.json` and retain every prediction/error. The natural-answer final reserve
was not used; completion of these studies does not mean whole-answer reliability is established.

`splits.json` is the source-connected partition contract; `medical.json` contains authored
source-grounded diagnostic labels; `natural.json` fixes 36 new RAGTruth training sources.
Public-label fixed claims, constructed diagnostics and natural-answer localization results
must be reported separately. No new independent clinical expert annotation is claimed.

The 60 historical RAGTruth official-test source groups remain reserved. They are not unlocked
by the fixed-task freeze. SciFact official dev is public labelled evaluation, not official test;
public data may be present in pretraining. Absence of rationale for a cited abstract means
insufficient support in that abstract, not medical falsehood.

## Fixed-claim study

- Development pilot: 60 pairs.
- Score fitting: 87 pairs / 50 connected groups.
- Threshold selection: 91 pairs / 50 groups.
- Final: 339 pairs / 247 groups, only after `fixed-method-freeze.json`.
- `fixed-*-metrics.json` and `calibration*.json` are offline derivatives, never labels.
- MiniCheck uses revision `96eafd01cee2d16cf81aaa2fb226b14f422a37b3`, FP32, full inputs
  up to 2048 tokens. Larger inputs fail explicitly; no hidden truncation or chunk selection.
- Independent GPU calibration was allowed to proceed alongside answer development because
  this fixed-target method was already frozen. No whole-answer method is tuned on final results.

## Medical construction

23 source groups × 4 variants = 92 short answers; 15 development / 8 transfer groups.
One initially selected source was excluded for internally inconsistent years and truncation.
Each source view consists only of specified original abstract sentences; labels apply only
to that view. Cases include faithful paraphrases, exact conversions, changed arm/value/population
and evidence removal. No claim is made that these represent the natural frequency of errors.

Primary constructed matching is deliberately visible: original fact character ranges are compared
with original answer anchors. Normalized model parsing is never silently matched by another model.
This avoids self-grading, but lexical matching can miss faithful paraphrases or credit broad spans;
it does not establish semantic extraction fidelity. Individual records must remain inspectable.

`medical-label-review.json` records a later developer/AI source-view review: medical-15 names
Natsal-3 although the supplied title and chosen sentences do not establish that wave identifier.
The original labels and primary results remain intact. `medical-label-sensitivity.json` reports
all methods after omitting that whole group, explicitly as a post-hoc sensitivity view, not new
expert gold or a replacement result. This also demonstrates why constructed labels need caveats.

## Sources and licenses

[SciFact](https://github.com/allenai/scifact) is cached from the pinned archive used in v0.5;
[RAGTruth](https://github.com/ParticleMedia/RAGTruth) retains its pinned revision and source terms.
Dataset/paper text is third-party material; the repository's Apache-2.0 license does not
relicense it. See [source attribution](../../../docs/research-sources.md) and the
[MiniCheck guide](../../../docs/minicheck-research.md). SciFact distinguishes CC BY 4.0
claims/annotations and ODC-By 1.0 corpus abstracts.
