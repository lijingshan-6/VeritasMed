# v0.8 research and development records

Completed v0.8 records. These combine software demonstrations and explicitly bounded
textual diagnostics; they do not establish clinical reliability.

| Artifact | Meaning |
|---|---|
| context-dev.json | 12 authored intent-resolution scenarios, fixed before model calls; not medical gold |
| context-run-01 / context-run-02 | Actual Flash development runs, 11/12 then 12/12 on the stated contract checks; both retained |
| grade-conversation-smoke.json | Two actual Ask turns and one Direct audit; importable conversation export, not an independent test |
| exposure/inventory.json | Repository source-use snapshot, including all supplied v0.7 distractors |
| exposure/inventory-local.json | Extended snapshot including specified local saved diagnostics; same source counts |
| r1-parent-binding/protocol.json | Offline replay input and implementation fingerprints |
| r1-parent-binding/summary.json | 167 saved Atomic runs, 1,203 facts; 82 recovered positions, no new semantic judgments |
| r1-parent-binding/records.jsonl | All original fact judgments alongside old/new position bindings |
| r1-parent-binding/changes.jsonl | All 82 recovered and all 24 unresolved facts, with original record references |
| r2/manifest.json | 24 source-separated groups / 96 constructed answers, 12 natural development answers and six predetermined repeat inputs |
| r2/development, r2/natural, r2/repeat | Actual Direct / v1 / v2 development outputs, every recorded attempt and its protocol |
| r2/method-freeze.json, r2/final | Candidate fingerprint and all 144 audits from one post-freeze final run |
| r2/summary.json | Offline mechanical summaries and source-group paired intervals; not clinical accuracy |

See the [development log](../../../docs/archive/worklogs/development-v0.8-worklog.md),
[exposure decision](../../../docs/reports/verification-v0.8-exposure.md), and
[localization report](../../../docs/reports/verification-v0.8-localization.md).
Dataset provenance and distinct upstream licenses remain in
[research sources](../../../docs/research-sources.md).

R2 contains all 348 scheduled audits and 577 recorded model calls. See the
[complete report](../../../docs/reports/verification-v0.8-report.md) for results, intervals and limitations.
The three full medical conversations are preserved separately in
[the actual replay directory](../../demo/conversations/README.md), not mixed into R2.
Only one unexposed public SciFact labelled pair
remains under the recorded exclusions; R3 cannot currently support a new semantic
generalization claim. Direct / Flash remains the default. The 60 reserved RAGTruth
official-test source groups have no recorded task exposure in this inventory.
