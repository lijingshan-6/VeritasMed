# VeritasMed

**English** | [简体中文](README.zh-CN.md)

**A medical literature Q&A agent that shows its work.** Ask about a paper, get an answer in which
every statement cites an original sentence, then open an audit that checks each claim against the
source and marks what is unsupported or unchecked.

![Recorded walkthrough: conversation, answer, claim audit](docs/assets/showcase/preview.gif)

React · FastAPI · LangGraph · BGE-M3 hybrid retrieval · Python 3.12 · Apache-2.0

## What it does

- **Answers with citations to exact sentences.** Each part of the question is bound to a sentence
  from a retrieved paper; a missing result is reported as a gap rather than guessed.
- **Checks itself before replying.** The agent grades the evidence, rewrites the search when it is weak, and
  reviews its own draft, with at most two retries of each.
- **Lets you audit any answer.** One click checks every claim against the source passages, with
  unresolved quotes, unchecked text and model disagreements left visible.
- **Keeps the conversation.** Follow-up questions, answer versions and their audits are stored in the
  browser and can be exported and imported as one file.

## Try it without an API key

Replay three recorded medical conversations (nine real answers and twelve audits). No model,
GPU or database is needed. Install [uv](https://docs.astral.sh/uv/) and Node.js 22.12+, then:

```sh
git clone https://github.com/lijingshan-6/medrag-agent.git
cd medrag-agent
uv venv --python 3.12
uv pip install -r requirements-audit.txt
uv pip install --no-deps -e .
```

Activate the environment (`.venv\Scripts\Activate.ps1` on Windows, `source .venv/bin/activate`
elsewhere) and run `python scripts/run_showcase.py`. Open http://127.0.0.1:5173, pick a conversation, select a question and press **Audit**.

## Ask your own questions

The live mode searches the three bundled papers (15 original abstract passages, CC0 / CC BY).
It needs the full dependencies (several GB, CPU is fine) and an OpenAI-compatible Flash endpoint:

```sh
uv pip sync requirements.lock --torch-backend cpu
uv pip install --no-deps -e .
cp .env.example .env        # then set OPENHUB_API_KEY (and the endpoint/model if different)
python scripts/run_demo.py  # add --skip-index on later starts
```

Answers can also come from a local model (`LLM_BACKEND=ollama`, `OLLAMA_MODEL=qwen3.5:9b`);
audits always use the Flash endpoint.

## How it works

![System overview](docs/assets/showcase/system-overview.svg)

1. **Resolve** the follow-up against up to six selected earlier turns. Earlier answers help
   interpret "it" or "those results" but are never used as evidence.
2. **Retrieve** with dense and sparse BGE-M3 search, merged with reciprocal rank fusion, then rerank.
   Match the paper the question names before picking passages.
3. **Plan the answer** by binding each requested part to sentence IDs in the retrieved text. Code checks
   that every quotation exists and belongs to the right paper.
4. **Generate and check.** Key numbers are quoted verbatim. A model review checks support,
   completeness and evidence boundaries, and asks for targeted repairs.

Details: [how it works](docs/how-it-works.md) · [agent graph source](src/medrag/agent/graph.py).

## What the evaluations showed

| Question | Result | Decision |
|---|---|---|
| Does the agent answer correctly from the right evidence? | Development questions: 5/15 strict passes in v0.2, 15/15 in v0.4 (pipeline and model changed). Held-out set, run once after freezing: **31/35** | Current answer pipeline |
| How reliable is a model as a claim checker? | On 339 public SciFact pairs, Flash wrongly accepted **6/201** unsupported claims; MiniCheck 14/201 | Flash as the default checker |
| Does a prescribed tool workflow beat simply reading the papers? | 31/40 vs 35/40 for direct reading and for free tool use | Keep the simpler flow |
| Does fine-grained (atomic) auditing keep qualifiers? | Keeps more conditions (101/104 vs 91/104) but completes fewer audits (26/48 vs 47/48) | Direct by default, Atomic v2 optional |

The full numbers, intervals and what each version changed are in the [research summary](docs/research.md).

## Limitations

- This is a research demo, not clinical advice. Labels come from public datasets and AI-assisted
  review, not clinicians.
- The bundled index has three papers, so it cannot answer arbitrary medical questions.
- A green check means a model judged the quoted text to support the claim. It is not a calibrated
  probability, and the audit does not grade study quality or resolve conflicts between papers.
- The web API has no authentication and is intended for local use. History lives in browser
  storage; export anything you want to keep.

## Repository

| Path | Contents |
|---|---|
| `src/medrag/agent/` | LangGraph answer graph, evidence binding, follow-up resolution, model factory |
| `src/medrag/verification/` | Direct and Atomic v2 audits, exact-quote binding, numeric checks |
| `src/medrag/retrieval/`, `index/` | Hybrid retrieval, reranking, Qdrant indexing |
| `src/medrag/api/` | FastAPI app (`app.py`) and key-free replay (`replay_app.py`) |
| `src/medrag/mcp_server/` | Optional local MCP tools (search, ask, evaluate) |
| `frontend/` | React app: conversations, answers, sources, audit view |
| `data/demo/conversations/` | Three source papers, corpus, and the recorded conversations |

Checks: `python -m pytest -q`, `ruff check src/`, `npm --prefix frontend test`,
`npm --prefix frontend run build`. None of them calls a model.

The research history (datasets, all experiment outputs, version reports) is archived at
[commit 81a1519](https://github.com/lijingshan-6/medrag-agent/tree/81a1519). See the
[changelog](CHANGELOG.md) and the [source attribution](data/demo/conversations/README.md).
