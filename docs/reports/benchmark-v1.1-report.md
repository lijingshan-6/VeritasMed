> Historical dataset/baseline report. Its then-unused 35-question split was evaluated in v0.4 and is now exposed; see [the Flash report](agent-v0.4-flash-report.md). Current research is summarized in [research-overview](../research-overview.md).

# VeritasMed benchmark v1.1 report

> The frozen dataset and original baseline below are preserved. For the improved Agent,
> see the [v0.3 development comparison](agent-v0.3-report.md): 10/15 strict passes and
> complete required-evidence retrieval on 13/13 answerable questions, with remaining failures disclosed.

VeritasMed v1.1 is a source-disjoint engineering benchmark for evidence-grounded medical-literature RAG. It is not clinician-reviewed and does not establish clinical safety. This report separates dataset quality, retrieval coverage, answer quality and the Agent's own self-check so that one number cannot hide a failure in another layer.

## Frozen dataset

| Property | Value |
|---|---:|
| Questions | 50 |
| Development / test | 15 / 35 |
| Unique sources | 44 |
| Domains | 20 |
| Complete / partial / unanswerable | 40 / 5 / 5 |
| Source overlap between splits | 0 |
| Evidence-chunk overlap between splits | 0 |
| Question SHA-256 | `d31c54cfe6847b53c72f96630f5047f90617dda87ab953c563a0e9246177056e` |

All required claims have exact evidence spans that resolve against the 44,768 normalized local chunks. Answerable items no longer use unrelated cross-domain passages as hard negatives. The five unanswerable items use same-topic passages that omit the requested comparator or outcome.

The snapshot is narrow: all sources are from 2026, most evidence is abstract-level and public test labels cannot provide a secret leaderboard. The benchmark is appropriate for repeatable engineering work on this corpus, not broad claims about medical QA.

## How the gold set was challenged

`qwen3.5:9b` generated a fresh 80-candidate pool, reviewed candidates with `medgemma1.5:4b`, and independently re-audited the final 50. `llama3.1:8b` served as an independent-family blind challenger. Models proposed defects; they never accepted an item or wrote the final label automatically.

The Llama challenger marked all 50 items for revision. Source-first adjudication accepted four useful findings and rejected the remaining false positives or self-contradictory findings. The accepted changes added a missing cohort-comparator span, replaced a vague risk statement with the exact 2-to-5-fold result, aligned one obstetric term with the source, and corrected one physiology term. Nine earlier source-first repairs brought the final total to 11 revised contracts and 39 retained contracts.

The final Qwen audit returned 46 passes and four top-level `revise` decisions whose subdimensions all passed and whose rationales endorsed the benchmark's abstention boundary. Those four disagreements are retained in the audit log and resolved explicitly rather than silently converted to passes.

Inspectable artifacts:

- [`quality_audit.jsonl`](../../data/benchmark/veritasmed_v1_1/quality_audit.jsonl): authoritative source-first decision for every item.
- [`model_adjudications.jsonl`](../../data/benchmark/veritasmed_v1_1/model_adjudications.jsonl): both model reviews, output hashes and the resolution for every challenge.
- [`model_manifest.json`](../../data/benchmark/veritasmed_v1_1/model_manifest.json): exact Ollama model digests and artifact hashes.
- [`revisions.jsonl`](../../data/benchmark/veritasmed_v1_1/revisions.jsonl): the 11 applied gold-contract changes.

## Production-Agent development baseline

Only the 15-question development split was executed. The 35-question test split remains unused.

Runtime configuration:

- production LangGraph Ask graph, with isolated thread IDs;
- `qwen3.5:9b`, explicit reasoning disabled, 4,096-token generation context and 6,144-token review context;
- BGE-M3 hybrid dense/sparse retrieval on CPU;
- `BAAI/bge-reranker-v2-m3` cross-encoding on CUDA;
- top-20 retrieval followed by top-5 reranking;
- Windows host, PyTorch 2.6.0 CUDA 12.4, RTX 4060 Laptop GPU;
- average end-to-end latency: 85.1 seconds per question.

### Retrieval

The retrieval table uses the Agent's final top-5 state after any query rewrite. Denominators exclude the two unanswerable items for required-claim metrics.

| Metric | 13 answerable development questions |
|---|---:|
| Required-claim Recall@5 | 0.8846 |
| Supporting-chunk Recall@5 | 0.8846 |
| All required claims found@5 | 0.8462 |
| nDCG@5 | 0.8933 |
| MRR@5 | 0.9231 |
| Hard-negative hit@5 | 0.0000 |

VMG-018 missed both required reconstruction-method sources and answered from different diffusion-reconstruction passages. VMG-011 retrieved the prostate-MRI source but missed the required breast-ultrasound source. These two misses explain the loss in claim completeness more directly than a single aggregate score does.

### Answers

`medgemma1.5:4b` proposed claim-to-citation mappings. It returned empty mappings for many obvious semantic matches, so all 15 assessments were checked against the answer, gold claim and retrieved passages. The raw judge hashes remain in the scored artifact; the visible curator overrides are the final assessments.

| Metric | 15 development questions |
|---|---:|
| Claim completeness | 0.9000 |
| Claim-support precision | 1.0000 |
| Citation coverage | 0.9000 |
| Answerability score | 0.8000 |
| Mean missing required qualifiers | 1.2667 per question |
| Unsupported material claims | 0 |
| Strict pass | **5/15 (0.3333)** |

Strict passes were VMG-009, VMG-010, VMG-024, VMG-034 and VMG-039. Seven answers omitted at least one required comparator, sample size, effect estimate, confidence interval or P value. VMG-013 gave the requested performance tradeoff but did not state the missing prospective-deployment evidence. VMG-014 and VMG-042 answered with adjacent single-arm or background results instead of refusing unsupported comparative outcome claims.

The Agent's internal faithfulness checker marked 15/15 final answers faithful. Source-first scoring passed only 5/15 strictly. This shows why the self-check is useful as a runtime repair loop but cannot serve as the benchmark judge.

Inspectable baseline artifacts:

- [`baseline_agent_dev_raw.json`](../../data/benchmark/veritasmed_v1_1/baseline_agent_dev_raw.json): answers, citations, retrieved chunks and graph counters.
- [`baseline_agent_dev_retrieval.json`](../../data/benchmark/veritasmed_v1_1/baseline_agent_dev_retrieval.json): per-question deterministic retrieval scores.
- [`answer_assessment_overrides_dev.jsonl`](../../data/benchmark/veritasmed_v1_1/answer_assessment_overrides_dev.jsonl): all 15 source-first answer decisions.
- [`baseline_agent_dev_scored.json`](../../data/benchmark/veritasmed_v1_1/baseline_agent_dev_scored.json): final per-question and aggregate metrics.
- [`baseline_agent_dev_manifest.json`](../../data/benchmark/veritasmed_v1_1/baseline_agent_dev_manifest.json): model, runtime and artifact hashes.

## Reproducing the checks

The frozen questions, review logs and saved baseline outputs are committed for inspection. The full raw PubMed/PMC corpus, model weights, index cache and local Qdrant store are intentionally excluded from Git. Re-running retrieval therefore requires rebuilding the local corpus with the repository ingestion scripts first.

With the project environment active and `PYTHONPATH=src` on shells that need it:

```sh
python scripts/benchmark/freeze_v1_1.py
python scripts/benchmark/audit_gold.py --questions data/benchmark/veritasmed_v1_1/questions.jsonl --output-dir data/benchmark/veritasmed_v1_1 --profile-only
python scripts/benchmark/build_runtime_index.py
python scripts/benchmark/run_agent.py --split development --model qwen3.5:9b --embedder-device cpu --reranker-device cuda --resume
python scripts/benchmark/score_answers.py --questions data/benchmark/veritasmed_v1_1/questions.jsonl --answers-input data/benchmark/veritasmed_v1_1/baseline_agent_dev_raw.json --output data/benchmark/veritasmed_v1_1/baseline_agent_dev_scored.json --overrides data/benchmark/veritasmed_v1_1/answer_assessment_overrides_dev.jsonl --split development --pipeline production-agent
```

The test split should be run only for a declared milestone after the Agent is improved on development. Its public labels make that policy a discipline rather than a security boundary.
