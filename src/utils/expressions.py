import re

LEVEL = {"AND": 1, "NAND": 1, "OR": 0, "NOR": 0, "XOR": 0, "XNOR": 0}

def tokenize(text):
    toks = re.findall(r"[A-Za-z_]\w*|\S", text)
    return [t.upper() if t.upper() in LEVEL or t.upper() == "NOT" else t for t in toks]

def parse(expr):
    toks, pos = tokenize(expr), [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        if pos[0] >= len(toks):
            raise ValueError("incomplete expression")
        pos[0] += 1
        return toks[pos[0] - 1]

    def chain(level, sub):
        node, cur = sub(), None
        while LEVEL.get(peek()) == level:
            op, rhs = take(), sub()
            if op == cur:
                node[1].append(rhs)
            else:
                node, cur = (op, [node, rhs]), op

        if cur in ("AND", "OR"):
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
                raise ValueError("missing ')'")
            return e

        if re.fullmatch(r"[A-Za-z_]\w*", t) and t not in LEVEL:
            return ("VAR", t)

        raise ValueError(f"unexpected token: {t}")

    tree = or_()
    if pos[0] != len(toks):
        raise ValueError(f"extra tokens: {toks[pos[0]:]}")
    return tree
