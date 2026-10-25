import schemdraw
from schemdraw import elements as elm
from schemdraw import logic

from utils.config import LOGIC
from utils.layout import channel_x, height

GAP, ROW, LEAD = LOGIC["gap"], LOGIC["row"], LOGIC["lead"]
GATES = {"AND": logic.And, "NAND": logic.Nand, "OR": logic.Or, "NOR": logic.Nor, "XOR": logic.Xor, "XNOR": logic.Xnor}

def draw_gates(d, node, state):
    op, arg = node

    if op == "VAR":
        y = -state["row"] * ROW
        state["row"] += 1
        d += elm.Line().at((-LEAD, y)).to((0, y)).label(arg, "left")
        return (0, y)

    pts = [draw_gates(d, c, state) for c in arg]
    x, y = height(node) * GAP, sum(p[1] for p in pts) / len(pts)
    g = GATES[op](inputs=len(arg)) if op != "NOT" else logic.Not()
    d += g.at((x, y)).anchor("out")

    for i, p in enumerate(pts, 1):
        name = f"in{i}" if op != "NOT" else "in1"
        pin = g.absanchors.get(name) or g.absanchors["in"]
        xm = channel_x(p, pin, i - 1, len(pts), 0.3, 0.4)
        d += elm.Line().at(p).to((xm, p[1]))
        d += elm.Line().at((xm, p[1])).to((xm, pin[1]))
        d += elm.Line().at((xm, pin[1])).to(pin)

    return (x, y)

def logic_diagram(eqs):
    d = schemdraw.Drawing()
    d.config(fontsize=LOGIC["fontsize"], unit=1)
    state = {"row": 0}

    for name, tree in eqs:
        out = draw_gates(d, tree, state)
        d += elm.Line().at(out).right(1.2).label(name, "right")
        state["row"] += 0.8

    return d
