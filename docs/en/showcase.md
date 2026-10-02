# VeritasMed v0.8: from an answer to inspectable evidence

**English** | [简体中文](../showcase.md)

v0.8 is a milestone for the **product flow and retained research evidence**: conversation,
literature sources, answer versions, claim audit, controlled comparisons and original records
are connected. The research has not established reliable whole-answer medical auditing or an
advantage over the same model using tools autonomously. These limits explain the next research stage.

This is the five-minute illustrated entrance. For setup, read [README](../../README.md);
for implementation, [architecture](architecture.md) and [Ask workflow](agent-workflow.md);
for results, [research overview](research-overview.md) and [reproduction](research-reproduction.md).
For node internals and actual execution, read the [illustrated system and node guide](system-guide.md).

## Watch an actual operation

[Watch / download the operation recording (MP4)](../assets/showcase/walkthrough.mp4)

![Short excerpts from the actual operation](../assets/showcase/preview.gif)

Recorded locally on 2026-09-30 using replay. The screen contains actual Ask and Flash audit
outputs saved on 2026-09-27. Recording made no new inference or API calls and did not rewrite
answers. The silent recording follows these steps:

1. Select GRADE's first turn and inspect the answer, sources and three-turn history.
2. Open **Audit** from the answer; inspect Direct and click evidence to locate the original passage.
3. Switch to Atomic v2 for the same answer, inspecting medication-period and treatment anchors.
4. Locate answer fragments and inspect actual **Needs review / partial_error** results.
5. Export the audit, return to the conversation, select the second turn and export the conversation.

This records replay operations; elapsed times on screen belong to the original inference.
The GIF contains excerpts for GitHub. Use the MP4 and full-size screenshots for details.
The other two conversations retain refusals, missed clarification, an unnecessary gap and an
omitted mortality question. See the [original conversation catalogue](../../data/demo/conversations/README.md).

## How the system connects

![System overview](../assets/showcase/system-overview.svg)

Ask remains the entrance. The browser relates conversations, questions, answer versions and
audit records, exporting source snapshots and traces together. Full Ask performs retrieval
and Agent execution. Lightweight replay uses the same saved format without requiring a model key.

Independent Audit receives one version's **unchanged answer and provided source text**. It does
not silently edit answers or retrieve new evidence. Research is a separate bounded named-paper
verification experiment over eight candidate abstracts, not the full Ask evaluation. It can
transfer unchanged answers and candidate sources into Audit.

Implementation: [API](../../src/medrag/api/), [Agent](../../src/medrag/agent/),
[verification](../../src/medrag/verification/), [conversation records](../../frontend/src/conversation/).

## How the Agent goes beyond a long prompt

![Agent workflow](../assets/showcase/agent-workflow.svg)

History resolves references such as “those results”; previous answers are not source evidence.
Each turn retrieves anew, fuses dense/sparse candidates, reranks and retains study identity.
After evidence grading, insufficient retrieval can trigger rewriting. The generated answer
contains citations and gaps and receives an internal faithfulness check.

Both loops have limits: two retrieval rewrites and two answer regenerations. At the limits,
answers may still contain gaps or failed checks; there is no confidence threshold guaranteeing
correctness. See [workflow boundaries](agent-workflow.md) and [graph branches](../../src/medrag/agent/graph.py).

![Actual Ask answer and source interface](../assets/showcase/ask-answer.png)

The left shows the saved process, the center the conversation/answer and the right the original
text. Retrieval scores, evidence coverage and internal model checks have different meanings;
none is a clinical confidence percentage.

## What a claim audit checks

![Claim, condition, model interpretation and source](../assets/showcase/claim-evidence.svg)

The diagram uses GRADE turn one's saved Atomic v2 `fact-1`, not a newly constructed medical
answer. It connects `10 (0.8%)`, `glargine` and `While participants were taking their assigned medications`.
Numbers, treatments and conditions must retain the original `respectively` mapping. The record
preserves answer fragments, interpretation, qualifier anchors, quotes, locations and fingerprints.

![Actual condition anchors and linked source](../assets/showcase/audit-qualifiers.png)

| Panel information | Question answered | What it does not establish |
|---|---|---|
| Unique exact binding and offsets | Where does the quote occur in supplied text? | Correct interpretation |
| Supported / Contradicted / Insufficient | What relation does the model assign between source and claim? | Clinical evidence grade or calibrated confidence |
| Conditions/numbers, Needs review and coverage | What extraction/binding issues need inspection? | No warning does not prove no omissions |

Direct checks original claims by default. Atomic v2 is a separate two-stage experiment:
decompose, then verify, with condition anchors and mechanical diagnostics. Inspect the
[actual input/output](../../data/demo/conversations/run01/v08-grade-follow-up-turn-1-atomic_v2.json).

![Actual incomplete judgment](../assets/showcase/audit-review.png)

Some facts still need parsing review, so the whole run is `partial_error`. Finding a passage
does not mean the parsed interpretation received a completed check. Read run status, fact
status and relation separately. Professional evidence grading and reliable cross-paper conflict
adjudication are not implemented; checker disagreements are not literature conflicts.

## What the research supports

Charts read committed metric files. This presentation work reran no models and changed no
frozen predictions. Each chart identifies the task, denominators and limits. Reports retain
all failures, costs and protocols.

### Given a claim and source, how does verification perform?

![Fixed-claim verifier comparison](../assets/showcase/research-verifiers.svg)

On SciFact's public development fixed-evidence task, Flash accepted fewer non-supports than
MiniCheck, but missed supported claims remain material. This is not whole-answer medical
accuracy. Independent selection produced no eligible acceptance threshold, so the panel
does not display an unsupported reliability percentage.
[Metrics](../../data/verification/v06/fixed-final-metrics.json),
[paired intervals and calibration report](reports/verification-v0.6-report.md),
[preserved calibration figure](../assets/v07-calibration.svg).

### Why not let the model use tools directly?

![Workflow results and actual calls](../assets/showcase/research-workflows.svg)

Read-all and autonomous tools each achieved 35/40 correct accepted decisions; the prescribed
workflow achieved 31/40. All accepted 2/19 non-supports. Structure reduced some call/input
overhead but did not improve this comparison. The autonomous method uses application-level
JSON actions, not an upper bound on native tool calling.
[Metrics](../../data/verification/v07/final-metrics.json), [all cases/costs](reports/verification-v0.7-report.md).

### Do better-preserved conditions mean more reliable auditing?

![Condition preservation and completion](../assets/showcase/research-qualifiers.svg)

V2 placed more target anchors together and preserved more numbers. Its completion contract
is stricter: only 26/48 final constructed answers fully completed, versus Direct's 47/48.
The other two metrics include successfully extracted fragments from partial runs. Requiring
completed judgments gives Direct 91/104 and v2 80/104 joint targets. These diagnose mechanical
retention, not semantic correctness.

![Paired differences and uncertainty](../assets/showcase/research-intervals.svg)

All three paired source-group 95% intervals include zero. Group means differ from the pooled
fractions in the previous chart. On 12 separate natural development answers, Direct/v2 fully
completed 12/12 and 3/12; warnings overlapped 8/12 marked error spans for both. Span overlap is
not correct detection of specific errors. **Direct / Flash stays default**; v2 remains inspectable.
[R2 metrics/intervals](../../data/verification/v08/r2/summary.json), [report](reports/verification-v0.8-report.md).

## From an ideal flow to an actual failure

![Saved case: three generation/check cycles, ending with an omission](../assets/system-guide/execution-en.svg)

A workflow explains design; actual events show what happened. Evidence limits turn three generates
and checks three times, still reporting an omitted mortality subquestion before retaining the answer.
Failures remain visible. Old events contain no complete intermediate states, which these figures cannot
recover. The [system and node guide](system-guide.md) also provides complete nodes, internal-logic cards
and source links.

These figures are readable directly in repository Markdown, using current source and original events,
without new inference or research scores.

## Six deliverables and maintenance

| Deliverable | Entry / file |
|---|---|
| README presentation order | [README](../../README.md): product → demo → architecture → research → setup |
| System overview | [SVG](../assets/showcase/system-overview.svg) |
| Agent workflow | [SVG](../assets/showcase/agent-workflow.svg) |
| Claim audit explanation | This chapter, [SVG](../assets/showcase/claim-evidence.svg) and actual screenshots |
| Research figures | Four charts above, [input fingerprints](../assets/showcase/figure-sources.json) |
| Operation demonstration | [MP4](../assets/showcase/walkthrough.mp4), GIF, [recording function](../../scripts/record_showcase.mjs) |

Each diagram/chart has an editable text-preserving SVG and same-name PNG. The
[renderer](../../scripts/render_showcase.py) reads saved metrics and writes input SHA256s.
Install optional `matplotlib` in a separate visualization environment and run
`python scripts/render_showcase.py`. These are not prerequisites for the app.

To record again, launch `python scripts/run_showcase.py`, then create a dedicated CLI session:

```sh
npx --yes --package @playwright/cli playwright-cli -s=showcase-v08 open http://127.0.0.1:5173/
npx --yes --package @playwright/cli playwright-cli -s=showcase-v08 resize 1440 1000
npx --yes --package @playwright/cli playwright-cli -s=showcase-v08 snapshot
```

Use the actual snapshot button to load GRADE, then:

```sh
npx --yes --package @playwright/cli playwright-cli -s=showcase-v08 video-start output/playwright/v08-walkthrough-hd.webm --size=1440x1000 --fps=12 --cursor
npx --yes --package @playwright/cli playwright-cli -s=showcase-v08 run-code --filename scripts/record_showcase.mjs
npx --yes --package @playwright/cli playwright-cli -s=showcase-v08 video-stop
```

First use may require `npx --yes --package playwright playwright install ffmpeg`. With optional
`imageio-ffmpeg`, run `python scripts/render_showcase_media.py --seconds 46` after recording.
Adjust seconds to actual completion; remove trailing idle only, never failures. MP4 is transcoded
actual recording; GIF uses excerpts; screenshots are unedited. See [media receipt](../assets/showcase/media.json).
This post-release main presentation does not rewrite `v0.8.0` or start v0.9 experiments.
