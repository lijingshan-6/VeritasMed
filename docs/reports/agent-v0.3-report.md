# Agent v0.3: development results

The complete 15-question development run improved strict passes from **5/15 to 10/15**.
All required evidence was found for all 13 answerable questions. Mean latency rose from
85.1 to 91.3 seconds. Two unsupported or incorrectly scoped additions remain, so the target
of zero unsupported material claims was **not met**.

This is a local showcase milestone with documented weaknesses, not a claim of clinical
readiness. The 35-question test split remains unexecuted.

## What changed

- Component searches and grouped reranking recover evidence for both sides of multi-paper questions.
- Named single-study questions retain the leading source instead of borrowing results from nearby papers.
- The original question and required details survive query rewriting. Exact numerical statements,
  uncertainty and explicitly requested toxicity outcomes are carried into generation.
- Support, completeness and evidence-boundary checks can request bounded answer regeneration.
  Invalid JSON is retried once in place. Statistical `<` signs survive HTML cleanup.

See the [current workflow](../agent-workflow.md) for implementation and interface boundaries.

## Comparison with the unchanged v1.1 baseline

Both runs used the production Agent and local `qwen3.5:9b` with BGE-M3 on CPU and CUDA
reranking. They used the same 15 questions and frozen evidence contracts.

| Metric | v0.2 baseline | v0.3 final |
|---|---:|---:|
| Required-claim Recall@5, 13 answerable questions | 88.5% | **100.0%** |
| All required evidence found@5 | 11/13 | **13/13** |
| nDCG@5 / MRR@5, answerable questions | 0.8933 / 0.9231 | 0.9546 / 0.9487 |
| Mapped core-claim completeness / citation coverage | 90.0% / 90.0% | 100.0% / 100.0% |
| Gold-claim citation precision | 100.0% | 100.0% |
| Answerability score | 12/15 | **14/15** |
| Missing required qualifiers | 19 total; 1.27/question | **5 total; 0.33/question** |
| Unsupported or incorrectly scoped material additions | 0 | **2** |
| Strict pass | 5/15 (33.3%) | **10/15 (66.7%)** |
| Mean end-to-end latency | 85.1 s | 91.3 s |
| Agent self-check passes | 15/15 | 14/15 |

Core-claim completeness counts mapped main claims; missing numerical or population qualifiers
are scored separately. Citation precision covers the adjudicated gold-claim mappings, not all
sentences in the answer. In particular, 100% on that metric does not erase the two extra
unsupported or incorrectly scoped statements. Strict pass requires all dimensions to pass.

Six questions gained a strict pass: VMG-001, 002, 012, 018, 032 and 042. VMG-010 regressed
by omitting the Nectin4 positive/negative uptake comparison. Four prior passes remained passes.
The earlier candidate and small probes were used for development; none of their answers were
substituted into this final complete run.

## The five remaining failures

| Question | Why strict scoring fails | Next improvement |
|---|---|---|
| VMG-006 | Omits the 21/20 sample counts | Bind each required population qualifier to its source span |
| VMG-010 | Omits the Nectin4 positive-versus-negative model contrast | Check the requested comparator for each source independently |
| VMG-011 | Omits the radiologist sensitivity comparator and appends an unscoped pooled estimate from a third review | Bind each claim to the requested study before generating; exclude unrelated aggregate conclusions |
| VMG-013 | Omits the radiologist sensitivity comparator and the missing prospective-deployment boundary | Preserve the unanswered component alongside supported results |
| VMG-014 | Correctly refuses clinical benefit, but adds an unsupported assertion that those outcomes were simulated | Constrain refusal reasons to supported study-design facts and the named missing evidence |

For VMG-011, the pooled numbers exist in the retrieved review, but the answer does not identify
that review's separate population or scope. They cannot be read as the combined result of the
two requested studies. For VMG-014, the source simulates diagnostic triage; it does not simulate
biopsy use or downstream patient outcomes. These two contextual support decisions are explicit
in the saved adjudications so a reader can challenge them.

The Agent self-check missed all five strict failures. It also rejected VMG-024 for a trailing
title fragment even though the requested sensitivities were correct. VMG-024 passes the frozen
content rubric but remains an awkward answer. The self-check therefore remains a repair aid,
not a reliable independent judge.

## Assessment and provenance

The final run began on a clean tree at `82e02abbcd69d1ed3fa14271e27ee5992b900d53`.
It used the unchanged question SHA-256
`d31c54cfe6847b53c72f96630f5047f90617dda87ab953c563a0e9246177056e` and Ollama model digest
`6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`.

Final answers were read against their gold claims and cited local passages by Codex. All 15
decisions are bound to the exact answer hashes. No MedGemma proposal was run for this iteration;
no human clinician independently adjudicated these answers. The baseline keeps its original
MedGemma proposals and curator overrides. The deterministic metric definitions are unchanged.

This small development set was used to choose the improvements. The two model tiers use
temperatures 0.2 and 0.6, and only one final complete run is reported. The comparison does not
establish repeat-run stability, performance on unseen questions or superiority over plain RAG.
The corpus remains a narrow 2026 snapshot, mostly abstracts. See the [dataset report](benchmark-v1.1-report.md).

## Inspect and reproduce

- [All 15 answers, gold quotes and decisions](agent-v0.3-cases.md)
- [Raw Agent run](../../data/benchmark/veritasmed_v1_1/agent_v03_dev_raw.json)
- [Source-first assessments](../../data/benchmark/veritasmed_v1_1/answer_assessment_overrides_v03_dev.jsonl)
- [Deterministic scores](../../data/benchmark/veritasmed_v1_1/agent_v03_dev_scored.json)
- [Run manifest](../../data/benchmark/veritasmed_v1_1/agent_v03_dev_manifest.json)
- [Earlier candidate, retained for inspection](../../data/benchmark/veritasmed_v1_1/agent_v03_candidate_dev_raw.json)

With Python 3.12, reproduce the saved scores without Ollama, PyTorch, Qdrant or raw corpus:

```sh
python -m pip install "pydantic>=2.7,<3"
python scripts/benchmark/recompute_saved_agent.py
```

This command was executed successfully in a fresh Pydantic-only environment on Windows.
Optional `--output output/scores.json --cases output/cases.md` writes derived artifacts.
It validates answer/hash/citation correspondence and recomputes arithmetic; it does not
independently re-adjudicate the semantic decisions.

To generate new answers, first prepare the full corpus and index as described in the
[benchmark report](benchmark-v1.1-report.md), then run:

```sh
python scripts/benchmark/run_agent.py --split development --output output/agent_dev_raw.json --model qwen3.5:9b --embedder-device cpu --reranker-device cuda --timeout 240
```

Use `--reranker-device cpu` without CUDA. A new answer run needs new source-first assessments;
the saved decisions must not be reused when answer hashes differ. Original corpus files and
model weights are not distributed with the repository, so exact fresh inference additionally
depends on obtaining the matching local snapshot. Saved-output inspection is available immediately.

## Next bounded iteration

The next change should be a source-bound answer outline: for each requested component, keep
the intended study, exact evidence span, required qualifiers and any unanswered part together.
Generation and checking should consume that same outline. This addresses source attribution
and dropped boundaries more directly than adding more topic-specific prompt rules. Run it on
development and repeat the hardest items before deciding to spend the untouched test split.
