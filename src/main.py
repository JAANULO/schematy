#!/usr/bin/env python3
import sys
import tomllib

from diagrams.block import block_diagram
from diagrams.logic import logic_diagram
from utils.config import GENERAL, PROJECT_DIR
from utils.expressions import parse

def main():
    try:
        with open(PROJECT_DIR / GENERAL["file"], "rb") as f:
            data = tomllib.load(f)
        eqs = [(name, parse(expr)) for name, expr in data.get("equations", {}).items()]
    except (OSError, ValueError) as ex:
        sys.exit(f"ERROR: {ex}")

    if not eqs:
        sys.exit(f"ERROR: no equations in the [equations] section of {GENERAL['file']}")
    desc = data.get("descriptions", {})

    out = PROJECT_DIR / "out"
    out.mkdir(exist_ok=True)

    jobs = [("block_diagram", block_diagram(eqs, desc)), ("logic_diagram", logic_diagram(eqs))]
    if GENERAL["separate"]:
        jobs += [(name, logic_diagram([(name, tree)])) for name, tree in eqs]

    for fname, drawing in jobs:
        path = out / f"{fname}.{GENERAL['fmt']}"
        drawing.save(str(path), dpi=GENERAL["dpi"])
        print(f"OK {path}")

if __name__ == "__main__":
    main()
