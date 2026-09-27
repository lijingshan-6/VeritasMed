"""Freeze authored R2 diagnostics and train-only natural cases before inference."""

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
# ruff: noqa: E402
from medrag.verification.atomic_v2_schema import AtomicV2Request
from medrag.verification.scifact import object_hash, read_jsonl
from v08_r2_definitions import DEFINITIONS, EXCLUDED, NEGATIONS

OUT = ROOT / "data/verification/v08/r2"
SEED = "v08-r2-source-v1"


def spans(text, term):
    pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
    return [
        {"start": m.start(), "end": m.end(), "text": m.group()}
        for m in re.finditer(pattern, text, flags=re.I)
    ]


def save(path, value):
    content = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != content:
        raise ValueError(f"Frozen file changed: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build():
    inventory = json.loads(
        (ROOT / "data/verification/v08/exposure/inventory-local.json").read_text(encoding="utf-8")
    )
    candidates = {x["document_id"]: x for x in inventory["construction_candidates"]}
    corpus = {
        str(d["doc_id"]): d for d in read_jsonl(ROOT / ".benchmark-runtime/scifact/corpus.jsonl")
    }
    selected = [d[0] for d in DEFINITIONS]
    if len(selected) != 24 or len({candidates[d]["group_id"] for d in selected}) != 24:
        raise ValueError("Need 24 distinct unexposed source groups")
    split_order = sorted(selected, key=lambda d: object_hash(["v08-r2-split-v1", d]))
    development = set(split_order[:12])
    cases = []
    for index, (doc, ids, scope, statements, groups, values, terms) in enumerate(DEFINITIONS, 1):
        record = corpus[doc]
        if doc in NEGATIONS:
            ids = sorted(set([*ids, NEGATIONS[doc][0]]))
        source = {"id": doc, "title": record["title"], "text": "\n".join(record["abstract"])}
        original = "\n".join(record["abstract"][i].strip() for i in ids)
        tail = [NEGATIONS[doc][1]] if doc in NEGATIONS else []
        all_statements = [*statements, *tail]
        changed = statements[0].replace(values[0], values[1], 1)
        if changed == statements[0]:
            raise ValueError(f"Missing mutation anchor: {doc}")
        variants = {
            "original": original,
            "paraphrase": " ".join([scope, *all_statements]),
            "cross_context": scope
            + "\n\nThe following findings concern that study population and setting.\n"
            + "\n".join(all_statements),
            "repeated_error": " ".join([scope, changed, *statements[1:], *tail]),
        }
        for variant, answer in variants.items():
            targets = []
            for target_index in range(2):
                value = (
                    values[1]
                    if variant == "repeated_error" and target_index == 0
                    else values[target_index]
                )
                if doc == "14726759" and variant == "original" and target_index == 1:
                    value = "Seven"  # The source writes this quantity as a word.
                group = groups[target_index]
                # Original wording and paraphrase spell some groups differently.
                aliases = {
                    ("5597586", 0): ["patients with AN", "AN"],
                    ("20422174", 0): ["ASCUS"],
                    ("20422174", 1): ["LSIL"],
                    ("36558211", 0): ["men"],
                    ("36558211", 1): ["women"],
                    ("16204011", 0): ["Care seeking", "care seeking"],
                }.get((doc, target_index), [group])
                group = next((a for a in aliases if spans(answer, a)), group)
                required = [("group_or_outcome", group), ("quantity", value)]
                meaningful_terms = [
                    t for t in terms if spans(scope + " " + statements[target_index], t)
                ]
                for term in meaningful_terms:
                    if spans(answer, term):
                        required.append(("qualifier", term))
                anchors = []
                for kind, term in required:
                    matches = spans(answer, term)
                    if not matches:
                        raise ValueError(f"{doc} {variant} target {target_index}: missing {term!r}")
                    anchors.append({"kind": kind, "term": term, "acceptable_spans": matches})
                targets.append(
                    {
                        "id": f"target-{target_index + 1}",
                        "anchors": anchors,
                        "literal_value": value,
                        "group_term": group,
                        "deliberate_error": variant == "repeated_error" and target_index == 0,
                        "expected_relation": "contradicted"
                        if variant == "repeated_error" and target_index == 0
                        else "supported",
                        "scope": "Authored textual constraint, not independent clinical ground truth",
                    }
                )
            if tail:
                terms_for_negation = NEGATIONS[doc][2]
                if all(spans(answer, t) for t in terms_for_negation):
                    targets.append(
                        {
                            "id": "target-negation",
                            "anchors": [
                                {
                                    "kind": "negation_or_subject",
                                    "term": t,
                                    "acceptable_spans": spans(answer, t),
                                }
                                for t in terms_for_negation
                            ],
                            "literal_value": None,
                            "group_term": terms_for_negation[-1],
                            "deliberate_error": False,
                            "expected_relation": "supported",
                            "scope": "Authored explicit-negation constraint; textual coverage is not semantic fidelity",
                        }
                    )
                else:
                    raise ValueError(
                        f"Negation wording must be annotated before inference: {doc} {variant}"
                    )
            item = AtomicV2Request(answer=answer, sources=[source])
            cases.append(
                {
                    "id": f"v08-{index:02d}-{variant}",
                    "document_id": doc,
                    "group_id": candidates[doc]["group_id"],
                    "split": "development" if doc in development else "final",
                    "variant": variant,
                    "input": item.model_dump(),
                    "input_sha256": object_hash(item.model_dump()),
                    "source_sentence_ids": ids,
                    "targets": targets,
                    "provenance": "AI/developer construction from the pinned SciFact corpus; complete abstract supplied. No independent expert annotation.",
                }
            )

    # Use only the pre-inventoried training pool, one answer per source.
    natural = []
    used = set()
    counts = {True: 0, False: 0}
    responses = {
        str(r["id"]): r for r in read_jsonl(ROOT / ".benchmark-runtime/ragtruth/response.jsonl")
    }
    sources = {
        str(r["source_id"]): r
        for r in read_jsonl(ROOT / ".benchmark-runtime/ragtruth/source_info.jsonl")
    }
    for candidate in sorted(
        inventory["natural_candidates"],
        key=lambda c: object_hash(["v08-natural-v1", c["response_id"]]),
    ):
        marked = candidate["has_marked_error"]
        source_id = candidate["source_id"]
        if source_id in used or counts[marked] == 6:
            continue
        response, source = responses[candidate["response_id"]], sources[source_id]
        if response["split"] != "train":
            raise ValueError("Official test must not enter development")
        item = AtomicV2Request(
            answer=response["response"],
            sources=[
                {
                    "id": source_id,
                    "title": f"RAGTruth {source['source']} · {source_id}",
                    "text": source["source_info"],
                }
            ],
        )
        if any(item.answer[s["start"] : s["end"]] != s["text"] for s in response["labels"]):
            raise ValueError("Natural label positions differ")
        natural.append(
            {
                "id": "v08-natural-" + candidate["response_id"],
                "response_id": candidate["response_id"],
                "source_id": source_id,
                "group_id": source_id,
                "split": "natural",
                "has_marked_error": marked,
                "gold_spans": response["labels"],
                "input": item.model_dump(),
                "input_sha256": object_hash(item.model_dump()),
            }
        )
        used.add(source_id)
        counts[marked] += 1
        if len(natural) == 12:
            break
    if len(natural) != 12:
        raise ValueError("Need six marked and six unmarked training sources")
    variants = list(variants)
    repeat_ids = [
        next(c["id"] for c in cases if c["document_id"] == doc and c["variant"] == variants[i % 4])
        for i, doc in enumerate(split_order[:6])
    ]
    return {
        "schema": 1,
        "seed": SEED,
        "inventory_sha256": object_hash(inventory),
        "selected_documents": selected,
        "excluded_after_input_review": EXCLUDED,
        "split_rule": "First 12 documents sorted by hash(['v08-r2-split-v1', document_id]) are development; remaining 12 final.",
        "methods": ["direct", "atomic_v1", "atomic_v2"],
        "counts": {
            "constructed": len(cases),
            "development": 48,
            "final": 48,
            "natural": 12,
            "deliberate_errors": 24,
        },
        "repeat_case_ids": repeat_ids,
        "repeat_methods": ["direct", "atomic_v2"],
        "total_attempts_per_repeat": 3,
        "scope": "Targeted anchor coverage and explicit numerical controls. Not exhaustive semantic annotations, clinical gold, or a new public-label generalization test.",
        "source_selection": "First 28 hash-ranked inventoried candidates whose abstracts mention patients/participants/women/men/adults/children; four input-only exclusions recorded. No model-output selection.",
        "construction_review": "Source context and quantitative assignments reviewed by the authoring AI before inference; no independent expert. Cross-context variants move shared scope to a preceding paragraph; they do not claim to span all pronoun phenomena.",
        "cases": cases,
        "natural_cases": natural,
    }


if __name__ == "__main__":
    manifest = build()
    save(OUT / "manifest.json", manifest)
    print(json.dumps(manifest["counts"], indent=2))
