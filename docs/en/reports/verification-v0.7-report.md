# v0.7 workflow comparison: is the structure worthwhile?

**English** | [简体中文](../../reports/verification-v0.7-report.md)

Three arms compare fixed-paper fact queries: read every abstract in one call, Flash choosing tools
autonomously, and a prescribed search–read–draft–verify workflow. **This bounded new module does
not validate the historical full Ask graph, open medical research or clinical conclusions.**

**Conclusion: the final 40 queries do not demonstrate better decisions from the prescribed workflow.
Read-all and autonomous tools each achieve 35/40 correct binary decisions; the prescribed workflow
accepts correct decisions on 31/40. All arms falsely accept 2/19 non-supports. Keep simple controls;
these results do not justify automatic answer repair.**

## Design and comparable scope

20 independent train source groups are development; 40 separately reserved groups form one final
comparison after freezing. Each group contributes one seeded query with a target paper title and
claim. Candidates are the target plus 7 fixed distractor abstracts. Models see no labels or gold
rationales. Public SciFact labels evaluate the specified paper relation, not every explanatory sentence.

The same Flash gateway settings, corpus, public search/read/verify tools and call ceilings apply.
Both tool arms allow at most 6 model calls and 8 non-model tool calls; verify consumes the same
model budget. Autonomous tools use an application JSON action protocol, not provider-native
`tool_calls`. The structured arm selects an exact title match. Naming the target makes search
easier; results do not generalize to open retrieval for unknown papers.

The Direct reader reads all eight abstracts once. Its compute/context differ from the tool arms;
this is a deliberately retained simpler option. Actual tokens, latency and calls are reported:
equal ceilings do not establish equal compute.

After the first development run, the autonomous action protocol was repaired. All three arms
were rerun once on the same 20 development queries before final freezing. Original records remain;
an underperforming baseline was not excluded. The structured arm preserves drafts and verifier
comments; disagreement or verification failure retains the judgment for review, rather than
automatically replacing it with the verifier's answer. The verifier is not gold.

## One final comparison

| Method | Acceptable completion | Correct binary / all | Non-support accepted | Support recall | Support precision | Correct three-way / all |
|---|---|---|---|---|---|---|
| direct_reader | 40/40 | 35/40 | 2/19 | 18/21 | 90.0% | 34/40 |
| autonomous_tools | 40/40 | 35/40 | 2/19 | 18/21 | 90.0% | 34/40 |
| structured_workflow | 36/40 | 31/40 | 2/19 | 15/21 | 88.2% | 31/40 |

Failures, unchecked items, disagreements, exhausted budgets and wrong papers stay in the all-query
denominator and are not correct rejections. Binary scoring merges contradicted/insufficient;
three-way scoring retains the distinction.

### Execution and protocol limitations

| Method | Workflow statuses | Initial parsing/call errors | Action normalization | Replies with DSML markers |
|---|---|---|---|---|
| direct_reader | {"ok": 40} | {} | {} | 0 |
| autonomous_tools | {"ok": 40} | {"JSONDecodeError": 18} | {"ignored_dsml_suffix": 18} | 18 |
| structured_workflow | {"ok": 36, "needs_review": 4} | {} | {} | 0 |

The first development run exposed conflicting finish-wrapper/bare-answer instructions and DSML
markers following JSON actions. Before running final queries, all original records were retained,
the prompt was corrected and explicit normalization was added in the second development run:
use only the leading complete JSON object, discard and do not execute the DSML suffix; wrap a
complete bare answer as finish, still checking that cited papers were read and citations exist.
Simulated tool output never becomes evidence.

The second run retains full raw replies, first parsing errors and normalization notes. An initial
JSONDecodeError need not mean final workflow failure; interpret it with workflow status and
adaptation counts. First-run failures remain. Final methods were frozen only after the complete
second development comparison. DSML text cannot establish whether the model or gateway caused
the issue, and it is not itself a medical reasoning error.

Scores jointly reflect output contracts/adaptation, completion and relation judgments. Other
native tool-call implementations were not compared. Even a prescribed-workflow lead could not
all be attributed to Agent reasoning structure or treated as the autonomous model's capability ceiling.

![Workflow and cost comparison](../../assets/v07-workflow-comparison.png)

| Structured − control | False-acceptance difference, 95% CI | Support-recall difference, 95% CI |
|---|---|---|
| structured_minus_direct_reader | +0.0 pp [+0.0, +0.0] | -14.3 pp [-31.6, +0.0] |
| structured_minus_autonomous_tools | +0.0 pp [+0.0, +0.0] | -14.3 pp [-31.6, +0.0] |

Paired source-group bootstrap: 40 groups, 2,000 resamples, seed 260926. Degenerate intervals and
small class denominators remain visible; a leading point estimate does not establish efficacy.

### Actual cost and retained drafts

| Method | Target paper read | Correct binary draft | Review required | Calls / query | Reported tokens / query | Mean seconds / query |
|---|---|---|---|---|---|---|
| direct_reader | 40/40 | 35/40 | 0 | 1.0 | 4605 | 6.3 |
| autonomous_tools | 40/40 | 35/40 | 0 | 3.4 | 5339 | 14.0 |
| structured_workflow | 40/40 | 35/40 | 4 | 2.0 | 3655 | 15.6 |

Draft scores retain answers rejected by verification and differ from final acceptable decisions.
Raw records contain every call, evidence sentence ID, tool arguments, returned texts and model
identifiers. Latency is per-query end-to-end time; API tokens cannot determine local GPU or monetary cost.

The prescribed workflow reports fewer tokens than direct reading but higher latency and lower
support recall. These are separate dimensions, not proof that one call/token metric makes it
cheaper or better. Read-all and autonomous tools share binary scores, but their per-query three-way
outputs are not identical.

### What are the four review items?

| Final case | Public relation | Draft | Verifier | Interpretation |
|---|---|---|---|---|
| scifact-train-788-4740447 | supported | supported | insufficient | Correctly supported original retained |
| scifact-train-296-4398832 | supported | supported | insufficient | Correctly supported original retained |
| scifact-train-1229-1676568 | supported | supported | insufficient | Correctly supported original retained |
| scifact-train-790-15493354 | contradicted | insufficient | contradicted | Three-way disagreement; draft already binary non-support |

All four drafts are binary correct, but only the first three exactly match public three-way labels.
The fourth verifier response cannot simply be called a false alarm, nor can abstention count as a
corrected answer. Original answers await review without automatic edits.
[All 40 case records](../../reports/verification-v0.7-cases.md) retain drafts and sources in their original language.

## Development separately: second protocol run

| Method | Correct binary / all | Completed | Non-support accepted | Support recall |
|---|---|---|---|---|
| direct_reader | 19/20 | 20/20 | 0/11 | 8/9 |
| autonomous_tools | 19/20 | 20/20 | 1/11 | 9/9 |
| structured_workflow | 15/20 | 15/20 | 0/11 | 6/9 |

Development informs implementation and freezing, and is not pooled with the final 40 queries.
Three showcase replays were seed-selected before running from development, not selected as the best cases.

### Retained first development run: protocol defects

| Method | Completed / 20 | Correct binary / 20 | Replies with DSML |
|---|---|---|---|
| direct_reader | 20 | 19 | 0 |
| autonomous_tools | 0 | 0 | 14 |
| structured_workflow | 18 | 17 | 0 |

Autonomous completion 0/20 exposed prompt/adaptation defects, not a valid tool-capability ceiling.
The second round added no papers, labels, permissions or call ceilings, and did not select the
best per-query result across runs. [development-original](../../../data/verification/v07/development-original/metrics.json)
preserves manifests, replies and first scores. Development is exposed; only the final 40 groups
provide the independent comparison after freezing.

## Interpretation and next research

The experiment measures how a prescribed workflow changes support judgments, retention and
cost for known target papers, a small fixed candidate pool and fixed Flash settings. It does not
alone compare a full medical Agent against a strong model freely using all production tools.

Direct remains default. Automatic repair and audit-driven open retrieval were not released as
proven effective: v0.6 found verifier false alarms and qualifier loss, so forcing answers toward
verifier outputs can damage correct content. Future independent tasks should require locating
unnamed papers/additional evidence, then measure individual steps. This final set is exposed and
can now serve only regression purposes.

## Reproduction, records and demonstration

[Raw outputs and frozen manifests](../../../data/verification/v07/README.md) ·
[Offline recomputation and separate new runs](../research-reproduction.md) ·
[Product demonstration](../research-demo.md) ·
[Original protocol (Chinese)](../../plans/v0.7-agent-comparison.md).

Labels follow [SciFact's official format](https://github.com/allenai/scifact/blob/master/doc/data.md).
An unannotated rationale means insufficient information in that abstract, not no evidence anywhere.
Public-data training contamination, title hints, fixed distractors, one model and small groups limit generalization.
