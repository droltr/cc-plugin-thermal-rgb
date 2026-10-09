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

## Themes

| # | Theme | Behaviour | Phase |
|---|---|---|---|
| T1 | **Temperature bands** | 4 bands with configurable thresholds and colours. Default: < 50 °C cold (blue), 50–65 warm (green/yellow), 65–80 hot (orange), > 80 very hot (red). Optional smooth gradient between stops. | 2 |
| T2 | **Heat wave** | Wave travels rear → front (JARGB 1/2 → RAM → JARGB 3). Colour from T1, speed rises with temperature. | 3 |
| T3 | **User colours rotating** | User-chosen palette cycles across the fan zones; optional temperature tint. | 3 |

## Phases

### Phase 0 — OpenRGB as a background server (prerequisite)
- Problem found today: `ujust openrgb install` ran the AppImage from
  `~/.cache/ujust/appimages/` without Gear Lever's final "Move to app menu" step. OpenRGB's own
  "start at login" then wrote `Exec=/tmp/.mount_OpenRG…/usr/bin/OpenRGB` into
  `~/.config/autostart/OpenRGB.desktop`. That temporary mount path disappears, so after a
  reboot autostart fails and `ujust openrgb status` reports "not installed".
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

- Exact colours for the four bands, and the thresholds (CPU only, or the hotter of CPU and GPU?).
- Should the RAM follow CPU temperature, or a DRAM temperature if one exists (spd5118 sensors are present)?
- Licence for the eventual public release (repository is private for now).
