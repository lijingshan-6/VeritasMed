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

There are two recordings of the same nine questions, each made with one request per question
and no retries chosen by outcome:

- **run02** (2026-10-04, v0.9 code) is what the replay shows.
- **run01** (2026-09-27, v0.8.0 code) is kept as the original record. The regression tests, the
  node-execution figure and the walkthrough video come from it.

| Conversation | run01 (v0.8) | run02 (v0.9, bundled) |
|---|---|---|
| GRADE | Results → population/follow-up → original sentence; Direct ok, Atomic v2 had items for review | Same answers. Atomic v2 extraction hit the 32,768-token output limit and returned truncated JSON (kept as a failure) |
| Diet / exercise | Turn 1 treated "do not rank" as missing evidence (partial label). Turn 3 gave both study durations | Turn 1 answers the four requested aspects with no false gap (complete). Turn 3 still gives both durations; the question names both studies |
| Evidence limits | Turn 3 quoted the duration but never answered the mortality clause after three repair attempts | Turn 3 answers both parts on the first attempt. The label shows partial because "no mortality result" is a stated evidence gap |

All nine Direct audits in both runs have status ok. These are execution and anchoring states,
**not nine correct answers or measured clinical accuracy**. `record-summary.json` lists every
turn of both runs.

Open the catalogue in Ask, or import an individual conversation JSON. Each export contains its
original answer/source fingerprints, actual traces, explicit context and attached audits.

Repackage saved records without model calls (default `run02`; pass `run01` for the original):

~~~sh
node --experimental-strip-types frontend/scripts/package-conversation-demo.mjs
~~~

Recording fresh answers calls the model: start the full Ask service, then run
`python scripts/record_conversation_demo.py --run-dir data/demo/conversations/run03`.
Always use a new run directory; existing runs are never overwritten.
