"""Render bilingual documentation diagrams from source AST and saved WS events.

Standard library only. No product route, runtime import or model call.
"""
from __future__ import annotations

import ast
from collections import Counter
import hashlib
from html import escape
import json
from pathlib import Path
import textwrap


def build_catalogue(root: Path) -> dict:
    graph_path = root / "src/medrag/agent/graph.py"
    constants_path = root / "src/medrag/agent/nodes/constants.py"
    state_path = root / "src/medrag/agent/state.py"
    graph = ast.parse(graph_path.read_text(encoding="utf-8"))
    constants = ast.parse(constants_path.read_text(encoding="utf-8"))
    values = {}
    for node in constants.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            values[node.targets[0].id] = ast.literal_eval(node.value)
    symbols = {}
    for file in sorted((root / "src/medrag/agent/nodes").glob("*.py")):
        for item in ast.parse(file.read_text(encoding="utf-8")).body:
            if isinstance(item, (ast.FunctionDef, ast.ClassDef)):
                symbols[item.name] = {"path": file.relative_to(root).as_posix(), "line": item.lineno}

    def label(item):
        if isinstance(item, ast.Constant):
            return item.value
        if isinstance(item, ast.Name):
            return {"START": "__start__", "END": "__end__"}.get(item.id, item.id)
        raise ValueError("Unrecognized graph label")

    build = next(n for n in graph.body if isinstance(n, ast.FunctionDef) and n.name == "_build_graph")
    nodes, edges = [], []
    for item in build.body:
        if not isinstance(item, ast.Expr) or not isinstance(item.value, ast.Call):
            continue
        call = item.value
        if not isinstance(call.func, ast.Attribute) or not isinstance(call.func.value, ast.Name) or call.func.value.id != "g":
            continue
        if call.func.attr == "add_node":
            symbol = label(call.args[1]) if isinstance(call.args[1], ast.Name) else "lambda"
            nodes.append({"id": label(call.args[0]), "symbol": symbol,
                          "source": symbols.get(symbol, {"path": graph_path.relative_to(root).as_posix(), "line": item.lineno})})
        elif call.func.attr == "add_edge":
            edges.append({"from": label(call.args[0]), "to": label(call.args[1])})
        elif call.func.attr == "add_conditional_edges":
            choices = call.args[2]
            if not isinstance(choices, ast.Dict):
                raise ValueError("Conditional graph choices must be explicit")
            for key, value in zip(choices.keys, choices.values):
                branch, target = label(key), label(value)
                edges.append({"from": label(call.args[0]), "to": target,
                              "predicate": label(call.args[1]), "branch": branch})
    state = ast.parse(state_path.read_text(encoding="utf-8"))
    klass = next(n for n in state.body if isinstance(n, ast.ClassDef) and n.name == "AgentState")
    return {"scope": "Current source structure; not a reconstruction of historical intermediate state",
            "nodes": nodes, "edges": edges,
            "budgets": {k: values[k] for k in ("MAX_REWRITES", "MAX_REGEN", "TOP_K", "PER_QUERY_K", "HISTORY_SUMMARIZE_EVERY")},
            "thresholds": values["_GRADE_THRESHOLDS"], "default_threshold": values["GRADE_THRESHOLD"],
            "state_fields": [n.target.id for n in klass.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)],
            "predicates": {n.name: {"path": graph_path.relative_to(root).as_posix(), "line": n.lineno}
                           for n in graph.body if isinstance(n, ast.FunctionDef) and n.name in ("_after_grade", "_after_check", "_maybe_summarize")},
            "fingerprint_format": "sha256-utf8-lf",
            "fingerprints": {p.relative_to(root).as_posix(): hashlib.sha256(p.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
                             for p in (graph_path, constants_path, state_path)}}


INK, MUTED, BLUE, GOLD, GREEN = "#203436", "#647273", "#296789", "#a9691e", "#28745b"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets/system-guide"
RECORD = "data/demo/conversations/run01/v08-evidence-limits-turn-3-events.jsonl"


class Figure:
    def __init__(self, title, subtitle, height):
        self.height = height
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="{height}" viewBox="0 0 1600 {height}" role="img">',
                      f"<title>{escape(title)}</title><desc>{escape(subtitle)}</desc>",
                      '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#647273"/></marker></defs>',
                      '<rect width="1600" height="100%" fill="#faf9f5"/>',
                      '<g font-family="Arial, Microsoft YaHei, sans-serif" fill="#203436">']
        self.text(50, 44, ["VERITASMED / v0.8 / DOCUMENTATION"], 18, BLUE)
        self.text(50, 91, [title], 34, INK, "bold")
        self.text(50, 129, [subtitle], 21, MUTED)

    def text(self, x, y, lines, size=22, color=INK, weight="normal"):
        for i, line in enumerate(lines):
            self.parts.append(f'<text x="{x}" y="{y+i*(size+10)}" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(str(line))}</text>')

    def rect(self, x, y, width, height, stroke="#d8dedc", fill="#ffffff"):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="12" stroke="{stroke}" stroke-width="2" fill="{fill}"/>')

    def path(self, d, loop=False):
        style = 'stroke-dasharray="8 6"' if loop else ""
        self.parts.append(f'<path d="{d}" fill="none" stroke="{GOLD if loop else MUTED}" stroke-width="2" {style} marker-end="url(#arrow)"/>')

    def save(self, name):
        (OUT / f"{name}.svg").write_text("\n".join(self.parts + ["</g></svg>"]) + "\n", encoding="utf-8")


LABELS = {
    "route": ("规划检索", "Plan retrieval", "model"),
    "retrieve": ("混合检索", "Hybrid retrieval", "resource"),
    "rerank": ("重排与研究匹配", "Rerank / match studies", "mixed"),
    "grade": ("绑定回答要点", "Bind answer components", "mixed"),
    "rewrite": ("改写检索", "Rewrite search", "model"),
    "generate": ("生成与定向补写", "Generate / targeted repair", "mixed"),
    "check": ("图内检查", "Internal check", "mixed"),
    "inc_regen": ("修复计数 +1", "Increment repair counter", "rule"),
    "append_history": ("保存图内历史", "Append graph history", "storage"),
    "summarize_gate": ("历史摘要分支", "History summary gate", "rule"),
    "summarize": ("压缩图内历史", "Summarize graph history", "model"),
    "resolve_context": ("理解追问（API 前置）", "Resolve follow-up (API)", "model"),
}
COLORS = {"model": BLUE, "resource": "#7887a2", "mixed": GOLD, "rule": MUTED, "storage": GREEN}


def render_graph(data, language):
    zh = language == "zh"
    f = Figure("Ask 节点与有界回环" if zh else "Ask nodes and bounded loops",
               "当前源码结构 · 追问解析在图之前 · 灰色辅助节点保留程序化兼容" if zh else
               "Current source structure / resolve context before the graph / helpers retain programmatic compatibility", 1120)
    positions = {"__start__": (210, 202), "route": (210, 305), "retrieve": (580, 305), "rerank": (950, 305),
                 "grade": (1320, 305), "append_history": (210, 530), "check": (580, 530),
                 "generate": (950, 530), "rewrite": (1320, 530), "summarize_gate": (210, 730),
                 "inc_regen": (580, 730), "summarize": (210, 910), "__end__": (580, 910)}
    for edge in data["edges"]:
        x1, y1 = positions[edge["from"]]
        x2, y2 = positions[edge["to"]]
        dx, dy = x2-x1, y2-y1
        horizontal = dy == 0
        pad_x, pad_y = (142, 0) if horizontal else (0, 58)
        if horizontal:
            direction = 1 if dx > 0 else -1
            target_pad = 62 if edge["to"] == "__end__" else pad_x
            d = f"M{x1+pad_x*direction},{y1} L{x2-target_pad*direction},{y2}"
        else:
            direction = 1 if dy > 0 else -1
            start_pad = 22 if edge["from"] == "__start__" else pad_y
            end_pad = 24 if edge["to"] == "__end__" else pad_y
            d = f"M{x1},{y1+start_pad*direction} L{x2},{y2-end_pad*direction}"
        if edge["from"] == "rewrite":
            d = "M1462,530 L1530,530 L1530,640 L770,640 L770,410 L580,410 L580,363"
        loop = edge["from"] in {"rewrite", "inc_regen"} or edge.get("branch") == "regenerate"
        f.path(d, loop)
    kinds = {"model": "模型调用" if zh else "Model", "resource": "本地检索" if zh else "Retrieval",
             "mixed": "模型 + 程序" if zh else "Model + rules", "rule": "程序规则" if zh else "Program rule",
             "storage": "保存记录" if zh else "Persistence"}
    for node in data["nodes"]:
        name = node["id"]
        x, y = positions[name]
        title = LABELS[name][0 if zh else 1]
        kind = LABELS[name][2]
        f.rect(x-140, y-55, 280, 110, COLORS[kind])
        f.text(x-124, y-25, [name], 22, INK, "bold")
        f.text(x-124, y+10, [title], 20)
        f.text(x-124, y+40, [kinds[kind]], 16, MUTED)
    for name, label in [("__start__", "START"), ("__end__", "END")]:
        x, y = positions[name]
        f.rect(x-60, y-22, 120, 44, MUTED, "#eff2ef")
        f.text(x-35, y+8, [label], 20, MUTED)
    f.text(1340, 416, ["score / rewrite budget" if not zh else "评分 / 改写预算"], 17, GOLD)
    f.text(950, 675, [f"rewrite ≤ {data['budgets']['MAX_REWRITES']}"], 20, GOLD)
    f.text(700, 750, [f"repair ≤ {data['budgets']['MAX_REGEN']}"], 20, GOLD)
    f.rect(940, 780, 585, 205, MUTED, "#f1f3f0")
    f.text(965, 820, ["图内历史 ≠ 浏览器会话" if zh else "Graph history ≠ browser conversation"], 24, INK, "bold")
    f.text(965, 865, ["网页每次使用独立 checkpoint。" if zh else "Web requests use fresh checkpoints.",
                      "浏览器历史另存于 IndexedDB。" if zh else "Browser history lives in IndexedDB.",
                      f"显式重用图内历史：每 {data['budgets']['HISTORY_SUMMARIZE_EVERY']} 轮摘要。" if zh else
                      f"Explicit graph reuse: summarize every {data['budgets']['HISTORY_SUMMARIZE_EVERY']} turns."], 21, MUTED)
    f.text(50, 1036, ["实线：普通分支；虚线：修复 / 改写。预算耗尽可以保留问题结束。" if zh else
                      "Solid: ordinary branches. Dashed: repair / rewrite. Unresolved issues can remain at exit.",
                      "来源：graph.py / nodes/constants.py。图内 check 与用户打开的独立 Audit 是两套流程。" if zh else
                      "Source: graph.py / nodes/constants.py. Internal check is separate from user-opened Audit."], 21, MUTED)
    f.save(f"nodes-{language}")


DETAILS = {
    "zh": [
        ["grade · 绑定回答要点", ["原问题、已匹配研究", "来源句 ID 与原文片段"],
         ["构造要点提纲，选择支持句 ID", "保留缺口；给出相关性评分"],
         ["解析原句、chunk 和引文", "核对数值与来源角色等窄规则"],
         ["answer_components / gaps", "relevance_score / rewrite_hint"],
         ["达到问题类型阈值 → generate", "否则有预算 → rewrite；耗尽 → 尽力生成"]],
        ["generate · 生成与补写", ["问题、绑定要点、原句", "修复轮附带指定问题项"],
         ["逐要点生成带引用的 claim", "只替换被指出的修复项"],
         ["拒绝未知要点 / 错误来源", "保留原句；恢复遗漏的数值与方法细节"],
         ["answer / citations / answer_claims", "evidence_status / binding issues"],
         ["生成后进入 check", "覆盖标签不等于医学正确"]],
        ["check · 图内检查", ["原问题、提纲、答案", "所选研究与原文"],
         ["核查支持、完整性与证据边界", "指出问题并选择定向修复项"],
         ["检查必需数值存在等窄规则", "保留不支持推断的拒绝"],
         ["faithful / faithfulness_issues", "repair_component_ids"],
         ["通过 → 保存；否则有预算 → 修复", "预算耗尽 → 保留问题后保存"]],
    ],
    "en": [
        ["grade / bind components", ["Original question / matched studies", "Sentence IDs / source passages"],
         ["Build components / choose sentence IDs", "Retain gaps / grade relevance"],
         ["Resolve quotes, chunks and citations", "Narrow numeric / source-role checks"],
         ["answer_components / gaps", "relevance_score / rewrite_hint"],
         ["Type threshold met → generate", "Else rewrite if budget; at cap → best effort"]],
        ["generate / targeted repair", ["Question / bound components / quotes", "Repair issues for a repair round"],
         ["Generate claims with component citations", "Replace identified repair components"],
         ["Reject unknown components / sources", "Retain quotes / recover omitted details"],
         ["answer / citations / answer_claims", "evidence_status / binding issues"],
         ["Proceed to check", "Coverage labels do not establish correctness"]],
        ["check / internal review", ["Question / outline / answer", "Selected studies / original passages"],
         ["Review support, completeness and limits", "Report issues / choose repair targets"],
         ["Narrow checks of required numeric presence", "Retain rejected unsupported inferences"],
         ["faithful / faithfulness_issues", "repair_component_ids"],
         ["Pass → persist; else repair within budget", "At the cap → persist with retained issues"]],
    ],
}


def render_details(language):
    zh = language == "zh"
    f = Figure("关键节点内部：模型判断与程序规则各做什么" if zh else "Inside key nodes: model judgments and program rules",
               "当前实现的职责图 · 绑定证明原句位置，不能证明语义正确" if zh else
               "Responsibilities in current code / exact binding establishes location, not semantic correctness", 1050)
    headings = ["输入", "模型处理", "程序处理", "输出", "分支 / 边界"] if zh else ["Input", "Model processing", "Program processing", "Output", "Branch / limits"]
    for i, content in enumerate(DETAILS[language]):
        x = 50+i*515
        f.rect(x, 178, 485, 774)
        f.text(x+20, 226, [content[0]], 27, INK, "bold")
        for j, lines in enumerate(content[1:]):
            y = 270+j*132
            color = [MUTED, BLUE, MUTED, GREEN, GOLD][j]
            f.rect(x+16, y, 453, 115, color, ["#f5f6f3", "#edf5fa", "#f5f6f3", "#edf5ef", "#fcf3e5"][j])
            f.text(x+32, y+30, [headings[j]], 18, color, "bold")
            f.text(x+32, y+64, lines, 19)
    f.text(50, 1005, ["规则是有限的保护与恢复机制；一次节点执行可以包含多次模型调用。独立 Audit 不在这条修复链中。" if zh else
                      "Rules provide narrow protection/recovery. A node may make multiple calls. Independent Audit is outside this repair chain."], 21, MUTED)
    f.save(f"node-logic-{language}")


def read_trace():
    frames = [json.loads(line) for line in (ROOT / RECORD).read_text(encoding="utf-8").split("\n") if line.strip()]
    steps, counts, open_nodes = [], Counter(), {}
    for row in frames:
        event, stamp = row["event"], row.get("received_at")
        name = event.get("node")
        if event["event"] == "node_start":
            counts[name] += 1
            step = {"node": name, "occurrence": counts[name], "started_at": stamp, "execution": "incomplete", "data": {}}
            steps.append(step)
            open_nodes[name] = step
        elif event["event"] == "node_end" and name in open_nodes:
            step = open_nodes.pop(name)
            step.update(execution="completed", data=event.get("data") or {}, elapsed_ms=stamp-step["started_at"])
    final = next(row["event"]["data"] for row in reversed(frames) if row["event"]["event"] == "done")
    export = json.loads((ROOT / "data/demo/conversations/v08-evidence-limits.json").read_text(encoding="utf-8"))
    question = next(t["question"] for t in export["conversation"]["turns"] if t["id"] == "v08-evidence-limits-turn-3")
    return {"question": question, "steps": steps, "final": {k: final[k] for k in ("answer", "faithful", "regen_count", "iterations", "faithfulness_issues")}}


def render_trace(trace, language):
    zh = language == "zh"
    f = Figure("一次真实执行：三轮生成，仍带遗漏结束" if zh else "An actual execution: three drafts, an omission remains",
               "保存的医学案例 · 只画实际事件，不补造隐藏节点或中间状态" if zh else
               "Saved medical case / observed events only; no invented hidden nodes or intermediate state", 1270)
    f.text(50, 180, ["节点与接收事件之间的耗时" if zh else "Nodes / event-receipt durations"], 23, INK, "bold")
    for i, step in enumerate(trace["steps"]):
        x, y = 50, 215+i*78
        issue = step["node"] == "check" and step["data"].get("faithful") is False
        color = GOLD if issue else BLUE if step["node"] == "generate" else MUTED
        if i:
            f.path(f"M345,{y-14} L345,{y}")
        f.rect(x, y, 600, 64, color, "#fcf3e5" if issue else "#ffffff")
        f.text(x+16, y+27, [f"{i+1:02d}  {step['node']}  #{step['occurrence']}"], 23, color, "bold")
        label = "已执行 · 发现问题" if issue and zh else "Executed / issues found" if issue else "已执行" if zh else "Executed"
        if step["execution"] != "completed":
            label = step["execution"]
        duration = f"{step['elapsed_ms']/1000:.2f}s" if "elapsed_ms" in step else "not recorded"
        f.text(x+16, y+52, [f"{label}  /  {duration}"], 17, MUTED)
    f.rect(695, 215, 855, 235)
    f.text(720, 253, ["原始问题（保持原文）" if zh else "Original question / unchanged"], 24, INK, "bold")
    f.text(720, 300, textwrap.wrap(trace["question"], 64), 23)
    f.rect(695, 478, 855, 285, GOLD, "#fcf3e5")
    f.text(720, 518, ["最后一次 check 仍报告遗漏" if zh else "The last check still reports an omission"], 25, GOLD, "bold")
    checks = [s for s in trace["steps"] if s["node"] == "check"]
    f.text(720, 558, ["faithful: " + " → ".join(str(s["data"].get("faithful")).lower() for s in checks)], 23, GOLD)
    reason = checks[-1]["data"]["issues"].split(" C2:")[0]
    f.text(720, 605, textwrap.wrap(reason, 79), 19)
    f.rect(695, 792, 855, 145, MUTED, "#f1f3f0")
    f.text(720, 831, ["最终返回字段（与中间草稿分开）" if zh else "Final returned fields / separate from drafts"], 24, INK, "bold")
    final = trace["final"]
    f.text(720, 876, [f"faithful = {str(final['faithful']).lower()} / regen_count = {final['regen_count']} / iterations = {final['iterations']}",
                      "最后观察到：check → append_history" if zh else "Last observed transition: check → append_history"], 21)
    f.rect(695, 965, 855, 190, MUTED)
    f.text(720, 1007, ["未保存的内容" if zh else "Not recorded"], 24, INK, "bold")
    f.text(720, 1050, ["完整节点输入、内部提示、当时提纲与各次完整草稿。" if zh else "Full node inputs, prompts, outlines and successive full drafts.",
                       "事件完成 ≠ 判断通过；自检通过 ≠ 回答可靠。" if zh else "Execution completion ≠ passing judgment ≠ reliable answer.",
                       "这次图内检查不是答案之后单独运行的 Audit。" if zh else "Internal check is separate from a later answer Audit."], 21, MUTED)
    f.text(50, 1210, ["耗时含调度 / 传输；原始事件未输出计数和摘要辅助节点。" if zh else
                      "Durations include scheduling / transport; original events omit counter/summary helpers.",
                      "来源：v08-evidence-limits-turn-3-events.jsonl。演示案例不是独立可靠性测试集。" if zh else
                      "Source: v08-evidence-limits-turn-3-events.jsonl. This demo is not an independent reliability test set."], 20, MUTED)
    f.save(f"execution-{language}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data, trace = build_catalogue(ROOT), read_trace()
    data["record"] = {"path": RECORD, "sha256": hashlib.sha256((ROOT / RECORD).read_bytes()).hexdigest(),
                      "observed_nodes": [{k: s[k] for k in ("node", "occurrence", "execution")} for s in trace["steps"]]}
    for language in ("zh", "en"):
        render_graph(data, language)
        render_details(language)
        render_trace(trace, language)
    (OUT / "source-records.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Documentation: 6 SVGs; {len(data['nodes'])} graph nodes / {len(trace['steps'])} observed steps; no model calls")


if __name__ == "__main__":
    main()
