# How it works

## Purpose

CoolerControl already drives the fans from temperature sensors. This plugin makes the LEDs show the same
temperature, so the colour tells you how hot the system is and, with the default stops, that the fans are
about to reach full speed. There is a single temperature source (CoolerControl) and a single LED driver
(OpenRGB).

## Terms

| Term | Meaning |
|---|---|
| **CoolerControl** | Linux fan and cooling control application; starts this plugin and provides the temperatures through its REST API |
| **OpenRGB SDK server** | OpenRGB running without a window, accepting colour commands on a local network port (`6742`) |
| **Zone** | One independently coloured group of LEDs, for example a motherboard header (`JARGB 1`) or a whole RAM module |
| **Colour stop** | A temperature paired with a colour; colours between two stops are blended |
| **Direct mode** | The OpenRGB mode in which the plugin sets static colours itself instead of the device running a built-in effect |
| **Access token** | A key that lets the plugin read CoolerControl's API; created in CoolerControl and stored in `credentials.json` |

## Data flow

```
coolercontrold ──starts──▶ thermal_rgb (Python, unprivileged cc-plugin-user)
                              │ GET /status  (Bearer token, every poll_interval_s)
                              ▼
                  temperature ─▶ smoothing ─▶ colour gradient ─▶ change filter
                                                                      │ OpenRGB SDK (127.0.0.1:6742)
                                                                      ▼
                                                        Direct-mode colour per zone
```

CoolerControl starts the plugin as a systemd service, restarts it when asked and collects its log. The
plugin never changes fan settings.

## Main loop

1. **Start-up.** Load `config.json` and `credentials.json`, connect to CoolerControl, find the CPU device
   (or use `temp_device_uid`), connect to OpenRGB, resolve the configured zones and switch the devices
   involved to Direct mode when `write_leds` is `true`.
2. **Read.** Fetch `/status` and take the last value of `temp_name` on the chosen device.
3. **Smooth.** A time-aware exponential moving average with time constant `smoothing_tau_s` (default 3 s)
   removes jitter while still following a fast-heating CPU.
4. **Colour.** The smoothed temperature is mapped through the colour `stops`. Below the first stop the first
   colour is held; above the last stop the last colour is held.
5. **Write only on change.** A colour is sent to the zones only when some channel moved by more than 2
   steps, which avoids redundant writes to the slow LED controller.
6. **Log.** A summary line (`CPU 44.1 °C (smoothed) -> colour (32, 96, 255)`) is logged once a minute.

## Colour model

Stops are interpolated in **OKLCH**, the polar form of OKLab, where equal steps look equally different.
Interpolating in plain RGB would pass through muddy grey between blue and yellow. Hue takes the short way
round, lightness and chroma are interpolated linearly, and the result is converted back to sRGB and
clamped to the displayable range.

Default stops: 50 °C `#2060ff` (blue), 60 °C `#ffd000` (yellow), 70 °C `#ff7a00` (orange),
80 °C `#ff0000` (red). The 80 °C red matches a fan curve that reaches 100 % there.

## Error handling

| Situation | Behaviour |
|---|---|
| CoolerControl or OpenRGB not reachable at start | Log `Not ready (…)` and retry every 10 s |
| HTTP 401 | The access token is missing or invalid; enter a new one on the settings page |
| HTTP 429 | CoolerControl is rate limiting; usually follows repeated 401 responses, retried automatically |
| A temperature read fails while running | Warn and wait five poll intervals before the next attempt |
| A zone cannot be matched | Warn and skip that zone |
| Invalid `config.json` | Exit with `Invalid configuration: …` in the journal |

## Status for the plugin page

CoolerControl plugin pages can only read and write the plugin's `config.json`, so the plugin reports to the page
through it. On start-up, while it waits for a dependency, and on shutdown it writes a read-only `_status` block:

```json
"_status": {
  "state": "running",            // running | waiting | stopped
  "version": "0.3.0",
  "token_stored": true,
  "write_leds": true,
  "openrgb": {"host": "127.0.0.1", "port": 6742},
  "temp_device_uid": "…", "temp_name": "temp1",
  "zones": [{"name": "rear_1", "device": "MSI MYSTIC LIGHT", "zone": "JARGB 1", "leds": 8}],
  "zones_unresolved": ["ram_1"],
  "update_check": true,
  "environment": {"platform": "Linux", "kernel": "7.2.9", "python": "3.14.8", "openrgb_python": "0.3.8"},
  "update": {"status": "up_to_date", "latest": "v0.3.1", "url": "…/releases/tag/v0.3.1", "checked_at": "…"},
  "error": "…",                  // only while waiting
  "updated": "2026-10-18T05:00:00+00:00"
}
```

The block never contains the token. It is rewritten only when something other than the timestamp changes, so
a plugin that keeps failing does not rewrite the file every retry. The **Info** tab shows this block, and reads
the live CPU temperature itself from CoolerControl through the plugin library; the colour on its gradient bar
is computed in the browser with the same OKLCH blend as the plugin (checked against `colors.py` for 140
temperatures).

## Update check

CoolerControl plugin pages cannot call external sites from their sandboxed iframe, so the plugin itself asks the public
GitHub releases API (`GET /repos/droltr/cc-plugin-thermal-rgb/releases/latest`) once at start and then every 12 hours, in
a background thread that never blocks the LEDs. It compares the latest tag with the running version
(`thermal_rgb/updates.py`) and publishes the result in `_status.update`: `up_to_date`, `update_available`, `ahead` (a
build newer than the last release) or `unknown` with an error when the request failed. The request is anonymous and
carries only a User-Agent with the plugin name and version; set `"update_check": false` to turn it off. The page shows
the result under **Version & Update** and only links to this repository's release pages. Pre-release tags are ignored.

## Token handling

The **API Settings** tab of the plugin page (`ui/index.html`) runs inside CoolerControl and saves the token with the plugin
config. At the next start the plugin moves a newly entered token into `credentials.json` (mode 0600, written
atomically) and replaces it in `config.json` by `***`. The page therefore never reads the real token back.
If the folder is not writable, the plugin still uses the token from the config and logs a warning.

## Source layout

| Module | Role |
|---|---|
| `thermal_rgb/__main__.py` | Command line, main loop, `--list`, `--sweep`, `--show` |
| `thermal_rgb/config.py` | Defaults, validation, token migration to `credentials.json` |
| `thermal_rgb/coolercontrol.py` | Minimal read-only REST client (standard library only) |
| `thermal_rgb/colors.py` | OKLCH gradient, hex parsing |
| `thermal_rgb/engine.py` | Smoothing and the temperature-bands theme, change filter |
| `thermal_rgb/openrgb_link.py` | OpenRGB connection and zone resolution |
| `thermal_rgb/status.py` | Builds and publishes the `_status` block (`StatusPublisher` keeps the update and environment blocks in every state) |
| `thermal_rgb/updates.py` | Update check against the latest GitHub release |
| `ui/index.html` | Plugin page: Info tab and API Settings tab |
