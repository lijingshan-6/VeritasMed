"""Preserve the exact experimental source while permitting verified formatting changes."""

import ast
import json

from medrag.verification.scifact import object_hash
from v06_prepare import ROOT, OUT


def code_hashes(paths):
    archive_path = OUT / "frozen-source.json"
    archive = json.loads(archive_path.read_text(encoding="utf8")) if archive_path.exists() else {}
    result = {}
    for path in paths:
        current = (ROOT / path).read_text(encoding="utf8")
        old = archive.get(path)
        if old and ast.dump(ast.parse(old["text"])) == ast.dump(ast.parse(current)):
            result[path] = object_hash(old["text"])
        else:
            result[path] = object_hash(current)
    return result


if __name__ == "__main__":
    paths = set()
    for directory in (OUT, ROOT / "data/verification/v07"):
        for p in directory.rglob("protocol.json"):
            paths.update(json.loads(p.read_text(encoding="utf8")).get("code_hashes", {}))
    destination = OUT / "frozen-source.json"
    if destination.exists():
        raise ValueError("Source archive is immutable")
    archive = {
        p: {
            "text": (ROOT / p).read_text(encoding="utf8"),
            "note": "Exact inference source before release formatting. AST equivalence is checked by runners; behavior changes fail.",
        }
        for p in sorted(paths)
    }
    destination.write_text(
        json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(f"Archived {len(paths)} exact source files")
