# cc-plugin-thermal-rgb

[![CI](https://github.com/droltr/cc-plugin-thermal-rgb/actions/workflows/ci.yml/badge.svg)](https://github.com/droltr/cc-plugin-thermal-rgb/actions/workflows/ci.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/droltr/cc-plugin-thermal-rgb)](https://github.com/droltr/cc-plugin-thermal-rgb/releases)

A [CoolerControl](https://gitlab.com/coolercontrol/coolercontrol) integration plugin that colours
case fans, RAM and motherboard LEDs by CPU temperature. CoolerControl is the single source of
temperatures and keeps driving the fans from the same sensors; [OpenRGB](https://openrgb.org) stays
the hardware driver and is reached through its SDK server.

```
CoolerControl (GET /status) ──▶ thermal-rgb plugin ──▶ OpenRGB SDK server (127.0.0.1:6742) ──▶ LEDs
```

This is **not** an OpenRGB plugin. OpenRGB plugins are Qt/C++ modules tied to the OpenRGB GUI. This
project is a separate Python process that CoolerControl starts and stops, and that talks to OpenRGB
over its network SDK.

## Status

Version 0.2.0 implements the **temperature bands** theme: every configured zone shows the gradient
colour for the smoothed CPU temperature (blue → yellow → orange → red). The heat-wave and rotating-colour
themes, and a full settings page, are planned but not implemented; see [docs/PLAN.md](docs/PLAN.md).

## Features

- Reads the CPU temperature from CoolerControl's REST API (`/status`).
- Smooths it with a time-aware exponential moving average and maps it to a colour through
  configurable stops, interpolated in the OKLCH colour space for even transitions.
- Writes the colour to OpenRGB zones selected by device name, zone name and location, and only when the
  colour changes by more than two steps per channel.
- Settings page in CoolerControl for entering the access token; the token is stored in
  `credentials.json` (mode 0600) and never shown again.
- Command-line tools to list zones, preview the gradient on the LEDs and hold a single colour.
- Dry-run mode (`write_leds: false`) that reads temperatures and resolves zones without touching the LEDs.

## Requirements

- Linux with systemd, CoolerControl 5.x with its plugin support, and Python 3.10 or newer.
- An OpenRGB 1.0 SDK server reachable on `127.0.0.1:6742` (see [OpenRGB server](#openrgb-server)).
- An access token created in CoolerControl (*Access Protection → Access Tokens*).

The default zone map targets one machine (MSI MAG B850 Tomahawk with Mystic Light `JARGB 1–3` and two
ENE DRAM modules); other hardware needs its own `zones` list, see [Configuration](#configuration).

## Installation

```bash
git clone https://github.com/droltr/cc-plugin-thermal-rgb.git
cd cc-plugin-thermal-rgb
sudo bash install.sh
sudo systemctl restart coolercontrold
```

`install.sh` copies the plugin to `/var/lib/coolercontrol/plugins/thermal-rgb/`, creates a Python
virtual environment there, and keeps an existing `config.json` and `credentials.json`. If no
`config.json` exists yet, it seeds the token from `~/.config/cc-token` when that file is present.
To remove the plugin, run `sudo bash uninstall.sh`; the LEDs keep their last colour until another
program sets them.

### Entering the access token

1. In CoolerControl open **Access Protection → Access Tokens** and generate a token.
2. Open **Plugins → thermal-rgb**, paste the token and press **Save and restart plugin**.

The plugin moves the token into `credentials.json` and leaves `***` in `config.json`. Without a valid
token the plugin logs `HTTP Error 401` and retries every 10 seconds.

### OpenRGB server

OpenRGB must run as a headless SDK server, and its own GUI autostart must be off because two writers
fight over the LEDs. `setup/install-openrgb-server.sh` does this for the Flatpak build as a user
service (no root needed) and `setup/uninstall-openrgb-server.sh` reverses it. Details and the
udev-rules note are in [docs/setup/openrgb.md](docs/setup/openrgb.md).

## Configuration

Settings live in `/var/lib/coolercontrol/plugins/thermal-rgb/config.json`; the plugin reads them at
start. Missing keys use the defaults below.

| Key | Default | Meaning |
|---|---|---|
| `coolercontrol_url` | `http://127.0.0.1:11987` | CoolerControl API address |
| `coolercontrol_token` | `""` | Set through the settings page; stored as `***` afterwards |
| `temp_device_uid` | `""` | Sensor device UID; empty uses the first CPU device |
| `temp_name` | `temp1` | Sensor name on that device |
| `openrgb_host`, `openrgb_port` | `127.0.0.1`, `6742` | OpenRGB SDK server (port 1024–65535) |
| `poll_interval_s` | `1.0` | Polling interval, 0.2–60 s |
| `smoothing_tau_s` | `3.0` | Smoothing time constant; `0` disables smoothing |
| `write_leds` | `true` | `false` reads and resolves only (dry run) |
| `stops` | 50 °C `#2060ff`, 60 °C `#ffd000`, 70 °C `#ff7a00`, 80 °C `#ff0000` | Temperature-to-colour stops |
| `zones` | five zones, rear to front | List of `{name, device, zone?, location?}` |

Example with custom stops and one zone:

```json
{
  "write_leds": true,
  "stops": [
    {"temp_c": 40, "color": "#2060ff"},
    {"temp_c": 75, "color": "#ff0000"}
  ],
  "zones": [
    {"name": "front", "device": "MSI MYSTIC LIGHT", "zone": "JARGB 3"}
  ]
}
```

An invalid file is rejected at start with a message in the journal (`Invalid configuration: …`).

## Usage

CoolerControl starts the plugin as the `cc-plugin-thermal-rgb` systemd service. Follow its log with:

```bash
journalctl -f -t run.sh | grep thermal_rgb
```

For development, run the module directly against a local config file (not the installed one):

```bash
python -m thermal_rgb --config config.local.json --list        # temperature, colour and zones
python -m thermal_rgb --config config.local.json --sweep 45 85  # play the gradient on the LEDs once
python -m thermal_rgb --config config.local.json --show '#ff7a00'  # hold one colour
python -m thermal_rgb --version
```

`--sweep` and `--show` write to the LEDs even when `write_leds` is `false`, so stop the installed plugin
first or the two will compete.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt ruff pytest pytest-cov
ruff format --check . && ruff check . && pytest -q --cov --cov-fail-under=80
```

CI runs the same three commands on every push and pull request. Code and documentation are in English,
commits follow [Conventional Commits](https://www.conventionalcommits.org/), and work happens on
`feature/*` and `fix/*` branches merged into `develop`; releases are merged into `main` and tagged.
See [CONTRIBUTING.md](CONTRIBUTING.md).

| Path | Contents |
|---|---|
| `thermal_rgb/` | Plugin package: config, CoolerControl client, colour maths, engine, OpenRGB link |
| `ui/index.html` | Settings page shown in CoolerControl |
| `tests/` | Unit tests (no hardware or servers needed) |
| `docs/` | Plan, settings-page design, request log, OpenRGB setup notes |

## Security

The access token grants CoolerControl API access. It is kept in `credentials.json` with mode 0600 and
never committed, logged or returned to the settings page. Report vulnerabilities privately as described
in [SECURITY.md](SECURITY.md).

## License

Copyright © 2026 droltr. Licensed under the [GNU General Public License v3.0 or later](LICENSE)
(`GPL-3.0-or-later`). You may use, modify and redistribute this software, but derivative works must be
released under the same license with the copyright notices kept intact.
