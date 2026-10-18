# Security policy

## Supported versions

Only the latest release receives fixes.

## Reporting a vulnerability

Please do not open a public issue. Use the **Report a vulnerability** button under the repository's
*Security* tab to send a private report, and include the plugin version (`python -m thermal_rgb --version`),
what you observed and how to reproduce it. You can expect an acknowledgement within a week.

## Scope

The plugin handles a CoolerControl access token. Reports about token exposure (logs, the settings page,
file permissions of `credentials.json`) are in scope. Never include a real token in a report.
