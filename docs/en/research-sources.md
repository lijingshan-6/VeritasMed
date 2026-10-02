# Research sources and attribution

**English** | [简体中文](../research-sources.md)

The repository's Apache-2.0 license applies to this project's code. It does not replace
the licenses of datasets, papers or model weights. The full upstream corpora and model
weights are downloaded into ignored local caches. Small source excerpts, demonstration
abstracts, claims and actual tool responses are retained with the published research records.

## SciFact

David Wadden, Shanchuan Lin, Kyle Lo, Lucy Lu Wang, Madeleine van Zuylen, Arman Cohan and
Hannaneh Hajishirzi, **Fact or Fiction: Verifying Scientific Claims**, EMNLP 2020.
[Paper](https://arxiv.org/abs/2004.14974) · [Dataset and code](https://github.com/allenai/scifact) ·
[Upstream license](https://github.com/allenai/scifact/blob/master/LICENSE.md).

The upstream license distinguishes claims/evidence annotations (**CC BY 4.0**), corpus
abstracts from Semantic Scholar S2ORC (**ODC-By 1.0**) and code (**Apache-2.0**).
Those distinctions also apply to the corresponding material retained here. Corpus document
IDs are SciFact IDs, not PubMed identifiers. Original paper titles accompany source records.

This project transforms claim/document pairs into source-grouped partitions, short constructed
diagnostics and named-paper queries. Constructed answers and transformations are marked as
developer/AI work; the original public relation labels are not rewritten after model output.
The three bundled workflow examples contain their eight original candidate abstracts so that
readers can inspect tool inputs without a separate download. Research traces also retain
actually read text. These are attributed dataset excerpts, not newly authored medical evidence.

## RAGTruth

[RAGTruth: A Hallucination Corpus for Developing Trustworthy Retrieval-Augmented Language Models](https://github.com/ParticleMedia/RAGTruth).
The pinned source and response files are downloaded separately. The retained upstream
[license](../../data/verification/ragtruth_v1/LICENSE-RAGTruth), source identifiers and manifests
accompany derived experiments. Our warning-span metrics and AI diagnostics are project
derivatives; public marked spans are retained without relabelling them to fit model output.
An unmarked answer is not an exhaustive expert guarantee of correctness.

## GRADE medical demonstration

Seaquist et al. (2024), [GRADE hypoglycemia outcomes](https://doi.org/10.1371/journal.pone.0309907),
CC0. The [source card and original XML](../../data/demo/medical/README.md) record the exact
abstract extraction. The unchanged Agent answer, swapped-arm control and evidence-removal
control have different provenance labels; the latter two are explicit constructions.

The [v0.8 two-turn conversation export](../../data/verification/v08/grade-conversation-smoke.json)
reuses this CC0 abstract and preserves two actual Ask answers plus one actual Direct audit.
It is a product workflow example, not an independent medical evaluation or expert annotation.

The [v0.8 offline localization replay](../reports/verification-v0.8-localization.md) reuses saved
SciFact/RAGTruth-derived Atomic outputs and the three GRADE demo audits. It changes
position binding only, retains original model judgments, and creates no expert labels.
The [exposure inventory](../reports/verification-v0.8-exposure.md) records source reuse and candidate
IDs; its mechanical candidate screen is not clinical annotation or a new gold dataset.

## MiniCheck

Liyan Tang, Philippe Laban and Greg Durrett, **MiniCheck: Efficient Fact-Checking of LLMs
on Grounding Documents**, EMNLP 2024. [Paper](https://arxiv.org/abs/2404.10774) ·
[Code](https://github.com/Liyan06/MiniCheck) ·
[Model](https://huggingface.co/lytang/MiniCheck-Flan-T5-Large).

The optional adapter follows the pinned upstream input/scoring format while using an explicit
full-input length limit instead of silent truncation or upstream chunk aggregation. Exact
revisions, model/code licenses and these changes are documented in the
[MiniCheck environment guide](minicheck-research.md). Weights are not redistributed here.


## v0.8 conversation demonstration

The three-paper Ask replay retains original publisher XML and every original abstract section
from Seaquist et al. (2024, GRADE, CC0), Lee et al. (2016, brown-rice-based vegan diet RCT,
CC BY 4.0), and Figueira et al. (2013, exercise crossover RCT, Creative Commons Attribution).
The older paper's snapshot does not identify a CC BY version; none is inferred.
Full titles, author lists, DOI/PMID/PMCID, license statements and hashes are in the
[source manifest](../../data/demo/conversations/source-manifest.json) and
[attribution/readme](../../data/demo/conversations/README.md).

The normalized corpus preserves original paragraph order. Saved model answers are clearly
labelled outputs, not source text or gold labels. Nine questions are frozen before inference;
failures and clarification are preserved. The corpus contains abstracts, not whole-text or
current-guideline coverage. New dialogue recordings are demonstrations and must be treated
as exposed data in any later source-use inventory.

The v0.8 R2 manifest adds 24 previously unused SciFact source groups (plus four input-only
exclusions inspected during selection) and 12 RAGTruth training sources. All are now exposed
for later research. The pre-v0.8 inventory remains an immutable pre-selection snapshot.
The manifest and output directories record these new uses rather than rewriting that snapshot.
