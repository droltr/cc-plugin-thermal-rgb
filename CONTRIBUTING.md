# Contributing

Thanks for your interest. Small, focused changes are easiest to review.

1. Open an issue first for anything larger than a bug fix, so the approach can be agreed.
2. Branch from `develop` as `feature/<topic>` or `fix/<topic>`.
3. Set up the environment and run the checks CI runs:

   ```bash
   python -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt ruff pytest pytest-cov
   ruff format --check . && ruff check . && pytest -q --cov --cov-fail-under=80
   ```

4. Add tests for new behaviour; coverage must stay at or above 80 %. Tests must not need hardware.
5. Keep code and documentation in English, use type hints and 100-character lines.
6. Write commit messages as [Conventional Commits](https://www.conventionalcommits.org/)
   (`feat:`, `fix:`, `docs:` …) and update `CHANGELOG.md` under *Unreleased*.
7. Open a pull request against `develop` and fill in the template.

## Hardware safety

Test against real LEDs only on hardware you own, and probe read-only (`--list`) before any write.
Never commit tokens, serial numbers or unredacted device logs.

## License

By contributing you agree that your work is released under the project's
[GPL-3.0-or-later](LICENSE) license.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).
