#!/usr/bin/env bash
# Undo setup/install-openrgb-server.sh.
set -euo pipefail
backup="$HOME/.local/state/cc-plugin-thermal-rgb/backup"
systemctl --user disable --now openrgb-server.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/openrgb-server.service"
systemctl --user daemon-reload
[ -f "$backup/OpenRGB.json" ] && cp -p "$backup/OpenRGB.json" \
    "$HOME/.var/app/org.openrgb.OpenRGB/config/OpenRGB/OpenRGB.json"
for f in org.openrgb.OpenRGB.desktop OpenRGB.desktop; do
    [ -f "$backup/$f" ] && mv "$backup/$f" "$HOME/.config/autostart/"
done
echo "OpenRGB server removed; GUI autostart restored."
