# Third-party notices

This project is licensed under GPL-3.0-or-later ([LICENSE](LICENSE)). It uses the following work by others.
Nothing below is copied into the repository except where stated.

## Used at run time (not bundled)

| Component | Use | License |
|---|---|---|
| [openrgb-python](https://github.com/jath03/openrgb-python) 0.3.8 by jath03 | Client library for the OpenRGB SDK; installed from PyPI by `install.sh` into the plugin's virtual environment | GPL-3.0 |
| [OpenRGB](https://openrgb.org) 1.0 | LED driver, reached over its network SDK as a separate process; not linked | GPL-2.0 |
| [CoolerControl](https://gitlab.com/coolercontrol/coolercontrol) | Starts the plugin, provides the REST API and the plugin page library (`/plugins/lib/cc-plugin-lib.js`) | GPL-3.0 |

## Algorithms and values

- **OKLab / OKLCH colour space** by Björn Ottosson, <https://bottosson.github.io/posts/oklab/> (2020). The matrix
  coefficients in `thermal_rgb/colors.py` come from his published reference code, which he released into the
  public domain (MIT as an alternative). The OKLCH gradient between temperature stops is built on it.
- **CoolerControl theme variables.** `ui/index.html` reads CoolerControl's `--colors-*` theme variables and uses
  its default dark-theme values as fallbacks, an approach also used by
  [CoolerDash](https://github.com/damachine/coolerdash) by Christian Kühn (MIT), which informed the page's
  structure and the masked-token idea. No CoolerDash code is included.

## Documents and conventions

- `CODE_OF_CONDUCT.md` is the [Contributor Covenant](https://www.contributor-covenant.org) 2.1,
  © the Contributor Covenant authors, licensed CC BY 4.0, with the contact method filled in.
- `LICENSE` is the GNU General Public License v3 text published by the Free Software Foundation.
- `CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
  [Semantic Versioning](https://semver.org/); commits follow [Conventional Commits](https://www.conventionalcommits.org/).

## Earlier work by the maintainer

The colour stops, the zone layout and the Mystic Light findings build on the maintainer's earlier experiments
(`openrgb-cpu-thermal-sync`, `mystic-light`), which this plugin replaces.
