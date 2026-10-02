# Startup, model configuration and troubleshooting

**English** | [简体中文](../configuration.md)

Ask is the product entrance. Follow [README](../../README.md) for installation and the
[conversation guide](conversation-guide.md) for operation. This page consolidates the valid
configuration from the old `PORTS.md` and `demo.md`.

## Choose a launch mode

| Purpose | Command | Frontend / API | Requirements |
|---|---|---|---|
| Replay actual saved conversations without a key | `python scripts/run_showcase.py` | 5173 / 8000 | Lightweight Python environment and Node; no models or index |
| New questions, follow-ups and per-answer audits | `python scripts/run_demo.py --conversations` | 5173 / 8000 | Full Python dependencies, models, BGE and demo index |
| Standalone audit / Research workspace | `python scripts/run_audit_demo.py` | 5174 / 8001 | Replay needs no model; new audits use Flash |
| Authored UI example | `npm --prefix frontend run dev`, visit `/?demo=1` | 5173 / none | Authored fixture, not actual inference |

Services listen on loopback by default. The first two modes share ports; stop the old service
before switching. Launchers wait for the API, set Vite mode/API addresses, and stop their own
children on Ctrl+C. Do not open the same embedded Qdrant directory from two full APIs.
Use `--skip-index` only after successfully building the corresponding corpus index.

Live demos use isolated `.demo-runtime` data and indexes; research corpora need no changes.
`--conversations` contains 15 abstract passages from three papers; `--medical` contains GRADE;
the old mode without flags contains three authored summaries. None is the full PubMed corpus
or the historical evaluation's 44,768 chunks.

## Current Flash configuration

Copy `.env.example` to `.env` in the repository root. Keep real keys in this ignored local file.
The identifier below comes from saved experiments; another compatible provider may require another name.

```dotenv
LLM_BACKEND=openhub
OPENHUB_BASE_URL=https://www.cun.ai/v1
OPENHUB_API_KEY=your-gateway-key
OPENHUB_MODEL=DeepSeek-V4.1-Flash
OPENHUB_REASONING_EFFORT=high
OPENHUB_MAX_TOKENS=32768
LLM_TIMEOUT_SECONDS=240
```

`openhub` is the retained adapter name; configuration determines the endpoint. Generation and
checking use Flash, with no automatic Pro fallback. Restart the API after changes; explicit shell
variables override `.env`. Output tokens are a per-call limit, not intended usage or a whole-question
budget. Returned model names are gateway metadata, not evidence of identical weights across providers.
See the [Flash decision](../decisions/2026-09-23-flash-research-baseline.md) (original Chinese record).

## Optional local model

```dotenv
LLM_BACKEND=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.5:9b
LLM_TIMEOUT_SECONDS=240
```

First run `ollama pull qwen3.5:9b`. This optional backend does not change the saved Flash experiments.
The listening address `0.0.0.0:11434` becomes a local connection address; explicit remote/container
hosts retain their configuration. Cloud models receive questions and selected literature passages.
[MCP controls](mcp_security.md) apply to that entry, not public multi-user authentication for the web API.

## Ports and legacy entries

Ask's Vite `/api` and WebSocket proxy target 8000. The standalone workspace connects directly to
8001 and allows the local 5174 browser origin. Changing only the frontend port does not update API/CORS.

| Optional entry | Scope |
|---|---|
| 6333 | Server Qdrant; small demos use embedded `QDRANT_PATH` and need no server |
| 11434 | Required only for Ollama |
| `start_dev.ps1` / `start_setup.ps1` | Legacy conda/Docker full-corpus flow, not lightweight replay |
| `start_mcp.ps1` | Local stdio MCP; no Ask HTTP port |
| Docker Compose | Retained legacy stack; not exercised locally for v0.8, not a verified launch path |

## Common problems

- **401 / insufficient balance:** check local model configuration and restart. Saved replay still works.
- **Port occupied:** stop the previously launched service, then restart the launcher.
- **Slow first search:** initial BGE download/loading and indexing precede warm operation.
- **Paper absent from the demo:** use matching demo questions or ingest a corpus; do not test old
  benchmark questions against a three-paper index.
- **Timeout / invalid structured output:** execution failure, not absence of source evidence. The
  web API deadline is about 300 seconds, with a browser fallback of 310 seconds. Increasing a
  single-call timeout does not extend the entire flow.
- **Conversation missing after refresh:** IndexedDB belongs to the browser origin. Ports 5173/5174
  and different browsers do not share storage. Export/import the complete conversation to migrate.

Offline recomputation and paid runs are separated in [research reproduction](research-reproduction.md).
