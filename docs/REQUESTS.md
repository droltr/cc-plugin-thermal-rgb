# Requests log

Status: ✅ done · 🔄 in progress · ⏳ planned · ❓ needs a decision.

## 2026-10-09

| # | Request | Status | Decision / where |
|---|---|---|---|
| 1 | LEDs change colour with temperature while the fans speed up | 🔄 | this project |
| 2 | Write it as a CoolerControl plugin if possible | ✅ | integration plugin, see `docs/PLAN.md` |
| 3 | Separate projects: thermal LEDs, game keyboard, mouse, GPU | ✅ | `cc-plugin-game-rgb`, `steelseries-rival5-rgb`, `gpu-rgb-rtx5080` |
| 4 | Private GitHub repositories, created together with the folders | ✅ | `droltr/cc-plugin-thermal-rgb` (private) |
| 5 | First theme: cold / warm / hot / very hot | 🔄 | colours computed (phase 1); LED writes in phase 2 |
| 6 | Colour stops: **50 °C blue, 60 °C yellow, 70 °C orange, 80 °C red**, smooth in-between shades that match human colour perception | ✅ decided | interpolate in OKLCH (perceptual); see `docs/PLAN.md` § Colour model |
| 7 | Temperature source: **CPU only** for now (GPU may be added later) | ✅ decided | CoolerControl `k10temp temp1` (Tctl) |
| 8 | **All LEDs, including both RAM modules, follow CPU temperature** | ✅ decided | zone map |
| 9 | Zones: rear fans JARGB 1 and JARGB 2 (separate); RAM ×2 ENE (separate); CPU block + CPU cooler fans + front on JARGB 3 | ✅ recorded | README |
| 10 | Later themes: heat wave moving rear → front; user colours rotating on the fans | ⏳ | phase 3 |
| 11 | Find out why OpenRGB "uninstalled itself" | ✅ | `docs/setup/openrgb.md` |
| 12 | OpenRGB 1.0 (Flatpak, Bazaar) installed by the owner: udev warning, new effects, mouse detected | ✅ | `docs/setup/openrgb.md` |
| 13 | Start the thermal plugin | 🔄 | phase 0 done (OpenRGB server), phase 1 done (v0.1.0, dry run) |
| 14 | Plan settings pages for the plugins | ✅ planned | `docs/SETTINGS-UI-PLAN.md` |
