# Scripts: demonstrations, reproduction and historical development

**English** | [简体中文](../../scripts/README.md)

Run from the repository root. Ordinary use needs only the first group below, not every numbered
script in sequence. Environment setup: [project README](../../README.md).

## Current use

| Command / file | Purpose | Model calls? |
|---|---|---|
| `python scripts/run_showcase.py` | No-key real conversation replay on 5173 | No |
| `python scripts/run_demo.py --conversations` | Full Ask on three papers; separate retrieval index on first start | Flash after submitting a question; indexing downloads/loads BGE |
| `python scripts/run_audit_demo.py` | Standalone audit/research on 5174 | No for replay; yes for new audits |
| `local_services.py` | Shared launcher implementation | No |
| `prepare_conversation_demo.py`, `prepare_medical_demo.py` | Build demo corpora from bundled originals | No |
| `bootstrap_demo.py` | Isolated embedded Qdrant demo index | Local embedding model |
| `record_conversation_demo.py` | Record new actual Ask/audits; read protocol and use separate run-dir | **Yes, paid** |
| `export_openapi.py` | REST type source; then run frontend `generate-types` | No |
| `python scripts/render_system_docs.py` | Standard-library Chinese/English node, internal-logic and execution figures from source and old WS | No |
| `render_showcase.py` | Rebuild diagrams/four research figures; optional matplotlib | No |
| `record_showcase.mjs` | Playwright CLI rerecording of saved GRADE conversation; see tour | No |
| `render_showcase_media.py` | Convert recording to MP4/GIF and package unchanged screenshots; optional imageio-ffmpeg | No |

`frontend/scripts/package-conversation-demo.mjs` reads existing raw records. It requires every
scheduled audit file before writing exports; missing files cannot be silently skipped as success.

## Research recomputation and separate experiments

`verification/` preserves v0.5 (unprefixed), v06, v07 and v08 contracts. Commands are in
[reproduction](research-reproduction.md), data in [catalogue](data-catalogue.md).
Most `*_report.py` entries are offline. Do not assume `*_run.py`, `*_benchmark.py`, `run_queue.py`
or `run_v06_v07.py` make no calls; read `--help` and the corresponding protocol first.

R2 recomputes mechanical metrics from complete raw audits, checking scheduled jobs/fingerprints;
it makes no calls or prediction edits. Historical algorithms/prompts cannot silently use a new
implementation and remain the same experiment. `benchmark/` retains v1/v1.1 datasets, model
comparisons and v0.3/v0.4 scoring/recomputation. `report_release.py` concerns earlier saved
evaluation; **passing it does not establish that every current experiment passed or clinical reliability**.

## Earlier pipelines and helpers

| File | Retained purpose / limits |
|---|---|
| `01_ingest_pubmed.py`, `02_ingest_pmc.py`, `04_build_index.py` | Build a full corpus; not lightweight demo prerequisites |
| `06_compare_pipelines.py`, `08_eval_retrieval.py`, `09_eval_answer.py`, `11_eval_agent.py` | Earlier retrieval/Agent comparisons; different metrics/contracts |
| `07_generate_golden.py`, `12_build_hard_set.py`, `parse_golden_dataset.py` | Earlier AI dataset generation/conversion; golden naming is not expert annotation |
| `13_eval_report.py`, `14_update_eval_report.py` | Earlier report reproduction; deterministic saved-report entry is `report_release.py` |
| `10_smoke_test_agent.py`, `quick_demo.py` | Manual full stack/old P1–P5 CLI; may call models, not new reliability evidence |
| `qdrant_status.py` | Service Qdrant in old PowerShell setup, not embedded demo index |
| `_inspect_qdrant.py` | Service payload debugging, not health checking; needs a nonempty collection |

Two earlier evaluation/validation functions remain duplicated. Migrating them adds no current
product benefit and broadens historical environment changes. Active launchers share service
management and graph inputs; Ask nodes/evidence binding are split by responsibility. New
`benchmark/run_agent.py` snapshots collect these packages; old snapshots remain unchanged.
Reports use `docs/reports/`; paid raw-output paths remain. The [v0.9 plan](plans/v0.9-question-coverage.md)
is design only: no v09 runners or experiment data exist yet.
