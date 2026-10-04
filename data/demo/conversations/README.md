# Actual medical conversation replays

The three conversations and all nine questions are fixed in `protocol.json`
before any Ask request. All nine returned answers are saved unchanged, together with their raw WebSocket events
and 12 actual audits. Any refusal or incomplete judgment remains visible. This is a software demonstration,
not expert-authored gold or a reliability sample.

## Original sources and reuse

All indexed text comes from the original abstracts, with every abstract section
included. Publisher XML snapshots and SHA-256 values are listed in
`source-manifest.json`. Paragraph whitespace is normalized; no medical text is
paraphrased in the corpus. Offsets refer to these normalized passages.

1. Seaquist ER et al.; GRADE Research Group (2024).
   [Glycemia reduction in type 2 diabetes—Hypoglycemia outcomes: A randomized clinical trial](https://doi.org/10.1371/journal.pone.0309907).
   PMID 39546502; PMC11567630. [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
   Publisher XML snapshot unchanged (`sources/PMC11567630.xml`).
2. Lee YM et al. (2016).
   [Effect of a Brown Rice Based Vegan Diet and Conventional Diabetic Diet on Glycemic Control of Patients with Type 2 Diabetes: A 12-Week Randomized Clinical Trial](https://doi.org/10.1371/journal.pone.0155918).
   PMID 27253526; PMC4890770. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
3. Figueira FR et al. (2013).
   [Aerobic and Combined Exercise Sessions Reduce Glucose Variability in Type 2 Diabetes: Crossover Randomized Trial](https://doi.org/10.1371/journal.pone.0057733).
   PMID 23536769; PMC3594238. Creative Commons Attribution; the bundled publisher
   XML explicitly permits redistribution with attribution but does not name a
   license version. See the [original license notice](https://pmc.ncbi.nlm.nih.gov/articles/PMC3594238/).

Full author lists and verbatim license statements are preserved in the manifest.
The complete XML is retained for provenance; the Ask corpus contains abstracts
only. These fixed older papers are examples, not a current clinical guideline.

Rebuild the corpus without any model call:

```bash
python scripts/prepare_conversation_demo.py
```


## Recorded behavior and limits

The same nine questions have been recorded several times, each with one request per question and
no retries chosen by outcome. `record-summary.json` lists every turn and audit of every run.

| Run | Code | Role |
|---|---|---|
| **run06** (bundled) | v0.9: plain-language answers; audits with the title-line hand-off | What the replay shows. Answers copied unchanged from run04; only the audits were re-run |
| run04 | v0.9: plain-language answers | Same answers; audits made before the hand-off fix (6 unresolved claims, 2 discarded audits) |
| run02 | v0.9 fixes, quote-style answers | Answer-coverage fixes confirmed with real calls |
| run01 | v0.8.0 | Original record; regression tests, node-execution figure and walkthrough video |

In run06 all nine Direct audits complete: 82 claims, 74 supported, 8 judged not supported by the
supplied sources, none unresolved. These are model judgments about the supplied text, **not
measured clinical accuracy**. Atomic v2 completed one of its three audits (one extraction hit the
output-token limit; one left 11 items for review).

Two recordings were not kept: run03 stopped when the gateway dropped the stream before the first
answer, and run05 used an incomplete source header that was corrected before packaging.

Open the catalogue in Ask, or import an individual conversation JSON. Each export contains its
original answer/source fingerprints, actual traces, explicit context and attached audits.

Repackage saved records without model calls (default `run06`; pass another run name to package it):

~~~sh
node --experimental-strip-types frontend/scripts/package-conversation-demo.mjs
~~~

Recording fresh answers calls the model: start the full Ask service, then run
`python scripts/record_conversation_demo.py --run-dir data/demo/conversations/run07`.
Always use a new run directory; existing runs are never overwritten.
