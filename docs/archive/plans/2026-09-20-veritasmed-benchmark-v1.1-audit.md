# VeritasMed Benchmark v1.1 Audit and Agent Evaluation Plan

**Goal:** Turn benchmark v1.0 from an auditable candidate set into a source-disjoint engineering gold set, then evaluate the real Agent against it.

**Authority:** `docs/archive/plans/2026-09-19-veritasmed-benchmark-v1-design.md`, with the stricter v1.1 gates below.

## Global constraints

- Preserve `data/benchmark/veritasmed_v1/` unchanged.
- Do not tune the Agent against test questions.
- Model reviews are challenge evidence, never final labels.
- Keep all clinical claims bounded to the frozen local passages.
- Continue to label the benchmark as engineering-reviewed and not clinician-validated.

### Task 1: Add benchmark quality auditing

- Add tests for duplicate content, source/chunk split overlap, year and study-design profiles, and per-item audit completeness.
- Add deterministic audit helpers and a CLI that produces an inspectable quality report.
- Generate a blind challenge for every question with a model family not used to draft the set.
- Curate one final audit decision per item: `keep`, `revise`, or `replace`.

### Task 2: Freeze source-disjoint v1.1

- Build question groups connected by shared source or evidence chunk.
- Assign complete groups to development or test with exactly 15/35 questions.
- Apply any source-first revisions found in Task 1.
- Freeze `veritasmed_v1_1` with new hashes, dataset card, audit log, and zero cross-split source/chunk overlap.

### Task 3: Align scoring with the benchmark contract

- Implement graded retrieval relevance: required evidence = 2, supporting evidence = 1.
- Record unsupported material claims and missing required qualifiers explicitly.
- Add hand-calculated tests for graded nDCG and strict answer failure conditions.

### Task 4: Evaluate the real Agent path

- Add an evaluation adapter that captures the final answer and citations produced by the same Agent graph used by Ask.
- Keep the existing direct-model script labelled as a component baseline.
- Run the real Agent only on the v1.1 development split during iteration.

### Task 5: Establish the trusted development baseline

- Curate all semantic answer mappings for the 15 development answers.
- Publish retrieval, answer, citation, answerability, and strict-pass dimensions separately.
- Document remaining weaknesses and the one-time milestone policy for the 35-question test split.
- Run the repository test suite, lint the changed benchmark code, and commit each completed task.

## v1.1 acceptance gates

- 50 schema-valid questions and 100% resolvable exact evidence quotes.
- Zero source and evidence-chunk overlap between development and test.
- Fifty complete item-audit decisions with no unresolved disagreement.
- No known ambiguous question or unsupported required claim.
- Scoring implementation matches the written relevance and strict-pass contract.
- Development answers come from the real Agent path and have curator-approved mappings.
- Dataset limitations state the one-year corpus scope and lack of clinician adjudication.
