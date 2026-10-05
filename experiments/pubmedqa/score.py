"""Score saved answers. No API calls; MiniCheck runs locally.

Rules (fixed before any pilot output was read):
- Sentences: split on . ! ? followed by whitespace and an uppercase letter or digit.
- Citation keys: [PMID:n] markers; removed from the sentence before checking.
- Absence statements ("does not establish / report / provide / show / state / address ...",
  "not reported / stated / addressed") say what the evidence lacks. They are counted separately
  and excluded from support denominators, for every arm alike.
- Citation support (A1, A2, A4): a cited sentence is supported if MiniCheck accepts it against
  the concatenated passages the method itself showed for the cited PMIDs. A sentence with no
  citation is unsupported for citation recall (ALCE convention).
- Source consistency (all arms incl. A0): each non-absence sentence is checked against the
  question's gold abstract. Measures agreement with the actual paper, regardless of citation.
- Accuracy: judged verdict vs the expert label; unparsable or failed answers count as wrong.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNTIME = HERE.parents[1] / ".exp-runtime" / "pubmedqa"
CITE = re.compile(r"\[(PMID:\d+)\]")
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
ABSENCE = re.compile(r"\b(?:do(?:es)?|did) not (?:establish|report|provide|show|state|address|include|contain|measure)|"
                     r"\bnot (?:reported|stated|addressed|established|measured)\b|\bno (?:data|information) (?:on|about)\b", re.I)


def sentences(answer: str) -> list[dict]:
    out = []
    for raw in SENTENCE.split(" ".join(answer.split())):
        if not raw.strip():
            continue
        keys = list(dict.fromkeys(CITE.findall(raw)))
        text = " ".join(CITE.sub("", raw).split()).replace(" .", ".")
        out.append({"text": text, "cites": keys, "absence": bool(ABSENCE.search(text))})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="main")
    ap.add_argument("--split", required=True)
    ap.add_argument("--arms", default="A0,A1,A2,A4")
    args = ap.parse_args()
    import sys
    sys.path.insert(0, str(HERE))
    from minicheck import MiniCheckAdapter

    checker = MiniCheckAdapter(cache_dir=str(HERE.parents[1] / ".exp-runtime" / "models"))
    questions = json.loads((RUNTIME / "questions.json").read_text(encoding="utf8"))
    run = HERE / "runs" / args.run
    for arm in args.arms.split(","):
        src = run / f"{args.split}-{arm}.jsonl"
        if not src.exists():
            continue
        # The last attempt per question is the one that counts (as in run.py and report.py).
        rows = list({r["pmid"]: r for r in map(json.loads, src.read_text(encoding="utf8").splitlines())}.values())
        out = run / f"{args.split}-{arm}.scored.jsonl"
        with out.open("w", encoding="utf8") as f:
            for row in rows:
                q = questions[row["pmid"]]
                gold = "\n".join(" ".join(t.split()) for t in q["gold_contexts"])
                scored = []
                for s in sentences(row.get("answer", "") if row["status"] == "ok" else ""):
                    item = dict(s)
                    if not s["absence"]:
                        item["gold"] = checker.score(gold, s["text"])["binary_prediction"]
                        if arm != "A0" and s["cites"]:
                            docs = "\n".join(c["text"] for c in row.get("chunks", []) if f"PMID:{c['doc_id']}" in s["cites"])
                            item["cited"] = checker.score(docs, s["text"])["binary_prediction"] if docs else 0
                    scored.append(item)
                f.write(json.dumps({"pmid": row["pmid"], "arm": arm, "status": row["status"], "sentences": scored},
                                   ensure_ascii=False) + "\n")
        print(f"scored {arm}: {len(rows)} answers")


if __name__ == "__main__":
    main()
