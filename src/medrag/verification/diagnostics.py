"""Source-anchored diagnostic views. Construction provenance stays out of prompts."""
import json
from pathlib import Path

from .schema import EvidenceDocument, GoldCase, VerificationInput
from .scifact import document_ids, object_hash, prepare_pilot, read_jsonl


def load_diagnostics(cache: Path, specification: Path) -> tuple[list[GoldCase], dict]:
    spec = json.loads(specification.read_text(encoding="utf-8"))
    corpus = {str(d["doc_id"]): d for d in read_jsonl(cache / "corpus.jsonl")}
    pilot, original_manifest = prepare_pilot(cache)
    dev = read_jsonl(cache / "claims_dev.jsonl")
    blocked = set().union(*(document_ids(c) for c in dev),
                          *(set(c.related_document_ids) for c in pilot))
    train_documents = set().union(*(document_ids(c) for c in read_jsonl(cache / "claims_train.jsonl")))
    seen_documents, seen_families = set(), set()
    cases, entries = [], []
    for index, family in enumerate(spec["families"]):
        docid = family["document_id"]
        family_id = family["family_id"]
        if docid in blocked or docid not in train_documents or docid in seen_documents:
            raise ValueError("Diagnostic sources must be unique eligible train documents")
        if family_id in seen_families:
            raise ValueError("Duplicate family ID")
        seen_documents.add(docid)
        seen_families.add(family_id)
        original = EvidenceDocument(document_id=docid, title=corpus[docid]["title"],
                                    sentences=corpus[docid]["abstract"])
        anchors = set(family["anchor_sentence_ids"])
        withheld = set(family["withheld_sentence_ids"])
        control = set(family["control_removed_sentence_ids"])
        if not anchors or not anchors <= withheld or anchors & control:
            raise ValueError("Anchor/removal contract violated")
        if len(withheld) != len(control) or withheld & control:
            raise ValueError("Need disjoint, equal-count deletions")
        if not (withheld | control) <= set(range(len(original.sentences))):
            raise ValueError("Out-of-range original sentence ID")
        for variant in ("supported", "equivalent", "contradicted", "withheld"):
            deleted = withheld if variant == "withheld" else control
            kept = [i for i in range(len(original.sentences)) if i not in deleted]
            document = EvidenceDocument(document_id=docid, title=original.title,
                                        sentences=[original.sentences[i] for i in kept])
            # Opaque case IDs prevent accidental label leakage through downstream identifiers.
            case_id = "controlled-" + object_hash([family_id, variant])[:16]
            relation = {"supported": "supported", "equivalent": "supported",
                        "contradicted": "contradicted", "withheld": "insufficient"}[variant]
            claim = family["claims"]["supported" if variant == "withheld" else variant]
            item = VerificationInput(case_id=case_id, claim=claim, document=document)
            cases.append(GoldCase(input=item, relation=relation,
                                  rationale_sets=[] if variant == "withheld" else [sorted(kept.index(i) for i in anchors)],
                                  original_split="constructed_development", claim_id=index,
                                  related_document_ids=[docid]))
            entries.append({"case_id": case_id, "family_id": family_id, "variant": variant,
                            "category": family["category"], "document_id": docid,
                            "source_sha256": original.sha256, "view_sha256": document.sha256,
                            "original_sentence_ids": kept, "input_sha256": object_hash(item.model_dump()),
                            "relation": relation})
    manifest = {"dataset": "controlled-v1", "split": "development",
                "label_provenance": spec["label_provenance"], "specification_sha256": object_hash(spec),
                "source_manifest_sha256": object_hash(original_manifest), "cases": entries}
    return cases, manifest
