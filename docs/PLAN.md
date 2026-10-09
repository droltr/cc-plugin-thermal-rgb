# Plan — cc-plugin-thermal-rgb

Date: 2026-10-09. Status: approved for planning; implementation starts with phase 0.

## Goals

- LEDs reflect system temperature with clear colour bands. First theme: cold /
  warm / hot / very hot.
- CoolerControl provides the temperatures (same sensors as the fan curves). No second sensor reader.
- Runs as a CoolerControl integration plugin: started, stopped and logged by
  CoolerControl, with settings on its plugin page.
- Reversible install under `/var/lib/coolercontrol/plugins/thermal-rgb/`, nothing in `/usr`.

## Non-goals (for now)

- Per-game keyboard layouts (separate project: `cc-plugin-game-rgb`).
- Mouse and GPU LEDs (separate projects: `steelseries-rival5-rgb`, `gpu-rgb-rtx5080`).
- Writing an OpenRGB (Qt) plugin.

## Architecture

```
coolercontrold ──spawns──▶ thermal-rgb (Python, unprivileged cc-plugin-user)
                              │  reads   REST /status or /sse (token from config)
                              │  writes  OpenRGB SDK 127.0.0.1:6742 (openrgb-python, protocol v3)
                              ▼
                 theme engine: temp → per-zone colour frames → OpenRGB "direct" updates
```

- **Temperature source:** configurable list of CoolerControl sensors (device UID +
  temp name). The default is the hotter of CPU `k10temp temp1` (Tctl) and `GPU Temp`,
  as in the verified MysticLight setup. Smoothing with an EMA (exponential moving
  average) plus hysteresis between bands avoids flicker.
- **Themes** are pure functions `(temps, time, zone layout) → colours`, so they are
  easy to unit-test without hardware.
- **Zone map** (config): logical names → OpenRGB device/zone, e.g. `rear_1 =
  MSI/JARGB 1`, `rear_2 = MSI/JARGB 2`, `front = MSI/JARGB 3`, `ram_1 = ENE DRAM #0`,
  `ram_2 = ENE DRAM #1`. The order rear → front is used by the heat-wave theme.
- **Ownership:** while the plugin runs it owns the board and DRAM LEDs. It does not
  touch the keyboard (owned by `cc-plugin-game-rgb`). The OpenRGB GUI must stay
  closed, because it overrides Direct mode (lesson from MysticLight).

## Decisions (2026-10-09, owner)

- **Source:** CPU only, CoolerControl `k10temp temp1` (Tctl). GPU may be added later as an option.
- **All LEDs follow CPU temperature**, including both RAM modules.
- **Colour stops:** 50 °C blue · 60 °C yellow · 70 °C orange · 80 °C red. Below 50 °C hold
  blue; at or above 80 °C hold red.

## Colour model

Smooth, perceptually even transitions. Interpolating in RGB produces muddy, uneven
in-between shades (blue→yellow passes through grey). Interpolate in **OKLCH**
(the polar form of OKLab, designed so equal steps look equally different), then
convert to sRGB and clamp to the LED gamut.

| Stop | °C | Target (sRGB) | Meaning |
|---|---|---|---|
| cold | 50 | `#2060ff` blue | idle |
| warm | 60 | `#ffd000` yellow | light load |
| hot | 70 | `#ff7a00` orange | heavy load |
| very hot | 80 | `#ff0000` red | at the fan-max threshold |

- Hue moves the short way (blue → green-cyan → yellow → orange → red). Lightness and chroma
  are interpolated linearly in OKLCH.
- LED correction: the per-channel gamma and white balance of WS2812-type LEDs differ from a
  monitor. Phase 2 adds a per-zone correction table, tuned by eye with the owner.
- Smoothing: EMA (exponential moving average) on temperature, τ ≈ 3 s; colour updates
  only when ΔE (OKLab) > 0.01.
- The 80 °C red stop matches the fan policy (all fans at 100 % above 80 °C), so the colour
  tells you the fans are at maximum.

## Themes

| # | Theme | Behaviour | Phase |
|---|---|---|---|
| T1 | **Temperature bands** | Smooth OKLCH gradient through the four stops above (configurable). | 2 |
| T2 | **Heat wave** | Wave travels rear → front (JARGB 1/2 → RAM → JARGB 3). Colour from T1, speed rises with temperature. | 3 |
| T3 | **User colours rotating** | User-chosen palette cycles across the fan zones; optional temperature tint. | 3 |

## Phases

### Phase 0 — OpenRGB as a background server (prerequisite)
- Problem found today: `ujust openrgb install` ran the AppImage from
  `~/.cache/ujust/appimages/` without Gear Lever's final "Move to app menu" step. OpenRGB's own
  "start at login" then wrote `Exec=/tmp/.mount_OpenRG…/usr/bin/OpenRGB` into
  `~/.config/autostart/OpenRGB.desktop`. That temporary mount path disappears, so after a
  reboot autostart fails and `ujust openrgb status` reports "not installed".
- Root cause confirmed in the `ujust` recipe `_install_appimage_file`: it downloads the
  AppImage to `~/.cache/ujust/appimages/` with `trap "rm -rf $DOWNLOAD_DIR" EXIT`, then
  opens Gear Lever. Unless **Unlock → Move to the app menu** is clicked in Gear Lever,
  closing that window deletes the only copy, so OpenRGB "uninstalls itself".
- Decide the OpenRGB build:
  - **1.0rc2** (ujust, 2025-09-14) registers the board.
  - **release_1.0** (2026-09-11) contains `93830c12`, which adds the board's 761-byte
    zone config, and is the version MysticLight verified. Preferred if an official
    AppImage exists; otherwise build it in a distrobox (MysticLight has the scripts).
- Place the AppImage at a stable path, run it as a **systemd user service** in
  `--server --noautoconnect` mode on 127.0.0.1:6742, disable OpenRGB's own GUI autostart,
  and enable linger so it starts at boot.
- Check: `--list-devices` shows MSI (JARGB 1/2/3, JAF), ENE DRAM ×2 and the Apex Pro.

### Phase 1 — Skeleton plugin
- `manifest.toml` (`type = "integration"`, `privileged = false`), launcher, venv
  installer with SELinux label, uninstaller (same pattern as `cc-plugin-zalman-lcd`).
- Read temps from CoolerControl (token in `config.json`), connect to OpenRGB, log the
  discovered zones. No LED writes yet.

### Phase 2 — Theme T1 temperature bands
- Zone map and band config, EMA smoothing and hysteresis, write only on change.
- Hardware check with the owner: heat the CPU (CoolerControl's stress test) and watch the bands change.

### Phase 3 — Themes T2 heat wave and T3 rotating colours
- Frame loop (~20–30 fps, capped by what the 761 controller accepts).

### Phase 4 — Plugin UI page
- CoolerControl plugin page writes `config.json`: theme, thresholds, colours, zone order.

### Phase 5 — Tests and release
- Unit tests for themes, smoothing and config validation (≥ 80 %). CI with ruff and pytest.
- Robustness: OpenRGB server restart, CoolerControl restart, suspend/resume, reboot.

## Risks

- **Write rate:** the 761-byte controller sends one large packet per update. A high
  frame rate may lag or wedge it. Measure in phase 3.
- **Two writers:** if the OpenRGB GUI or another daemon also writes, colours fight.
  Mitigation: one owner; document it.
- **Permissions at boot:** `uaccess` ACLs apply to the logged-in seat user. A
  linger-started user service before login may lack hidraw/i2c access. Verify in phase 0;
  fall back to a udev group rule if needed.
- **OpenRGB SDK protocol:** openrgb-python needs `protocol_version=3` against this
  server (MysticLight finding).

## Open questions for the owner

- Licence for the eventual public release (repository is private for now).
