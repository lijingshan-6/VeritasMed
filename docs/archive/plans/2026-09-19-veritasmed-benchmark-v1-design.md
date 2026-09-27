# VeritasMed Evidence-Grounded Benchmark v1 Design

**Status:** Approved for implementation on 2026-09-19  
**Owner:** VeritasMed project  
**Milestone:** v0.2.0 effectiveness convergence  
**Supersedes for release claims:** `data/golden/golden_dataset.jsonl` and
`data/golden/golden_hard.jsonl`

## Purpose

VeritasMed needs a benchmark that measures whether its retrieval and Agent workflow can
answer realistic medical-literature questions from the indexed PubMed/PMC corpus. The existing
question sets were generated early in development. They are useful historical artifacts, but
they are not suitable as release evidence: the same model family helped construct and judge
them, their questions were selected from arbitrary chunks, their evidence annotations are
incomplete, and the hard set contains artificial cross-domain combinations that a real user
would not ask.

The new benchmark is a curated, evidence-grounded engineering benchmark. It is not a clinical
validation dataset. Until a qualified domain expert reviews it, the dataset card must say that
the questions and evidence were curated with AI assistance and source-level human-style review,
without clinician adjudication.

## Intended final state

The repository contains a frozen 50-question benchmark with an auditable path from every
required answer claim to exact evidence text in a versioned corpus snapshot. Fifteen questions
form a visible development split and thirty-five form a holdout test split. The Agent may be
tuned on the development split; the holdout split is run only at milestone checkpoints.

The benchmark supports three evaluations without collapsing them into one composite:

1. Retrieval: did the system retrieve all required evidence, useful supporting evidence, and
   avoid plausible but non-answering hard negatives?
2. Answering: did the system cover the required claims without adding unsupported material?
3. Citation: does each citation support the specific claim attached to it?

The release report presents these dimensions separately and includes a strict per-question pass
rate. A question passes only when all required claims are correct, no material claim is
unsupported, citations entail the attached claims, and answerability is handled correctly.

## Scope

### Included

- The current 1,975 PubMed abstracts, 348 PMC full-text records, and 44,768 cached chunks.
- Corpus manifest with file hashes, record counts, and stable snapshot identifier.
- Source inventory and automatic exclusion flags for incomplete or retracted material.
- Eighty candidate questions reduced through review to fifty frozen questions.
- Exact evidence quotes, required/supporting labels, hard negatives, source metadata, and review
  status for every frozen question.
- A 15-question development split and 35-question holdout split.
- Deterministic schema validation and retrieval/answer scoring.
- Local drafting with `qwen3:8b` and adversarial medical review with
  `medgemma1.5:4b`.
- Baseline runs of the current retrieval and Agent against the frozen benchmark.

### Excluded

- Clinical diagnosis or treatment validation.
- A claim that the benchmark was written or approved by clinicians.
- Fine-tuning on the holdout split.
- Medical image or visual-search evaluation.
- Questions that require sources outside the frozen corpus snapshot.
- Random cross-domain analogy questions created only to make retrieval difficult.

## Model roles

`qwen3:8b` is the primary local model. It may propose natural phrasings, split answers into
atomic claims, produce schema-constrained drafts, and run the Agent baseline. It is never the
sole authority for accepting a question or evidence relationship.

`medgemma1.5:4b` is an adversarial reviewer. It looks for medical ambiguity, missing qualifiers,
population/intervention/outcome mismatches, causal overstatement, and facts that are not directly
supported. Agreement between the two models is not sufficient for acceptance.

Final acceptance is source-first: the curator reads the evidence passages, resolves disagreements,
and records the decision in the review log. Model names, digests, prompts, dates, and decisions are
preserved as provenance.

On the RTX 4060 Laptop GPU, model calls and BGE indexing/retrieval run sequentially when necessary.
The benchmark tools default to an 8,192-token Ollama context to leave GPU memory for inference.

## Dataset composition

The 50 frozen questions target the following task mix:

| Task type | Count | Purpose |
|---|---:|---|
| `single_evidence` | 10 | Fact, method, cohort, or numerical extraction |
| `within_document_synthesis` | 15 | Combine multiple passages from one study |
| `cross_document_comparison` | 10 | Compare genuinely related studies on the same medical topic |
| `limitations_and_safety` | 10 | Limitations, negative findings, adverse events, and boundaries |
| `insufficient_evidence` | 5 | Partial or unsupported questions requiring calibrated abstention |

Answerability is balanced independently:

- 40 `complete`
- 5 `partial`
- 5 `unanswerable`

Domain balance follows the usable corpus rather than an arbitrary equal quota. No domain may
occupy more than seven frozen questions, and at least eight medical domains must be represented.
Cross-document questions must share a clinically meaningful disease, intervention, diagnostic
method, population, or outcome.

## Question contract

Every frozen question contains:

- Stable ID, version, split, task type, medical domain, answerability, and difficulty rationale.
- Natural-language question representing a plausible literature-search intent.
- Atomic gold claims marked `required` or `optional`.
- One or more exact evidence spans per claim, including chunk ID, verbatim quote, and support type.
- Source records with PMID/PMCID, title, year, publication type, study design, source role, and
  limitations relevant to interpretation.
- Supporting chunk IDs and hard-negative chunk IDs.
- Forbidden claims that a tempting but unsupported answer might introduce.
- A rubric defining what a complete, partial, or unacceptable answer looks like.
- Review state and provenance.

Evidence support levels are deliberately simple:

- `direct`: the quoted text explicitly states the claim.
- `derived`: the claim follows from a transparent calculation or comparison using quoted values.
- `context`: the passage is useful background but cannot satisfy a required claim by itself.

Study strength is recorded descriptively as source metadata. The benchmark must not invent a
single numeric source-quality score that compares unlike study designs.

## Question schema example

```json
{
  "id": "VMG-001",
  "version": "1.0.0",
  "split": "test",
  "task_type": "within_document_synthesis",
  "answerability": "complete",
  "category": "cardiology",
  "question": "...",
  "gold_claims": [
    {
      "claim_id": "C1",
      "text": "...",
      "importance": "required",
      "evidence": [
        {
          "chunk_id": "pmc:doc123:7",
          "quote": "Exact supporting text from the frozen chunk.",
          "support": "direct"
        }
      ]
    }
  ],
  "sources": [
    {
      "source_id": "PMC:doc123",
      "pmid": "12345678",
      "pmcid": "PMC1234567",
      "title": "...",
      "year": 2024,
      "publication_type": "Journal Article",
      "study_design": "retrospective cohort",
      "role": "primary_study",
      "limitations": ["..."]
    }
  ],
  "supporting_chunk_ids": [],
  "hard_negative_chunk_ids": [],
  "forbidden_claims": [],
  "rubric": {
    "complete_if": ["C1 is present and correctly qualified"],
    "partial_if": ["The outcome is present but the population qualifier is missing"],
    "fail_if": ["A causal effect is claimed from observational evidence"]
  },
  "review": {
    "evidence_checked": true,
    "ambiguity_checked": true,
    "answer_checked": true,
    "status": "frozen"
  }
}
```

## Construction workflow

### 1. Freeze the corpus

Hash the raw PubMed file, raw PMC file, and chunk cache. Record record/chunk counts and a snapshot
ID. All later evidence quotes must resolve against this snapshot.

### 2. Inventory source quality

Build document-level inventory rows. Flag retracted publication types, missing identifiers,
empty or very short text, parse failures, duplicate identifiers, and incomplete metadata. Flags
support review; they do not silently delete a source.

### 3. Write an intent blueprint

Draft realistic literature-search intents before looking at current retrieval ranks. Examples
include cohort eligibility, diagnostic validity, treatment outcomes, adverse effects, study
limitations, comparison of related studies, and whether the corpus supports a requested claim.

### 4. Build eighty candidates

Select sources and evidence first, then write questions and atomic claims. Qwen may propose wording
variants, but the evidence text and question purpose constrain generation. No current Agent output
may be copied into the gold answer.

### 5. Evidence review

Check each number, unit, population, time point, comparator, negation, and causal qualifier against
the exact quote. Reject any required claim that depends on general model knowledge.

### 6. Realism and ambiguity review

Reject artificial cross-domain combinations, trivia without retrieval value, questions with
multiple equally valid interpretations, and questions that leak rare phrases from the evidence.

### 7. Adversarial model review

Run Qwen and MedGemma independently with only the proposed evidence. Record disagreements and
failure modes. The curator resolves each issue from the source text.

### 8. Select and freeze fifty

Balance task type, answerability, domain, evidence count, and source design. Assign 15 development
and 35 holdout questions deterministically, then hash all benchmark artifacts.

## Review states

Candidates move through these explicit states:

`draft` → `evidence_checked` → `ambiguity_checked` → `adversarial_checked` → `adjudicated` → `frozen`

Every transition appends a review-log entry. Frozen questions are immutable within v1. Corrections
create a new dataset version and preserve the previous item.

## Scoring

### Retrieval

- Required Evidence Recall@K
- Supporting Evidence Recall@K
- All-required-found@K
- nDCG@K with graded relevance: required=2, supporting=1, other=0
- Hard-negative rate@K

### Answer and citation

- Required claim completeness
- Generated claim support precision
- Claim-level citation entailment
- Citation coverage for required claims
- Answerability accuracy
- Unsupported material-claim count

### Strict pass

A question passes only if all required claims are correctly covered, no material unsupported claim
is present, every required claim has an entailing citation, and the complete/partial/unanswerable
decision is correct. Dimension scores remain visible even when strict pass fails.

An LLM judge may suggest claim mappings, but deterministic checks validate citation IDs and evidence
availability, and all disputed semantic mappings remain reviewable.

## Repository layout

```text
data/benchmark/veritasmed_v1/
├── manifest.json
├── corpus_inventory.jsonl
├── candidates.jsonl
├── questions.jsonl
├── review_log.jsonl
├── dataset_card.md
└── legacy/

src/medrag/benchmark/
├── __init__.py
├── schema.py
├── inventory.py
├── validation.py
└── scoring.py

scripts/benchmark/
├── build_inventory.py
├── validate_dataset.py
├── build_candidates.py
├── review_candidates.py
├── score_retrieval.py
└── score_answers.py
```

Large raw corpus files remain ignored. The small manifest, inventory metadata, benchmark questions,
review log, dataset card, and scoring code are committed.

## Acceptance criteria

- Both pinned Ollama models are installed and their exact tags/digests are recorded.
- The corpus manifest resolves to the current raw/cache files and fails clearly on drift.
- Every frozen question validates against the schema.
- Every required claim contains at least one resolvable exact evidence quote.
- Partial and unanswerable questions define expected missing evidence and abstention behavior.
- No frozen question is selected because of current P1/P2/P3 rank.
- The old question sets remain available under a clear legacy label and are excluded from new
  headline metrics.
- Development and holdout results are reported separately.
- The release makes no clinician-validation claim.
