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
   Snapshot reused from `../medical/article.xml`, without changing it.
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

| Conversation | Returned answers | Actual saved audits | Observed behavior |
|---|---|---|---|
| GRADE | 3 | 3 Direct + 1 Atomic v2 | Results → population/follow-up → original sentence. Direct completed; v2 retains extraction items for review. |
| Diet / exercise | 3 | 3 Direct + 1 Atomic v2 | The first answer treats the instruction not to rank the trials as an evidence gap, producing an unnecessary partial label. The last question's singular reference did **not** trigger clarification; the model returned both study durations. |
| Evidence limits | 3 | 3 Direct + 1 Atomic v2 | First answer refuses to establish five-year mortality; subsequent turns use measured exercise outcomes. The final answer quotes the duration but omits an explicit answer to the mortality clause and is marked partial. |

All nine Direct audits have status ok. Atomic v2 has two partial_error records and one ok.
These are execution/anchoring states, **not nine correct answers or measured clinical accuracy**.
A successfully audited quotation can still be an incomplete answer to the question. None of
these recordings was replaced by a nicer retry. The intent resolver supports clarification,
but this particular ambiguous scenario did not take that path.

Open the catalogue in Ask, or import an individual conversation JSON. Each export contains
its original answer/source fingerprints, actual traces, explicit context and attached audits.
Raw streams and unchanged API responses remain in run01; record-summary.json lists every turn.

Repackage the saved records without model calls:

~~~sh
node --experimental-strip-types frontend/scripts/package-conversation-demo.mjs
~~~

Recording fresh answers is different: scripts/record_conversation_demo.py sends the fixed
questions to the full local Ask service and performs paid Flash audits. Use a new --run-dir
for an intentional independent recording; do not replace run01. The current packager reads
run01 and is intended to reproduce this milestone's bundled exports.
