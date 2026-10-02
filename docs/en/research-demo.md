# v0.7 demonstration: atomic auditing and workflow comparisons

**English** | [简体中文](../research-demo.md)

Use the lightweight [README](../../README.md) environment:

```sh
python scripts/run_audit_demo.py
```

One service supplies `/audit` and `/research`. After installation, replay/location/export needs
no key, model downloads, Qdrant or GPU. **SAVED INFERENCE** does not rerun a model on loading.

## Three original-source medical audits

At `http://127.0.0.1:5174/audit`, select **Atomic facts · experimental** and a GRADE case.
Sources remain Seaquist et al.'s [CC0 paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC11567630/);
original extracted abstract and actual Ask output are in the [source card](../../data/demo/medical/README.md).

| Case | Input | Inspect |
|---|---|---|
| GRADE · unchanged real Agent answer | Unchanged v0.5 answer/sources, newly audited in this experiment | Compound sentence decomposition, omissions and unresolved facts |
| GRADE · deliberately swapped arm values | Constructed swap of glargine/glimepiride severe counts/percentages only | Numbers present but paired to the wrong arm; misses remain |
| GRADE · result evidence deliberately removed | Same answer, original background passage only | Insufficient vs execution failure vs unchecked; supplied gaps are not global absence |

The latter two are constructions, not naturally occurring Agent errors or natural error-rate
estimates. Each retains one Direct and one atomic-v1 run, not the best retry.

| Actual saved output | Direct | Atomic |
|---|---|---|
| Original answer | 4 supported | 13 supported, 9 unchecked/unresolved |
| Swapped arms | 4 supported, 1 contradicted | 14 supported, 1 contradicted, 9 unchecked/unresolved |
| Evidence removal | 3 supported, 9 insufficient | 12 insufficient, 11 unchecked/unresolved |

Extraction granularities differ; green counts are not comparable effectiveness. Atomic records
retain 22/24/23 MiniCheck GPU checks, all 69 completed; swapped/removal cases each have two disagreements.

![Actual atomic facts and original highlights](../assets/v07-atomic-medical.png)
![Constructed swapped arms and checker disagreement](../assets/v07-checker-disagreement.png)

1. Select a parsed fact and **Original answer fragments**, preserving original wording.
2. Compare **Explicit qualifications**: population, arms, values, time and qualifiers. Slots are
   interpretations; empty does not prove absent information, filled does not prove clinical scope.
3. Inspect **Fragment and evidence locations** / **Answer context**. Non-unique bindings stay
   unresolved; no guessed first occurrence.
4. **Locate in full source** and **Open original paper** show provenance.
5. **Checkers disagree** exposes recorded outputs, preserving Flash and a separate MiniCheck
   support/non-support result. MiniCheck sees a standalone normalized fact while Flash also sees
   answer context: this product observation is not strict same-input E2. No votes/confidence synthesis.
6. Export raw inputs, positions, Flash calls and MiniCheck supplementary records as JSON.

MiniCheck's separate GPU run is a sidecar merged by record/fact hashes during replay; Flash is
not overwritten. Incomplete/review facts are not absorbed into Supported counts.
To inspect all 36 natural answers, optionally run `python scripts/verification/answer_benchmark.py download`,
restart and choose RAGTruth IDs/Direct/Split/Atomic. Cached sources must match pinned fingerprints,
not approximate replacement text. Repeats stay in raw records, not substituted best outputs.

## Actual three-workflow comparison

Open `http://127.0.0.1:5174/research` or select **Research**.

1. Choose a saved fact query. Three development examples were seeded before inference;
   [selection.json](../../data/demo/research/selection.json) retains rules/IDs, not outcome-based selection.
2. Compare **Read all documents / Autonomous tools / Structured workflow** answers, relations,
   calls, duration and tokens. Public labels shown below the question were not sent to the model.
3. Expand **Execution trace** for search/read/verify and replies. Verify counts as a model call.
   Autonomous uses application JSON actions, not provider-native tools.
4. Disagreements stay review-needed; original answers are not automatically replaced. Valid
   location identifies a quote, not correct meaning.
5. **Audit this answer with the candidate sources** transfers the unchanged answer and all eight
   abstracts without inference. **Run new audit** then uses your configured Flash endpoint.
6. **Export all traces** saves all arms. Final tables use a separate 40-query set, not the three
   development demos; the report retains paired intervals and original draft scores.

The task is whether a named paper supports a claim, without open web search or the full historical
Ask retrieval/rewrite/repair graph. It cannot establish Agent superiority for clinical questions.

![Actual saved workflow/tool trace](../assets/v07-research.png)
![Final 40-query denominators and costs](../assets/v07-research-results.png)

Replay uses development round two after action-protocol correction. All 60 first-round records
and protocol failures remain. Traces identify normalization; DSML suffixes remain raw output
only, never executed or source evidence.

## New runs and export boundaries

New audits need Flash in ignored `.env`. Atomic allows at most 48 facts / 3 model calls; complex
answers can reach limits or leave unchecked facts. See [other limits](audit-demo.md). MiniCheck
is optional research software, not an automatic download during visitors' live Flash audits.

New workflows also have POST `/api/research`; fields are in `http://127.0.0.1:8001/docs`.
The interface primarily compares saved real flows. For paid batches and independent directories,
see [reproduction](research-reproduction.md); exposed questions are not new unseen tests.
These labels do not automatically establish grades, cross-paper comparability or literature
conflicts. They show traceable text judgments, unresolved items and distribution-specific research.
