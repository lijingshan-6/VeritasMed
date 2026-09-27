# v0.4 Flash convergence worklog

Started 2026-09-23 under the [Flash baseline decision](../../decisions/2026-09-23-flash-research-baseline.md).
Status: v0.4.0 research showcase published; development 15/15, independent repetition
10/10 and first post-freeze held-out evaluation 31/35. Entries below preserve the chronology.

## Fixed scope

Use `deepseek-v4.1-flash` for every Agent role, retaining high reasoning and the existing output
budget. Preserve the frozen gold questions and scoring rules. Develop on the 15 development
questions; do not read or run the 35 held-out questions until the implementation is fixed.
No Pro calls are planned. Existing Qwen and Pro/Flash answers remain separate historical records.

## Work order and completion criteria

1. Normalize descriptive identifier suffixes without changing the underlying study identity.
2. Keep requirements tied to the original question, make partial gaps precise, and review
   the answer together with every displayed gap. Preserve valid evidence-boundary refusals.
3. Keep concise supported explanations in the answer and full quotations in expandable evidence.
4. Run the known development failures and boundary cases: 009, 010, 014, 018, 032, 034, 042.
   Inspect saved answers against source passages; any new implementation gets a new run directory.
5. After repairs, run all 15 development questions and independently repeat the same seven cases.
   Aim for complete supported answers, correct gaps and no unsupported material statements;
   retain and disclose every failure and repeat, including ambiguous judgments.
6. Record the frozen implementation before a single 35-question held-out evaluation. Results on
   that split are for reporting; do not tune this release against its answers.
7. Exercise actual Flash Live Ask, source navigation and the README setup path. Package the
   real cases, screenshots, release notes and updated guidance with honest remaining limitations.

## First implementation

- Strip descriptive suffixes such as `-targeted` from named source identifiers, retaining real variants.
- Preserve a narrow missing-outcome phrase for partial components; avoid blanket missing-evidence wording.
- Give study-specific planning/review the original question. Review both component answer and gap,
  allow correction of an incorrect missing/partial label, and remove unrequested outline components.
- Stop unconditional replacement of numerical/method answers by whole source paragraphs. Continue
  checking bound numbers and source roles, retaining explicit source quotation for omitted numbers.

Execution results will be appended here; no completed experiment is overwritten.

## Probe 1: 4/7 strict passes; not selected for delivery

All seven questions completed. All five answerable questions retrieved their required evidence,
but 010, 018 and 032 still failed. The complete [answers and source reviews](../../reports/agent-v0.4-flash-probe1-cases.md)
are retained with the exact runtime snapshot in `v04_flash_probe1`.

The source-filter fix admitted both target papers. A deeper defect remained: independently
planning each study while seeing the whole user request created a missing component for the
other study. Separate reviews then accepted that gap without seeing the other study's answer.
018 repeated retrieval twice unnecessarily and took 382.2 seconds, exceeding the web deadline.
032 still added an unreported simultaneous-measurement assertion. 009 was factually supported
but verbose, with unrequested training details and repeated performance findings.

## Second implementation

- Use one shared evidence outline over all selected studies and one review of the complete
  final answer. Keep citation bindings and requested study identities; remove the isolated
  per-study planning/review calls that concealed contradictions.
- Rewrite the outline instructions around the original question, recording its exact requested
  phrase for each component. Qualitative findings do not require invented quantitative metrics.
- Preserve fixed outcome/comparator wording for evidence-boundary questions. Explain design
  limits without inventing a measurement schedule or turning higher uptake into specificity.
- Avoid restoring the same bound number twice when it already appears with the same study's citation.

Probe 2 uses the same seven questions. The implementation is not yet frozen for the test split.

## Probe 2: 5/7 strict passes; shared planning removes the cross-study contradiction

[All seven answers](../../reports/agent-v0.4-flash-probe2-cases.md) are preserved. Required evidence was found
for 5/5 answerable questions. 018 no longer contradicted itself or rewrote retrieval, completing
in 73.7 seconds instead of 382.2 in the preceding probe, but omitted the fMRI validation's
simulated/experimental condition. 032 still asserted an unreported simultaneous measurement.
There were no execution errors or questions over 300 seconds. 010 retained an unasked
absolute-uptake gap, and 034's otherwise correct answer was falsely rejected by a parser defect.

## Third implementation

- Router suggestions no longer become authoritative answer requirements in the evidence planner.
- Normalize scalar detail strings as one item, rather than iterating their individual characters.
  This caused the spurious missing-digit repairs in 034.
- When proposed detail excerpts are paraphrases, retain their selected exact source sentences
  instead of silently discarding the requested conditions. Additional evidence already bound
  to a component no longer automatically promotes every sentence to a mandatory quotation.
- Reject an unreported simultaneous-measurement assertion and request a source-bounded repair,
  using a narrow protocol guard alongside the existing cohort-role guard. It does not establish
  general semantic correctness and contains no benchmark question IDs or model-specific rules.
- Render fixed yes/no evidence gaps as statements while retaining outcomes and comparators.

Probe 3 uses the same seven questions; the held-out split remains unused.

## Probe 3: 4/7 strict passes; preserve the regression

[All seven answers](../../reports/agent-v0.4-flash-probe3-cases.md) completed without execution errors or
unsupported material additions. 010 lost the LGR5 source because a different descriptive suffix
still hit the lexical filter. 018 still omitted the fMRI validation's simulated/experimental
qualifier. 032 no longer invented timing but refused to explain the design-derived causal
limitation. All seven self-checks passed despite those three failed answers.

## Fourth implementation and complete development run

- Use identifier matches to prioritize four candidate studies, with match/mismatch hints for
  semantic study selection. Do not discard candidates solely because generated search wording
  contains a descriptive suffix. Reference lists remain excluded from identity matching.
- Explicitly allow cited logical limits entailed by a reported study design throughout planning,
  generation and review; do not require an author-written explanation verbatim. Unreported
  protocol details remain unsupported.
- Require validation findings to retain their reported data types and setting in both generation
  and review. Fix a shadowed parser variable in method-detail binding.
- Run all 15 development questions in `v04_flash_development`, then independently repeat the
  predeclared seven. This full run includes all seven earlier diagnostic cases. No Pro calls,
  changed gold claims or changes to scoring thresholds are involved.

## First complete development run: 12/15

[All 15 answers](../../reports/agent-v0.4-flash-development-first-cases.md) are retained. All 13 answerable
questions found their required source chunks, all requests completed, and mean latency was
73.7 seconds. Three answers still failed despite 15/15 internal self-checks:

- 009 invented identity between the development dataset and the validation dataset.
- 010 retained the negative cell control but omitted the negative tumor-control comparison.
- 032 replaced a rejected timing-based explanation with a design quotation, losing the explanation.

The last failure exposed a code defect: re-binding restored quotations overwrote the original
binding issues. Keep those rejection instructions through checking and regeneration. Also extend
the cohort-role guard to unsupported same-dataset aliases, and the quotation fallback to selected
non-numeric contrasts whose second arm is substantially omitted. Both are narrow safeguards,
not a general entailment proof. Clarify that answering what remains untested does not make the
missing outcome's evidence complete. The next full run is `v04_flash_development_final`.

## Second complete development run: 13/15; not frozen

The just-mentioned directory was renamed to `v04_flash_development_round2` after completion;
its answers and runtime snapshot are unchanged. [All 15 cases](../../reports/agent-v0.4-flash-development-round2-cases.md)
are retained. Evidence coverage remained 13/13, with no execution errors, but 011 invented a
separate validation set and 032 still lacked its causal explanation after rejecting unsupported
timing wording. The latter now correctly remains flagged as unresolved instead of silently passing.
One unsupported addition means the development goal is still unmet despite reaching 13/15.

The cohort guard now covers both claimed identity and claimed separation; neither relationship
can be inferred from a bare statement of multicenter validation. Timing-repair feedback names
the exact rejected draft and every triggering phrase, so replacing "simultaneously" with
"at a single time point" cannot be mistaken for completing the repair.

The next full run uses the current `v04_flash_development_final` directory. Its subsequent
independent repeat will include the seven originally declared cases **plus 011 as an additional
diagnostic**, selected now because this round exposed its dataset-partition error. Report the
seven-case subset and the extra case separately as well as all eight; do not pick a best answer.

## Third complete development run: 13/15; change factual presentation

The completed directory was renamed to `v04_flash_development_round3`; [all answers](../../reports/agent-v0.4-flash-development-round3-cases.md)
and the exact runtime are preserved. 032 now gives its requested causal explanation without
unreported measurement timing. However, 002 added an unreported scaffold-absorption mechanism,
and 006 omitted the required GDF-15 finding. This run again misses the zero-addition criterion.

The next implementation renders critical numerical, population and method components from
their selected exact source sentences before binding the final claims. Separately requested
design explanations remain generative and still receive review and repair. This uses the existing
source-context renderer, with the unrequested generic causal-aside path removed. Repairs preserve
unaffected components. Saved traces distinguish source projection from later quotation recovery.

This is an explicit presentation tradeoff: accept evidence-excerpt wording and some extra length
to avoid paraphrases inventing mechanisms or cohort partitions. It does not prove that selection
is complete or that an original paper's conclusion is justified. Gold and scoring remain unchanged.

The next complete run is the current `v04_flash_development_final`. Before any repeat is run,
add 002 and 006 to the previously declared extra diagnostic 011: the independent repeat will
therefore contain the original seven plus these three newly exposed cases (10 total), all reported.

## Fourth complete attempt: billing interruption and gateway change

The fourth full attempt is preserved as `v04_flash_development_billing_blocked`, including
all answers, five execution errors and the exact runtime. Its ten completed answers passed
source-first review without unsupported additions or missing qualifiers. OpenHub then returned
HTTP 403 `insufficient balance` for 024, 032, 034, 039 and 042. The recorded result is 10/15 with
five errors, not a ten-question success rate substituted for the planned run.

The user supplied a new compatible endpoint, `https://www.cun.ai/v1`. Its model inventory lists
`DeepSeek-V4.1-Flash`; a real structured streaming call returned a usable JSON answer. Preserve
the exact case-sensitive request ID and endpoint in the run metadata. The internal backend
configuration name remains `openhub`. No Pro call or gold/scoring change is involved.

The model-comparison runner now honors `OPENHUB_MODEL` for Flash instead of hard-coding the
old gateway's spelling. This transport configuration adjustment is included in the new runtime
snapshot. The fresh full run is `v04_flash_development_final`; no failed row is replaced in an
earlier run. The new provider's underlying weights cannot be independently authenticated or
assumed identical to OpenHub's. Its compatibility response supplied no token usage, so missing
usage must remain unavailable rather than zero.

The declared ten-question repeat and the still-unused 35-question test retain their order and
unchanged acceptance criteria. Only after full development and repeats meet those criteria may
the implementation be frozen and the held-out test run once.

## First new-gateway run: 14/15; one timing assertion retained as a failure

All 15 requests completed on the new endpoint; evidence coverage was 13/13 and all displayed
coverage labels were appropriate. The mean was 51.8 seconds, with token usage unavailable.
032 still described the variables as "concurrently measured", which the source does not
establish. This is counted consistently with the earlier unsupported timing statements, despite
all 15 internal self-checks passing. The directory is preserved as `v04_flash_cun_development_round1`.

The next implementation keeps a narrow, explicit repair for this design-explanation failure.
When a requested causal-limit component is bound to one study that explicitly reports a
cross-sectional design, and the draft invents measurement timing, render the actual design
quotation plus an association-versus-intervention limitation. Do not invent a schedule or an
assigned intervention. Other designs and safe explanations retain model review. This is a
documented design-based inference, not a quotation pretending to be an explanation, and is
logged separately as `design_scope`. It uses no benchmark identifiers, answers or source IDs.

The new full development run again uses a fresh `v04_flash_development_final` directory.
Original and expanded repeat sets remain unchanged; held-out questions are still unused.

## Final full development run: 15/15; independent repeat started

The new full 15-question run passes all frozen strict criteria in source-first review:
zero unsupported additions, zero missing required qualifiers, 13/13 answerable questions with
all required evidence, zero execution errors and no displayed coverage-label mismatches.
Mean latency is 51.9 seconds and the maximum is 101.2 seconds, excluding retrieval-model startup.
The provider reported no token usage for its 77 model calls; usage is unavailable.

All 13 answerable responses used critical-fact source projection. The new design-scope repair
was not triggered in this run: 032 generated an acceptable explanation directly. The score
change therefore cannot be attributed to that rule as an observed causal effect. Development
questions have been reused extensively; this is not independent generalization evidence.

The declared ten-case independent repetition has started under identical runtime and model
settings in `v04_flash_repeat`. Preserve the original seven and extra three as separate subsets
as well as the whole run. The 35-question held-out split has still not started.

## Independent repetition: 10/10; implementation frozen before held-out use

The original seven cases pass 7/7, and the three additional diagnostics pass 3/3. All ten
answers preserve their required claims and boundaries, with zero unsupported additions,
missing qualifiers or execution errors, and required evidence for all 8/8 answerable cases.
Mean latency is 57.0 seconds; maximum 73.7 seconds. Usage is unavailable for all 53 calls.
No design-scope repair was triggered; eight answers used critical-fact source projection.

006 correctly explains the missing longitudinal trajectory in its answer but displays complete
coverage. This is recorded as one presentation mismatch, independently of the unchanged strict
answer-content rubric. Repetition does not establish perfectly reliable coverage labels.

At **2026-09-23 09:50:05 UTC**, the implementation was frozen in
`data/benchmark/veritasmed_v1_1/v04_flash_release/freeze_manifest.json` with 65 production,
runner, reporting and dependency files. The two runs match on runtime hashes, question hash,
model ID and configuration. The snapshot includes all production Python files, extending the
smaller per-run snapshots. At that point no held-out output directory existed.

The next step is one full 35-question held-out run using this implementation. Preserve every
answer and review against the frozen evidence; do not tune code or prompts from these results.

## Live walkthrough and presentation packaging

The current Flash browser answer to the fastMRI+ question completed in 49.30 seconds with
zero rewrites/regenerations, retaining the annotation findings and withholding diagnostic accuracy.
Source quotations expand and highlight the matching passage; Markdown download works. A real
Explore search opens the local source document. Screenshots and the downloaded answer are linked
from the demo guide. The answer's coverage label remains complete despite its explicit outcome
limit; this known limitation is preserved in both screenshot and documentation.

Opening the local document exposed obsolete utility-class styling and a missing scroll area.
Only `frontend/src/pages/DocumentPage.tsx` and presentation CSS were adjusted to match the existing
theme and support long/mobile reading. The frontend build and actual desktop/mobile rendering
completed. This occurred after the Agent freeze; no frozen Python, prompt, scorer or gold file
was changed, and no held-out answer informed an inference change.

## First held-out evaluation and local milestone completion

The single frozen 35-question test completed with **31/35 strict passes**. All 32 answerable
questions retrieved their required evidence. Source-first review observed zero unsupported
material additions, one missing required qualifier and zero execution errors. Mean latency
was 72.5 seconds, maximum 254.8 seconds; four regenerations and two retrieval rewrites occurred.
Only 2/194 model calls reported usage (668 input and 2,938 output tokens); this partial subtotal
is not the run's consumption or cost. No Pro calls were made during Flash convergence.

The retained failures are 023 (clinical-adoption/outcome boundary), 037 (independent MVI and
AFP-L3 prognostic estimates), 041 (composite-endpoint definition and causal-design limit),
and 049 (the requested rehabilitation-comparator/patient-outcome gap). All four still passed
the internal check, as did every other test answer. These are answer-completeness failures,
not evidence-retrieval failures. The gold and score were not relaxed to make them pass.

Six coverage labels disagree with gold. For 021, 047 and 048, the actual question is broader
than its narrow required claims, so the additional model gaps are defensible. These ambiguities
are recorded separately, without changing frozen labels. Case 030 is explicitly recorded as
a borderline accepted judgment: its exact P value and confidence interval express the null
finding without a separate plain-language statement. Review is AI source-first engineering
review, not independent clinician adjudication.

All raw outputs, reviews, scores and failures are retained. The implementation remains the
one frozen before the test. These 35 questions are now exposed and can support regression
work, but future unseen-performance claims need fresh independent evidence. The README,
workflow, demo guide, actual screenshots/export and version notes now describe the same
local milestone. No remote push, stable tag or GitHub Release has been performed.

## GitHub source publication — 2026-09-23

After the local milestone, the user requested documentation consolidation and GitHub publication.
The README now offers a fixed-version clone and source ZIP; the release notes collect the main
changes, measured results, four retained failures, real browser screenshot and next research
priorities. Current document entries refer to the released source; earlier chronological entries
retain their original local/candidate status.

The milestone is published to `main` and source tag `v0.4.0`, following the v0.3 source/tag
publication convention. No separate GitHub Release page is created. Publication changes do not
alter the frozen Agent, dataset, scoring or saved answers and do not make additional model calls.
Commits and the annotated tag use the owner's Git identity without an additional coauthor.
