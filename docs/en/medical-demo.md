# Original medical paper: Ask → Audit

**English** | [简体中文](../medical-demo.md)

The v0.8 three-paper, three-turn conversations are in the [conversation guide](conversation-guide.md).
This page retains the earlier single-paper demo of Seaquist et al. (2024), GRADE hypoglycemia:
retrieval, actual answer, claim audit, source location and export. It is a software demonstration,
not an evaluation score or medication recommendation.

The original v0.5 full Ask/audit remains unchanged. v0.7 adds Direct/Atomic checks of that answer
and explicit swapped-arm/evidence-removal inputs; see [three medical cases](research-demo.md).
[PLOS](https://doi.org/10.1371/journal.pone.0309907),
[PMC11567630](https://pmc.ncbi.nlm.nih.gov/articles/PMC11567630/),
[snapshots/license/extraction](../../data/demo/medical/README.md).

The paper is CC0. Publisher XML and all five abstract passages are retained; only the abstract
is indexed. Authored summaries do not substitute for original text, and no unseen full-text
reading is implied. Extraction removes XML tags and normalizes whitespace only.

## Replay actual records without a key

Install the lightweight [README](../../README.md) environment, then:

```sh
python scripts/run_audit_demo.py
```

Open **http://127.0.0.1:5174/audit**; **Medical · GRADE hypoglycemia trial** is default.
Sources are bundled; no RAGTruth download, key or GPU is required.

1. **SAVED INFERENCE** means an actual saved call, not new generation.
2. Select the first claim, read rationale/evidence and **Locate in full source** to Abstract Results.
3. Select the third; distinguish the per-protocol 4,830 from randomized 5,047 participants.
4. **Open source** opens the paper; **Source fingerprint** shows the text hash.
5. Inspect **Uncovered answer text** for text outside valid judgments.
6. **Export audit JSON** saves answer, full sources, ranges, judgments, execution and Ask mapping.

![Actual medical audit replay](../assets/v05-medical-audit.png)

## Run the full flow again

Install full dependencies and configure Flash using README, then:

```sh
python scripts/run_demo.py --medical
```

Open **http://127.0.0.1:5173** and select the GRADE question:

> In the GRADE trial report on hypoglycemia, what were the severe hypoglycemia rates for glargine,
> glimepiride, liraglutide and sitagliptin while participants were taking their assigned medications,
> and which population and analysis do these results describe?

After the answer, open **Audit**, keep **Direct Flash** and select **Run audit**. The original
question/answer/sources remain; **Back to answer** returns and the composer remains available.
Retrieval, generation and auditing actually run, require a usable key and may differ. Later use
`python scripts/run_demo.py --medical --skip-index`.

![Actual Ask answer and retrieved passages](../assets/v05-medical-ask.png)

## Actual run on 2026-09-26

| Item | Saved result |
|---|---|
| Agent | One full Ask, 90.19 seconds including first local-model load |
| Retrieval | All 5 original abstract passages, 1 paper |
| Answer | Medication-period severe-hypoglycemia data, population and analysis; 0 rewrites/regenerations |
| Independent audit | Direct, 1 Flash call, 24.093 seconds, 7,453 reported tokens |
| Output | 4 Supported, 0 Contradicted, 0 Insufficient, 0 failed/unchecked |
| Transfer | `input_edited=false`; original answer and all passages unchanged |
| Identity | Configured Flash; returned `deepseek-v4.1-flash` is gateway metadata |

[Ask events](../../data/demo/medical/ask-events.json), [browser export](../../data/demo/medical/audit.json).
One Ask and one audit, not repeated success selection. First-load duration is not steady-state
latency. Complete role usage is absent from the browser export; 7,453 is not total pipeline tokens.

The long extractive answer is easy to inspect. The auditor treats the result sentence's four
arms and two outcomes as one compound claim, not independently checked atomic facts. Four
green labels are not four independent medical validations. Uncovered framing/citation text
remains visible; coverage does not prove semantic completeness. Cross-paper conflicts, grades
and patient applicability were not measured.

Replay sets display mode to saved and adds a demo note. Downloads retain original live mode
and provenance, without changing outputs/judgments/positions. Nonmedical false alarms, misses
and unstable repeats in the [original v0.5 report](../reports/verification-v0.5-specific-errors.md)
are not cancelled by an easy demonstration.
