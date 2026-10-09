# Project guidelines

General workspace rules apply: English-only code and docs, Conventional Commits,
branches `main` / `develop` / `feature/*` / `fix/*`, tests before docs (≥ 80 %
coverage target), type hints, ruff (100-char lines), soft-delete into `.deleted/`.

## Project-specific

- Python modules use snake_case (importable); scripts and docs use kebab-case.
- Lighting ownership: board, fans and DRAM belong to `cc-plugin-thermal-rgb`; the
  keyboard belongs to `cc-plugin-game-rgb`. Never write a device you do not own.
- Hardware safety: read-only probing first; every first write to a new device needs
  the owner's explicit approval while watching the hardware.
- Never commit tokens, serial numbers or unredacted device logs.
- Install only under `/var/lib/coolercontrol/plugins/<id>/` or user space; never `/usr`.
