# cc-plugin-thermal-rgb

**Status: phase 2 (v0.2.0): reads temperatures, resolves zones, and writes the temperature colour to the LEDs.**
See [docs/PLAN.md](docs/PLAN.md).

## Install

```bash
bash setup/install-openrgb-server.sh            # once: headless OpenRGB SDK server (user service)
sudo bash install.sh && sudo systemctl restart coolercontrold
python -m thermal_rgb --config config.local.json --list   # dev: show temperature, colour and zones
```

**Token:** open CoolerControl → Plugins → thermal-rgb, paste an access token (Access Protection →
Access Tokens) and press *Save and restart plugin*. The plugin keeps it in `credentials.json`
(mode 0600) and shows only `***` afterwards.

Other settings live in `/var/lib/coolercontrol/plugins/thermal-rgb/config.json`: temperature
source, colour stops, zone map, and `write_leds` (default `true`; set it to `false` to run in
read-only/dry-run mode).

A CoolerControl **integration plugin** that colours the case, fan, RAM and
motherboard LEDs by temperature, while CoolerControl drives the fans from the
same sensors. CoolerControl is the single source of temperatures. OpenRGB stays
the hardware driver and is reached through its SDK server.

```
CoolerControl (temps: REST /status, /sse) ──▶ cc-plugin-thermal-rgb ──▶ OpenRGB SDK server (127.0.0.1:6742) ──▶ JARGB 1/2/3, ENE DRAM ×2, …
```

This is **not** an OpenRGB plugin. OpenRGB plugins are Qt/C++ modules loaded into
the OpenRGB GUI and tied to its exact Qt version. This plugin is a separate
process, managed by CoolerControl, that talks to OpenRGB over its network SDK.

## Target hardware (owner's system)

| Zone (OpenRGB) | Physical | Control |
|---|---|---|
| MSI Mystic Light `JARGB 1` | Rear fan 1 | own zone |
| MSI Mystic Light `JARGB 2` | Rear fan 2 | own zone |
| MSI Mystic Light `JARGB 3` | CPU block + CPU cooler fans + front fans, one chain | own zone |
| ENE DRAM (`0x71`) | RAM module 1 | own device |
| ENE DRAM (`0x73`) | RAM module 2 ("middle") | own device |

Board: MSI MAG B850 TOMAHAWK MAX WIFI (MS-7E62), Mystic Light USB `0db0:0076`,
OpenRGB "761-byte" controller in zone-based direct mode. Each zone takes one
colour; LEDs appear in blocks of 8.

## Owner's ideas (captured 2026-10-09)

1. **Temperature bands (first theme):** every LED shows cold / warm / hot /
   very hot as colours.
2. **Heat wave:** a wave moving from the rear fans towards the front (JARGB 1/2 →
   JARGB 3), with its colour and speed following temperature.
3. **User colours rotating on the fans:** user-picked colours cycle around the fans.
4. More themes later. Temperature comes first.

## Prior work this builds on

- `RgbLighting/openrgb-cpu-thermal-sync`: Python daemon (CPU temp → OpenRGB colour), 2026-09-11.
- `RgbLighting/mystic-light` (+ submodule `game-lighting`, branch `working-temperature-rgb`):
  verified JARGB 1–3 and JAF zones, temperature-based Direct mode for the board and DRAM
  (stops 40 °C blue, 55 °C green, 70 °C yellow, 85 °C orange, 95 °C red, using the hotter
  of CPU and GPU), and OpenRGB release_1.0 built from source. Verified 2026-09-15, before the reinstall.

This project replaces the standalone daemons with a CoolerControl-managed plugin
and reuses their verified findings.
