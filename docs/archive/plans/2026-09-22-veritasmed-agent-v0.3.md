# VeritasMed Agent v0.3 implementation and evaluation

## Goal

Improve the production Agent's evidence coverage and answer boundaries on the frozen
v1.1 development set. Deliver working code, inspectable real answers, a source-first
assessment, and updated showcase documentation. Keep the 35-question test split unused.

## Work completed

- Plan component searches while retaining the original user question throughout the graph.
- Batch reranking of component retrievals and retain evidence for different requested sources.
- Constrain named single-study questions to the leading source, including multi-part questions
  about methods, results, or missing prospective evidence from that study.
- Carry exact source details into generation, including comparators, uncertainty and toxicity.
- Preserve statistical inequalities when removing actual HTML tags from source sentences.
- Require support, completeness and evidence-boundary checks; retry malformed structured
  output once in place and retain failures after the existing bounded regeneration loop.
- Record search plans, answer requirements, evidence status, runtime settings and code hashes.

## Finalization sequence

1. Preserve the first complete 15-question candidate run and record a code checkpoint.
2. Run all 15 development questions once from that checkpoint using qwen3.5:9b,
   CPU embeddings and CUDA reranking. Do not combine selected probe answers into the score.
3. Read each final answer against its frozen gold claims and cited passages. Save an explicit
   assessment per question; distinguish Codex source-first adjudication from clinician review.
4. Score final retrieved evidence and adjudicated answers with the existing deterministic
   scorer. Compare against the unchanged production baseline, including failures and latency.
5. Update README, the v0.3 report, architecture notes and demonstration instructions. Commit
   locally; remote publishing is outside this implementation step.

## Development targets

Strict pass at least 10/15; answerability at least 14/15; all-required evidence found in at
least 12/13 answerable questions; mean missing qualifiers at most 0.5; zero unsupported
material claims. These are targets, not promised results. Publish misses without changing
the frozen questions or accepting the Agent's self-check as the benchmark score.

## Progress

The first complete candidate run is retained as `agent_v03_candidate_dev_raw.json`.
Subsequent targeted probes exposed single-study source contamination, dropped toxicity
requirements and HTML stripping of P values; fixes are included in the final checkpoint.
The final full-run assessment and results are recorded in `docs/reports/agent-v0.3-report.md`.

Finalization completed: one clean-checkpoint run at `82e02ab`, 15 hash-bound source-first
assessments, deterministic scores, all-case evidence walkthrough, current workflow docs and
the Pydantic-only recalculation command. Strict pass 10/15; answerability 14/15; required
evidence 13/13; missing qualifiers 0.33/question. The zero-unsupported target was not met
(two additions), and that gap is explicit in the report. Mean latency was 91.3 seconds.
