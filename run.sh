#!/usr/bin/env bash
# Started by CoolerControl (systemd unit cc-plugin-thermal-rgb) as cc-plugin-user.
set -euo pipefail
dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export PYTHONPATH="$dir/lib"
exec "$dir/venv/bin/python" -P -m thermal_rgb --config "$dir/config.json" "$@"
