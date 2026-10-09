# OpenRGB on this machine

Last updated: 2026-10-09.

## Current installation

- **Flatpak `org.openrgb.OpenRGB` 1.0** (commit `81bbe18a`, 2026-09-11), system-wide,
  installed by the owner through Bazaar, together with the plugins
  `org.openrgb.OpenRGB.Plugin.Effects` 1.0 and `org.openrgb.OpenRGB.Plugin.VisualMap` 1.0.
- Sandbox: `devices=all`, so hidraw and i2c are reachable.
- Config: `~/.var/app/org.openrgb.OpenRGB/config/OpenRGB/` (logs in `logs/`).
- Autostart created by OpenRGB: `~/.config/autostart/org.openrgb.OpenRGB.desktop`.

Devices detected (log `OpenRGB_20261009_051401.log`): ENE DRAM ×2, MSI MYSTIC LIGHT,
**SteelSeries Rival 5**, SteelSeries Apex Pro.

## "udev rules are not installed" warning: harmless here

OpenRGB 1.0 (`DetectionManager.cpp`) shows this dialog when it cannot find
`60-openrgb.rules` in `/etc/udev/rules.d` or `/usr/lib/udev/rules.d`. Inside the
Flatpak sandbox `/usr` belongs to the runtime, so the host file is invisible. The rules
**are** installed on the host by Bazzite's `openrgb-udev-rules` rpm
(`/usr/lib/udev/rules.d/60-openrgb.rules`, giving `uaccess` to i2c and the MSI/SteelSeries
HID devices). All devices are detected, which confirms it.

**Action:** tick "Don't show this message again". Do not install a second copy into
`/etc/udev/rules.d`: OpenRGB then warns about duplicate rules, and the two files can conflict.

## Why the earlier AppImage "uninstalled itself"

`ujust openrgb install` runs the recipe `_install_appimage_file`, which:
1. downloads the AppImage to `~/.cache/ujust/appimages/`,
2. sets `trap "rm -rf $DOWNLOAD_DIR" EXIT`,
3. opens Gear Lever on that file.

Unless **Unlock → Move to the app menu** is clicked in Gear Lever before the window is
closed, the trap deletes the only copy. OpenRGB had also written its own autostart
entry with the temporary mount path (`Exec=/tmp/.mount_OpenRG…/usr/bin/OpenRGB`), which
fails after a reboot. The AppImage was 1.0rc2 (2025-09-14), which lacks the Rival 5
detector and the MS-7E62 761-byte configuration.

## Cleanup still to do (phase 0)

- [ ] Remove the stale rc2 autostart: `~/.config/autostart/OpenRGB.desktop` (`Exec=/tmp/.mount_…`).
- [ ] Two `openrgb` Flatpak processes were running at 05:1x. Keep a single instance.
- [ ] Run OpenRGB headless as the SDK server for the plugins
  (`flatpak run org.openrgb.OpenRGB --server --server-host 127.0.0.1 --noautoconnect`),
  as a systemd user service, and disable the GUI autostart. The GUI overrides Direct mode.
- [ ] Decide whether the Effects plugin may stay enabled. It writes the same LEDs as this plugin.
