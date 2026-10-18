# User test sessions

One numbered folder per tested change: `NNN-YYYY-MM-DD-slug/tests.json` (steps, expected results and the pre-flight
checks that prove the right version is installed and running). A fix after a failed test is a **new** session
(`...-fixN`); existing sessions are not edited once they have a report.

Run the guide with `tools/test-guide/launch.sh [session]`. Reports are written to
`.private/test-reports/<session>/cc-plugin-thermal-rgb__<session>__runNN.{json,md}` and are not published.
See `docs/testing.md`.
