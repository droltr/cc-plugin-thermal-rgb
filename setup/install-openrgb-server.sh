#!/usr/bin/env bash
# Run OpenRGB (Flatpak) as a headless SDK server for the current user, started at login.
# Disables OpenRGB's own GUI autostart, because a second instance fights over the LEDs.
# Everything is reversible with setup/uninstall-openrgb-server.sh. No root needed.
set -euo pipefail

src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
unit_dir="$HOME/.config/systemd/user"
cfg="$HOME/.var/app/org.openrgb.OpenRGB/config/OpenRGB/OpenRGB.json"
autostart="$HOME/.config/autostart"
backup="$HOME/.local/state/cc-plugin-thermal-rgb/backup"

if pgrep -f 'bin/openrgb|/app/bin/openrgb' >/dev/null; then
    echo "Close the OpenRGB window first (an instance is running)." >&2
    exit 1
fi

mkdir -p "$unit_dir" "$backup"

# 1. Turn off OpenRGB's own "start at login" (it would recreate its autostart entry).
if [ -f "$cfg" ] && [ ! -f "$backup/OpenRGB.json" ]; then
    cp -p "$cfg" "$backup/OpenRGB.json"
fi
if [ -f "$cfg" ]; then
    python3 - "$cfg" <<'PY'
import json, sys
path = sys.argv[1]
with open(path) as f:
    cfg = json.load(f)
cfg.setdefault("AutoStart", {})["enabled"] = False
with open(path, "w") as f:
    json.dump(cfg, f, indent=4)
PY
fi

# 2. Move the GUI autostart entries aside (kept in the backup folder).
for f in "$autostart/org.openrgb.OpenRGB.desktop" "$autostart/OpenRGB.desktop"; do
    [ -f "$f" ] && mv "$f" "$backup/"
done

# 3. Install and start the headless server.
install -m 0644 "$src/openrgb-server.service" "$unit_dir/openrgb-server.service"
systemctl --user daemon-reload
systemctl --user enable --now openrgb-server.service
systemctl --user --no-pager status openrgb-server.service | head -5
echo "OpenRGB SDK server enabled. Backups in $backup"
