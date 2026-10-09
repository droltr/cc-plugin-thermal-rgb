# Plan — settings pages for our CoolerControl plugins

Date: 2026-10-09. Status: **planned, not started.** Requested by the owner: "plan settings
pages where the plugins can be configured". Covers `cc-plugin-thermal-rgb` (first),
`cc-plugin-game-rgb` and `cc-plugin-zalman-lcd`.

## How CoolerControl plugin pages work (CoolerControl 5.0.1)

- A plugin ships `ui/index.html` in its plugin folder
  (`/var/lib/coolercontrol/plugins/<id>/ui/index.html`). CoolerControl embeds it in an iframe on
  the plugin's page in the **Plugins** sidebar, either as a full page or as a modal.
- The page loads the daemon-served library `/plugins/lib/cc-plugin-lib.js`:
  - `runPluginScript(fn)` is the entry point and injects CoolerControl's theme (Tailwind classes such as
    `bg-bg-two` and `text-accent`), so pages match dark, light and high-contrast themes.
  - `getPluginConfig()` / `savePluginConfig(obj)` read and write the plugin's **`config.json`**
    (the daemon reads and writes the file and sets its owner and permissions).
  - `restartPlugin()` restarts an integration plugin so it re-reads its config.
  - `getDevices()` and `getStatus()` return live CoolerControl data. Note: `getStatus()` is a
    `Map<uid, Map<sensor, {temp…}>>` with **string** values.
- **Secret handling:** the daemon returns `config.json` verbatim to the page. A token stored there
  would be shown in the browser. CoolerDash solves this with a separate `credentials.json` that the
  page never reads; it shows `***` and only sends a new token when the user types one. We do the same.

## Shared design (all three plugins)

| Topic | Decision |
|---|---|
| Technology | One self-contained `ui/index.html` per plugin: plain HTML, CSS and JavaScript, no build step, no external CDN. Ships with the plugin and is installed by `install.sh`. |
| Look and feel | CoolerControl's injected classes only, so the page follows the app theme. English UI text. |
| Source of truth | The Python `config.py` defaults and validation are authoritative. The page validates for convenience; the plugin re-validates on start, logs errors and **keeps the last good config** instead of crashing. |
| Save flow | Save → `savePluginConfig()` → `restartPlugin()` → status line shows the result; errors are shown inline next to the field. |
| Secrets | Token in `credentials.json` (mode 0600, plugin user). The page shows `•••` with a "replace token" field. The plugin migrates a token found in `config.json` once and blanks it there. |
| Discovered hardware | The page cannot reach OpenRGB (port 6742 is not HTTP). At start the plugin writes the zones it discovered into a read-only `"_discovered"` section of `config.json`, only when it changed; the page shows them as pick lists. |
| Version | `"_schema": 1` in `config.json`, with migrations in `config.py`. |

## Page 1 — `cc-plugin-thermal-rgb` (first; issue #5, phase 4)

Sections:
1. **Status:** plugin running, CPU temperature (live from `getStatus()`, refreshed every 2 s),
   current colour swatch, LED output on or off.
2. **Temperature source:** device and sensor drop-downs filled from `getDevices()` / `getStatus()`.
   Default CPU `temp1` (Tctl). GPU is selectable later; per the owner's decision it is not the default.
3. **Colour stops:** table of temperature and colour picker, with add and remove. A live **gradient bar**
   uses CSS `linear-gradient(in oklch, …)`, the same colour model as the plugin, so the bar
   matches the LEDs. Presets: *Default (blue / yellow / orange / red)*, *No green (direct)*.
4. **Theme:** *Temperature bands* (now); *Heat wave* and *Rotating colours* appear when phase 3
   lands. Each theme exposes its own options (wave speed, palette).
5. **Zones:** discovered zones with a checkbox each, plus the rear → front order (drag to reorder) used
   by the heat wave. Default: JARGB 1, JARGB 2, RAM ×2, JARGB 3.
6. **Advanced:** smoothing τ, poll interval, CoolerControl URL, OpenRGB host and port, token (masked).
7. **Preview on LEDs:** sets `"preview": {"from": 45, "to": 85}` in the config and restarts the plugin.
   The plugin runs the existing sweep once, then clears the flag. The CPU is not heated.

Work items: credentials split and migration; `_discovered` writer; `preview` flag; `ui/index.html`;
`install.sh` copies `ui/`; tests for config migration and preview flag (Python); manual UI checklist.

## Page 2 — `cc-plugin-game-rgb` (with its phase 5)

- Profile list (desktop profile and one per game), active profile indicator.
- Profile editor: name, executable path (text plus "paste from running processes" helper filled by the
  plugin into `_discovered.processes`), Steam AppId, base theme (static, breathe, left-to-right) and colour.
- **Keyboard map:** a clickable Apex Pro layout from the plugin-discovered LED names. Click keys to
  assign colours; WASD preset for Counter-Strike 2.
- Reactive effect toggle, once phase 4 decides firmware vs software.

## Page 3 — `cc-plugin-zalman-lcd` (device plugin; smaller)

- Defaults: brightness and orientation applied at start.
- Status: serial port, connected or not, last update time.
- **Possible workaround for CoolerControl's UI bug (#1 there):** an image upload on this page that calls
  CoolerControl's REST LCD endpoint from the iframe (same origin, user's session). It needs a
  feasibility check first; skip it if CoolerControl fixes the bug upstream.

## Order and tracking

1. thermal-rgb page (existing issue #5, milestone v0.2.0), after phase 2 (LED tuning) is accepted.
2. game-rgb page, with its phase 5.
3. zalman-lcd page (new issue in that repository, milestone v1.0.0).

## Testing

- Python: config schema and migration, credentials split, `_discovered` writer, preview flag; part of
  CI (coverage ≥ 80 %).
- Page: local development with a copied `cc-plugin-lib.js`; then a manual checklist in CoolerControl
  for full page and modal, dark and light themes, save → restart → effect visible, an invalid value
  shown inline, and the token never visible.

## Open questions for the owner

1. Is a single page per plugin fine, or do you want one combined "Lighting" page for both RGB plugins?
2. Should the colour presets include your own named themes (for example "Night: dim blue")?
