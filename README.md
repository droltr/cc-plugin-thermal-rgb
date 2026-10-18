# cc-plugin-thermal-rgb

[![CI](https://github.com/droltr/cc-plugin-thermal-rgb/actions/workflows/ci.yml/badge.svg)](https://github.com/droltr/cc-plugin-thermal-rgb/actions/workflows/ci.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/droltr/cc-plugin-thermal-rgb)](https://github.com/droltr/cc-plugin-thermal-rgb/releases)

A [CoolerControl](https://gitlab.com/coolercontrol/coolercontrol) integration plugin that colours case
fans, RAM and motherboard LEDs by CPU temperature, so the lighting shows how hot the system is.

## Contents

[Purpose](#purpose) · [Hardware](#hardware) · [How it works](#how-it-works) · [Installation](#installation) ·
[Configuration](#configuration) · [Usage](#usage) · [Testing](#testing) · [Development](#development) ·
[Documentation](#documentation) · [Security](#security) · [License](#license)

## Purpose

CoolerControl already drives the fans from temperature sensors. This plugin reuses the same sensor for
the LEDs: blue when the CPU is cool, then yellow, orange and finally red as it heats up. There is one
temperature source (CoolerControl) and one LED driver ([OpenRGB](https://openrgb.org)), so the fan
behaviour and the lighting always agree.

This is **not** an OpenRGB plugin (those are Qt/C++ modules inside the OpenRGB GUI). It is a separate
Python process that CoolerControl starts, stops and logs, and that talks to OpenRGB over its SDK server.

Version 0.2.1 implements the **temperature bands** theme. A heat-wave theme, rotating user colours and a
full settings page are planned but not implemented.

## Hardware

Written for, and tested only on, one machine:

| | |
|---|---|
| Board | MSI MAG B850 TOMAHAWK MAX WIFI (MS-7E62), Mystic Light `JARGB 1–3` |
| CPU | AMD Ryzen 7 9800X3D (`k10temp` Tctl) |
| RAM | 2 × 32 GiB DDR5-6000 (`F5-6000J3636F32G`), lit through an ENE RGB controller on each module |
| GPU | NVIDIA GeForce RTX 5080 (not used by this plugin) |
| Software | Bazzite (Fedora Atomic), CoolerControl 5.0.1, OpenRGB 1.0 (Flatpak) |

The plugin works wherever OpenRGB sees your LEDs, but the default zone map matches only this machine;
other hardware needs its own `zones` list. Full details, the zone table and a guide for other hardware:
[docs/hardware.md](docs/hardware.md).

## How it works

```
CoolerControl (GET /status) ──▶ thermal-rgb ──▶ OpenRGB SDK server (127.0.0.1:6742) ──▶ LEDs
```

Every second the plugin reads the CPU temperature, smooths it (exponential moving average, 3 s), maps it
through four colour stops interpolated in the perceptual OKLCH colour space, and writes the result to the
configured zones only when the colour actually changes.

| °C | 50 | 60 | 70 | 80 |
|---|---|---|---|---|
| Colour | blue `#2060ff` | yellow `#ffd000` | orange `#ff7a00` | red `#ff0000` |

Below 50 °C the colour stays blue and from 80 °C it stays red. Details, error handling and the module
layout: [docs/how-it-works.md](docs/how-it-works.md).

## Installation

Requirements: Linux with systemd, CoolerControl 5.x with plugin support, Python 3.10 or newer, an OpenRGB
1.0 SDK server on `127.0.0.1:6742`, and a CoolerControl access token.

```bash
git clone https://github.com/droltr/cc-plugin-thermal-rgb.git
cd cc-plugin-thermal-rgb
sudo bash install.sh
sudo systemctl restart coolercontrold
```

`install.sh` copies the plugin to `/var/lib/coolercontrol/plugins/thermal-rgb/`, creates a Python virtual
environment there and keeps an existing `config.json` and `credentials.json`. If no `config.json` exists
yet, it seeds the token from `~/.config/cc-token` when that file is present. Remove the plugin with
`sudo bash uninstall.sh`; the LEDs keep their last colour until another program sets them.

**Access token.** In CoolerControl open *Access Protection → Access Tokens* and generate a token, then open
*Plugins → thermal-rgb*, paste it and press *Save and restart plugin*. The plugin stores it in
`credentials.json` (mode 0600) and shows only `***` afterwards. Without a valid token the log shows
`HTTP Error 401` and the plugin retries every 10 seconds.

**OpenRGB server.** OpenRGB must run headless as an SDK server, with its own GUI autostart off (two
writers fight over the LEDs). `setup/install-openrgb-server.sh` sets this up for the Flatpak build as a
user service without root; `setup/uninstall-openrgb-server.sh` reverses it.

## Configuration

Settings live in `/var/lib/coolercontrol/plugins/thermal-rgb/config.json` and are read at start. Missing
keys use the defaults below.

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
| `stops` | the four stops above | List of `{temp_c, color}` |
| `zones` | five zones, rear to front | List of `{name, device, zone?, location?}` |

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

An invalid file is rejected at start with `Invalid configuration: …` in the journal.

## Usage

CoolerControl runs the plugin as the `cc-plugin-thermal-rgb` systemd service. Follow its log with
`journalctl -f -t run.sh | grep thermal_rgb`.

For development or colour checks, run the module against a local config file:

```bash
python -m thermal_rgb --config config.local.json --list            # temperature, colour and zones
python -m thermal_rgb --config config.local.json --sweep 45 85     # play the gradient on the LEDs once
python -m thermal_rgb --config config.local.json --show '#ff7a00'  # hold one colour
python -m thermal_rgb --version
```

`--sweep` and `--show` write to the LEDs even when `write_leds` is `false`; stop the installed plugin first
or the two will compete.

## Testing

72 automated tests (98 % coverage, no hardware needed) run in CI on every push and pull request. The
colours and the temperature response were also checked by eye on the reference machine: device discovery,
each colour stop, a CPU heat test from blue to red and back, and the token flow. What was and was not
verified is listed in [docs/testing.md](docs/testing.md).

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt ruff pytest pytest-cov
ruff format --check . && ruff check . && pytest -q --cov --cov-fail-under=80
```

Code and documentation are in English, commits follow [Conventional Commits](https://www.conventionalcommits.org/),
and work happens on `feature/*` and `fix/*` branches merged into `develop`; releases are merged into
`main` and tagged. See [CONTRIBUTING.md](CONTRIBUTING.md).

| Path | Contents |
|---|---|
| `thermal_rgb/` | Plugin package: config, CoolerControl client, colour maths, engine, OpenRGB link |
| `ui/index.html` | Token settings page shown in CoolerControl |
| `setup/` | Optional helper that runs OpenRGB as a headless user service |
| `tests/` | Unit tests |
| `docs/` | Hardware, how it works, testing |

## Documentation

- [docs/hardware.md](docs/hardware.md): tested hardware, zone map, using other hardware
- [docs/how-it-works.md](docs/how-it-works.md): data flow, colour model, error handling, token storage
- [docs/testing.md](docs/testing.md): automated tests, hardware verification, what is not tested
- [CHANGELOG.md](CHANGELOG.md) · [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md)

## Security

The access token grants CoolerControl API access. It is kept in `credentials.json` with mode 0600 and is
never committed, logged or returned to the settings page. Report vulnerabilities privately as described in
[SECURITY.md](SECURITY.md).

## License

Copyright © 2026 droltr. Licensed under the [GNU General Public License v3.0 or later](LICENSE)
(`GPL-3.0-or-later`). You may use, modify and redistribute this software, but derivative works must be
released under the same license with the copyright notices kept intact.
