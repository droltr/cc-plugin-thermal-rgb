# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.2] - 2026-10-18

Documentation release; no behaviour changes.

### Added
- `docs/troubleshooting.md`: every log message with its cause and fix, LED and settings-page checklists.
- README: "what it does / does not do" summary, troubleshooting section; glossary in `docs/how-it-works.md`.

### Changed
- Hardware documentation lists the complete reference system (CPU, RAM modules, board and BIOS, GPU,
  other RGB devices) and clarifies that ENE is the RAM LED controller, not the memory brand.

## [0.2.1] - 2026-10-18

Documentation and repository release; no behaviour changes.

### Added
- `LICENSE` (GPL-3.0-or-later), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1),
  `SECURITY.md`, issue forms and a pull request template.

### Changed
- Maintainer notes, plans and machine-specific setup files are no longer tracked (kept locally, listed in
  `.gitignore`); the repository holds only code, tests, packaging and user-facing documentation.
- Documentation added under `docs/`: tested hardware and zone map, how it works, testing.
- README rewritten to match the code: requirements, installation, token setup, configuration
  reference, command-line tools and development workflow.
- License, author and project URLs added to `pyproject.toml` and `manifest.toml`.

## [0.2.0] - 2026-10-18

Changes since 0.1.0 (the dry-run release that only read temperatures).

### Added
- Phase 2: the temperature colour is written to the LEDs, plus `--sweep` (gradient preview) and
  `--show HEX` (hold one colour) for checking colours by eye; the four colour stops were approved
  on the reference system.
- Settings page (`ui/index.html`) to enter the CoolerControl access token from the plugin's page
  in CoolerControl. The plugin moves the token into `credentials.json` (mode 0600) and leaves `***`
  in `config.json`, so the page never shows it again. `install.sh` ships `ui/` and keeps `credentials.json`.

### Changed
- `write_leds` now defaults to `true` (was `false` in 0.1.0); set it to `false` for dry-run mode.
  `install.sh` creates new configs with it enabled.
- `.private/` and `.agent-sessions/` are git-ignored.

## [0.1.0] - 2026-10-09

### Added
- Phase 0: `setup/openrgb-server.service` and install/uninstall scripts for a headless
  OpenRGB 1.0 (Flatpak) SDK server started at login.
- Phase 1: `thermal_rgb` package: CoolerControl REST temperature reader, OpenRGB zone
  resolution (device, zone, location), OKLCH colour gradient (50 °C blue → 60 yellow → 70 orange →
  80 red), EMA smoothing, `--list` mode, LED writes behind `write_leds` (off).
- Plugin packaging (`manifest.toml`, `run.sh`, `install.sh`, `uninstall.sh`), 55 unit tests
  (98 % coverage), GitHub Actions CI (ruff, pytest, coverage ≥ 80 %).
- Project skeleton and plan (`docs/PLAN.md`).
