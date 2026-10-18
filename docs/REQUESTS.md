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
| 13 | Start the thermal plugin | 🔄 | phases 0–2 done (PRs #7, #8); GPU source next |
| 14 | Plan settings pages for the plugins | ✅ planned | `docs/SETTINGS-UI-PLAN.md` |
| 15 | Sweep preview: hard transitions, flashes back to blue, yellow looked orange-brown, no green seen | 🔄 | cause 1: running plugin fought the preview; cause 2: LED green channel weaker than a monitor. Next: show colours one by one with the plugin stopped, then a correction table |
| 16 | Show colours one at a time first; temperature test only after the colours are OK | ✅ | 2026-10-09 with the plugin stopped: red, green, blue, white all clean; pure `#ffff00` leans green (normal for WS2812); our stops approved: `#2060ff` "ice blue", `#ffd000` clean yellow, `#ff7a00` orange, `#ff0000` red, clearly distinct from orange. No correction table needed. |
| 17 | Temperature test after the colour check | ✅ | 17:40 heat test: blue → yellow → orange → red at the right thresholds, red for 81 s, back to blue; transitions fast (CPU heats ~7 °C/s) |
| 18 | LED transition speed | ✅ decided | keep the fast response (smoothing τ = 3 s) |
| 19 | LEDs must also react when the GPU heats up | ⏳ planned | owner chose: **all LEDs show whichever of CPU or GPU is hotter** (the LCD already shows which one). Each source is first mapped onto its own stops, then compared. GPU default stops 55 / 65 / 75 / 83 °C, same colours. CPU-only stays the default when no GPU source is configured |
| 20 | Where do these settings live? | ✅ answered | CoolerControl → Plugins → thermal-rgb page (LEDs, sources, themes); game-rgb page (game profiles); coolerdash page (LCD) |
| 21 | Reach the GPU LEDs | ⏳ | project `RgbLighting/gpu-rgb-rtx5080` |
