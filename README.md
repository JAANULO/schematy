# Block and Logic Diagrams

Script for generating block diagrams and logic/control diagrams from Boolean equations,
for the class *Fundamentals of Industrial Computer Science – Laboratory*.

From one set of equations it draws:

- **`block_diagram.png`** – inputs → function blocks (AND, OR, NOT, …) → outputs, with input/output descriptions
- **`logic_diagram.png`** – the same equations as logic gate symbols, all outputs in one drawing
- optionally **`Q1.png`, `Q2.png`, …** – a separate logic diagram for each output

## Requirements

- Python 3.11+ (uses the built-in `tomllib`)
- [`schemdraw`](https://schemdraw.readthedocs.io/) and `matplotlib`

```sh
pip install schemdraw matplotlib
```

On NixOS:

```sh
nix-shell -p "python3.withPackages(ps: [ps.schemdraw ps.matplotlib])"
```

## Usage

```sh
python src/main.py
```

The script takes no arguments: equations come from `equations.toml`, everything else from `config.toml`.
Diagrams are always written to `out/` in the project root (only the empty directory is kept in git).
The script can be run from any directory; relative paths in `config.toml` are resolved
against the project root.

## Equations file (`equations.toml`)

```toml
# Input/output descriptions (optional) - shown in the block diagram
[descriptions]
I1 = "left operator button"
I2 = "right operator button"
Q1 = "press actuator"

# Equations: output = "expression"
[equations]
Q1 = "I1 AND I2 AND NOT I3"
Q2 = "(I1 OR I2) NAND I3"
```

Equations are drawn in the order they appear in the file.

### Operators

`NOT`, `AND`, `NAND`, `OR`, `NOR`, `XOR`, `XNOR`. Parentheses `( )` group sub-expressions. Operator words are case-insensitive; no other symbols are accepted.

**Precedence:** `NOT` > `AND`/`NAND` > `OR`/`NOR`/`XOR`/`XNOR`.
For example, `A XOR B AND C OR D` means `(A XOR (B AND C)) OR D`.

**Multi-input gates:**

- A chain of the same operator becomes one gate with several inputs:
  `A NAND B NAND C` → one 3-input NAND.
- Parentheses with AND/OR are merged too, since the result is the same:
  `(A AND B) AND C` → one 3-input AND.
- Parentheses with other operators stay as separate gates:
  `(A NAND B) NAND C` → two NAND gates.
- A different operator starts a new gate: `A AND B NAND C` → `(A AND B) NAND C`.

Variable names are letters, digits and `_`, starting with a letter or `_` (e.g. `I1`, `Q2`, `start_btn`).

## Settings (`config.toml`)

```toml
[general]
file = "equations.toml" # relative path = relative to the project root
fmt = "png"             # png | svg | pdf
dpi = 200               # resolution (raster formats)
separate = false        # also a separate logic diagram for each output

[logic]                 # logic diagram layout
gap = 3.2               # horizontal spacing between gate levels
row = 1.3               # vertical spacing between inputs
lead = 0.7              # input wire length
fontsize = 12

[block]                 # block diagram layout
colw = 4.8              # column width
io_w = 3.6              # input/output block width
gate_w = 1.5            # function block width
gate_h = 0.8            # function block height
vsep = 0.4              # vertical spacing between input blocks
wrap = 19               # wrap descriptions after this many characters
fontsize = 10
io_color = "#e8e8e8"    # input/output block fill
gate_color = "white"    # function block fill
```

All keys are required.

## Project structure

```
config.toml          settings
equations.toml       input/output descriptions and equations
out/                 generated diagrams (contents ignored by git)
src/
  main.py            entry point: reads the equations, saves the diagrams
  diagrams/          one file per diagram type
    block.py         block diagram
    logic.py         logic diagram (gate symbols)
  utils/             shared code
    config.py        loads config.toml
    expressions.py   Boolean expression tokenizer and parser
    layout.py        layout helpers shared by both diagrams
```
