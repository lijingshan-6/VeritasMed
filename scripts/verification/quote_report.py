"""Render the complete frozen quote-v2 comparison offline, including supported judgments."""
import argparse
from collections import Counter
import json
from pathlib import Path

from quote_benchmark import ROOT, cases_for
from medrag.verification.ragtruth import char_set
from medrag.verification.scifact import object_hash, read_jsonl


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=ROOT)
    parser.add_argument("--cache", type=Path, default=Path(".benchmark-runtime/ragtruth"))
    args = parser.parse_args()
    cases, fixed, manifest = cases_for(args.cache)
    protocol = json.loads((args.run / "protocol.json").read_text(encoding="utf8"))
    rows = read_jsonl(args.run / "predictions.jsonl")
    if object_hash(manifest) != protocol["manifest_sha256"]:
        raise ValueError("Inputs differ from frozen manifest")
    def key(row):
        return tuple(row[k] for k in ("task", "strategy", "case_id", "attempt"))
    if Counter(map(key, rows)) != Counter(map(key, protocol["schedule"])):
        raise ValueError("A full report needs every scheduled attempt exactly once")
    metrics = json.loads((args.run / "metrics.json").read_text(encoding="utf8"))
    lines = ["# Quote-v2：全部输出对照", "", "公开 train 开发数据；不改原标签，固定目标不测提取，原文复制是自拟简单对照。", "",
             "| 整段方法 | 完成 | 原错误任意/半范围 | 无标错回答警报 | 字符 F1 | token |", "|---|---:|---:|---:|---:|---:|"]
    for method in ("direct", "quote_v2"):
        m = metrics["whole"][method]
        c = m["counts"]
        lines.append(f"| {method} | {c['completed_answers']}/8 | {c['span_hit_any']}/5 · {c['span_hit_half']}/5 | {c['false_positive_answers']}/4 | {m['character_f1']:.1%} | {m['reported_tokens']['total_tokens']} |")
    lines += ["", "| 固定目标方法 | 完成 | 二分类参考一致 | 非支持误接受 | 原文复制误拒绝 |", "|---|---:|---:|---:|---:|"]
    for method in ("direct", "quote_v2"):
        c = metrics["fixed"][method]["counts"]
        lines.append(f"| {method} | {c['complete']}/8 | {c['binary_agrees']}/8 | {c['non_support_accepted']}/4 | {c['supported_control_flagged']}/4 |")
    repeats = []
    for row in [r for r in rows if r["attempt"] == 2]:
        first = next(r for r in rows if r["attempt"] == 1 and all(r[k] == row[k] for k in ("task", "strategy", "case_id")))
        item = next(c for c in (cases if row["task"] == "whole" else fixed) if c["id"] == row["case_id"])["input"]
        def flags(r):
            return char_set(item.answer, [c["answer_span"] for c in r["audit"]["claims"] if c["status"] == "ok" and c["relation"] in ("contradicted", "insufficient")])
        a, b = flags(first), flags(row)
        repeats.append({"case_id": row["case_id"], "task": row["task"], "first_flagged": bool(a), "repeat_flagged": bool(b),
                        "first_chars": len(a), "repeat_chars": len(b), "jaccard": len(a & b) / len(a | b) if a | b else None})
    lines += ["", "## 重复", "", "两次均无警报时 Jaccard 留空；不能解释为可靠性。", "", json.dumps(repeats, ensure_ascii=False, indent=2)]
    for case in cases:
        lines += ["", f"## 回答 {case['id']} / 来源 {case['source_id']}", "", case["input"].answer, "", "原标签：", "", json.dumps(case["gold_spans"], ensure_ascii=False, indent=2)]
        target = next(c for c in fixed if c["id"] == case["id"])
        lines += ["", "固定目标：" + target["target"], "", "目标来源：" + target["label_origin"]]
        for row in sorted([r for r in rows if r["case_id"] == case["id"]], key=key):
            audit = row["audit"]
            lines += ["", f"### {row['task']} / {row['strategy']} / attempt {row['attempt']} / {audit['status']}"]
            for c in audit["claims"]:
                lines += ["", f"- {c['id']} **{c['relation']}** ({c['status']})：{c['quote']}", "  理由：" + c["explanation"]]
                lines += [f"  来源 {e['source_id']} [{e['start']}:{e['end']}]：{e['text']}" for e in c["evidence"]]
            for m in audit.get("meta_text", []):
                lines += ["", f"呈现说明 ({m['status']})：{m['quote']} / {m['explanation']}"]
    (args.run / "results.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    print(json.dumps({"saved": str(args.run / "results.md"), "repeats": repeats}, ensure_ascii=False))


if __name__ == "__main__":
    main()
