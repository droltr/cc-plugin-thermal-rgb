# Testing

Two layers: automated unit tests that need no hardware, and a manual hardware check on the reference
system ([hardware.md](hardware.md)). Only the first is repeatable by anyone; the second records what was
actually verified.

## Automated tests

```bash
pip install -r requirements.txt ruff pytest pytest-cov
ruff format --check . && ruff check . && pytest -q --cov --cov-fail-under=80
```

72 tests, 98 % line coverage (CI requires at least 80 %). GitHub Actions runs the same commands on every
push to `main` and `develop` and on every pull request.

| File | Covers |
|---|---|
| `tests/test_colors.py` | Hex parsing and rejection, OKLCH round trip, gradient exact at the stops, held outside the range, independent of stop order, blue→yellow midpoint not grey |
| `tests/test_config.py` | Defaults, validation errors, file loading, token migration to `credentials.json`, masking, unwritable folder |
| `tests/test_coolercontrol.py` | Latest-sample lookup, missing sensor, Bearer token header, wrapped HTTP errors, unexpected payload, no CPU device |
| `tests/test_engine_and_zones.py` | Smoothing (first sample, time constant, no smoothing), colour change threshold, default zones resolve, unresolvable zone, device listing |
| `tests/test_main.py` | Dry run writes nothing, colours written in Direct mode, temperature errors survived, skipped zones, `--list`, `--sweep`, `--show`, invalid config, retry until ready |

Tests use fake OpenRGB and CoolerControl clients, so no server, LED or token is needed.

## Update check

`tests/test_updates.py` covers version parsing and comparison (including `0.9.0` < `0.10.0` and pre-release tags), the
GitHub request (headers, release URL fallback), failures that must not break the plugin, the 12-hourly loop, the
status publisher that keeps the update block through every state, and the `update_check` switch. The real request to
GitHub is not part of the automated tests; it is verified by hand in the user test guide (session 002).

## User test guide

Changes that a person can observe are also verified by the user through an interactive guide that belongs to this
project: `tools/test-guide/` (engine) and `tests/user/<NNN-date-slug>/tests.json` (one numbered folder per change; a
fix after a failed test is a new folder). Start it with `tools/test-guide/launch.sh [session]`; it opens
`http://127.0.0.1:8766/`.

- **Pre-flight checks** run when the page opens and again when a report is saved: the tests belong to this project, the
  source tree, the installed copy (version, code and page, compared with `diff`) and the **running** process
  (`thermal-rgb X.Y.Z starting` in the journal) are the version under test, the service is active and OpenRGB is
  listening. A failed check turns the page red; a report can then only be saved after an explicit acknowledgement and
  the failure is recorded in it.
- **Project and path** are shown on the page. The server refuses reports for another project or path, for an unknown
  session, or when `tests.json` changed after the page was loaded (its SHA-256 is part of the report).
- **Reports** are written to `.private/test-reports/<session>/cc-plugin-thermal-rgb__<session>__runNN.json` and `.md`,
  numbered, never overwritten and never committed.
- The server is covered by `tests/test_test_guide.py` (pre-flight rules, refused programs, numbering, project and
  hash checks, acknowledgement of failed pre-flight).

The procedure for this guide is shared by all projects (workspace file `.MD/USER_TEST_STANDARD.md`).

## Plugin page (Info and API Settings tabs)

Checked outside CoolerControl by running `ui/index.html` in jsdom with a mock of CoolerControl's plugin library:
Info tab with a running, a waiting (HTTP 401 with hint) and a never-reported plugin; live temperature, marker and
colour swatch; zone table with found and missing zones; API Settings tab opens first when no token is stored;
saving sends the token to `savePluginConfig`, restarts the plugin and then shows `***`. The browser colour
blend matched `colors.py` exactly for 140 temperatures from 30 to 99.5 °C. These checks are not part of CI.
The visual check inside the real CoolerControl iframe (full-page and modal view, dark and light theme) is session
`001-2026-10-18-info-page-v0.3.0` of the user test guide above; until its report is logged here, treat the layout
as unverified.

## Hardware verification (reference system)

| Date | Check | Result |
|---|---|---|
| 2026-10-09 | Device discovery with `--list` | MSI Mystic Light (`JARGB 1–3`) and both RAM modules (ENE controllers) found; all five zones resolved |
| 2026-10-09 | Colours shown one by one with `--show`, plugin stopped | Red, green, blue and white clean; the four default stops judged by eye and approved (`#2060ff`, `#ffd000`, `#ff7a00`, `#ff0000`, red clearly distinct from orange) |
| 2026-10-09 | Heat test (CoolerControl's CPU stress test) | Blue → yellow → orange → red at the expected thresholds, red held for 81 s, back to blue on cooling; transitions follow the fast-heating CPU |
| 2026-10-18 | Settings page and token flow in CoolerControl 5.0.1 | New token entered on the page, moved to `credentials.json`, `config.json` shows `***`, HTTP 401/429 stopped |
| 2026-10-18 | Release build installed with `install.sh` | Five zones resolved, `write_leds=True`, LEDs follow the CPU temperature, no warnings afterwards |

Observations worth knowing:

- Pure `#ffff00` looks greenish on addressable LEDs, which is why the default yellow is `#ffd000`.
- Running `--sweep` while the installed plugin is active makes the two fight; stop the plugin first.

## Not tested

- Hardware other than the reference system, including Intel CPUs and other Mystic Light boards.
- Suspend and resume, and restarting the OpenRGB server while the plugin runs (the plugin retries on
  connection errors, but this has not been exercised on hardware).
- Python versions other than 3.12 (CI) and 3.14 (reference system).

## Reproducing a hardware check

With the plugin installed (see [Usage](../README.md#usage)); `$PLUGIN` is
`/var/lib/coolercontrol/plugins/thermal-rgb/run.sh`:

1. `sudo systemctl stop cc-plugin-thermal-rgb` so nothing else writes the LEDs, and check with `systemctl status`.
2. `sudo -u cc-plugin-user $PLUGIN --list` to confirm the zones.
3. `--show '#ff7a00'` (and the other stops) to judge each colour, then `--sweep 45 85` for the gradient.
4. `sudo systemctl start cc-plugin-thermal-rgb`, apply load and watch the journal for the `colour (…)` summary lines.
