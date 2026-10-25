import re

TIME_RE = re.compile(r"^\d+(?:\.\d+)?(?:ms|s|m|h)$", re.I)
LEVEL = {"AND": 2, "NAND": 2, "XOR": 1, "XNOR": 1, "OR": 0, "NOR": 0}


def tokenize(text):
    # Zamiana symboli matematycznych i programistycznych na standardowe operatory
    text = text.replace("∧", " AND ").replace("∨", " OR ").replace("¬", " NOT ")
    text = text.replace("&&", " AND ").replace("||", " OR ")
    text = text.replace("&", " AND ").replace("|", " OR ")
    text = text.replace("~", " NOT ").replace("!", " NOT ")
    text = text.replace("^", " XOR ")
    toks = re.findall(r"\d+(?:\.\d+)?(?:ms|s|m|h)\b|[A-Za-z_]\w*|[(),]", text)
    return [
        t.lower() if TIME_RE.fullmatch(t)
        else t.upper() if t.upper() in LEVEL or t.upper() == "NOT"
        else t
        for t in toks
    ]


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

        if cur in ("AND", "OR", "XOR"):
            node = (cur, [x for c in node[1] for x in (c[1] if c[0] == cur else [c])])
        return node

    def or_():
        return chain(0, xor_)

    def xor_():
        return chain(1, and_)

    def and_():
        return chain(2, not_)

    def not_():
        t = take()
        if t == "NOT":
            return ("NOT", [not_()])

        if t == "(":
            e = or_()
            if take() != ")":
                raise ValueError("missing ')'")
            return e

        if TIME_RE.fullmatch(t):
            raise ValueError(f"time '{t}' can only be an argument of a function")

        if re.fullmatch(r"[A-Za-z_]\w*", t) and t not in LEVEL:
            if peek() == "(":
                take()
                args = []
                if peek() != ")":
                    while True:
                        if peek() and TIME_RE.fullmatch(peek()):
                            args.append(("TIME", take()))
                        else:
                            args.append(or_())
                        if peek() == ",":
                            take()
                            continue
                        break
                if take() != ")":
                    raise ValueError(f"missing ')' in call {t}")
                return ("CALL", t, args)
            return ("VAR", t)

        raise ValueError(f"unexpected token: {t}")

    tree = or_()
    if pos[0] != len(toks):
        raise ValueError(f"extra tokens: {toks[pos[0]:]}")
    return tree
