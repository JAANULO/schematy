#!/usr/bin/env python3
"""Generator schematu blokowego i schematu logicznego z równań boolowskich.

Z równań w equations.toml (ustawienia: config.toml) powstają dwa rysunki:
    schemat_blokowy.png   - wejścia -> bloki funkcyjne -> wyjścia (jak szkic z zajęń)
    schemat_logiczny.png  - bramki logiczne (wszystkie wyjścia na jednym rysunku)

Użycie:
    python bramki.py                              # domyślnie: equations.toml -> ./out
    python bramki.py -f inne.toml -o outdir
    python bramki.py "Q4 = I1 XOR I2" --fmt svg   # dodatkowe równanie
    python bramki.py --osobno                     # dodatkowo Q1.png, Q2.png, ...

Dodatkowe linie z CLI:
    I1: lewy przycisk obsługi         <- opis wejścia/wyjścia
    Q1 = I1 AND I2 AND NOT I3         <- równanie

Operatory:  NOT AND NAND OR NOR XOR XNOR (również & && ∧, | || ∨, ~ ! ¬) plus nawiasy ().
Priorytet: NOT > AND/NAND > OR/NOR/XOR/XNOR.
"""
import argparse
import os
import re
import sys
import textwrap
import tomllib
from pathlib import Path

import schemdraw
from schemdraw import elements as elm
from schemdraw import flow, logic

# ----- konfiguracja (config.toml obok skryptu) -----
SCRIPT_DIR = Path(os.path.abspath(__file__)).parent
with open(SCRIPT_DIR / "config.toml", "rb") as f:
    CFG = tomllib.load(f)
CLI, LOG, BLK = CFG["cli"], CFG["logiczny"], CFG["blokowy"]

# ======================= PARSER =======================
LEVEL = {"AND": 1, "NAND": 1, "OR": 0, "NOR": 0, "XOR": 0, "XNOR": 0}  # priorytet operatorów 2-arg.
SYMBOLS = (("&&", "AND"), ("||", "OR"), ("∧", "AND"), ("∨", "OR"), ("¬", "NOT"), ("&", "AND"), ("|", "OR"), ("!", "NOT"), ("~", "NOT"))
def tokenize(text):
    for sym, word in SYMBOLS:
        text = text.replace(sym, f" {word} ")
    toks = re.findall(r"[A-Za-z_]\w*|[()]", text)
    return [t.upper() if t.upper() in LEVEL or t.upper() == "NOT" else t for t in toks]

def parse(expr):
    """Zwraca drzewo: ('VAR', nazwa) albo (op, [dzieci]), op in NOT lub klucze LEVEL."""
    toks, pos = tokenize(expr), [0]
    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None
    def take():
        if pos[0] >= len(toks):
            raise ValueError("niepełne wyrażenie")
        pos[0] += 1
        return toks[pos[0] - 1]
    def chain(level, sub):
        # A op B op C -> jedna bramka n-wejściowa; zmiana operatora zaczyna nową bramkę
        node, cur = sub(), None
        while LEVEL.get(peek()) == level:
            op, rhs = take(), sub()
            if op == cur:
                node[1].append(rhs)
            else:
                node, cur = (op, [node, rhs]), op
        if cur in ("AND", "OR"):  # łączne: (A AND B) AND C -> AND3
            node = (cur, [x for c in node[1] for x in (c[1] if c[0] == cur else [c])])
        return node
    def or_():
        return chain(0, and_)
    def and_():
        return chain(1, not_)
    def not_():
        t = take()
        if t == "NOT":
            return ("NOT", [not_()])
        if t == "(":
            e = or_()
            if take() != ")":
                raise ValueError("brak ')'")
            return e
        if re.fullmatch(r"[A-Za-z_]\w*", t) and t not in LEVEL:
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
GAP, ROW, LEAD = LOG["gap"], LOG["row"], LOG["lead"]
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
    gate = {"AND": logic.And, "NAND": logic.Nand, "OR": logic.Or, "NOR": logic.Nor,
            "XOR": logic.Xor, "XNOR": logic.Xnor}.get(op, logic.Not)
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
    d.config(fontsize=LOG["fontsize"], unit=1)
    state = {"row": 0}
    for name, tree in eqs:
        out = draw_gates(d, tree, state)
        d += elm.Line().at(out).right(1.2).label(name, "right")
        state["row"] += 0.8
    return d

# ======================= SCHEMAT BLOKOWY =======================
COLW, IO_W, GATE_W, GATE_H, VSEP, WRAP = (BLK[k] for k in ("colw", "io_w", "gate_w", "gate_h", "vsep", "wrap"))
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
        put_box(d, 0, y, IO_W, h, text, BLK["kolor_io"])
        return (IO_W / 2, y)
    pts = [draw_blocks(d, c, state, desc) for c in arg]
    x, y = height(node) * COLW, sum(p[1] for p in pts) / len(pts)
    put_box(d, x, y, GATE_W, GATE_H, op, BLK["kolor_bramki"])
    left = x - GATE_W / 2
    for i, p in enumerate(pts):
        xm = channel_x(p, (left, y), i, len(pts), 0.25, 0.5)
        d += elm.Line().at(p).to((xm, p[1]))
        d += elm.Line().at((xm, p[1])).to((xm, y))
        d += elm.Arrow().at((xm, y)).to((left, y))
    return (x + GATE_W / 2, y)
def block_diagram(eqs, desc):
    d = schemdraw.Drawing()
    d.config(fontsize=BLK["fontsize"])
    state = {"y": 0.0}
    for name, tree in eqs:
        p = draw_blocks(d, tree, state, desc)
        text, h = io_text(name, desc)
        x = (height(tree) + 1) * COLW
        put_box(d, x, p[1], IO_W, h, text, BLK["kolor_io"])
        d += elm.Arrow().at(p).to((x - IO_W / 2, p[1]))
        state["y"] -= 0.7
    return d

# ======================= CLI =======================
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lines", nargs="*", help='równania / opisy, np. "Q1 = I1 & ~I2"')
    ap.add_argument("-f", "--file", default=str(SCRIPT_DIR / CLI["plik"]),
                    help=f"plik z równaniami i opisami (domyślnie '{CLI['plik']}')")
    ap.add_argument("-o", "--outdir", default=str(SCRIPT_DIR / CLI["outdir"]),
                    help=f"katalog wyjściowy (domyślnie {CLI['outdir']})")
    ap.add_argument("--fmt", default=CLI["fmt"], choices=["png", "svg", "pdf"])
    ap.add_argument("--dpi", type=int, default=CLI["dpi"])
    ap.add_argument("--osobno", action=argparse.BooleanOptionalAction, default=CLI["osobno"],
                    help="dodatkowo osobny schemat logiczny dla każdego wyjścia")
    a = ap.parse_args()
    # ---- wczytywanie danych: plik z równaniami + dodatkowe linie z CLI ----
    input_path = Path(a.file)
    if not input_path.is_file():
        ap.error(f"Nie znaleziono pliku wejściowego: {a.file}")
    try:
        data = tomllib.loads(input_path.read_text(encoding="utf-8"))
        eqs = [(name, parse(expr)) for name, expr in data.get("rownania", {}).items()]
        desc = dict(data.get("opisy", {}))
        cli_eqs, cli_desc = parse_lines(a.lines)
    except ValueError as ex:  # tomllib.TOMLDecodeError też dziedziczy po ValueError
        sys.exit(f"BŁĄD: {ex}")
    eqs += cli_eqs
    desc.update(cli_desc)
    if not eqs:
        ap.error("podaj równania w pliku (-f, sekcja [rownania]) lub w CLI")
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
