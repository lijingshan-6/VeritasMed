"""Materialize attributed, original abstract excerpts for the v0.8 conversations."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/demo/conversations"


def text(element):
    return " ".join("".join(element.itertext()).split())


def materialize():
    manifest = json.loads((OUT / "source-manifest.json").read_text(encoding="utf8"))
    rows = []
    for source in manifest["sources"]:
        raw = (ROOT / source["xml_path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["xml_sha256"]:
            raise ValueError(f"Publisher snapshot changed: {source['doi']}")
        article = ET.fromstring(raw)
        sections = article.findall(".//abstract/sec")
        for i, section in enumerate(sections):
            rows.append({
                "chunk_id": f"pmc:{source['pmcid']}:{i}", "doc_id": source["pmcid"],
                "pmid": source["pmid"], "source": "pmc", "title": source["title"],
                "section": "Abstract / " + text(section.find("title")),
                "chunk_idx": i, "total_chunks": len(sections),
                "content_kind": "original_article_excerpt",
                "source_url": source["article_url"], "doi": source["doi"],
                "license": source["license"], "year": source["year"],
                "journal": "PLOS ONE", "authors": source["authors"],
                "text": "\n\n".join(text(p) for p in section.findall("p")),
            })
    return rows


if __name__ == "__main__":
    rows = materialize()
    (OUT / "corpus.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf8", newline="\n",
    )
    print(f"Materialized {len(rows)} passages from three original abstracts; no model calls.")
