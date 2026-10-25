import os
import re
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

# Limity wejść bloków w Siemens LOGO!
MAX_IN = {"AND": 4, "OR": 4, "XOR": 2}
SYMBOL = {"AND": "&", "OR": "≥1", "XOR": "=1", "NOT": "NOT"}
PREC = {"OR": 1, "XOR": 2, "AND": 3, "NOT": 4}
OUT_RE = re.compile(r"Q\d+")
SRC_RE = re.compile(r"I\d+|Q\d+|HI|LO")
TIME_RE = re.compile(r"\d+(?:\.\d+)?(?:ms|s|m|h)")

FUNCS = {
    "RS":     dict(pins=["S", "R"], need=2, timed=False,
                   pl="Przekaźnik zatrzaskowy", en="Latching relay"),
    "IMP":    dict(pins=["Trg", "S", "R"], need=1, timed=False,
                   pl="Przekaźnik impulsowy", en="Pulse relay"),
    "TON":    dict(pins=["Trg"], need=1, timed=True,
                   pl="Opóźnienie załączenia", en="On-delay"),
    "TOF":    dict(pins=["Trg", "R"], need=1, timed=True,
                   pl="Opóźnienie wyłączenia", en="Off-delay"),
    "TONOFF": dict(pins=["Trg"], need=1, timed=True,
                   pl="Opóźnienie załączenia/wyłączenia", en="On/Off-delay"),
    "TP":     dict(pins=["Trg"], need=1, timed=True,
                   pl="Przekaźnik czasowy impulsowy", en="Wiping relay"),
}


class Node:
    def __init__(self, uid, kind, label, ins=None, spec=None, time=None):
        self.uid, self.kind, self.label = uid, kind, label   # CONN, GATE, FUNC, OUT, DUMMY
        self.ins = ins or []        # [(źródło, zanegowane)] lub None
        self.spec, self.time = spec, time
        self.level, self.pos, self.bid = 0, 0, None
        self.x = self.y = self.w = self.h = 0.0
        self.lines = [label]


class Net:
    def __init__(self, eqs):
        self.nodes, self.cache, self.resolved, self.busy = [], {}, {}, set()
        names = [n for n, _ in eqs]
        for n in names:
            if re.fullmatch(r"I\d+|HI|LO", n):
                raise ValueError(f"'{n}' to wejście - nie można go przypisać")
            if names.count(n) > 1:
                raise ValueError(f"nazwa '{n}' ma więcej niż jedno równanie")

        has_q = any(OUT_RE.fullmatch(n) for n in names)
        self.alias = {n: t for n, t in eqs if has_q and not OUT_RE.fullmatch(n)}
        outputs = [eq for eq in eqs if not has_q or OUT_RE.fullmatch(eq[0])]

        for name, tree in outputs:
            n, neg = self.lit(tree)
            if neg:
                n = self.not_block(n)
            self.new("OUT", name, [(n, False)])

    def new(self, kind, label, ins=None, spec=None, time=None):
        n = Node(len(self.nodes), kind, label, ins, spec, time)
        self.nodes.append(n)
        return n

    def conn(self, name):
        key = ("C", name)
        if key not in self.cache:
            self.cache[key] = self.new("CONN", name)
        return self.cache[key]

    def not_block(self, n):
        key = ("NOT", n.uid)
        if key not in self.cache:
            self.cache[key] = self.new("GATE", "NOT", [(n, False)])
        return self.cache[key]

    def mk(self, op, lits):
        key = (op, tuple(sorted((n.uid, g) for n, g in lits)))
        if key not in self.cache:
            self.cache[key] = self.new("GATE", op, list(lits))
        return self.cache[key]

    def var(self, name):
        if name in self.alias:
            if name in self.resolved:
                return self.resolved[name]
            if name in self.busy:
                raise ValueError(f"pętla w definicji '{name}' (sprzężenie rób przez wyjście Q lub RS)")
            self.busy.add(name)
            r = self.lit(self.alias[name])
            self.busy.discard(name)
            self.resolved[name] = r
            return r
        if SRC_RE.fullmatch(name) or True:  # akceptuj wejścia
            return self.conn(name), False

    def lit(self, t):
        op = t[0]
        if op == "VAR":
            return self.var(t[1])
        if op == "NOT":
            n, neg = self.lit(t[1][0])
            return n, not neg
        if op in MAX_IN:
            return self.gate(op, [self.lit(c) for c in t[1]])
        if op == "NAND":
            gate_node, _ = self.gate("AND", [self.lit(c) for c in t[1]])
            return gate_node, True
        if op == "NOR":
            gate_node, _ = self.gate("OR", [self.lit(c) for c in t[1]])
            return gate_node, True
        return self.call(t)

    def gate(self, op, lits):
        if op != "XOR":
            uniq = []
            for l in lits:
                if all((l[0].uid, l[1]) != (u[0].uid, u[1]) for u in uniq):
                    uniq.append(l)
            lits = uniq
        if len(lits) == 1:
            return lits[0]
        mx = MAX_IN.get(op, 4)
        while len(lits) > mx:
            if op == "XOR":
                lits = [(self.mk(op, lits[:2]), False)] + lits[2:]
            else:
                chunks = [lits[i:i + mx] for i in range(0, len(lits), mx)]
                lits = [(self.mk(op, c), False) if len(c) > 1 else c[0] for c in chunks]
        return self.mk(op, lits), False

    def call(self, t):
        name, args = t[1], t[2]
        spec = FUNCS.get(name)
        if not spec:
            raise ValueError(f"nieznana funkcja '{name}' (dostępne: {', '.join(FUNCS)})")
        sig = [a for a in args if a[0] != "TIME"]
        tm = [a[1] for a in args if a[0] == "TIME"]
        if len(tm) != (1 if spec["timed"] else 0):
            raise ValueError(f"{name}: " + ("wymaga jednego czasu, np. 5s" if spec["timed"] else "nie przyjmuje czasu"))
        if not spec["need"] <= len(sig) <= len(spec["pins"]):
            raise ValueError(f"{name}: oczekiwano {spec['need']}-{len(spec['pins'])} wejść ({', '.join(spec['pins'])})")
        ins = []
        for a in sig:
            n, neg = self.lit(a)
            ins.append((self.not_block(n) if neg else n, False))
        ins += [None] * (len(spec["pins"]) - len(ins))
        key = (name, tuple(e[0].uid if e else None for e in ins), tuple(tm))
        if key not in self.cache:
            self.cache[key] = self.new("FUNC", name, ins, spec, tm[0] if tm else None)
        return self.cache[key], False


VSEP, PITCH = 0.4, 0.6


def pin_y(n, i):
    if n.kind in ("CONN", "OUT", "DUMMY") or (n.kind == "GATE" and len(n.ins) == 1):
        return n.y
    if n.kind == "GATE":
        return n.y + n.h / 2 - (i + 0.5) * n.h / len(n.ins)
    return n.y + n.h / 2 - 0.55 - (i + 0.5) * PITCH


def measure(n, desc):
    if n.kind == "DUMMY":
        n.w, n.h = 0.0, 0.3
    elif n.kind in ("CONN", "OUT"):
        n.lines = [n.label] + (textwrap.wrap(desc[n.label], 18) if n.label in desc else [])
        n.w = max(1.2, 0.13 * max(len(s) for s in n.lines) + 0.4)
        n.h = 0.6 + 0.26 * (len(n.lines) - 1)
    elif n.kind == "GATE":
        n.w, n.h = 1.0, max(0.9, 0.55 * len(n.ins) + 0.3)
    else:
        n.w = max(2.0, 0.15 * len(n.spec["en"]) + 0.4)
        n.h = 0.55 + PITCH * len(n.spec["pins"]) + (0.4 if n.spec["timed"] else 0)


def layout(net, desc):
    real = net.nodes
    for n in real:
        n.level = 0 if n.kind == "CONN" else 1 + max((e[0].level for e in n.ins if e), default=0)
    maxl = max((n.level for n in real if n.kind != "OUT"), default=0)
    for n in real:
        if n.kind == "OUT":
            n.level = maxl + 1

    chains, edges, dummies = {}, [], []

    def at(s, lvl):
        if lvl == s.level:
            return s
        c = chains.setdefault(s.uid, {})
        if lvl not in c:
            prev = at(s, lvl - 1)
            dn = Node(10000 + len(dummies), "DUMMY", "")
            dn.level = lvl
            c[lvl] = dn
            dummies.append(dn)
            edges.append((prev, dn, 0, False))
        return c[lvl]

    for d in real:
        for i, e in enumerate(d.ins):
            if e:
                edges.append((at(e[0], d.level - 1), d, i, e[1]))
    allnodes = real + dummies
    for n in allnodes:
        measure(n, desc)
    cols = {}
    for n in allnodes:
        cols.setdefault(n.level, []).append(n)
    top = max(cols)
    preds = {n.uid: [a for a, d, i, g in edges if d is n] for n in allnodes}
    succs = {n.uid: [d for a, d, i, g in edges if a is n] for n in allnodes}

    def reindex(col_level):
        for i, n in enumerate(cols[col_level]):
            n.pos = i

    for col_level in cols:
        reindex(col_level)

    def sweep(col_level, nb):
        cols[col_level].sort(
            key=lambda n: (sum(m.pos for m in nb[n.uid]) / len(nb[n.uid])) if nb[n.uid] else n.pos
        )
        reindex(col_level)

    for _ in range(6):
        for col_level in range(1, top + 1):
            sweep(col_level, preds)
        for col_level in range(top - 1, -1, -1):
            sweep(col_level, succs)

    for col_level in cols:
        y = 0.0
        for n in cols[col_level]:
            n.y = y - n.h / 2
            y -= n.h + VSEP

    def settle(col_level, nb):
        col = cols[col_level]
        want = [(sum(m.y for m in nb[n.uid]) / len(nb[n.uid])) if nb[n.uid] else n.y for n in col]
        prev = None
        for n, w in zip(col, want):
            n.y = w if prev is None else min(w, prev.y - prev.h / 2 - n.h / 2 - VSEP)
            prev = n
        shift = sum(w - n.y for n, w in zip(col, want)) / len(col)
        for n in col:
            n.y += shift

    for col_level in range(1, top + 1):
        settle(col_level, preds)
    for col_level in range(top - 1, -1, -1):
        settle(col_level, succs)
    for col_level in range(1, top + 1):
        settle(col_level, preds)

    colw = {col_level: max(n.w for n in cols[col_level]) for col_level in cols}
    left, right, x = {}, {}, 0.0
    for col_level in range(top + 1):
        ngrp = len({a.uid for a, d, i, g in edges if a.level == col_level})
        left[col_level], right[col_level] = x, x + colw[col_level]
        for n in cols[col_level]:
            n.x = x + colw[col_level] / 2
            if n.kind != "DUMMY":
                n.w = colw[col_level]
        x += colw[col_level] + 0.6 + 0.3 * ngrp

    k = 0
    for n in sorted((n for n in real if n.kind in ("GATE", "FUNC")), key=lambda n: (n.level, n.uid)):
        k += 1
        n.bid = k
    return allnodes, edges, left, right, top


def draw(net, desc, path, dpi):
    allnodes, edges, left, right, top = layout(net, desc)
    scale = 0.5
    xs0 = min(n.x - n.w / 2 for n in allnodes) - 0.4
    xs1 = max(n.x + n.w / 2 for n in allnodes) + 0.4
    ys0 = min(n.y - n.h / 2 for n in allnodes) - 0.6
    ys1 = max(n.y + n.h / 2 for n in allnodes) + 0.5
    fig = plt.figure(figsize=(max(4, (xs1 - xs0) * scale), max(3, (ys1 - ys0) * scale)))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(xs0, xs1)
    ax.set_ylim(ys0, ys1)
    ax.axis("off")

    chan = {}
    for col_level in range(top):
        srcs = []
        for a, d, i, g in edges:
            if a.level == col_level and a not in srcs:
                srcs.append(a)

        def key(src_node):
            ds = [pin_y(d, i) for a2, d, i, g in edges if a2 is src_node]
            down = sum(ds) / len(ds) < src_node.y
            return (0, src_node.y) if down else (1, -src_node.y)

        srcs.sort(key=key)
        x0, x1 = right[col_level] + 0.25, left[col_level + 1] - 0.25
        for j, src_node in enumerate(srcs):
            chan[(col_level, src_node.uid)] = x0 + (j + 1) * (x1 - x0) / (len(srcs) + 1)

    fan = {}
    for a, d, i, g in edges:
        fan[a.uid] = fan.get(a.uid, 0) + 1
    for a, d, i, neg in edges:
        xs, ys = a.x + a.w / 2, a.y
        xd, yd = d.x - d.w / 2, pin_y(d, i)
        xm = chan[(a.level, a.uid)]
        xe = xd - (0.2 if neg else 0)
        ax.plot([xs, xm, xm, xe], [ys, ys, yd, yd], color="#222", lw=1.1, zorder=1,
                solid_joinstyle="miter")
        if neg:
            ax.add_patch(Circle((xd - 0.1, yd), 0.1, fc="white", ec="#222", lw=1.1, zorder=3))
        if fan[a.uid] > 1:
            ax.plot([xm], [ys], marker="o", ms=3, color="#222", zorder=2)

    has_fb = False
    for n in allnodes:
        if n.kind == "DUMMY":
            continue
        l, b = n.x - n.w / 2, n.y - n.h / 2
        if n.kind in ("CONN", "OUT"):
            fb = n.kind == "CONN" and n.label.startswith("Q")
            has_fb |= fb
            ax.add_patch(FancyBboxPatch(
                (l, b), n.w, n.h, boxstyle="round,pad=0,rounding_size=0.12", zorder=2,
                fc="#e8e8e8" if n.kind == "CONN" else "#cfe8cf", ec="#444",
                ls="--" if fb else "-", lw=1.2))
            top_y = n.y + (len(n.lines) - 1) * 0.13
            for k, s in enumerate(n.lines):
                ax.text(n.x, top_y - k * 0.26, s, ha="center", va="center", zorder=4,
                        fontsize=9 if k == 0 else 7, fontweight="bold" if k == 0 else "normal")
        else:
            ax.add_patch(Rectangle((l, b), n.w, n.h, fc="white", ec="#222", lw=1.4, zorder=2))
            ax.text(l, b + n.h + 0.05, f"B{n.bid}", fontsize=7, color="#777", va="bottom")
            if n.kind == "GATE":
                ax.text(n.x, n.y, SYMBOL.get(n.label, n.label), ha="center", va="center", zorder=4,
                        fontsize=8 if n.label == "NOT" else 12, fontweight="bold")
            else:
                ax.text(n.x, b + n.h - 0.27, n.spec["en"], ha="center", va="center",
                        fontsize=8, fontweight="bold", zorder=4)
                for i, p in enumerate(n.spec["pins"]):
                    ax.text(l + 0.08, pin_y(n, i), p, fontsize=8, va="center", zorder=4)
                if n.time:
                    ax.text(n.x, b + 0.22, f"T = {n.time}", fontsize=8, ha="center",
                            va="center", zorder=4)
    if has_fb:
        ax.text(xs0 + 0.1, ys0 + 0.2, "linia kreskowana = odczyt stanu wyjścia Q (sprzężenie zwrotne)",
                fontsize=7, color="#555")
    fig.savefig(path, dpi=dpi)
    plt.close(fig)


def ref(s, neg=False):
    r = s.label if s.kind == "CONN" else f"B{s.bid}"
    return f"NIE {r}" if neg else r


def plan_text(net, desc):
    nodes = net.nodes
    out = ["# Plan klikania — LOGO! Soft Comfort", "",
           "Numery B1, B2… są tylko do orientacji; Soft Comfort nada własne.",
           "Negacja bramki = zaneguj **wejście** bloku (opcja w menu prawego przycisku — "
           "sprawdź w programie). Przy blokach RS/timerach i wyjściach użyto osobnego bloku NOT.", "",
           "## Wejścia i wyjścia", "", "| Nazwa | Rola | Opis |", "|---|---|---|"]
    names = sorted({n.label for n in nodes if n.kind in ("CONN", "OUT")},
                   key=lambda s: (s[0] != "I", s[0] != "Q", int(re.sub(r"\D", "", s) or 0), s))
    for nm in names:
        role = "wejście" if nm.startswith("I") else "wyjście" if nm.startswith("Q") else "stała"
        out.append(f"| {nm} | {role} | {desc.get(nm, '')} |")
    out += ["", "## Bloki (buduj od lewej do prawej)", ""]
    for n in sorted((n for n in nodes if n.kind in ("GATE", "FUNC")), key=lambda n: n.bid):
        parts = []
        if n.kind == "GATE":
            head = f"**B{n.bid}** — {n.label} ({SYMBOL.get(n.label, n.label)})"
            for i, (s, g) in enumerate(n.ins, 1):
                parts.append(f"wej. {i} ← {ref(s)}" + (" (zanegowane)" if g else ""))
        else:
            head = f"**B{n.bid}** — {n.spec['pl']} / {n.spec['en']}"
            for p, e in zip(n.spec["pins"], n.ins):
                parts.append(f"{p} ← {ref(e[0]) if e else '(niepodłączone)'}")
            if n.time:
                parts.append(f"Par: T = {n.time}")
        out.append(f"1. {head}: " + " · ".join(parts))
    out += ["", "## Wyjścia", ""]
    out += [f"- {n.label} ← {ref(n.ins[0][0])}" for n in nodes if n.kind == "OUT"]
    return "\n".join(out) + "\n"


def sentence(t, desc, prec=0):
    op = t[0]
    if op == "VAR":
        return f"{t[1]} ({desc[t[1]]})" if t[1] in desc else t[1]
    if op == "NOT":
        return "NIE " + sentence(t[1][0], desc, PREC["NOT"])
    if op == "CALL":
        pins = FUNCS[t[1]]["pins"] if t[1] in FUNCS else []
        sig = [a for a in t[2] if a[0] != "TIME"]
        tm = [a[1] for a in t[2] if a[0] == "TIME"]
        parts = [f"{p}: {sentence(a, desc)}" for p, a in zip(pins, sig)] + [f"T = {x}" for x in tm]
        return f"blok {t[1]}[" + "; ".join(parts) + "]"
    word = {"AND": " ORAZ ", "OR": " LUB ", "XOR": " ALBO (XOR) "}.get(op, f" {op} ")
    s = word.join(sentence(c, desc, PREC.get(op, 0)) for c in t[1])
    return f"({s})" if PREC.get(op, 0) < prec else s


def sentences_text(eqs, desc):
    out = ["# Zdania logiczne", ""]
    for name, tree in eqs:
        label = f"{name} ({desc[name]})" if name in desc else name
        verb = "jest aktywne (=1), gdy" if not OUT_RE.fullmatch(name) else "=1, gdy"
        out.append(f"- {label} {verb} {sentence(tree, desc)}.")
    return "\n".join(out) + "\n"


def generate_logo(eqs, desc, out_dir, fmt="png", dpi=200, plan=True, sentences=True):
    net = Net(eqs)
    out_path = Path(out_dir) / f"schemat_logo.{fmt}"
    draw(net, desc, str(out_path), dpi)
    created = [out_path]

    if plan:
        plan_path = Path(out_dir) / "plan_klikania.md"
        plan_path.write_text(plan_text(net, desc), encoding="utf-8")
        created.append(plan_path)

    if sentences:
        sent_path = Path(out_dir) / "zdania_logiczne.md"
        sent_path.write_text(sentences_text(eqs, desc), encoding="utf-8")
        created.append(sent_path)

    return created
