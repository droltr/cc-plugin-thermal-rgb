# Troubleshooting

Start with the plugin log:

```bash
journalctl -b -t run.sh | grep thermal_rgb | tail -30
```

The plugin retries every 10 seconds, so a problem that is fixed (a token entered, a server started) clears
by itself without restarting CoolerControl.

## Reading the log

| Log line | Meaning | What to do |
|---|---|---|
| `Not ready (GET /status failed: HTTP Error 401: Unauthorized)` | CoolerControl rejected the access token (missing, expired or revoked) | Create a new token under *Access Protection → Access Tokens* and enter it on *Plugins → thermal-rgb* |
| `Not ready (GET /status failed: HTTP Error 429: Too Many Requests)` | CoolerControl is rate limiting. It usually follows repeated 401 responses, from this plugin or another plugin that restarts in a loop | Fix the token first; check `journalctl -b` for other plugins that crash and restart every second; the limit lifts shortly afterwards |
| `Not ready (… Connection refused)` | CoolerControl (`11987`) or the OpenRGB SDK server (`6742`) is not running | Check `systemctl status coolercontrold`; for OpenRGB see [OpenRGB server](../README.md#installation) |
| `Not ready (no CPU device reported by CoolerControl)` | CoolerControl lists no device of type CPU | Set `temp_device_uid` in `config.json` to the sensor device you want |
| `Not ready (temperature 'temp1' not found for device …)` | The sensor name does not exist on that device | Set `temp_name` (compare with the sensors shown in CoolerControl) |
| `zone 'x' not found (device=…, zone=…, location=…) (skipped)` | A configured zone does not match any OpenRGB device | Run `python -m thermal_rgb --config config.local.json --list` and copy the exact device and zone names |
| `Connected: 0 zones resolved` | No zone matched, so nothing can change colour | Same as above; the default zone map fits only the reference system |
| `Invalid configuration: …` | `config.json` is malformed or a value is out of range | Fix the key named in the message ([Configuration](../README.md#configuration)) |
| Info tab: *Could not check* under Version & Update | The plugin could not reach `api.github.com` (offline, firewall) or hit the anonymous rate limit | Harmless; the plugin retries every 12 hours. Use *Check again* to retry now, or look at the releases page. Set `"update_check": false` to stop checking |
| `Temperature read failed: …` | A temperature request failed while running | Transient errors recover on their own; a repeating one points to CoolerControl |
| `Could not move the token to credentials.json (…); using it from config` | The plugin folder is not writable by the plugin user | The token still works, but stays in `config.json`; check the folder permissions |

## The LEDs do not change colour

1. The log shows `Connected: N zones resolved, write_leds=True` with `N > 0`? If not, see the table above.
2. `write_leds` is `false`? That is dry-run mode; set it to `true`.
3. The summary line `CPU 44.1 °C (smoothed) -> colour (…)` appears once a minute. If the colour is the same
   as before, the temperature is still inside the same band, so nothing needs to change.
4. Another program writes the same LEDs (the OpenRGB window with effects, another plugin or script).
   Close it; two writers make the colours flicker or jump.
5. Check the colour by hand with the plugin stopped: `python -m thermal_rgb --config config.local.json --show '#ff0000'`.

## The plugin page

- **Check the Info tab first.** It shows the plugin state, the last error and which zones were found.
- **State "Not reported yet".** The plugin has not written its status; restart it (or CoolerControl) once.

- **Token is not accepted after saving.** The plugin only moves the token at start. Press *Save and restart plugin*,
  then check the log for `Stored the CoolerControl token in credentials.json`.
- **Field shows `***`.** That is intended: a token is stored and is never shown again. Paste a new token to replace it.
- **Page is blank.** The `ui/` folder is missing from the installed plugin; run `sudo bash install.sh` again.
- **Live temperature shows a dash.** The page could not read the sensor through CoolerControl; the plugin itself is
  not affected. Check `temp_device_uid` and `temp_name`.

## Collecting information for an issue

Include the plugin version (`python -m thermal_rgb --version`), your CoolerControl and OpenRGB versions, the
output of `--list` and the log lines above. Remove any token before posting.
