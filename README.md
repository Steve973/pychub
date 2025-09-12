# pychub

## Overview

**pychub** is a packaging tool that bundles your Python wheel and all of its
dependencies into a single, self-extracting `.chub` file.

It’s like a "wheel extension": it still uses your host Python interpreter, but
comes with all dependencies and extras pre-downloaded, so installs are
**predictable, reproducible, and network-free**.

To be clear, **pychub** does not compete with any other post-build packaging
tools. Any of the various tools in this space might fit your needs better than
any of the others. Each of these tools has overlap with the others, and each
shines in their particular target areas. Likewise, **pychub** is most useful
when you want a bundle that you can ship to any machine, regardless of the
environment, and install the wheels and dependencies persistently.

## Quickstart

While **pychub** has quite a few features, you can get started with just two
commands in your shell, and you can see it demonstrate its simplest feature.

**Build** a `.chub` from your wheel:

    pychub dist/mypackage-1.0.0-py3-none-any.whl

**Run** (extract/install) it anywhere with Python 3.9+:

    python mypackage-1.0.0.chub

That’s it — no pip, no network, no surprises.

## Features

- **Single-file distribution** — ship a `.chub` anywhere.
- **Network-free installs** — dependencies are already inside the bundle.
- **Environment agnostic** — works with system Python, venv, or conda.
- **Optional entrypoint** — run your tool right after installation.
- **Extras included** — add configs, docs, or scripts if you want.

## Build tool integration

Use your favorite build system with a companion plugin:

- [pychub-poetry-plugin](https://pypi.org/project/pychub-poetry-plugin/)
- [pychub-hatch-plugin](https://pypi.org/project/pychub-hatch-plugin/)
- [pychub-pdm-plugin](https://pypi.org/project/pychub-pdm-plugin/)

See the [pychub-build-plugins repo](https://github.com/Steve973/pychub-build-plugins).

If you use another build system, please consider requesting, or even contributing,
a plugin for it!

## Learn more

For a full walkthrough with CLI options, examples, comparison tables, and
roadmap, see the [USER_GUIDE](USER_GUIDE.md).

---

Released under the MIT [License](LICENSE).
