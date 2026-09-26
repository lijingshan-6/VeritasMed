import json

from medrag.verification.scifact import read_jsonl


def test_jsonl_preserves_unicode_separators_inside_source_text(tmp_path):
    rows = [{"source": "first\u2028second\u2029third\u0085fourth"}, {"source": "next document"}]
    path = tmp_path / "sources.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf8")
    assert read_jsonl(path) == rows


def test_replay_reads_complete_records_without_splitting_unicode(tmp_path):
    from medrag.api.routes.audit import complete_rows

    row = {"quote": "before\u2028after"}
    path = tmp_path / "predictions.jsonl"
    path.write_text(json.dumps(row, ensure_ascii=False) + '\n{"unfinished":', encoding="utf8")
    assert complete_rows(path) == [row]
