# Follow-up experiments E1 and E2 (registered before any run)

Written after the main Experiment A analysis. The main run found, as an **exploratory**
result, that the answer's first sentence (its yes/no bottom line) is where plain RAG goes
beyond its evidence: uncited or rejected by the Flash citation judge in 40.1% of plain-RAG
answers vs 15.8% for VeritasMed (paired difference -21.3 pp [-26.6, -16.1]); body sentences
differ little. E1 and E2 test that finding on new outputs. Nothing below changes after the runs.

## E1 - Is the multi-step pipeline needed? (A5, strict-prompt RAG)

- **Arm A5**: the plain-RAG arm (same retriever, same top-5 passages with whole-abstract
  completion, one Flash call) with a stricter prompt: every sentence cites; the bottom line is
  no stronger than the cited results (association is not effect, non-significance is not "no
  difference", say when the passages do not settle it); no unstated design labels or
  limitations. The prompt (`STRICT_RULES` in `arms.py`) is frozen at this commit. It was written
  with knowledge of the main results, which favours A5; this is conservative for VeritasMed.
- **Data**: all 500 test questions, one attempt each. The 50 dev questions run first only to
  catch format failures; the prompt is not changed after the dev run.
- **Primary metric**: bottom-line unsupported rate (first sentence uncited, or rejected by
  the Flash citation judge; absence-statement first sentences excluded), paired bootstrap.
- **Decision rule**: A5 is "as good as VeritasMed" if the upper bound of the 95% interval for
  A5 - A2 is at most +5 pp. Then the product drops the multi-step generator for one strict call
  plus audit. Otherwise the pipeline is retained as measurably better at grounding conclusions.
- **Secondary**: overall unsupported rate (Flash; uncited count as unsupported), accuracy and
  macro-F1, cost and latency per question.

## E2 - Does the audit catch errors that occur naturally? (not planted)

- **Data**: plain-RAG (A1) answers for the 100 questions of the judge-agreement sample.
- **Procedure**: one Direct audit per answer, sources = the passages A1 used (one per PMID).
- **Units**: every non-absence sentence of those answers; reference label = Flash citation
  judgment (uncited sentences count as unsupported).
- **Flagged**: some valid audit claim overlapping the sentence is contradicted or insufficient.
- **Reported**: flag rate among reference-unsupported vs reference-supported sentences, for all
  sentences and for bottom lines; disagreements between audit and Flash on bottom lines are
  then adjudicated by reading the passages, with every label and reason saved.
