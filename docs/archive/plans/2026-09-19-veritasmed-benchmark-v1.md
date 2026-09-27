# VeritasMed Evidence-Grounded Benchmark v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a frozen, source-auditable 50-question medical-literature RAG benchmark and use it to establish the current VeritasMed baseline.

**Architecture:** Add a focused `medrag.benchmark` package for schema, corpus inventory, validation, and scoring. Keep question creation source-first: generate an 80-item candidate pool, record exact claim-level evidence, run two local-model review passes, then adjudicate and freeze 15 development plus 35 holdout questions. Historical datasets remain immutable legacy inputs.

**Tech Stack:** Python 3.12, Pydantic 2, JSONL, Ollama `qwen3:8b`, Ollama `medgemma1.5:4b`, existing PubMed/PMC corpus and Qdrant/BGE retrieval stack.

**Spec:** `docs/archive/plans/2026-09-19-veritasmed-benchmark-v1-design.md`

## Global Constraints

- Preserve `data/golden/*.jsonl` and all current evaluation JSONs byte-for-byte.
- Describe the new artifact as an evidence-grounded engineering benchmark without clinician review.
- Do not select or reject questions using current retrieval rank.
- Every required claim needs an exact quote resolvable in the frozen chunk snapshot.
- Use `qwen3:8b` for drafting and `medgemma1.5:4b` for adversarial review; neither model can auto-accept an item.
- Freeze exactly 15 development and 35 holdout questions only after review.
- Default automation must not require network access except explicit Ollama review commands.

## Review Focus

- Duplicate chunk or source identifiers must be reported rather than silently overwritten; Task 2 tests this.
- Evidence quotes that do not occur in the referenced chunk must fail validation; Task 2 tests this.
- `partial` and `unanswerable` questions must define missing evidence and expected behavior; Task 2 tests this.
- Corpus file drift must fail the snapshot check with the changed path named; Task 3 tests this.
- Model disagreement and curator resolution must remain visible in the append-only review log; Task 4 tests this.

---

### Task 1: Pin local model runtime and record provenance

**Files:**
- Create: `data/benchmark/veritasmed_v1/model_manifest.json`
- Create: `docs/archive/plans/benchmark-review-guide.md`
- Modify: `.env.example`

**Interfaces:**
- Consumes: Ollama `/api/tags` model metadata.
- Produces: pinned model tags and digests consumed by candidate/review scripts.

- [ ] **Step 1: Pull the primary model**

Run: `ollama pull qwen3:8b`

Expected: Ollama reports `success` and `/api/tags` lists `qwen3:8b`.

- [ ] **Step 2: Pull the adversarial review model**

Run: `ollama pull medgemma1.5:4b`

Expected: Ollama reports `success` and `/api/tags` lists `medgemma1.5:4b`.

- [ ] **Step 3: Record exact runtime metadata**

Write `model_manifest.json` with schema version, creation time, Ollama version, explicit model tags,
digests, quantization, file sizes, roles, and `num_ctx: 8192`.

- [ ] **Step 4: Document model-review rules**

Write `docs/archive/plans/benchmark-review-guide.md` with the six review dimensions: population, intervention or
exposure, comparator, outcome, time point, and causal/uncertainty qualifier. State that model
agreement never auto-accepts a question.

- [ ] **Step 5: Commit Task 1**

```bash
git add .env.example data/benchmark/veritasmed_v1/model_manifest.json docs/archive/plans/benchmark-review-guide.md
git commit -m "docs: pin benchmark review models"
```

### Task 2: Define the benchmark schema and strict validation

**Files:**
- Create: `src/medrag/benchmark/__init__.py`
- Create: `src/medrag/benchmark/schema.py`
- Create: `src/medrag/benchmark/validation.py`
- Create: `tests/test_benchmark_schema.py`
- Create: `scripts/benchmark/validate_dataset.py`

**Interfaces:**
- Consumes: JSONL question rows and a `chunk_id -> text` mapping.
- Produces: `BenchmarkQuestion`, `ReviewEvent`, and `validate_questions(...) -> list[str]`.

- [ ] **Step 1: Write failing schema tests**

Add tests proving that a valid complete question parses, an unsupported quote fails, duplicate IDs
fail, and partial/unanswerable questions without `missing_evidence` fail.

- [ ] **Step 2: Run the tests and confirm RED**

Run: `python -m pytest tests/test_benchmark_schema.py -q`

Expected: FAIL because `medrag.benchmark.schema` does not exist.

- [ ] **Step 3: Implement the minimal Pydantic models**

Implement enums and models for split, task type, answerability, support level, evidence span, claim,
source, rubric, review state, question, and review event. Reject empty quotes, duplicate claim IDs,
missing required evidence, and inconsistent answerability metadata.

- [ ] **Step 4: Implement source-aware validation**

Implement exact quote lookup after normalizing whitespace only. Return all validation failures with
question/claim/chunk identifiers rather than stopping at the first error.

- [ ] **Step 5: Add a JSONL validation CLI**

`validate_dataset.py --questions PATH --chunks PATH` prints counts and exits nonzero on schema,
duplicate, unresolved chunk, or quote failures.

- [ ] **Step 6: Run focused and full tests**

Run: `python -m pytest tests/test_benchmark_schema.py -q`

Expected: all benchmark schema tests pass.

Run: `python -m pytest -q`

Expected: the complete project suite passes.

- [ ] **Step 7: Commit Task 2**

```bash
git add src/medrag/benchmark scripts/benchmark/validate_dataset.py tests/test_benchmark_schema.py
git commit -m "feat: add auditable benchmark schema"
```

### Task 3: Freeze and inventory the current corpus

**Files:**
- Create: `src/medrag/benchmark/inventory.py`
- Create: `tests/test_benchmark_inventory.py`
- Create: `scripts/benchmark/build_inventory.py`
- Create: `data/benchmark/veritasmed_v1/manifest.json`
- Create: `data/benchmark/veritasmed_v1/corpus_inventory.jsonl`

**Interfaces:**
- Consumes: `data/raw/pubmed/abstracts.jsonl`, `data/raw/pmc/full_texts.jsonl`, and
  `data/index_cache/chunks.jsonl`.
- Produces: content hashes, counts, duplicate/exclusion flags, and `chunk_id -> text` inventory.

- [ ] **Step 1: Write failing inventory tests**

Test stable SHA-256 output, duplicate identifier reporting, retracted publication flags, missing
identifier flags, short-text flags, and manifest drift detection naming the changed path.

- [ ] **Step 2: Run the tests and confirm RED**

Run: `python -m pytest tests/test_benchmark_inventory.py -q`

Expected: FAIL because inventory functions do not exist.

- [ ] **Step 3: Implement streaming inventory builders**

Read JSONL one row at a time, calculate file hashes, count records, map PMC/PubMed metadata, report
duplicates, and emit deterministic document rows sorted by source and identifier.

- [ ] **Step 4: Implement manifest verification**

`verify_manifest(manifest, root)` recomputes size/hash/count and reports every drifted input.

- [ ] **Step 5: Generate the real manifest and inventory**

Run: `python scripts/benchmark/build_inventory.py`

Expected: 1,975 PubMed rows, 348 PMC rows, 44,768 chunks, plus explicit flag counts.

- [ ] **Step 6: Run focused and full tests**

Run: `python -m pytest tests/test_benchmark_inventory.py -q`

Expected: all inventory tests pass.

Run: `python -m pytest -q`

Expected: the complete project suite passes.

- [ ] **Step 7: Commit Task 3**

```bash
git add src/medrag/benchmark/inventory.py scripts/benchmark/build_inventory.py tests/test_benchmark_inventory.py data/benchmark/veritasmed_v1/manifest.json data/benchmark/veritasmed_v1/corpus_inventory.jsonl
git commit -m "feat: freeze benchmark corpus snapshot"
```

### Task 4: Build the candidate and review workflow

**Files:**
- Create: `src/medrag/benchmark/review.py`
- Create: `tests/test_benchmark_review.py`
- Create: `scripts/benchmark/build_candidates.py`
- Create: `scripts/benchmark/review_candidates.py`
- Create: `data/benchmark/veritasmed_v1/candidates.jsonl`
- Create: `data/benchmark/veritasmed_v1/review_log.jsonl`

**Interfaces:**
- Consumes: corpus inventory, pinned model manifest, candidate source/evidence selections.
- Produces: schema-valid candidates and append-only `ReviewEvent` rows.

- [ ] **Step 1: Write failing review-ledger tests**

Test allowed state transitions, rejection of skipped transitions, preservation of model
disagreement, and required curator resolution before `adjudicated`.

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m pytest tests/test_benchmark_review.py -q`

Expected: FAIL because review workflow functions do not exist.

- [ ] **Step 3: Implement review state transitions**

Implement append-only events and derive current state from the log. Events store actor, model tag,
prompt version, findings, decision, and source-based resolution.

- [ ] **Step 4: Implement schema-constrained Ollama calls**

Use the local Ollama HTTP API with JSON Schema, `temperature=0`, `num_ctx=8192`, explicit timeout,
and no automatic acceptance. Save raw model output hashes, not hidden reasoning.

- [ ] **Step 5: Create eighty source-first candidates**

Select evidence before question wording. Apply the task/answerability/domain targets from the spec.
Every candidate begins in `draft` and contains exact evidence quotes.

- [ ] **Step 6: Run evidence, ambiguity, and adversarial passes**

Use Qwen for independent answer reconstruction and MedGemma for adversarial medical review. Resolve
every flagged issue from the source passages and append review events.

- [ ] **Step 7: Commit Task 4**

```bash
git add src/medrag/benchmark/review.py scripts/benchmark tests/test_benchmark_review.py data/benchmark/veritasmed_v1/candidates.jsonl data/benchmark/veritasmed_v1/review_log.jsonl
git commit -m "feat: add benchmark candidate review workflow"
```

### Task 5: Adjudicate and freeze the fifty-question benchmark

**Files:**
- Create: `src/medrag/benchmark/selection.py`
- Create: `tests/test_benchmark_selection.py`
- Create: `data/benchmark/veritasmed_v1/questions.jsonl`
- Create: `data/benchmark/veritasmed_v1/dataset_card.md`

**Interfaces:**
- Consumes: adjudicated candidates and review log.
- Produces: exactly 15 development and 35 holdout questions with deterministic ordering and hashes.

- [ ] **Step 1: Write failing selection tests**

Test exact split counts, task/answerability quotas, maximum seven questions per domain, at least
eight domains, frozen-only eligibility, and deterministic output for a fixed seed.

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m pytest tests/test_benchmark_selection.py -q`

Expected: FAIL because selection functions do not exist.

- [ ] **Step 3: Implement deterministic constrained selection**

Prefer evidence quality and review completeness, then satisfy task, answerability, and domain
constraints. Never read retrieval ranks.

- [ ] **Step 4: Curate final questions**

Read every selected question and its evidence. Revise or replace any item that is artificial,
ambiguous, leaky, or insufficiently supported; rerun review transitions for changed items.

- [ ] **Step 5: Freeze and document v1**

Write sorted `questions.jsonl`, dataset hashes, creation provenance, limitations, split policy, and
legacy-dataset explanation in `dataset_card.md`.

- [ ] **Step 6: Validate the frozen artifact**

Run: `python scripts/benchmark/validate_dataset.py --questions data/benchmark/veritasmed_v1/questions.jsonl --normalized-corpus-root .`

Expected: 50 valid questions, 15 development, 35 holdout, zero evidence failures.

- [ ] **Step 7: Commit Task 5**

```bash
git add src/medrag/benchmark/selection.py tests/test_benchmark_selection.py data/benchmark/veritasmed_v1/questions.jsonl data/benchmark/veritasmed_v1/dataset_card.md data/benchmark/veritasmed_v1/review_log.jsonl
git commit -m "data: freeze VeritasMed benchmark v1"
```

### Task 6: Add scoring and establish the current baseline

**Files:**
- Create: `src/medrag/benchmark/scoring.py`
- Create: `tests/test_benchmark_scoring.py`
- Create: `scripts/benchmark/score_retrieval.py`
- Create: `scripts/benchmark/score_answers.py`
- Create: `docs/reports/benchmark-report.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: frozen questions, retrieved chunk IDs, generated claims/citations.
- Produces: dimension metrics, strict question pass/fail, development and holdout reports.

- [ ] **Step 1: Write hand-calculated scoring tests**

Cover required/supporting recall, all-required-found, nDCG, hard-negative rate, claim completeness,
claim support precision, citation coverage, answerability, and the strict pass gate.

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m pytest tests/test_benchmark_scoring.py -q`

Expected: FAIL because scoring functions do not exist.

- [ ] **Step 3: Implement deterministic retrieval scoring**

Calculate metrics per question and aggregate by split, task type, answerability, and domain.

- [ ] **Step 4: Implement reviewable answer scoring**

Deterministically validate citation IDs and coverage. Use schema-constrained model assistance only
to propose claim mappings; persist mappings and allow curator correction before final scores.

- [ ] **Step 5: Run the current baseline**

Run P1, P2, P3 and the current Agent on development first, then the frozen holdout. Record model,
corpus, code commit, hardware, failures, and per-question artifacts.

- [ ] **Step 6: Write the benchmark report and README summary**

Report dimensions separately, show three representative cases, and keep historical legacy metrics
in a clearly separated section.

- [ ] **Step 7: Run final checks and commit**

Run: `python -m pytest -q`

Expected: full suite passes.

Run: `ruff check src/ scripts/benchmark tests/`

Expected: no lint findings.

```bash
git add src/medrag/benchmark scripts/benchmark tests docs/reports/benchmark-report.md README.md data/benchmark/veritasmed_v1
git commit -m "feat: report VeritasMed benchmark v1 baseline"
```
