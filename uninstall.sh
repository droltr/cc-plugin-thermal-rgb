#!/usr/bin/env bash
# Remove the plugin. LEDs keep their last colour until another program sets them.
# Usage: sudo bash uninstall.sh
set -euo pipefail
test "$(id -u)" -eq 0 || { echo "run with sudo" >&2; exit 1; }
rm -rf /var/lib/coolercontrol/plugins/thermal-rgb /var/lib/coolercontrol/plugins/thermal-rgb.new
systemctl restart coolercontrold
echo "thermal-rgb plugin removed"
