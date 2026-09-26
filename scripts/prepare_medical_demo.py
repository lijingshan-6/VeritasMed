"""Rebuild the small medical corpus from the bundled, attributed publisher XML."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "data/demo/medical"


def materialize() -> list[dict]:
    raw = (ROOT / "article.xml").read_bytes()
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf8"))
    if hashlib.sha256(raw).hexdigest() != manifest["article_xml_sha256"]:
        raise ValueError("Publisher XML differs from the recorded snapshot")
    article = ET.fromstring(raw)

    def text(element):
        return " ".join("".join(element.itertext()).split())

    sections = article.findall(".//abstract/sec")
    return [{
        "chunk_id": f"pmc:PMC11567630:{i}", "doc_id": "PMC11567630", "pmid": "39546502",
        "title": text(article.find(".//article-title")),
        "section": "Abstract / " + text(section.find("title")),
        "chunk_idx": i, "total_chunks": len(sections), "content_kind": "original_article_excerpt",
        "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11567630/",
        "doi": manifest["doi"], "license": "CC0-1.0", "year": 2024, "journal": "PLOS ONE",
        "authors": "Seaquist ER et al.; GRADE Research Group",
        "text": "\n\n".join(text(p) for p in section.findall("p")),
    } for i, section in enumerate(sections)]


if __name__ == "__main__":
    rows = materialize()
    (ROOT / "corpus.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf8", newline="\n",
    )
    print(f"Materialized {len(rows)} original abstract passages; no model calls.")
