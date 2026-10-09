# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Phase 0: `setup/openrgb-server.service` and install/uninstall scripts for a headless
  OpenRGB 1.0 (Flatpak) SDK server started at login.
- Phase 1: `thermal_rgb` package: CoolerControl REST temperature reader, OpenRGB zone
  resolution (device, zone, location), OKLCH colour gradient (50 °C blue → 60 yellow → 70 orange →
  80 red), EMA smoothing, `--list` mode, LED writes behind `write_leds` (off).
- Plugin packaging (`manifest.toml`, `run.sh`, `install.sh`, `uninstall.sh`), 55 unit tests
  (98 % coverage), GitHub Actions CI (ruff, pytest, coverage ≥ 80 %).
- Project skeleton and plan (`docs/PLAN.md`).
