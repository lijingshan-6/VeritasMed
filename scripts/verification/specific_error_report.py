"""Build a traceable post-hoc review; never use text matching as a semantic judge."""
import argparse
from collections import Counter
import json
from pathlib import Path

from context_benchmark import OLD, select_cases, write_json
from medrag.verification.answer_audit import text_hash
from medrag.verification.ragtruth import char_set
from medrag.verification.scifact import object_hash, read_jsonl

ROOT = Path("data/verification/specific_error_v2")
CONTEXT = Path("data/verification/context_v1/run01")
STATUSES = {"identified", "partial", "overlap_only", "missed", "unresolved"}


def review_claim(claim):
    return {k: claim[k] for k in ("id", "quote", "relation", "explanation", "status", "answer_span", "evidence")}


def build(cache, output):
    groups, manifest = select_cases(cache)
    notes = json.loads((ROOT / "review_notes.json").read_text(encoding="utf8"))
    for path, expected_hash in notes["source_predictions_text_sha256"].items():
        if text_hash(Path(path).read_text(encoding="utf8")) != expected_hash:
            raise ValueError("Reviewed saved outputs changed; existing review cannot judge a new output")
    old, current = read_jsonl(OLD / "predictions.jsonl"), read_jsonl(CONTEXT / "predictions.jsonl")
    expected = {(c["id"], n + 1) for g in ("regression", "development") for c in groups[g] for n in range(len(c["gold_spans"]))}
    reviews = {(r["case_id"], r["gold_index_1based"]): r for r in notes["entries"]}
    if len(reviews) != len(notes["entries"]) or set(reviews) != expected:
        raise ValueError("Every original error needs exactly one development review")
    cards, answers = [], []
    for group in ("regression", "development"):
        for case in groups[group]:
            pair = {}
            for method in ("direct", "context"):
                rows = old if group == "regression" and method == "direct" else current
                row = next(r for r in rows if r["case_id"] == case["id"] and r["strategy"] == method and r.get("group", group) == group)
                pair[method] = row["audit"]
                if row["audit"]["answer_sha256"] != text_hash(case["input"].answer):
                    raise ValueError("Saved output belongs to different text")
            answers.append({"case_id": case["id"], "group": group, "source_id": case["source_id"],
                            "input_sha256": object_hash(case["input"].model_dump()), "original_gold_count": len(case["gold_spans"]),
                            "audits": {m: {"original_audit_id": a["id"], "status": a["status"], "summary": a["summary"],
                                            "claims": [review_claim(c) for c in a["claims"]], "meta_text": a.get("meta_text", [])}
                                       for m, a in pair.items()},
                            "note": "All judgments retained; raw calls/context remain in the linked original run. Unmarked text is not independently confirmed correct."})
            for n, gold in enumerate(case["gold_spans"], 1):
                review = reviews[case["id"], n]
                issue, reason = review["issue"], review["reason"]
                card = {"id": f"{case['id']}:{n}", "case_id": case["id"], "group": group,
                        "source_id": case["source_id"], "original_gold": gold,
                        "source_sha256": text_hash(case["input"].sources[0].text),
                        "issue_paraphrase_by_ai": issue, "review_reason": reason, "methods": {}}
                for method in ("direct", "context"):
                    status, refs = review[method]["status"], review[method]["claim_ids"]
                    audit = pair[method]
                    claims = {c["id"]: c for c in audit["claims"]}
                    if status not in STATUSES or any(r not in claims for r in refs):
                        raise ValueError("Unknown review status or claim reference")
                    flags = [c for c in claims.values() if c["status"] == "ok" and c["relation"] in ("contradicted", "insufficient")]
                    if any(claims[r] not in flags for r in refs):
                        raise ValueError("Reviewed warning must have a valid original binding")
                    target = char_set(case["input"].answer, [gold])
                    overlap = target & char_set(case["input"].answer, [c["answer_span"] for c in flags])
                    card["methods"][method] = {"development_review": status, "claim_ids": refs,
                        "reviewed_claims": [review_claim(claims[r]) for r in refs], "audit_status": audit["status"],
                        "original_character_hit_any": bool(overlap), "original_character_hit_half": len(overlap) * 2 >= len(target)}
                cards.append(card)
    totals = {m: dict(Counter(c["methods"][m]["development_review"] for c in cards)) for m in ("direct", "context")}
    result = {"version": notes["version"], "provenance": notes["provenance"],
              "scope": "Specific public error identification only. Not three-class accuracy, precision, expert correctness or a judge usable on unseen outputs.",
              "reference_manifest_sha256": object_hash(manifest), "review_notes_sha256": object_hash(notes),
              "saved_predictions_text_sha256": {p.as_posix(): text_hash(p.read_text(encoding="utf8")) for p in (OLD / "predictions.jsonl", CONTEXT / "predictions.jsonl")},
              "answer_count": len(answers), "original_error_count": len(cards), "counts": totals, "cards": cards, "answers": answers}
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "report.json", result)
    lines = ["# 具体错误诊断 v2", "", notes["provenance"], "",
             "人工原标注和原字符分数不改；以下是 AI 在看过输出后逐项整理的开发诊断，不是独立语义准确率。",
             "`identified` 仅指明确认出该问题，不保证三分类、其他警报或整份回答正确。`partial` 不当完整命中；`unresolved` 不从分母去掉。", "",
             f"48 份回答 / {len(cards)} 处原错误 / {len(cards)*2} 项方法对照；24 份无标错回答的全部输出保留在 JSON，未自动判定其中警报对错。", "",
             "| 方法 | 识别具体问题 | 部分识别 | 仅位置重叠 | 遗漏 | 未裁定 |", "|---|---:|---:|---:|---:|---:|"]
    for m, count in totals.items():
        lines.append(f"| {m} | " + " | ".join(str(count.get(s, 0)) for s in ("identified", "partial", "overlap_only", "missed", "unresolved")) + " |")
    for card in cards:
        lines += ["", f"## {card['id']} · {card['issue_paraphrase_by_ai']}", "",
                  f"来源 {card['source_id']}，{card['group']}。原类别：{card['original_gold']['label_type']}。", "",
                  "原标注文字：" + card["original_gold"]["text"], "", "原人工说明：", "", card["original_gold"]["meta"], "",
                  "开发审阅：" + card["review_reason"]]
        for method, result in card["methods"].items():
            lines += ["", f"**{method}: {result['development_review']}** · 原位置任意/半范围 {result['original_character_hit_any']}/{result['original_character_hit_half']} · 整次 {result['audit_status']}"]
            for claim in result["reviewed_claims"]:
                lines += ["", f"- {claim['id']} / {claim['relation']}：{claim['quote']}", f"  理由：{claim['explanation']}"]
                lines += [f"  原文 [{e['start']}:{e['end']}]：{e['text']}" for e in claim["evidence"]]
    # Markdown presentation trims trailing spaces; JSON keeps the exact public annotation.
    markdown = "\n".join(line.rstrip() for line in "\n".join(lines).splitlines())
    (output / "report.md").write_text(markdown + "\n", encoding="utf8")
    print(json.dumps({"answers": len(answers), "errors": len(cards), "development_review_counts": totals}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(".benchmark-runtime/ragtruth"))
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    build(args.cache, args.output)
