import textwrap

import schemdraw
from schemdraw import elements as elm
from schemdraw import flow

from utils.config import BLOCK
from utils.layout import channel_x, height

COLW, IO_W, GATE_W, GATE_H, VSEP, WRAP = (BLOCK[k] for k in ("colw", "io_w", "gate_w", "gate_h", "vsep", "wrap"))

def io_text(name, desc):
    lines = [name] + (textwrap.wrap(desc[name], WRAP) if name in desc else [])
    return "\n".join(lines), 0.5 + 0.32 * len(lines)

def put_box(d, x, y, w, h, text, fill):
    d += (flow.Box(w=w, h=h).at((x, y)).anchor("center").fill(fill).label(text, "center"))

def draw_blocks(d, node, state, desc):
    op, arg = node

    if op == "VAR":
        text, h = io_text(arg, desc)
        y = state["y"] - h / 2
        state["y"] -= h + VSEP
        put_box(d, 0, y, IO_W, h, text, BLOCK["io_color"])
        return (IO_W / 2, y)

    pts = [draw_blocks(d, c, state, desc) for c in arg]
    x, y = height(node) * COLW, sum(p[1] for p in pts) / len(pts)
    put_box(d, x, y, GATE_W, GATE_H, op, BLOCK["gate_color"])

    left = x - GATE_W / 2
    for i, p in enumerate(pts):
        xm = channel_x(p, (left, y), i, len(pts), 0.25, 0.5)
        d += elm.Line().at(p).to((xm, p[1]))
        d += elm.Line().at((xm, p[1])).to((xm, y))
        d += elm.Arrow().at((xm, y)).to((left, y))

    return (x + GATE_W / 2, y)

def block_diagram(eqs, desc):
    d = schemdraw.Drawing()
    d.config(fontsize=BLOCK["fontsize"])
    state = {"y": 0.0}

    for name, tree in eqs:
        p = draw_blocks(d, tree, state, desc)

        text, h = io_text(name, desc)
        x = (height(tree) + 1) * COLW
        put_box(d, x, p[1], IO_W, h, text, BLOCK["io_color"])
        d += elm.Arrow().at(p).to((x - IO_W / 2, p[1]))

        state["y"] -= 0.7

    return d
