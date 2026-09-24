"""Freeze and execute a bounded context/metatext development experiment, never official test."""
import argparse
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from medrag.verification.answer_audit import AuditInput, AuditSource, DIRECT_PROMPT, audit_answer
from medrag.verification.context_audit import audit_context, prompt_for
from medrag.verification.ragtruth import char_set, prepare, score_answers
from medrag.verification.scifact import object_hash, read_jsonl

SEED = "veritasmed-context-meta-v1-2026-09-24"
OLD = Path("data/verification/ragtruth_v1/run01")


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def select_cases(cache):
    old, original_manifest = prepare(cache)
    if object_hash(original_manifest) != object_hash(json.loads((OLD / "manifest.json").read_text(encoding="utf8"))):
        raise ValueError("Original pilot manifest differs")
    sources = {s["source_id"]: s for s in read_jsonl(cache / "source_info.jsonl")}
    responses = read_jsonl(cache / "response.jsonl")
    excluded = {r["source_id"] for r in responses if r["split"] == "test"} | {c["source_id"] for c in old}
    candidates = [r for r in responses if r["split"] == "train" and r["quality"] == "good"
                  and r["source_id"] not in excluded and sources[r["source_id"]]["task_type"] == "Summary"
                  and len(r["response"]) <= 12000 and len(sources[r["source_id"]]["source_info"]) <= 50000]
    counts, used, new = Counter(), set(), []
    for row in sorted(candidates, key=lambda r: object_hash([SEED, r["id"]])):
        category = "annotated_error" if row["labels"] else "unmarked"
        if counts[category] >= 12 or row["source_id"] in used:
            continue
        source = sources[row["source_id"]]
        item = AuditInput(answer=row["response"], sources=[AuditSource(id=row["source_id"],
                          title=f"RAGTruth {source['source']} · source {row['source_id']}", text=source["source_info"])])
        new.append({"id": row["id"], "source_id": row["source_id"], "input": item, "gold_spans": row["labels"]})
        counts[category] += 1
        used.add(row["source_id"])
    if len(new) != 24:
        raise ValueError("Cannot select the fixed 12+12 new-source batch")
    repeat = []
    for positive in (True, False):
        repeat.extend(sorted([c for c in new if bool(c["gold_spans"]) == positive],
                             key=lambda c: object_hash([SEED, "repeat", c["id"]]))[:3])
    manifest = {"seed": SEED, "dataset_revision": original_manifest["revision"], "files": original_manifest["files"],
                "official_split": "train", "old_manifest_sha256": object_hash(original_manifest),
                "groups": {group: [{"response_id": c["id"], "source_id": c["source_id"],
                                     "input_sha256": object_hash(c["input"].model_dump()), "gold_spans": c["gold_spans"]}
                                    for c in cases] for group, cases in (("regression", old), ("development", new), ("repeat", repeat))},
                "reserved_official_test": original_manifest["reserved_official_test"],
                "policy": "All gold spans retained, no relabelling; no official test calls; balanced public development data, not clinical validation."}
    return {"regression": old, "development": new, "repeat": repeat}, manifest


def code_hashes():
    paths = [Path(__file__), *[Path("src/medrag/verification") / f for f in
                             ("context_audit.py", "answer_audit.py", "ragtruth.py", "gateway.py", "schema.py", "scifact.py")]]
    return {p.as_posix(): hashlib.sha256(p.read_text(encoding="utf8").encode()).hexdigest() for p in paths}


def ledger(cases, output):
    records = read_jsonl(OLD / "predictions.jsonl")
    entries = []
    for case in cases:
        answer = case["input"].answer
        gold = char_set(answer, case["gold_spans"])
        for row in [r for r in records if r["case_id"] == case["id"]]:
            audit = row["audit"]
            flags = [c for c in audit["claims"] if c["status"] == "ok" and c["relation"] in ("contradicted", "insufficient")]
            predicted = char_set(answer, [c["answer_span"] for c in flags])
            for claim in flags:
                chars = char_set(answer, [claim["answer_span"]])
                entries.append({"case_id": case["id"], "source_id": case["source_id"], "strategy": row["strategy"],
                                "kind": "flag_without_gold_overlap" if not chars & gold else "flag_overlapping_gold",
                                "claim": claim, "gold_overlap_characters": len(chars & gold),
                                "flagged_characters": len(chars), "original_gold_spans": case["gold_spans"],
                                "note": "Overlap is mechanical. No overlap is a disagreement with the reference, not an expert ruling that the model is wrong."})
            for span in case["gold_spans"]:
                target = char_set(answer, [span])
                if len(target & predicted) * 2 < len(target):
                    entries.append({"case_id": case["id"], "source_id": case["source_id"], "strategy": row["strategy"],
                                    "kind": "gold_missed" if not target & predicted else "gold_below_half_coverage",
                                    "original_gold_span": span, "overlap_characters": len(target & predicted)})
    write_json(output / "prior_disagreement_ledger.json", {"status": "development diagnostics, not new gold labels",
               "source_run": OLD.as_posix(), "counts": dict(Counter(e["kind"] for e in entries)), "entries": entries})
    lines = ["# 上一轮逐条差异台账", "", "自动定位全部警报及漏检，原标注不变；不是独立人工复核。完整理由、证据切片、原标签见同目录 JSON。", "",
             "| 回答 | 策略 | 类型 | 回答原文 / 标注原文 |", "|---|---|---|---|"]
    for e in entries:
        quote = e.get("claim", {}).get("quote") or e["original_gold_span"]["text"]
        quote = quote.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {e['case_id']} | {e['strategy']} | {e['kind']} | {quote} |")
    (output / "prior_disagreement_ledger.md").write_text("\n".join(lines) + "\n", encoding="utf8")


def metrics_for(cases, rows):
    result = score_answers(cases, rows)
    by_id = {r["case_id"]: r["audit"] for r in rows}
    meta_counts = Counter()
    located = 0
    for case in cases:
        audit = by_id.get(case["id"], {})
        meta = [m["answer_span"] for m in audit.get("meta_text", []) if m["status"] == "not_source_checked"]
        routed = char_set(case["input"].answer, meta)
        gold = char_set(case["input"].answer, case["gold_spans"])
        meta_counts.update(routed_ranges=len(meta), gold_characters_routed_as_meta=len(routed & gold),
                           gold_spans_routed_as_meta=sum(bool(routed & char_set(case["input"].answer, [s])) for s in case["gold_spans"]),
                           invalid_meta_ranges=sum(m["status"] == "invalid_reference" for m in audit.get("meta_text", [])))
        flags = [c["answer_span"] for c in audit.get("claims", []) if c["status"] == "ok" and c["relation"] in ("contradicted", "insufficient")]
        located += bool(gold & char_set(case["input"].answer, flags))
    result["meta_routing"] = dict(meta_counts)
    result["labelled_error_answers_with_located_error"] = located
    return result


def report(groups, rows, output):
    old_direct = [r for r in read_jsonl(OLD / "predictions.jsonl") if r["strategy"] == "direct"]
    results = {}
    for group, variants in (("regression", ("direct", "context_only", "meta_only", "context")),
                            ("development", ("direct", "context")), ("repeat", ("context",))):
        results[group] = {}
        for variant in variants:
            selected = old_direct if group == "regression" and variant == "direct" else [r for r in rows if r["group"] == group and r["strategy"] == variant]
            results[group][variant] = metrics_for(groups[group], selected)
    def flags(row, case):
        return char_set(case["input"].answer, [c["answer_span"] for c in row["audit"]["claims"]
                        if c["status"] == "ok" and c["relation"] in ("contradicted", "insufficient")])
    stability = []
    for case in groups["repeat"]:
        pair = [next((r for r in rows if r["group"] == g and r["strategy"] == "context" and r["case_id"] == case["id"]), None)
                for g in ("development", "repeat")]
        if not all(pair):
            stability.append({"case_id": case["id"], "status": "incomplete"})
            continue
        a, b = [flags(r, case) for r in pair]
        stability.append({"case_id": case["id"], "status": "ok" if all(r["audit"]["status"] == "ok" for r in pair) else "partial_error",
                          "answer_flag_agrees": bool(a) == bool(b), "flagged_character_jaccard": len(a & b) / len(a | b) if a | b else 1,
                          "first_flagged_chars": len(a), "repeat_flagged_chars": len(b)})
    results["stability"] = stability
    write_json(output / "metrics.json", results)
    lines = ["# Context / meta 开发实验数表", "", "原始 Direct 回归结果来自上一轮；新开发组是同批次交错调用。全部参考错误留在分母，元文本路由不豁免错误。", "",
             "| 数据组 / 策略 | 完成 | 错误范围任意命中 | 至少半范围 | 无标错回答警报 | 字符 P / R / F1 | token | meta 覆盖 gold 字符 |", "|---|---:|---:|---:|---:|---|---:|---:|"]
    for group in ("regression", "development", "repeat"):
        for variant, m in results[group].items():
            c = m["counts"]
            percentages = " / ".join(f"{m[k]:.1%}" if m[k] is not None else "n/a" for k in ("character_precision", "character_recall", "character_f1"))
            lines.append(f"| {group} / {variant} | {c.get('completed_answers',0)}/{m['total_answers']} | {c['span_hit_any']}/{c['gold_spans']} | {c['span_hit_half']}/{c['gold_spans']} | {c['false_positive_answers']}/{c['unmarked_answers']} | {percentages} | {(m['reported_tokens'] or {}).get('total_tokens','n/a')} | {m['meta_routing'].get('gold_characters_routed_as_meta',0)} |")
    lines += ["", "重复记录的字符 Jaccard：两次均无警报定义为 1；仅衡量警报位置稳定，不证明正确。", "", "| 回答 | 状态 | 回答警报一致 | 字符 Jaccard |", "|---|---|---|---|"]
    for s in stability:
        lines.append(f"| {s['case_id']} | {s['status']} | {s.get('answer_flag_agrees','n/a')} | {s.get('flagged_character_jaccard','n/a')} |")
    (output / "results.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    print(json.dumps({g: {v: {"counts": m["counts"], "meta": m["meta_routing"]} for v, m in results[g].items()}
                      for g in ("regression", "development", "repeat")}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "report"))
    parser.add_argument("--cache", type=Path, default=Path(".benchmark-runtime/ragtruth"))
    parser.add_argument("--output", type=Path, default=Path("data/verification/context_v1/run01"))
    args = parser.parse_args()
    groups, manifest = select_cases(args.cache)
    if args.action == "prepare":
        from medrag.verification.gateway import FlashGateway
        args.output.mkdir(parents=True, exist_ok=False)
        schedule = [{"group": g, "case_id": c["id"], "strategy": s}
                    for g, strategies in (("regression", ("context", "context_only", "meta_only")),
                                          ("development", ("direct", "context")), ("repeat", ("context",)))
                    for c in groups[g] for s in strategies]
        schedule.sort(key=lambda j: object_hash([SEED, "order", j]))
        write_json(args.output / "manifest.json", manifest)
        write_json(args.output / "protocol.json", {"prepared_utc": datetime.now(timezone.utc).isoformat(),
                   "schedule": schedule, "workers": 3, "manifest_sha256": object_hash(manifest), "code_hashes": code_hashes(),
                   "settings": FlashGateway().settings, "prompts": {"direct": DIRECT_PROMPT, **{v: prompt_for(v) for v in ("context", "context_only", "meta_only")}},
                   "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                   "old_predictions_sha256": hashlib.sha256((OLD / "predictions.jsonl").read_bytes()).hexdigest()})
        ledger(groups["regression"], args.output)
        print(f"Frozen {len(schedule)} calls, 24 old + 24 new sources; 60 test sources remain unused")
        return
    protocol = json.loads((args.output / "protocol.json").read_text(encoding="utf8"))
    if object_hash(manifest) != protocol["manifest_sha256"]:
        raise ValueError("Inputs changed after preparation")
    if args.action == "report":
        report(groups, read_jsonl(args.output / "predictions.jsonl"), args.output)
        return
    from medrag.verification.gateway import FlashGateway
    gateway = FlashGateway()
    if code_hashes() != protocol["code_hashes"] or gateway.settings != protocol["settings"]:
        raise ValueError("Code/configuration changed after freeze")
    if (args.output / "run.json").exists() or (args.output / "predictions.jsonl").exists():
        raise ValueError("Never overwrite run attempts")
    state = {"started_utc": datetime.now(timezone.utc).isoformat(), "settings": gateway.settings}
    write_json(args.output / "run.json", state)
    cases = {c["id"]: c for group in groups.values() for c in group}
    def execute(job):
        item = cases[job["case_id"]]["input"]
        audit = audit_answer(item, gateway) if job["strategy"] == "direct" else audit_context(item, gateway, job["strategy"])
        return {**job, "audit": audit}
    rows, jobs = [], iter(protocol["schedule"])
    stop = False
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending = {pool.submit(execute, next(jobs)) for _ in range(3)}
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                row = future.result()
                rows.append(row)
                with (args.output / "predictions.jsonl").open("a", encoding="utf8") as stream:
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                print(f"{len(rows)}/{len(protocol['schedule'])} {row['group']} {row['case_id']} {row['strategy']} {row['audit']['status']}", flush=True)
                stop |= any(c.get("http_status") in (401, 402, 403, 429) for c in row["audit"]["calls"])
            if not stop:
                for _ in done:
                    job = next(jobs, None)
                    if job:
                        pending.add(pool.submit(execute, job))
    state.update(completed_utc=datetime.now(timezone.utc).isoformat(), completed=len(rows),
                 stop_reason="Provider access/balance/rate limit; attempts retained" if stop else None)
    write_json(args.output / "run.json", state)
    report(groups, rows, args.output)


if __name__ == "__main__":
    main()
