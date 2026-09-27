# DeepSeek Pro / Flash: full Agent comparison

**Completed experiment; current selection updated 2026-09-23.** The user now selects Flash
as the continuing research baseline because of Pro's token cost. See the
[current decision](../../decisions/2026-09-23-flash-research-baseline.md).

Started 2026-09-22. The original experiment authorized OpenHub API use, with at most three
concurrent requests, and did not use cost as a selection criterion. Those were the historical
comparison conditions; the new cost decision governs future work. Credentials stay in the ignored local `.env`.

## Question and fixed conditions

Does `deepseek-v4.1-flash` preserve the current Agent's intended behavior, or does
`DeepSeek-v4-pro` give a meaningful quality advantage? These are OpenHub model IDs;
gateway names and returned metadata do not independently authenticate the underlying weights.

Use all 15 existing development questions with the unchanged gold contract and scorer.
The 35 test questions remain unused. Keep production graph, prompts, retrieval corpus,
study matching, evidence binding, repair loops and limits unchanged. Model-dependent
query planning and retrieved evidence may differ and are part of the end-to-end result.
Neither model receives gold answers. No simplified pipeline in this comparison.

Both fast and review roles use the same selected model, thinking enabled, effort `high`,
32,768 output tokens per call, JSON-object mode for structured calls, 240-second request
timeout, with streamed chunks assembled into the same final message consumed by the graph.
The component schema remains in the unchanged checker prompt. No 8K local-context
restriction is imposed on the cloud models. Do not silently lower reasoning or output budgets.
Record any length-truncated responses or technical failures, not just successful answers.

One process reuses the local index and warmed CUDA embedding/reranking models. Alternate
Pro-first / Flash-first when queuing question pairs; at most three questions run concurrently,
each with sequential API calls. Model selection belongs to each question's graph configuration,
not a shared changing environment variable. GPU retrieval operations are serialized with
unchanged inputs and algorithms. This avoids replicating ML models on a 16GB machine. Saved Qwen results
are historical context only: its CPU embedding and disabled thinking differ from this setup.

## Execution and decision

1. Add gateway configuration and a runner that saves each production answer and node call.
2. Run the paired 15-question development comparison without per-model prompt tuning.
3. Review every answer against frozen sources and required/forbidden claims. Separately
   record self-check false positives/negatives, wrong evidence labels, source attribution,
   unnecessary regeneration and readability. Model self-check is not the final judge.
4. If a technical integration defect invalidates a run, retain it and repeat both models
   at the corrected common configuration. Do not replace a semantic failure with a retry.
5. Repeat the same six difficult questions (009, 011, 014, 018, 032, 042) for both models
   if a stable preference cannot be established from the complete first run. Report all rounds.
6. Publish raw answers, call metadata, source-based assessments, paired case comparisons
   and a recommendation. Keep original Qwen artifacts and failed attempts.

Existing development floor: at least 13/15 strict content passes, zero unsupported material
additions, all required evidence found for 13/13 answerable questions. Passing this floor
does not prove unrestricted generalization or clinical reliability. To say Flash is enough,
it should show no meaningful content/control disadvantage on these paired development cases;
ties remain ties, and no statistical equivalence is inferred from 15 examples. Choose Pro
for a repeatable semantic advantage, not for its name. If both are hindered by the same
graph assumptions, report that architectural limit explicitly instead of blaming one model.

## Execution notes

The initial launch used the CPU-only showcase venv and failed during GPU initialization,
before answering any question. Its setup log is retained. The existing CUDA research
environment is `C:/Users/lijingshan/.conda/envs/medrag/python.exe` (PyTorch 2.6.0+cu124).

A serial trial is retained in `data/benchmark/veritasmed_v1_1/deepseek_comparison`.
Pro's first answer took 194.9 seconds, including 79.8 seconds in outlining and 91.3 in
checking. It contained the required facts but added an unrequested quantitative-evidence
gap. To avoid spending most of the comparison waiting on remote calls, the scheduler was
changed to share local resources across up to three question jobs. The graph prompts and
reasoning settings were not changed. Start the complete paired run in the separate
`deepseek_comparison_paired` directory; retain serial results and any interrupted work
separately rather than mixing them into its scores. The earlier Pro defect remains a finding.

The first concurrent, non-streaming attempt is retained in `deepseek_comparison_paired`.
Pro question 002 encountered HTTP 524: the gateway reported a 120-second proxy read
timeout. Generation and its SDK retry failed after 251.7 seconds; the full question took
486.8 seconds without an answer. This is a transport failure, not evidence of a semantic
error. Unfinished jobs were interrupted to correct the shared transport. Both models then
passed a streaming compatibility probe. Start a fresh full paired comparison in
`deepseek_comparison_streaming`, preserving the same prompts, thinking and output budget.
Do not substitute selected streaming answers into the earlier run.

Two streaming-run startups failed in the Windows native tensor loader while initializing
the reranker after the retriever. Their logs and the original runner are retained. Loading
the reranker first allowed setup to finish in 35.8 seconds with the same weights and devices.
The following attempt was paused at the user's request while Pro 001, Flash 001 and Flash 002
were in flight, before any completed streaming answer was saved. Its process was stopped
and its log is retained as `deepseek_comparison_streaming/user_pause_log.txt`.

Resumed on 2026-09-23 at the user's request, with no active Python jobs and an idle GPU.
The streaming attempt starts from question 001 because the interrupted attempt saved no answers.

During the streaming round, both models showed different semantic/control defects, so a
stable model preference has not been established. Execute the predeclared six-question
repeat after this full round. Add VMG-010 as a separately identified, post-observation
diagnostic repeat: Flash's generated `LGR5-targeted` / `Nectin4-targeted` wording caused
the unchanged source-card identifier filter to discard correct sources. A saved offline
counterfactual confirms that removing just the descriptive `-targeted` suffix admits
both correct corpus candidates. Do not change the production filter or any prompt for
the repeat; retain the failed answer in the primary result. Report the original six
and the extra diagnostic question separately, not as fresh held-out validation.

Completed on 2026-09-23: full round Pro 13/15, Flash 12/15; seven-question repeat Pro 7/7,
Flash 5/7. For the predeclared six alone, first-round scores were Pro 4/6 and Flash 5/6,
then repeat scores Pro 6/6 and Flash 4/6. Diagnostic 010 passed for both on repeat.
All 44 answers, source-first assessments, traces and offline summaries are retained.
No full-round failure is replaced with a repeat answer. The 35 test questions remain unused.

Initial recommendation (superseded): use Pro as a pragmatic research baseline; the result
does not establish that Pro is necessary or sufficient. The user subsequently chose Flash
for continued work because of cost. Shared Agent defects remain the next priority. See the
[comparison report](../../reports/agent-model-comparison-report.md) for the distinctions between
content errors, presentation defects, source-filter failures and conservative adjudications.

Status: comparison complete; no evaluation process remains running.
No release or push is part of this comparison.
