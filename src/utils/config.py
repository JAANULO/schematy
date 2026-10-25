import tomllib
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]

with open(PROJECT_DIR / "config.toml", "rb") as f:
    CFG = tomllib.load(f)

GENERAL, LOGIC, BLOCK = CFG["general"], CFG["logic"], CFG["block"]
