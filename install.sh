#!/usr/bin/env bash
# Install (or update) the plugin into CoolerControl's plugin directory.
# Keeps an existing config.json; otherwise creates one with the owner's token from
# ~/.config/cc-token. Remove with uninstall.sh.  Usage: sudo bash install.sh
set -euo pipefail

src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
target=/var/lib/coolercontrol/plugins/thermal-rgb
stage="$target.new"
owner_home=$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)

test "$(id -u)" -eq 0 || { echo "run with sudo" >&2; exit 1; }

rm -rf "$stage"
mkdir -p "$stage/lib"
cp "$src/manifest.toml" "$src/run.sh" "$src/requirements.txt" "$stage/"
cp -r "$src/thermal_rgb" "$stage/lib/"
cp -r "$src/ui" "$stage/"
find "$stage/lib" -name __pycache__ -prune -exec rm -rf {} +
/usr/bin/python3 -m venv "$stage/venv"
"$stage/venv/bin/pip" install --quiet --disable-pip-version-check -r "$stage/requirements.txt"
chmod 0755 "$stage/run.sh"

if [ -f "$target/config.json" ]; then
    cp -p "$target/config.json" "$stage/config.json"
else
    python3 - "$owner_home/.config/cc-token" "$stage/config.json" <<'PY'
import json, os, sys
token_file, out = sys.argv[1:]
token = open(token_file).read().strip() if os.path.exists(token_file) else ""
json.dump({"coolercontrol_token": token, "write_leds": True}, open(out, "w"), indent=2)
PY
    chmod 0600 "$stage/config.json"
fi

# The token entered on the settings page lives here; keep it across updates.
if [ -f "$target/credentials.json" ]; then
    cp -p "$target/credentials.json" "$stage/credentials.json"
fi

rm -rf "$target"
mv "$stage" "$target"
# SELinux: systemd (init_t) may not execute var_lib_t files; label only the launcher.
if command -v selinuxenabled >/dev/null && selinuxenabled; then
    chcon -t bin_t "$target/run.sh"
fi
echo "Installed to $target (CoolerControl hands the folder to cc-plugin-user on start)"
echo "Activate with: sudo systemctl restart coolercontrold"
