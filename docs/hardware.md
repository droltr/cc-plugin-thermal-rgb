# Hardware and tested configuration

The plugin was written for one machine and verified on it. It is not a generic RGB controller:
it works wherever **OpenRGB can see your LEDs** and CoolerControl can read your CPU sensor, but the
default zone map (`DEFAULT_ZONES` in `thermal_rgb/config.py`) matches only the reference system
below. Other hardware needs its own `zones` list ([Configuration](../README.md#configuration)).

## Reference system (the only tested configuration)

| Component | Details |
|---|---|
| Motherboard | MSI MAG B850 TOMAHAWK MAX WIFI (MS-7E62), Mystic Light USB `0db0:0076` |
| LED controller | OpenRGB "761-byte" Mystic Light controller, zone-based Direct mode, one colour per zone |
| RAM | Two ENE DRAM modules (OpenRGB addresses `0x71` and `0x73`) |
| CPU sensor | AMD `k10temp`, `temp1` (Tctl), as reported by CoolerControl |
| Operating system | Bazzite (Fedora Atomic), Linux 7.2 |
| CoolerControl | 5.0.1 (integration plugin, REST API on `127.0.0.1:11987`) |
| OpenRGB | 1.0 (Flatpak `org.openrgb.OpenRGB`) run as a headless SDK server on `127.0.0.1:6742` |
| Python | 3.14 on the host; CI runs 3.12; `openrgb-python==0.3.8` |

### Zone map

| Plugin zone | OpenRGB device / zone | Physical LEDs |
|---|---|---|
| `rear_1` | MSI MYSTIC LIGHT / `JARGB 1` | Rear fan 1 |
| `rear_2` | MSI MYSTIC LIGHT / `JARGB 2` | Rear fan 2 |
| `ram_1` | ENE DRAM at `address 0x71` (whole device) | RAM module 1 |
| `ram_2` | ENE DRAM at `address 0x73` (whole device) | RAM module 2 |
| `front` | MSI MYSTIC LIGHT / `JARGB 3` | CPU block, CPU cooler fans and front fans on one chain |

The order is rear to front, which the planned heat-wave theme will use. LEDs on the Mystic Light
headers appear in blocks of eight, and each zone takes a single colour, so every zone shows the same
temperature colour.

## Using other hardware

1. Make sure OpenRGB detects your devices and run the SDK server.
2. List what the plugin can see: `python -m thermal_rgb --config config.local.json --list`. It prints the
   CPU temperature and every configured zone as `name -> device N zone M (K LEDs)`.
3. Write your own `zones` entries (`name`, `device`, optional `zone` and `location` substrings) and, if your
   CPU sensor is not the first CPU device's `temp1`, set `temp_device_uid` and `temp_name`.
4. Zones that cannot be resolved are skipped with a warning, so a partly matching map still runs.

Intel CPUs, other boards and other OpenRGB controllers are expected to work through the same path but
have **not** been tested. Reports are welcome as issues.

## Not part of this plugin

Keyboard, mouse and GPU LEDs are deliberately untouched. The plugin only writes the zones in its
`zones` list, so another program can own the remaining devices. Do not run OpenRGB effects or another
writer on the same zones at the same time, or the colours will fight.
