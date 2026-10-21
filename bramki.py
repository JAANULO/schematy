#!/usr/bin/env python3
"""Generator schematu blokowego i schematu logicznego z równań boolowskich.

Z jednego pliku z równaniami powstają dwa rysunki:
    schemat_blokowy.png   - wejścia -> bloki funkcyjne -> wyjścia (jak szkic z zajęń)
    schemat_logiczny.png  - bramki AND/OR/NOT (wszystkie wyjścia na jednym rysunku)

Użycie:
    python bramki.py                              # domyślnie: rownania.txt -> ./out
    python bramki.py -f in.txt -o outdir
    python bramki.py "Q1 = I1 & I2 & ~I3" --fmt svg
    python bramki.py --osobno                     # dodatkowo Q1.png, Q2.png, ...

Format pliku (kolejność dowolna, # = komentarz):
    I1: lewy przycisk obsługi         <- opis wejścia/wyjścia (opcjonalny)
    Q1 = I1 & I2 & ~I3                <- równanie

Operatory:  AND: & && ∧ AND   OR: | || ∨ OR   NOT: ~ ! ¬ NOT   plus nawiasy ().
Priorytet: NOT > AND > OR.
"""
import argparse
import os
import re
import sys
import textwrap
from pathlib import Path

import schemdraw
from schemdraw import elements as elm
from schemdraw import flow, logic

# ----- stałe konfiguracyjne -----
DEFAULT_INPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rownania.txt")
DEFAULT_OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

# ======================= PARSER =======================
def tokenize(text):
    text = (text.replace("∧", "&").replace("∨", "|").replace("¬", "~").replace("&&", "&").replace("||", "|").replace("!", "~"))
    text = re.sub(r"\bAND\b", "&", text, flags=re.I)
    text = re.sub(r"\bOR\b", "|", text, flags=re.I)
    text = re.sub(r"\bNOT\b", "~", text, flags=re.I)
    return re.findall(r"[A-Za-z_]\w*|[&|~()]", text)

def parse(expr):
    """Zwraca drzewo: ('VAR', nazwa) albo (op, [dzieci]), op in AND/OR/NOT."""
    toks, pos = tokenize(expr), [0]
    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None
    def take():
        if pos[0] >= len(toks):
            raise ValueError("niepełne wyrażenie")
        pos[0] += 1
        return toks[pos[0] - 1]
    def nary(op, items):
        flat = []
        for it in items:
            flat.extend(it[1] if it[0] == op else [it])
        return flat[0] if len(flat) == 1 else (op, flat)
    def or_():
        items = [and_()]
        while peek() == "|":
            take()
            items.append(and_())
        return nary("OR", items)
    def and_():
        items = [not_()]
        while peek() == "&":
            take()
            items.append(not_())
        return nary("AND", items)
    def not_():
        t = take()
        if t == "~":
            return ("NOT", [not_()])
        if t == "(":
            e = or_()
            if take() != ")":
                raise ValueError("brak ')'")
            return e
        if re.fullmatch(r"[A-Za-z_]\w*", t):
            return ("VAR", t)
        raise ValueError(f"nieoczekiwany token: {t}")
    tree = or_()
    if pos[0] != len(toks):
        raise ValueError(f"nadmiarowe tokeny: {toks[pos[0]:]}")
    return tree

def parse_lines(lines):
    eqs, desc = [], {}
    for raw in lines:
        line = raw.split("#")[0].strip()
        if not line:
            continue
        m = re.match(r"^(\w+)\s*:\s*(.+)$", line)
        if m and "=" not in line:
            desc[m.group(1)] = m.group(2).strip()
        elif "=" in line:
            name, expr = (s.strip() for s in line.split("=", 1))
            eqs.append((name, parse(expr)))
        else:
            raise ValueError(f"nie rozumiem linii: '{line}'")
    return eqs, desc

# ======================= SCHEMAT LOGICZNY =======================
GAP, ROW, LEAD = 3.2, 1.3, 0.7
def channel_x(p, pin, i, n, min_gap, base):
    k = i if p[1] >= pin[1] else n - 1 - i
    return max(p[0] + min_gap, pin[0] - base - 0.25 * k)
def height(n):
    return 0 if n[0] == "VAR" else 1 + max(height(c) for c in n[1])
def draw_gates(d, node, state):
    op, arg = node
    if op == "VAR":
        y = -state["row"] * ROW
        state["row"] += 1
        d += elm.Line().at((-LEAD, y)).to((0, y)).label(arg, "left")
        return (0, y)
    pts = [draw_gates(d, c, state) for c in arg]
    x, y = height(node) * GAP, sum(p[1] for p in pts) / len(pts)
    gate = {"AND": logic.And, "OR": logic.Or}.get(op, logic.Not)
    g = gate(inputs=len(arg)) if op != "NOT" else gate()
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
    d.config(fontsize=12, unit=1)
    state = {"row": 0}
    for name, tree in eqs:
        out = draw_gates(d, tree, state)
        d += elm.Line().at(out).right(1.2).label(name, "right")
        state["row"] += 0.8
    return d

# ======================= SCHEMAT BLOKOWY =======================
COLW, IO_W, GATE_W, GATE_H, VSEP, WRAP = 4.8, 3.6, 1.5, 0.8, 0.4, 19
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
        put_box(d, 0, y, IO_W, h, text, "#e8e8e8")
        return (IO_W / 2, y)
    pts = [draw_blocks(d, c, state, desc) for c in arg]
    x, y = height(node) * COLW, sum(p[1] for p in pts) / len(pts)
    put_box(d, x, y, GATE_W, GATE_H, op, "white")
    left = x - GATE_W / 2
    for i, p in enumerate(pts):
        xm = channel_x(p, (left, y), i, len(pts), 0.25, 0.5)
        d += elm.Line().at(p).to((xm, p[1]))
        d += elm.Line().at((xm, p[1])).to((xm, y))
        d += elm.Arrow().at((xm, y)).to((left, y))
    return (x + GATE_W / 2, y)
def block_diagram(eqs, desc):
    d = schemdraw.Drawing()
    d.config(fontsize=10)
    state = {"y": 0.0}
    for name, tree in eqs:
        p = draw_blocks(d, tree, state, desc)
        text, h = io_text(name, desc)
        x = (height(tree) + 1) * COLW
        put_box(d, x, p[1], IO_W, h, text, "#e8e8e8")
        d += elm.Arrow().at(p).to((x - IO_W / 2, p[1]))
        state["y"] -= 0.7
    return d

# ======================= CLI =======================
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lines", nargs="*", help='równania / opisy, np. "Q1 = I1 & ~I2"')
    ap.add_argument("-f", "--file", default=DEFAULT_INPUT,
                    help="plik z równaniami i opisami (domyślnie 'rownania.txt')")
    ap.add_argument("-o", "--outdir", default=DEFAULT_OUTDIR,
                    help="katalog wyjściowy (domyślnie ./out)")
    ap.add_argument("--fmt", default="png", choices=["png", "svg", "pdf"]) 
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--osobno", action="store_true", help="dodatkowo osobny schemat logiczny dla każdego wyjścia")
    a = ap.parse_args()
    # ---- wczytywanie danych ----
    lines = []
    input_path = Path(a.file)
    if input_path.is_file():
        lines += input_path.read_text(encoding="utf-8").splitlines()
    else:
        ap.error(f"Nie znaleziono pliku wejściowego: {a.file}")

    # dodatkowe równania podane bezpośrednio w CLI
    lines += list(a.lines)

    try:
        eqs, desc = parse_lines(lines)
    except ValueError as ex:
        sys.exit(f"BŁĄD: {ex}")
    if not eqs:
        ap.error("podaj równania lub plik (-f)")
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    jobs = [("schemat_blokowy", block_diagram(eqs, desc)), ("schemat_logiczny", logic_diagram(eqs))]
    if a.osobno:
        jobs += [(name, logic_diagram([(name, tree)])) for name, tree in eqs]
    for fname, drawing in jobs:
        path = out / f"{fname}.{a.fmt}"
        drawing.save(str(path), dpi=a.dpi)
        print(f"OK {path}")

if __name__ == "__main__":
    main()
