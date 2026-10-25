# TODO

## Zadania po refaktoryzacji

- [x] **Przywrócenie obsługi symboli logicznych w lekserze**
  - Obsługa znaków: `∧`, `∨`, `¬` (notacja laboratoryjna) oraz `&`, `|`, `~`, `&&`, `||`, `!`, `^` (notacja programistyczna).
  - Normalizacja tokenów w `src/utils/expressions.py` przed parsowaniem wyrażeń.

- [x] **Integracja generatora LOGO! FBD z nową architekturą**
  - Przeniesienie generatora z `tem.py` do modułu `src/diagrams/logo.py`.
  - Dodanie sekcji `[logo]` do `config.toml` oraz wpięcie generowania do `src/main.py`.
  - Generowanie `schemat_logo.png`, `plan_klikania.md` i `zdania_logiczne.md`.
