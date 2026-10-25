#!/usr/bin/env python3
import sys
import tomllib
from pathlib import Path

# Zapewnienie poprawnego działania importów niezależnie od katalogu wywołania
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from diagrams.block import block_diagram
from diagrams.logic import logic_diagram
from diagrams.logo import generate_logo
from utils.config import GENERAL, LOGO, PROJECT_DIR
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

    # 1. Schemat blokowy i logiczny (schemdraw)
    jobs = [("block_diagram", block_diagram(eqs, desc)), ("logic_diagram", logic_diagram(eqs))]
    if GENERAL.get("separate", False):
        jobs += [(name, logic_diagram([(name, tree)])) for name, tree in eqs]

    for fname, drawing in jobs:
        path = out / f"{fname}.{GENERAL['fmt']}"
        drawing.save(str(path), dpi=GENERAL["dpi"])
        print(f"OK {path}")

    # 2. Schemat LOGO! FBD i raporty (matplotlib)
    if LOGO.get("enabled", True):
        created_logo = generate_logo(
            eqs,
            desc,
            out,
            fmt=GENERAL.get("fmt", "png"),
            dpi=GENERAL.get("dpi", 200),
            plan=LOGO.get("plan", True),
            sentences=LOGO.get("sentences", True),
        )
        for path in created_logo:
            print(f"OK {path}")


if __name__ == "__main__":
    main()
