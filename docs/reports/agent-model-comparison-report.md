# DeepSeek Pro and Flash through the production Agent

**Current decision (2026-09-23): use Flash as the research baseline because of Pro's token cost.**
This user decision supersedes this report's initial recommendation to use Pro; see the
[decision record](../decisions/2026-09-23-flash-research-baseline.md). The empirical results remain unchanged.

Pro had fewer retained whole-answer failures, fewer unnecessary repair cycles and lower
observed average latency in these runs, which motivated the initial recommendation.
This is not proof that Pro is necessary, that Flash lacks the required knowledge, or that either
model removes the Agent's limitations. Flash can perform the main literature tasks; its
current end-to-end behavior is not yet equally dependable on these observed cases.

This comparison uses the user-supplied OpenHub gateway. `DeepSeek-v4-pro` and
`deepseek-v4.1-flash` are the
gateway's model IDs; the IDs and response metadata do not independently authenticate
the underlying model weights or establish an official same-generation tier comparison.

**Do not substitute model choice for the identified Agent fixes.** Both models are limited
by requirement expansion, overly strict source filtering, gap rendering, and a self-check
that often accepts contradictions. Neither satisfies a zero-unsupported-statements target
over the full round. The 35-question test split remains unused.

## Full development round

The uninterrupted streaming round on 2026-09-23 completed all 15 questions for each model.
The same existing scorer consumes answer-hash-bound, source-reviewed assessments.

| Observation | Pro | Flash |
|---|---:|---:|
| Strict whole-answer passes | 13/15 | 12/15 |
| All required evidence found, answerable questions | 13/13 | 12/13 |
| Unsupported or contradictory material statements | 2 | 3 |
| Missing required qualifiers | 0 | 0 |
| Execution errors / truncated model calls | 0 / 0 | 0 / 0 |
| Agent self-check accepts | 15/15 | 15/15 |
| Self-check accepts a failed answer | 2 | 3 |
| Evidence-label contract mismatches | 4 | 6 |
| Query rewrites / answer regenerations | 0 / 1 | 2 / 3 |
| Mean / median question latency | 80.1 / 79.8 s | 112.5 / 90.2 s |
| Slowest question | 140.3 s | 252.1 s |
| Questions exceeding the existing 300 s API deadline | 0 | 0 |
| Answers with deterministic source-quote replacement | 13 | 12 |

Raw answers and scoring inputs are in
[`deepseek_comparison_streaming`](../../data/benchmark/veritasmed_v1_1/deepseek_comparison_streaming).
Read the [Pro cases](agent-model-comparison-pro-cases.md) and
[Flash cases](agent-model-comparison-flash-cases.md) to inspect the actual text.
Model self-check agreement is not a correctness score: every retained answer was accepted,
including the failures below. The observed timing advantage for Pro belongs to this gateway
and run; it is not a general claim about the two models' intrinsic speed.

### What failed, and where

- **Flash, VMG-010:** incorrect refusal with no final evidence. Its otherwise natural
  `LGR5-targeted` / `Nectin4-targeted` queries hit a brittle production identifier filter.
  The filter treats the descriptive suffix as part of the identifier and discards the
  correct source cards before any LLM can select or read them. Calling the unchanged
  filter with each correct corpus passage rejects both cards; removing just `-targeted`
  admits both. See the [saved diagnostic](../../data/benchmark/veritasmed_v1_1/deepseek_comparison_streaming/identifier_filter_diagnostic.json).
  This is a real end-to-end failure and an Agent robustness defect, not a source-reading
  ability test that Flash failed.
- **Pro, VMG-018:** both required methods and validation results are correctly present,
  but the final gap says no validation result is established for the diffusion filters.
  That directly contradicts the quoted synthetic/real-image validation. Unlike a wrong
  status badge, this adds a materially contradictory statement to the answer.
- **Both, VMG-032:** the estimates and basic cross-sectional limitation are correct.
  Flash adds that the measurements were simultaneous, which the passage does not specify,
  and ends by denying the design limitation it just explained. Pro adds a causal-inference
  rationale tied to the nonsignificant flow-by-vintage interaction; the source does not
  establish that rationale. A nonsignificant interaction and a cross-sectional design
  are different issues.
- **Flash, VMG-034:** the requested factors and outcome comparisons are correct, but the
  answer calls the pelvic comparison a subgroup analysis and then declares subgroup or
  sensitivity analyses for that comparison unavailable. It also invents unrequested
  requirements for success/failure rates and neonatal outcomes.

The Pro VMG-032 causal-rationale decision and Flash VMG-034 subgroup-gap decision are
conservative judgments of ambiguous explanatory wording, with the exact text published
for inspection. Even setting those two penalties aside would leave clear failures in
both models. A statement that contradicts a reported result counts as a content failure;
an accurate but unrequested absence of evidence counts as a control/presentation defect.
An evidence-label mismatch alone does not fail the content score.

Both models correctly refuse the unsupported prospective biopsy/patient-benefit claim
(014) and comparative ASRT survival/local-control claim (042). Both preserve the SCAR-Net
development-versus-validation distinction (009). Neither model receives credit for
proving that the entire Agent is reliable beyond these development questions.

## Repeat and stability

The unchanged implementation then ran the predeclared six difficult questions
**009, 011, 014, 018, 032, 042**, plus **010** as an explicitly post-observation diagnostic.
The extra question was chosen to investigate the first-round source-filter failure;
it is not a new independent test. No prompts, rules or model budgets changed between rounds.

| Paired question set | Pro | Flash |
|---|---:|---:|
| Full first round | 13/15 | 12/15 |
| Predeclared six, their first-round answers | 4/6 | 5/6 |
| Same six, independently generated repeat | 6/6 | 4/6 |
| Extra diagnostic 010, first round | Pass | Fail |
| Extra diagnostic 010, repeat | Pass | Pass |

The complete seven-question repeat therefore scores **7/7 Pro versus 5/7 Flash**.
All required evidence is found for 5/5 answerable questions by both models. Neither has
an execution error, truncation or question over 300 seconds. Pro averages **80.9 s**
(median 81.9, maximum 99.8); Flash averages **97.4 s** (median 81.0, maximum 195.0).
Pro performs no regeneration; Flash regenerates twice on 018. Coverage-label mismatches
remain in one Pro answer and three Flash answers.

Flash's repeat 009 adds an overbroad gap denying building/architecture information after
quoting it. Its repeat 018 insists that qualitative validation is insufficient without
unrequested numerical results; after two repair cycles, the final answer incorrectly
says the validation result is missing. The checker flags that answer, but for the invented
numerical requirement, not because it identifies the contradictory gap. Pro's repeat 032
has the correct causal explanation but still adds an unrequested future-study-design gap.

For 010, Flash generates a different query wording and succeeds with the same code and
sources. This supports the source-filter diagnosis and argues against interpreting its
first failure as inability to understand the papers. The original failure is not replaced.

Read [repeat Pro cases](agent-model-comparison-repeat-pro-cases.md),
[repeat Flash cases](agent-model-comparison-repeat-flash-cases.md), and the
[repeat artifacts](../../data/benchmark/veritasmed_v1_1/deepseek_comparison_repeat).
The six-question first-round ordering actually favors Flash, while the repeat favors Pro:
variation matters. These small, reused development samples do not establish statistical
superiority or equivalence. Do not pool the rounds and label them independent accuracy.

## Next changes to the Agent

1. Separate named entity identifiers from descriptive suffixes such as `-targeted`.
   Preserve the actual target/tracer identity without rejecting a paper because the model
   phrased its query differently. Keep evidence selection source-bound.
2. Build required components only from the user's request. Unasked AUCs, success rates,
   or detailed numerical validation must not become blocking requirements. When a component
   is partly answered, render only the precise missing outcome, not the entire requirement
   as if none of it were supported.
3. Check the final answer together with its evidence-gap sentences for contradictions.
   A component can contain correct quotations while the merged answer denies them.
   The current self-check result must not be presented as an independent correctness score.
4. Keep full quotations in expandable evidence and render a concise supported explanation.
   Preserve numerical comparators, study population roles and causal boundaries explicitly;
   wholesale source replacement should not dominate every otherwise adequate answer.

These are shared Agent changes, not model-specific workarounds. Keep Flash fixed as
the research baseline under the current decision and retain Pro's saved runs as historical
comparisons. A new Pro run is optional, not part of routine development. Use the untouched
test split only after those design decisions are fixed. Current priorities are maintained
in the [decision record](../decisions/2026-09-23-flash-research-baseline.md).

## What this experiment compares

Both models run the actual v0.4 Agent: route the question, retrieve and rerank literature,
select the requested study, build evidence components, generate the answer, and check
or repair it. The same selected model fills every LLM role within each question.
The prompts, graph, source corpus, evidence handling and scoring rules are unchanged.
The question-dependent searches and resulting evidence can differ; those differences
are part of the end-to-end result.

Use the frozen 15-question development split. The 35-question test split remains unused.
Neither model is shown gold answers. Answer assessments compare each saved answer with
its frozen sources, including additional claims beyond the minimum gold facts.
These are AI-assisted source-first engineering reviews, not independent clinician reviews.

Both models request thinking enabled, reasoning effort `high`, and 32,768 output tokens
per call. Structured calls request JSON-object output; the existing component schema
is also present in the unchanged checker prompt. Calls use streaming transport and
a 240-second client timeout, with one SDK retry. At most three question jobs overlap;
each job's LLM calls are sequential. Local retrieval operations share one set of CUDA
models and run serially.

## Reading the results

Strict content correctness, evidence coverage labels, and model self-check results
are separate observations. For example, an answer can correctly explain that a
longitudinal result is unknown while the interface incorrectly labels the question
as fully supported. That label discrepancy is not automatically a false medical claim.

The existing browser API has a 300-second question deadline. This research runner lets
the graph finish beyond that limit and records the elapsed time. A correct answer
produced after the deadline does not establish that the current browser flow can deliver it.
Local model initialization is outside the per-question timings; shared GPU queuing is
included. These are observed end-to-end timings, not isolated model throughput measurements.

Earlier Qwen results use different thinking and embedding-device settings. They are
historical context, not a controlled speed or model-quality comparison with this run.

The production `preserve_result_context` and `restore_numeric_quotes` steps replace or
supplement model prose with source sentences. Their intervention is logged in 13 Pro and
12 Flash answers. This protects numbers and study roles but also explains long, repetitive
answers; it must not be attributed entirely to model quality. Likewise, refusal rendering
can collapse an explanation into a question-shaped gap sentence. These shared behaviors
remain even with a stronger model.

## Reproduce the saved scores

These commands need the installed project dependencies, but no API key, model or GPU:

```sh
python scripts/benchmark/report_model_comparison.py
python scripts/benchmark/report_model_comparison.py --directory data/benchmark/veritasmed_v1_1/deepseek_comparison_repeat --case-prefix agent-model-comparison-repeat
```

## Optional replay of the historical paired experiment

For routine Flash-only development, use the [research guide](../configuration.md#flash-research-profile).
The command below explicitly calls **both Flash and paid Pro**; it is not the default baseline run.
To repeat that paired experiment, prepare the existing frozen research index and configure the
ignored `.env` with `OPENHUB_BASE_URL`, `OPENHUB_API_KEY`, and an exact gateway model ID.
The paired runner selects each model per question; it does not mutate a shared model
environment variable. It requires the CUDA research environment used here, unlike the
CPU-only showcase quick start. The index must already be in `.benchmark-runtime/qdrant`,
collection `veritasmed_benchmark_v1_1`.

```sh
python scripts/benchmark/compare_agent_models.py --models pro flash --output-dir .benchmark-runtime/my-model-comparison
```

The runner refuses to overwrite a saved run. `--resume` permits continuation only with
matching question hashes, runtime-file hashes and common settings. New live answers need
new source-first assessments; an old assessment cannot score a different answer hash.

## Preserved attempts

- `data/benchmark/veritasmed_v1_1/deepseek_comparison`: initial setup failure and serial trial.
- `data/benchmark/veritasmed_v1_1/deepseek_comparison_paired`: concurrent non-streaming trial,
  including Pro's HTTP 524 generation failure on VMG-002. The gateway reported its
  120-second proxy read timeout. This is a transport failure, not a semantic error.
- `data/benchmark/veritasmed_v1_1/deepseek_comparison_streaming`: complete comparison target,
  plus startup failure logs and the user's interrupted attempt. No answer completed in
  that interrupted streaming attempt; execution resumed on 2026-09-23.
- `data/benchmark/veritasmed_v1_1/deepseek_comparison_repeat`: seven-question repeat on the
  identical runtime files/settings. Its raw files reference the same implementation hashes
  and use the implementation snapshot retained in the streaming directory.

No selected answer is substituted from one attempt into another. The raw artifacts
retain model calls, requested settings, final outputs, timings, and implementation hashes.
Credentials and internal reasoning transcripts are excluded.

The [experiment plan](../archive/plans/2026-09-22-deepseek-agent-comparison.md)
records the predeclared decision criteria, the six-question repeat and the subsequent
diagnostic addition. In total, the two completed rounds retain **44 production-Agent answers**.
Three concurrent question jobs were enough to complete them without a retained execution
error; this is observed adequacy for this workload, not a load-capacity claim.
