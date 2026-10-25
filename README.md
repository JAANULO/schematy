# Block and Logic Diagrams

Skrypt do generowania schematów blokowych, logicznych oraz schematów FBD (Siemens LOGO! Soft Comfort) z równań boolowskich, przygotowany na zajęcia _Podstawy informatyki przemysłowej – Zajęcia laboratoryjne_.

Z jednego zestawu równań program generuje:

- **`block_diagram.png`** – wejścia → bloki funkcyjne (AND, OR, NOT, RS, …) → wyjścia, wraz z opisami.
- **`logic_diagram.png`** – te same równania w postaci bramek logicznych (schemdraw).
- **`schemat_logo.png`** – schemat blokowy FBD odwzorowujący środowisko Siemens LOGO! Soft Comfort (symbole `&`, `≥1`, `=1`, numeracja bloków `B1..`, negacje na wejściach, linie przerywane dla sprzężeń zwrotnych).
- **`plan_klikania.md`** – instrukcja krok po kroku do wyklikania układu w LOGO! Soft Comfort.
- **`zdania_logiczne.md`** – zdania logiczne po polsku (do sprawozdania).
- opcjonalnie **`Q1.png`, `Q2.png`, …** – osobny schemat logiczny dla każdego wyjścia (`separate = true`).

## Wymagania

- Python 3.11+
- [`schemdraw`](https://schemdraw.readthedocs.io/) i `matplotlib`

```sh
pip install -r requirements.txt
```

## Uruchomienie

```sh
python src/main.py
```
lub
```sh
python -m src.main
```

Równania pobierane są z `equations.toml`, a ustawienia z `config.toml`. Ścieżki w konfiguracji są rozwiązywane względem głównego katalogu projektu.

## Plik z równaniami (`equations.toml`)

```toml
# Opisy wejść i wyjść
[descriptions]
I1 = "lewy przycisk"
I2 = "prawy przycisk"
Q1 = "siłownik prasy"

# Równania: wyjście = "wyrażenie"
[equations]
Q1 = "I1 ∧ I2 ∧ ¬I3"
Q2 = "RS(I1 & ~Q1, I2)"
```

### Obsługiwane operatory i symbole

Możesz używać zarówno zapisu słownego, jak i symboli matematycznych oraz programistycznych:
- **AND**: `AND`, `&`, `&&`, `∧`
- **OR**: `OR`, `|`, `||`, `∨`
- **NOT**: `NOT`, `~`, `!`, `¬`
- **XOR**: `XOR`, `^`
- **Inne**: `NAND`, `NOR`, `XNOR`
- Nawiasy `( )` do grupowania podwyrażeń.

**Priorytet operatorów:** `NOT` > `AND`/`NAND` > `XOR`/`XNOR` > `OR`/`NOR`.

### Bloki specjalne / PLC (funkcje czasowe i bistabilne)

- `RS(S, R)` – przekaźnik zatrzaskowy (Latching relay)
- `IMP(Trg[, S, R])` – przekaźnik impulsowy (Pulse relay)
- `TON(Trg, 5s)` – opóźnienie załączenia (On-delay)
- `TOF(Trg[, R], 30s)` – opóźnienie wyłączenia (Off-delay)
- `TONOFF(Trg, 5s)` – opóźnienie zał./wył. (On/Off-delay)
- `TP(Trg, 2s)` – przekaźnik czasowy impulsowy (Wiping relay)

Czasy podaje się w formatach: `ms`, `s`, `m`, `h` (np. `500ms`, `5s`, `2m`).

## Ustawienia (`config.toml`)

```toml
[general]
file = "equations.toml" # ścieżka do pliku z równaniami
fmt = "png"             # format wyjściowy: png | svg | pdf
dpi = 200               # rozdzielczość
separate = false        # osobny rysunek logiczny dla każdego wyjścia

[logic]                 # parametry schematu logicznego (schemdraw)
gap = 3.2
row = 1.3
lead = 0.7
fontsize = 12

[block]                 # parametry schematu blokowego (schemdraw)
colw = 4.8
io_w = 3.6
gate_w = 1.5
gate_h = 0.8
vsep = 0.4
wrap = 19
fontsize = 10
io_color = "#e8e8e8"
gate_color = "white"

[logo]                  # parametry generatora LOGO! Soft Comfort
enabled = true          # czy generować schemat LOGO! FBD i raporty
plan = true             # czy generować plan_klikania.md
sentences = true        # czy generować zdania_logiczne.md
```

## Struktura projektu

```
config.toml          Ustawienia programu
requirements.txt     Zależności Pythona
equations.toml       Równania i opisy wejść/wyjść
out/                 Wygenerowane schematy i raporty
src/
  main.py            Punkt wejściowy programu
  diagrams/
    block.py         Schemat blokowy (schemdraw)
    logic.py         Schemat logiczny bramek (schemdraw)
    logo.py          Schemat FBD Siemens LOGO! i raporty (matplotlib)
  utils/
    config.py        Wczytywanie i walidacja config.toml
    expressions.py   Tokenizer i parser wyrażeń boolowskich
    layout.py        Algorytmy routingu połączeń i wyliczania wysokości
```
