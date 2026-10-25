import tomllib
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]

with open(PROJECT_DIR / "config.toml", "rb") as f:
    CFG = tomllib.load(f)

GENERAL = CFG.get("general", {"file": "equations.toml", "fmt": "png", "dpi": 200, "separate": False})
LOGIC = CFG.get("logic", {"gap": 3.2, "row": 1.3, "lead": 0.7, "fontsize": 12})
BLOCK = CFG.get("block", {
    "colw": 4.8, "io_w": 3.6, "gate_w": 1.5, "gate_h": 0.8,
    "vsep": 0.4, "wrap": 19, "fontsize": 10,
    "io_color": "#e8e8e8", "gate_color": "white"
})
LOGO = CFG.get("logo", {"enabled": True, "plan": True, "sentences": True})
