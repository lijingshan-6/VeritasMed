# Actual answer audit panel

**English** | [简体中文](../audit-demo.md)

Open **Audit** inside Ask. v0.8 retains conversations, versions and audit runs. The same component
shows atomic facts, conditions and independent-checker disagreements. Standalone `/audit` is an
experiment/replay entry accepting one answer and 1–40 source texts. It exposes model judgments,
answer/source ranges and uncovered text. It checks only supplied text support, without retrieval,
answer repair or clinical grading.

## Lightweight startup

Use `python scripts/run_showcase.py` (5173) for three-turn actual conversation replay. The optional
standalone workspace below uses 5174, Python 3.12, Node.js 22.12+ and uv; no Ollama, Qdrant or GPU.
Skip installation if the full project environment already exists.

```sh
uv venv --python 3.12
uv pip install -r requirements-audit.txt
uv pip install --no-deps -e .
```

Activate with `.\.venv\Scripts\Activate.ps1` on PowerShell or `source .venv/bin/activate` elsewhere:

```sh
python scripts/run_audit_demo.py
```

Open **http://127.0.0.1:5174/audit**. The launcher runs `npm ci` if needed, starts frontend and
lightweight API 8001 and stops both on Ctrl+C. Ports must be free. If activation fails, use
`.\.venv\Scripts\python.exe` in place of `python`.

The default [GRADE replay](medical-demo.md) includes original sources, actual Ask and audit;
no key, GPU, index or extra download. Claims, locations, paper links and JSON export work.
Optionally download pinned nonmedical RAGTruth with `python scripts/verification/answer_benchmark.py download`:
about 37 MB in ignored `.benchmark-runtime/ragtruth/`. Installation/download needs network;
replay then needs no model calls. Missing/changed caches and hash mismatch error rather than fabricate sources.

The lightweight service has Audit lab/Research and **Ask ↗** linking to full Ask; it does not start
retrieval. Full FastAPI registers the same `/api/audit` routes, preserving Ask, Explore and Guided
demo. Ask's **Audit** retains the original question/answer, all passages, citation→chunk mapping
and composer. **Run audit** invokes a model; **Back to answer** closes the view, and reopening keeps
results. New questions have separate records; earlier answers/audits remain. **Saved runs** selects
version-scoped records; complete exports restore them elsewhere. More than 40 passages or text
limits error explicitly, never silently truncate or replace answers. Guided transfers are
**Authored demo input**, not actual Agent outputs. Full original three-paper flow uses
`python scripts/run_demo.py --conversations` at 5173; no-flag mode uses authored fastMRI summaries.

The historical 2026-09-24 example asked “What kinds of data does the fastMRI knee dataset provide?”
Its actual answer and all 2 passages transferred unchanged to Context + meta: one 8.5-second
Flash call, 3 Supported, [raw JSON](../assets/v05-ask-audit.json), `input_edited=false`, full handoff/mapping.
The corpus was authored `medrag_demo`, not original medical validation or a research score.

![Actual historical Ask-to-Audit](../assets/v05-ask-audit.png)

## Replay steps

1. In **Real saved runs**, choose medical/RAGTruth input and method. [Atomic medical examples](research-demo.md)
   supplement earlier records. **SAVED INFERENCE** is actual saved output, not on-demand generation.
2. Select an underlined answer fragment or marked source quote; expand its claim. **Locate in full source**
   navigates to the complete supplied text.
3. Inspect **Uncovered answer text**. Unbound characters, invalid quotes and failures are not passes.
4. **Run provenance & execution** shows actual calls, time, response identifiers and usage.
5. **Export audit JSON** saves input, positions, judgments and execution.

The saved `RAGTruth #296 / direct` screenshot labels “already retired” incompatible with “about
to retire”. It demonstrates location, not verifier reliability.
![Saved output and source location](../assets/v05-answer-audit.png)

## Audit your own answer

Configure ignored `.env` with the README Flash profile:

```dotenv
LLM_BACKEND=openhub
OPENHUB_BASE_URL=https://www.cun.ai/v1
OPENHUB_API_KEY=your-gateway-key
OPENHUB_MODEL=DeepSeek-V4.1-Flash
OPENHUB_REASONING_EFFORT=high
OPENHUB_MAX_TOKENS=32768
LLM_TIMEOUT_SECONDS=240
```

Choose **Audit your own answer**, supply answer, source titles and original texts, then **Run new audit**.
Each source ≤50,000 characters, total ≤80,000; answer ≤12,000; original methods ≤24 claims, Atomic
≤48 facts. The panel flags caps. Only pasted text is checked; an abstract is not full-text evidence.

Direct uses one call. Split extracts then checks each claim, potentially taking minutes and more
tokens; splitting is not assumed better. Waiting/result states retain actual execution.
Context + meta is a one-call experiment showing answer paragraphs for attribution/negation/tense;
paragraphs are context, not source evidence. Framing/format/word-count text becomes **Presentation
text**, not Supported. Routing can be wrong, so text remains locatable and in reference-error
denominators. Whitespace-separated tokens are a mechanical count, not linguistic words or proof
of satisfying a requested count. Direct stays default.

**Atomic facts · experimental** decomposes qualified facts, then batch-checks them. Original
fragments, slots, normalized interpretation and evidence remain separately inspectable. Compound
or uncertain parsing is review-needed, not a completed pass. Extraction can omit content.

**Exact quotes v2** lets code calculate positions/answer paragraphs rather than requiring model
paragraph numbers or occurrence counts. **Original text locations** distinguishes unique, repeated,
absent quotes and unknown sources. Only exact unique text binds; repeated candidates stay ambiguous.
Presentation text also shows location failures. This remains optional.

On 2026-09-24 the browser replayed `RAGTruth #2336 / Exact quotes v2`, inspected its third
misattribution, located sources and [exported JSON](../assets/v05-quote-v2.json). It came from the
saved 8-source development experiment, without new replay inference or clinical validation.
![Actual quote-v2 output](../assets/v05-quote-v2.png)
![Actual Context answer/source view](../assets/v05-context-audit.png)

`RAGTruth #718 / Context + meta` shows answer paragraphs plus separate framing/count text;
this is interaction, not clinical evidence. **NEW INFERENCE** sends text to the locally configured
gateway. The service does not persist personal submissions; export explicitly. Failures remain
failures, not insufficient evidence.

The actual 2026-09-24 two-sentence functional example supplied a sample of 20 with no success
rate, while the answer added 95%. One 11.6-second call returned 1 Supported/1 Insufficient and
[JSON export](../assets/v05-live-audit.json). Input was authored, output real Flash, not a RAGTruth
score. The local HTTP service has no authentication and is not covered by MCP controls.

## Status meanings

| Display | Meaning |
|---|---|
| Supported | Model believes supplied text supports the claim; not expert confirmation |
| Contradicted | Model cites incompatible text |
| Insufficient evidence | Supplied text is insufficient, not global absence of evidence |
| Unresolved quote | Answer/source quote cannot bind exactly; not completed |
| Repeated quote · location unresolved | Multiple exact occurrences retained, not arbitrarily selected; not completed |
| Execution failed / Invalid model output | Call/structure failure, original execution retained |
| Not checked | Extracted but not completed |
| Needs review | Compound/uncertain parsing or other issues; model output retained, not completed |
| Checkers disagree | Saved support/non-support disagreement, not literature conflict |
| Presentation text · not source-checked | Classified framing, without source-support verification or correctness guarantee |

Character coverage measures validly located judgments over nonspace text, not semantic completeness
or accuracy. No uncalibrated confidence percentage or automatic literature-conflict inference.

Original historical reports: [whole answers](../reports/verification-v0.5-answer-audit.md),
[RAGTruth records](../../data/verification/ragtruth_v1/README.md),
[Context plan](../plans/v0.5-context-audit.md), [inputs](../../data/verification/context_v1/README.md),
[results](../reports/verification-v0.5-context-audit.md),
[specific errors/36 quote-v2 calls](../reports/verification-v0.5-specific-errors.md),
[quote-v2 artifacts](../../data/verification/quote_v2/README.md). Records retain their original language.

## Atomic v2 original qualifier text

Full Ask can run **Atomic v2 · qualifier anchors · experimental**. Each saved conversation's
first auditable answer retains actual v2 output; v1 remains available. V2 first binds a unique
parent, then fragments within it. Qualifiers retain their own parents/exact ranges, including
cross-sentence population, time, comparator, quantity and negation. Non-unique locations fail;
no fuzzy matching or guessed first occurrences.

**Model relation and completion are separate.** Missing numbers/anchors, compound parsing and
duplicates remain review-needed; original supported/contradicted/insufficient output does not
make an item completed. Rules inspect returned content only; absence of alarms proves neither
complete extraction nor correct meaning. See [v0.8 report](reports/verification-v0.8-report.md)
and [original case review](../reports/verification-v0.8-extraction-review.md).
