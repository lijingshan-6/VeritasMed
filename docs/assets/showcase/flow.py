"""Draw the "how a question becomes a checkable answer" diagram, light and dark.

    python docs/assets/showcase/flow.py     # writes flow-light.svg and flow-dark.svg here

Plain SVG with literal colours (it is shown through <img>, so currentColor cannot inherit).
Colours follow the VeritasMed logo: dark ink and teal; teal marks the evidence link.
"""
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
W, H = 1000, 676
SANS = "Inter, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
SERIF = "Georgia, 'Times New Roman', serif"
THEMES = {
    "light": dict(ink="#17323B", sub="#4E5F66", muted="#7A878C", line="#C7D1D4", card="#FFFFFF", soft="#F3F6F6",
                  teal="#246F80", teal_soft="#DCEEF1", good="#2E7D4F", warn="#B26A12", gray="#7A878C"),
    "dark": dict(ink="#F4F5F1", sub="#C2CBCE", muted="#8E9A9F", line="#33434A", card="#141D24", soft="#1A252D",
                 teal="#8CC5D0", teal_soft="#1F3940", good="#6CC08F", warn="#E2A04D", gray="#9AA5AA"),
}


def text(x, y, s, size=12.5, fill="ink", weight=400, anchor="start", family=SANS, style=""):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{{{fill}}}" text-anchor="{anchor}"{style}>{escape(s)}</text>')


def lines(x, y, rows, size=12.5, fill="sub", gap=17, **kw):
    return "".join(text(x, y + i * gap, r, size, fill, **kw) for i, r in enumerate(rows))


def box(x, y, w, h, stroke="line", fill="card", sw=1.2, rx=10):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{{{fill}}}" stroke="{{{stroke}}}" stroke-width="{sw}"/>'


def arrow(x1, y1, x2, y2, color="muted", sw=1.4, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{{{color}}}" stroke-width="{sw}"{d} '
            f'marker-end="url(#head-{color})"/>')


def chip(x, y, label, color, w):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="24" rx="12" fill="{{card}}" stroke="{{{color}}}" stroke-width="1.2"/>'
            f'<circle cx="{x + 13}" cy="{y + 12}" r="4" fill="{{{color}}}"/>' + text(x + 23, y + 16.5, label, 12, "ink"))


def draw() -> str:
    bx = [24, 278, 532, 786]          # four steps, 190 wide, 64 apart
    by, bw, bh = 96, 190, 112
    steps = [
        ("1", "Understand", ["Follow-ups resolved from", "earlier turns: context,", "never evidence"], "line"),
        ("2", "Retrieve", ["BGE-M3 dense + sparse,", "fused and reranked; the", "named paper first"], "line"),
        ("3", "Bind evidence", ["Each part of the question", "→ exact sentence IDs.", "Nothing found → a gap"], "teal"),
        ("4", "Write and check", ["Plain words, conclusion", "first; reviewed for", "support and scope"], "line"),
    ]
    o = []
    # Entry: the question comes in from the top of step 1.
    o.append(text(bx[0], 34, "Your question", 13, "ink", 600))
    o.append(arrow(bx[0] + 95, 44, bx[0] + 95, by - 3))
    for (n, title, body, stroke), x in zip(steps, bx):
        o.append(box(x, by, bw, bh, stroke, sw=2 if stroke == "teal" else 1.2))
        o.append(text(x + 16, by + 27, f"{n}  {title}", 14, "teal" if stroke == "teal" else "ink", 650))
        o.append(lines(x + 16, by + 52, body))
    for (x, label) in [(bx[0], "query"), (bx[1], "passages"), (bx[2], "sentences")]:
        o.append(arrow(x + bw + 4, by + bh / 2, x + bw + 60, by + bh / 2))
        o.append(text(x + bw + 32, by + bh / 2 - 8, label, 11.5, "muted", anchor="middle"))
    # Bounded retries, drawn as arcs over the steps they repeat.
    o.append(f'<path d="M {bx[2] + 70} {by - 2} C {bx[2] + 40} 40, {bx[1] + 150} 40, {bx[1] + 120} {by - 4}" fill="none" '
             f'stroke="{{muted}}" stroke-width="1.3" stroke-dasharray="4 4" marker-end="url(#head-muted)"/>')
    o.append(text((bx[1] + bx[2] + bw) / 2, 42, "weak evidence → search again (≤2)", 11.5, "muted", anchor="middle"))
    o.append(f'<path d="M {bx[3] + 140} {by - 2} C {bx[3] + 140} 46, {bx[3] + 50} 46, {bx[3] + 50} {by - 4}" fill="none" '
             f'stroke="{{muted}}" stroke-width="1.3" stroke-dasharray="4 4" marker-end="url(#head-muted)"/>')
    o.append(text(bx[3] + 95, 42, "unsupported → repair (≤2)", 11.5, "muted", anchor="middle"))
    # The literature index under the retriever.
    ly = 246
    o.append(box(bx[1], ly, bw, 50, "line", "soft", rx=8))
    o.append(text(bx[1] + 16, ly + 21, "Literature index", 13, "ink", 600))
    o.append(text(bx[1] + 16, ly + 39, "Qdrant · abstract passages", 12, "sub"))
    o.append(arrow(bx[1] + 70, by + bh + 3, bx[1] + 70, ly - 3))
    o.append(arrow(bx[1] + 120, ly - 3, bx[1] + 120, by + bh + 3))
    o.append(text(bx[1] + 64, by + bh + 25, "search", 11.5, "muted", anchor="end"))
    o.append(text(bx[1] + 126, by + bh + 25, "passages", 11.5, "muted"))

    # The mechanism: a claim in the answer is bound to one source sentence.
    cy, ch = 336, 150
    src_x, src_w = 24, 446
    ans_x, ans_w = 532, 444
    o.append(arrow(bx[3] + 95, by + bh + 3, bx[3] + 95, cy - 3))
    o.append(text(bx[3] + 101, cy - 12, "answer", 11.5, "muted"))
    o.append(box(ans_x, cy, ans_w, ch))
    o.append(text(ans_x + 18, cy + 26, "CITED ANSWER", 11, "muted", 600))
    o.append(text(ans_x + 18, cy + 54, "Severe hypoglycemia: glargine 0.8%,", 15, "ink", family=SERIF))
    o.append(text(ans_x + 18, cy + 76, "glimepiride 1.3%, liraglutide 0.5%", 15, "ink", family=SERIF))
    o.append(f'<rect x="{ans_x + 276}" y="{cy + 62}" width="22" height="19" rx="5" fill="{{teal_soft}}" stroke="{{teal}}"/>')
    o.append(text(ans_x + 287, cy + 76, "1", 12, "teal", 700, anchor="middle"))
    o.append(text(ans_x + 18, cy + 110, "Five-year mortality: not in the sources", 15, "sub", family=SERIF, style=' font-style="italic"'))
    o.append(f'<rect x="{ans_x + 18}" y="{cy + 120}" width="96" height="20" rx="10" fill="none" stroke="{{warn}}"/>')
    o.append(text(ans_x + 66, cy + 134, "reported gap", 11, "warn", 600, anchor="middle"))

    o.append(box(src_x, cy, src_w, ch))
    o.append(text(src_x + 18, cy + 26, "SOURCE SENTENCE · PMC11567630 · RESULTS", 11, "muted", 600))
    o.append(f'<rect x="{src_x + 14}" y="{cy + 38}" width="{src_w - 28}" height="74" rx="6" fill="{{teal_soft}}"/>')
    o.append(f'<rect x="{src_x + 14}" y="{cy + 38}" width="3" height="74" fill="{{teal}}"/>')
    o.append(lines(src_x + 28, cy + 60, ["“While participants were taking their assigned",
                                          "medications, severe hypoglycemia occurred in",
                                          "10 (0.8%), 16 (1.3%), 6 (0.5%) and 4 (0.3%) …”"], 14, "ink", gap=20, family=SERIF))
    o.append(text(src_x + 18, cy + 134, "Shown beside the claim; quoted exactly, located once.", 12, "sub"))
    # The binding itself: from the citation down into the gap between lines, then across to the source.
    cx, ly2 = ans_x + 287, cy + 92
    o.append(f'<path d="M {cx} {cy + 81} L {cx} {ly2 - 6} Q {cx} {ly2} {cx - 6} {ly2} L {src_x + src_w + 4} {ly2}" '
             f'fill="none" stroke="{{teal}}" stroke-width="2" marker-end="url(#head-teal)"/>')
    o.append(text((src_x + src_w + ans_x) / 2, ly2 - 8, "bound to", 11.5, "teal", 600, anchor="middle"))

    # The audit, run on demand against the same passages.
    ay, ah = 540, 112
    o.append(arrow(ans_x + ans_w / 2, cy + ch + 3, ans_x + ans_w / 2, ay - 3))
    o.append(text(ans_x + ans_w / 2 + 8, cy + ch + 33, "one click", 11.5, "muted"))
    o.append(arrow(src_x + src_w / 2, cy + ch + 3, src_x + src_w / 2, ay - 3))
    o.append(text(src_x + src_w / 2 + 8, cy + ch + 33, "same passages", 11.5, "muted"))
    o.append(box(24, ay, 952, ah))
    o.append(text(44, ay + 30, "Claim audit", 14, "ink", 650))
    o.append(lines(44, ay + 54, ["Every claim is checked against", "exact source quotes. The answer", "itself is never rewritten."], 12.5, "sub"))
    o.append(chip(330, ay + 22, "Supported", "good", 104))
    o.append(chip(446, ay + 22, "Not supported", "warn", 128))
    o.append(chip(586, ay + 22, "Quote not found", "gray", 140))
    o.append(lines(330, ay + 74, ["Unchecked text stays visible; nothing is hidden or averaged."], 12.5, "sub"))
    o.append(f'<rect x="752" y="{ay + 22}" width="204" height="70" rx="8" fill="none" stroke="{{warn}}" stroke-dasharray="3 3"/>')
    o.append(lines(766, ay + 44, ["⚠ Flags “no difference” claims", "resting on a non-significant", "result"], 12, "warn", gap=16))

    heads = "".join(
        f'<marker id="head-{c}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{{{c}}}"/></marker>' for c in ("muted", "teal"))
    label = ("How VeritasMed turns a question into a checkable answer: understand, retrieve, bind each part of the "
             "question to exact source sentences or report a gap, write and self-check with bounded retries; "
             "each claim is linked to its sentence, and a one-click audit checks every claim against the same passages.")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{escape(label)}"><title>{escape(label)}</title><defs>{heads}</defs>' + "".join(o) + "</svg>")


def main() -> None:
    template = draw()
    for name, colours in THEMES.items():
        svg = template
        for key, value in colours.items():
            svg = svg.replace("{" + key + "}", value)
        assert "{" not in svg, "unfilled colour slot"
        (HERE / f"flow-{name}.svg").write_text(svg + "\n", encoding="utf8")
        print("wrote", f"flow-{name}.svg")


if __name__ == "__main__":
    main()
