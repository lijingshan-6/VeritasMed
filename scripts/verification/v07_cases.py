"""Readable final cases, including every failure and retained draft; offline only."""

from medrag.verification.scifact import read_jsonl
from v06_prepare import ROOT
from v07_benchmark import METHODS, V07, load_tasks


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def main():
    tasks = load_tasks("final")
    rows = read_jsonl(V07 / "final/predictions.jsonl")
    by = {(r["case_id"], r["method"]): r["result"] for r in rows}
    if len(rows) != len(tasks) * len(METHODS):
        raise ValueError("Finish all final attempts before generating the case report")
    lines = [
        "# v0.7 最终 40 题逐题记录",
        "从保存输出生成，不调用模型、不修订标签；包括失败与被保留的原草稿。公开标签只评指定论文与 claim 的关系，不代表每个解释句都经过独立核查。",
        "[主报告](verification-v0.7-report.md) · [原始 JSONL](../../data/verification/v07/final/predictions.jsonl) · [冻结清单](../../data/verification/v07/manifest.json)",
    ]
    for entry, task in sorted(tasks, key=lambda pair: pair[0]["case_id"]):
        lines += [
            f"## {entry['case_id']}",
            f"**论文：** {task.target_title}",
            f"**待核查陈述：** {task.claim}",
            f"**公开标签：** {entry['relation']}；目标 document ID `{entry['document_id']}`。",
        ]
        case_table = [
            "| 方法 | 状态 | 原答关系 | 引用文献 | 已接受二分类正确 | 模型调用 |",
            "|---|---|---|---|---|---|",
        ]
        for method in METHODS:
            r = by[(entry["case_id"], method)]
            a = r.get("answer") if isinstance(r.get("answer"), dict) else {}
            accepted = r["status"] == "ok" and a.get("document_id") == entry["document_id"]
            correct = accepted and (a.get("relation") == "supported") == (
                entry["relation"] == "supported"
            )
            case_table.append(
                "| "
                + " | ".join(
                    cell(v)
                    for v in (
                        method,
                        r["status"],
                        a.get("relation", "无有效答案"),
                        a.get("document_id", "—"),
                        "是" if correct else "否",
                        r["model_calls"],
                    )
                )
                + " |"
            )
        lines.append("\n".join(case_table))
        for method in METHODS:
            r = by[(entry["case_id"], method)]
            a = r.get("answer") if isinstance(r.get("answer"), dict) else {}
            lines += [
                f"**{method} 原回答：**",
                str(a.get("answer") or "没有可用答案，原始返回保留在 JSONL/trace。"),
                f"依据句 ID：`{[s['sentence_id'] for s in r['evidence']]}`；已读文献：`{r['read_document_ids']}`。",
            ]
            if r.get("review_reason"):
                lines += [f"保留原因：{r['review_reason']}"]
    (ROOT / "docs/reports/verification-v0.7-cases.md").write_text(
        "\n\n".join(lines) + "\n", encoding="utf8"
    )
    print("Wrote all 40 final cases with all three original outputs")


if __name__ == "__main__":
    main()
