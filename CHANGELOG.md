# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-10-18

Changes since 0.1.0 (the dry-run release that only read temperatures).

### Added
- Phase 2: the temperature colour is written to the LEDs, plus `--sweep` (gradient preview) and
  `--show HEX` (hold one colour) for checking colours by eye; the four colour stops were approved
  on the owner's hardware.
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
