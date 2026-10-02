# Literature conversations and per-answer audits (v0.8)

**English** | [简体中文](../conversation-guide.md)

Ask is the entrance. Each question retains answer versions, full sources, context interpretation
and audit records. Audit reviews the selected answer; it does not replace conversation or
automatically rewrite an answer into something the verifier accepts.

## View actual conversations without a key

Install lightweight dependencies using [README](../../README.md), then run:

```sh
python scripts/run_showcase.py
```

Open `http://127.0.0.1:5173/` and choose a **SAVED INFERENCE** conversation. Three conversations
contain three turns each, with questions fixed before inference. Original papers, actual outputs
and incomplete judgments are retained. The second mistakes “do not rank” for a requirement needing
evidence and fails to clarify an ambiguous follow-up; the third omits an additional subquestion.

1. Select a question to inspect its full answer, retrieved sources and trace.
2. Open **Audit**; **Saved runs** selects Direct / Atomic v2 records for that answer.
3. Select a claim to see answer fragments, model interpretation and source sentences. V2 also
   shows original qualifier anchors.
4. **Back to answer** returns to the conversation. **Export conversation** saves the complete record.

Replay submits no new questions or audits. Model support judgments can be wrong; saved outputs
are not medical reference answers. See [demo sources and questions](../../data/demo/conversations/README.md)
(original source catalogue).

![Actual GRADE conversation and sources](../assets/v08-conversation.png)

## New questions and follow-ups

Stop replay, install full retrieval dependencies and configure Flash as described in README, then run:

```sh
python scripts/run_demo.py --conversations
```

Later use `--skip-index` to reuse the index. This mode retrieves 15 original abstract sections
from three papers, not enough for arbitrary questions. The older single-paper GRADE mode uses `--medical`.

1. Enter a question. The center retains each question and answer preview; select a turn for its
   complete answer, sources and trace.
2. Leave **Use selected history** on for follow-ups. Context follows the selected answer and
   its preceding context; choosing an older turn excludes later answers.
3. Turn history off for an independent question, or use **+ New** to start a conversation.
4. **Re-run** appends a version; **Answer version** switches versions without deleting old audits.
5. **Audit** makes no model call. **Run audit** starts a new check; **Saved runs** selects existing
   records. Editing the input produces an **Edited experiment**, not approval of the original answer.
6. **Export conversation** / **Import** preserves complete records across browsers or computers.

IndexedDB stores questions, full sources, versions, traces and raw audits. Refresh restores the
conversation and selected answer. An unfinished answer becomes interrupted after reopening.
Server checkpoints do not persist these browser records; backing up the server database is insufficient.

## How context is used

- At most **6 complete turns / 12,000 Unicode characters**, including questions, answers and source
  titles. Select from newest to oldest; stop at an oversized turn. Show omitted counts without
  truncating qualifiers.
- The resolver interprets references and current scope. Preserve the original question verbatim
  and append interpretation separately. Superseded populations, comparators or times should not
  return through history.
- The resolver is instructed to clarify ambiguous references and invalid formats. This is not
  guaranteed: the saved two-study case returned both durations rather than clarifying.
- Each turn retrieves using new graph state. Previous answers are not evidence and citations
  are not automatically carried forward.
- **Question interpretation** displays the original and retrieval input, history IDs, omissions,
  raw resolver output, elapsed time and provider usage. Resolver usage is not total Agent cost.

`?demo=1` remains an **Authored demo** fixture. It illustrates history/version operations but
does not measure actual follow-up performance or provide live context.

## Storage and import limits

- No automatic cross-computer sync. Origins, ports and profiles have separate storage; clearing
  site data deletes history. Export valuable conversations. Edit a conversation in one tab.
- Unavailable/full storage triggers a warning, not automatic deletion. The current tab can keep
  working and export.
- Old `vm_threads` contains only IDs; migration creates explicitly empty records, not invented history.
- Export includes format version, checksums and answer/source fingerprints. Import rejects
  inconsistent content/relations, without approximate text repair. Fingerprints detect changes;
  they are not author signatures or proof of medical truth.
- A single import is limited to 25 MB; oversized files are rejected without modification.
- Different versions sharing an ID do not overwrite silently. Another browser profile can retain
  them; automatic merging is not implemented.
- A lost audit response is saved as `transport_error`: server completion is unknown, with no pass conclusion.

## Qualifiers and completion

Atomic v2 first binds a unique parent sentence, then its fragments. Repeated sentences remain
ambiguous. A qualifier can come from another sentence but must match the unchanged answer and
retain its own parent. **Locate in answer** returns to that text; source quotes have separate navigation.

Model interpretations can omit numbers, populations, times or negation. Mechanical rules inspect
only declared anchors and numbers; they cannot guarantee all conditions were declared. Preserve
the model relation but flag issues for review rather than counting them as completed checks.
No mechanical alarm does not prove semantic fidelity; a group and number in the same claim can
still be incorrectly paired.

![Actual Atomic v2 qualifiers and locations](../assets/v08-qualifier-detail.png)

The record below omits a mortality subquestion. Execution completion, finding a source and
answer completeness are distinct. Replay retains the failed self-check and partial coverage.

![Actual partial answer retained in replay](../assets/v08-partial-answer.png)

Direct / Flash remains default. Atomic v1, historical failures and reports remain available:
[v0.8 report](reports/verification-v0.8-report.md), [localization](../reports/verification-v0.8-localization.md)
and [source inventory](../reports/verification-v0.8-exposure.md) (original detailed records).
The 12 context scenarios, constructed set and three medical replays are not independent clinical gold.
The earlier [two-turn GRADE record](../../data/verification/v08/grade-conversation-smoke.json) remains a historical development example.
