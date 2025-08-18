# pychubby

## Table of Contents

- [Overview](#overview)
- [The Name](#the-name)
- [Why pychubby?](#why-pychubby)
- [Why not just use insert favorite tool name here?](#why-not-just-use-insert-favorite-tool-name-here)
  - [Feature Comparison](#feature-comparison)
  - [Use Case Alignment](#use-case-alignment)
- [How it works](#how-it-works)
- [CLI Parameters](#cli-parameters)
  - [Building a Chub](#building-a-chub)
  - [Operating a Chub](#operating-a-chub)
- [The `.chubconfig` metadata file](#the-chubconfig-metadata-file)
- [Roadmap](#roadmap)
- [License](#license)

## Overview

**pychubby** is a Python packaging tool that bundles your wheel and all of its
dependencies into a single self-extracting `.chub` file.

The `.chub` file can be executed directly with any compatible Python interpreter
(system Python, virtual environment, conda env, etc.) to install the package and
its dependencies into the current environment.

Optionally, it can run a specified entry point after installation.

---

## The Name

As you might guess, **pychubby** is a portmanteau of **py**thon and **chub**by.
While the standard wheels are quite a bit leaner, consisting of your application
and the metadata required to install it, **pychubby** bundles all of your
dependencies into a single file. This results in a "thicker" file and, thus, the
**pychubby** name was born.

Sometimes software developers like to have a little fun with naming, since
deadlines and testing and debugging are often fairly serious matters.

---

## Why pychubby?

Most Python packaging tools fall into one of two extremes:

- **Frozen binaries** (PyInstaller, PyOxidizer, etc.) – lock you to a specific
  platform, bundle the Python runtime, and create large artifacts.
- **Wheel distribution only** – require manual `pip install` commands, assume
  users know how to manage dependencies.

**pychubby** lives in between: it **avoids runtime bloat** by using the host
Python interpreter, but also **keeps the experience smooth** by shipping all
dependencies pre-downloaded and ready to install.

This makes it:

- **Build-tool agnostic** – Poetry, setuptools, Hatch, Flit, pygradle… if it
  spits out a wheel, pychubby can chub it.
- **Environment agnostic** – works in any Python environment that meets your
  `Requires-Python` spec.
- **Simple** – `python yourpackage.chub` installs everything; optionally runs
  your tool.

---

## Why not just use [insert favorite tool name here]?

Well, you might be right! This is not a simple question, and I will not
presume that I can make that determination for you. You have the best knowledge
of your use case, and that means that you are in the best position to make that
decision.

There are several really great packaging tools available for python. Many of
them share a few overlapping capabilities, and they all have their own unique
features that help with the use cases that they were designed to solve. Pychubby
is no exception. It shares some features with other tools, but it was designed
with a slightly different perspective to address particular use cases.

Here is a table that might help users decide which tool is the best fit for
their use case. (Hint: it might, or might not, be pychubby!)

### Feature comparison
| Feature/Need                | pychubby                        | pex                                  | zipapp                         | PyInstaller / PyOxidizer                         |
|-----------------------------|---------------------------------|--------------------------------------|--------------------------------|--------------------------------------------------|
| Single-file distribution    | Yes (`.chub`)                   | Yes                                  | Yes (`.pyz`)                   | Yes (binary)                                     |
| Includes Python interpreter | No - uses current environment   | Yes - bundled runtime                | No - uses host interpreter     | Yes - frozen binary                              |
| Reproducible install        | Yes - exact wheel copies        | Yes - via PEX-locked deps            | Sometimes - zip structure      | No - binary blob                                 |
| Works in venv/conda/sys env | Yes - pip into any target       | Somewhat (venv-only)                 | Yes - but ephemeral venv       | Yes – standalone embedded runtime (not reusable) |
| Create a new venv           | Yes - ephemeral or persistent   | Yes - existing or new/ephemeral      | Yes - ephemeral                | No – uses frozen, internal environment           |
| Post-install hooks          | Yes - run user scripts          | No (limited post setup)              | No                             | Yes - compile-time hooks                         |
| Runtime execution           | Optional via entrypoint         | Yes                                  | Yes                            | Yes                                              |
| Cross-platform artifact     | Yes - platform-agnostic         | Often - but not always               | Yes - but watch dependencies   | No - platform-specific                           |
| Network-free install        | Yes - offline ready             | Yes - offline ready                  | Often - depends on config      | Yes - all-in-one                                 |
| Target audience             | Devs shipping flexible installs | Devs deploying apps with sealed deps | Devs shipping portable scripts | Devs targeting end users                         |

The table below shows how various packaging tools align with common deployment
needs. Rather than list features, it focuses on use cases so that you can choose
the tool that best fits your project’s real-world requirements. Each column
reflects how well a given tool supports that scenario, whether it’s a perfect
match, a partial fit, or better suited elsewhere.

### Use case alignment
| Use Case / Scenario                              | pychubby  | pex        | zipapp    | PyInstaller / PyOxidizer |
|--------------------------------------------------|-----------|------------|-----------|--------------------------|
| Distribute a CLI/lib in one file                 | best fit  | best fit   | works     | overkill                 |
| Ship sealed GUI/CLI to end users with no Python  | n/a       | n/a        | n/a       | best fit                 |
| Run directly from compressed archive             | works     | best fit   | best fit  | n/a                      |
| Reproducible install without network             | best fit  | best fit   | possible¹ | works                    |
| Install into *any* Python env (sys, venv, conda) | best fit  | venv-only² | best fit  | n/a                      |
| Include Python interpreter in artifact           | n/a       | yes        | n/a       | yes                      |
| Use post-install scripts                         | runtime³  | n/a        | n/a       | build-time⁴              |
| Install from wheels using pip                    | yes       | yes        | optional  | no                       |
| Build Docker containers with no runtime pip      | best fit  | works      | works     | works                    |
| Bundle for ephemeral one-off jobs                | works     | best fit   | best fit  | overkill                 |
| Deploy via container without re-downloading deps | best fit  | best fit   | partial   | yes                      |
| Target cross-platform deployment                 | yes       | partial⁵   | yes       | no                       |
| Package with Conda dependencies                  | roadmap⁶  | n/a        | n/a       | n/a                      |
| Support compile-time customization or setup      | limited³  | n/a        | n/a       | yes (scriptable)         |

Notes:
1. Possible: zipapps can embed dependencies, but behavior varies based on how the archive is constructed.
2. Venv-only: PEX works best when it controls or isolates the environment; system installs are not its design goal.
3. Runtime post-install hooks: Only pychubby supports user-defined scripts that run after install.
4. Build-time only: PyOxidizer allows scripted setup during packaging, not at install time.
5. Partial cross-platform: PEX artifacts must match target platforms; wheel compatibility can limit this.
6. Planned feature: pychubby currently supports pip-based installs only. Conda support is on the potential roadmap.

So the point isn’t that any of these are "best" or "wrong" tools. They’re all
excellent for the jobs they were built for. Pychubby simply covers a different
slice of the space: *inherently reproducible, single-file, wheel-based bundles
that install into the current Python environment without pulling from the
network*.

---

## How it works

When you run `pychubby`, it creates a structure like this:
```bash
dist1-version/    # main wheel package directory
  libs/           # your main wheel and all dependency wheels
  scripts/        # post-install scripts
dist2-version/    # additional wheel package directory, if present
  libs/           # second main wheel and all dependency wheels
  scripts/        # post-install scripts
runtime/          # bootstrap installer
.chubconfig       # metadata: ID, version, entrypoint, post-install
__main__.py       # entry that bootstraps the runtime
```

This happens through the following steps:

1. **Create a wheel package directory**
   - Wheel filenames follow the PEP 427 naming convention:
     - `{distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl`
   - The wheel package directory is `{distribution}-{version}`
   - Include a `libs/` directory for your main wheel and all dependency wheels
   - Include a `scripts/` directory for post-install scripts
2. **Copy your wheel** into `libs/`.
3. **Resolve and download dependencies** using pip (also into `libs/`).
4. **Copy any additional user-specified files** to their destination paths.
5. **Copy any post-install scripts** to `scripts/`.
6. **Inject the pychubby runtime** and include `__main__.py` to enable the runtime CLI
   and its operations.
7. **Update the `.chubconfig` metadata** with the ID, version, entrypoint, and
   post-install scripts.
8. **Package everything** into a `.chub` file using `zip`.
9. **Repeat as needed** by invoking `pychubby` for additional wheels, and with
   the same `--chub` argument, and each set of wheels will be located in their
   own wheel package directory

---

## CLI Parameters

This section describes the CLI commands available in `pychubby` for building,
and then operating, a `.chub` file.

### Building a Chub

The `pychubby` build CLI packages your Python project’s wheel and its  
dependencies into a single `.chub` file.

    usage: pychubby <wheel> [build options]

| Option             | Short Form | Description                                   | 
|--------------------|------------|-----------------------------------------------|
| `<wheel>`          | N/A        | Path to the main wheel file to process        | 
| `--chub`           | `-c`       | Optional path to the output `.chub` file      |
| `--entrypoint`     | `-e`       | Optional entrypoint to run after install      |
| `--includes`       | `-i`       | Optional list of files to include             | 
| `--metadata-entry` | `-m`       | Optional metadata to include in `.chubconfig` |
| `--scripts`        | `-s`       | Optional list of post-install scripts         |
| `--version`        | `-v`       | Show version info and exit                    |

Notes:
- `<wheel>`:
  - Mandatory argument.
  - Any legal path/file name.
- `--chub`:
  - Defaults to `<Name>-<Version>.chub` derived from metadata.
  - Mandatory argument to include additional wheels.
- `--entrypoint`:
  - Used in conjunction with `--run` or `--exec`.
  - May be overridden during runtime invocation.
  - Format: `module:function` (optional single argument supported).
- `--includes`:
  - Each file may optionally specify a destination relative to the wheel’s module directory.
  - Format: `file1[::dest] file2[::dest] fileN[::dest]`
- `--metadata-entry`:
  - Repeatable option to supply multiple key-value pairs.
  - Values can be single items or comma‑separated lists.
  - Lists are parsed as YAML arrays in the `.chubconfig` file. 
  - Format: `key1 value1`, `key1 listval1,listval2,listvalN`
- `--scripts`:
  - Runs after installation but before the entrypoint.

## Example usage

The usage of `pychubby` should be fairly straightforward and intuitive, as you
can see in the following examples:

```bash
# 1. Basic usage – builds a .chub from a wheel
pychubby dist/mypackage-1.0.0-py3-none-any.whl

# 2. Custom output file
pychubby dist/mypackage-1.0.0-py3-none-any.whl \
  --chub dist/fatpackage.chub

# 3. With entrypoint
pychubby dist/mypackage-1.0.0-py3-none-any.whl \
  --entrypoint mypackage.cli:main

# 4. With post-install scripts
pychubby dist/mypackage-1.0.0-py3-none-any.whl \
  --scripts setup.sh finish.sh

# 5. With includes (in the wheel package directory)
pychubby dist/mypackage-1.0.0-py3-none-any.whl \
  --includes extra.cfg data.json

# 6. Includes with destination paths inside the package
pychubby dist/mypackage-1.0.0-py3-none-any.whl \
  --includes README.md::docs readme.txt::docs

# 7. Adding metadata to the .chubconfig file
pychubby dist/mypackage-1.0.0-py3-none-any.whl \
  --metadata-entry maintainer me@example.com \
  --metadata-entry tags http,client

# 8. Everything together
pychubby dist/mypackage-1.0.0-py3-none-any.whl \
  --entrypoint mypackage.cli:main \
  --scripts setup.sh finish.sh \
  --includes config.toml::conf \
  --metadata-entry maintainer me@example.com \
  --metadata-entry tags http,client \
  --chub dist/platform.chub

# 9. Appending a second package to `dist/multi.chub`
pychubby dist/anotherlib-0.9.1-py3-none-any.whl \
  --entrypoint anotherlib.runner:start \
  --scripts init.sh \
  --chub dist/platform.chub
```

---

### Operating a Chub

When you run a `.chub` file directly with Python, it operates in  
**runtime mode** and installs its bundled wheels into the current  
Python environment (system Python, venv, conda env, etc.).

    usage: python /path/to/some.chub [runtime options]

| Option               | Short Form | Description                                       |
|----------------------|------------|---------------------------------------------------|
| `--dry-run`          | `-d`       | Show actions without performing them              |
| `--exec`             | `-e`       | Run the entrypoint directly instead of installing |
| `--help`             | `-h`       | Show help and exit                                |
| `--list`             | `-l`       | List bundled wheels and exit                      |
| `--no-scripts`       |            | Skip post-install scripts                         |
| `--no-deps`          |            | Install/unpack only the main wheel                |
| `--only NAMES`       | `-o`       | Install/unpack only named wheels                  |
| `--only-deps`        |            | Install/unpack only dependency wheels             |
| `--quiet`            | `-q`       | Suppress output wherever possible                 |
| `--run [ENTRYPOINT]` | `-r`       | Run the baked-in or specified `ENTRYPOINT`        |
| `--unpack [DIR]`     | `-u`       | Copy bundled wheels to current or `DIR` and exit  |
| `--version`          |            | Show version info and exit                        |
| `--venv NAME`        |            | Create a venv and install wheels into it          |
| `--verbose`          | `-v`       | Extra logs wherever possible                      |

Notes:
- `--dry-run`:
  - Prevents any changes from being made to the environment.
  - Compatible with:
    - `--no-scripts`
    - `--no-deps`
    - `--only`
    - `--only-deps`
    - `--run`
    - `--unpack`
    - `--venv`
- `--exec`:
  - Nothing is installed.
  - Implies a no-arg `--run` unless explicitly provided.
  - State is not preserved between runs.
  - Since nothing is installed, and state is not preserved, this option implies
    `--no-scripts`.
  - Compatible with:
    - `--run`
- `--no-scripts`:
  - Compatible with:
    - `--dry-run`
    - `--run`
    - `--venv`
- `--no-deps`:
  - Performs extraction only.
  - Disables `--exec` and `--run`.
  - Compatible with:
    - `--dry-run`
    - `--unpack`
    - `--venv`
- `--only NAMES`:
  - Performs extraction only.
  - Disables `--exec` and `--run`.
  - Acceptable delimiters: comma or space.
  - Compatible with:
    - `--dry-run`
    - `--unpack`
    - `--venv`
- `only-deps`:
  - Performs extraction only.
  - Disables `--exec` and `--run`.
  - Compatible with:
    - `--dry-run`
    - `--unpack`
    - `--venv`
- `-q`, `--quiet`:
  - Overrides `--verbose`.
  - Compatible with any other option, though results may vary.
- `--run [ENTRYPOINT]`:
  - Override the baked-in entrypoint specified during build with an
    argument of `module:function`.
  - Compatible with:
    - `--dry-run`
    - `--exec`
    - `--no-scripts`
    - `--venv`
- `--unpack [DIR]`:
  - Copies bundled wheels to the current directory and exits
  - Specify a directory as `DIR` to extract to the specified directory.
  - Compatible with:
    - `--dry-run`
    - `--no-deps`
    - `--only`
    - `--only-deps`
- `--version`:
  - Shows version information (then exits) for:
    - current environment's Python interpreter
    - pychubby
    - bundled wheels
- `--venv NAME`:
  - Creates a virtual environment at path `NAME` and installs wheels into it.
  - Compatible with:
    - `--dry-run`
    - `--no-scripts`
    - `--run`
- `-v`, `--verbose`:
  - Ignored if `--quiet` is used.
  - Compatible with any other option, though results may vary.

## Example usage (runtime)

```bash
# 1. Install everything to the current environment
python mypackage.chub

# 2. Just show what would be installed (no changes)
python mypackage.chub --dry-run

# 3. Install, but skip post-install scripts
python mypackage.chub --no-scripts

# 4. Skip installing dependencies (main package only)
python mypackage.chub --no-deps

# 5. Install only select wheels by prefix
python mypackage.chub --only requests numpy

# 6. Install only dependency wheels (skip main)
python mypackage.chub --deps-only

# 7. Install into a new virtual environment
python mypackage.chub --venv ./myenv

# 8. Show bundled wheels (names only)
python mypackage.chub --list

# 9. Unpack wheels into a directory
python mypackage.chub --unpack ./tmp

# 10. Dry-run unpack (see what would be unpacked)
python mypackage.chub --dry-run --unpack ./tmp

# 11. Create a venv and skip post-install scripts
python mypackage.chub --venv ./myenv --no-scripts

# 12. Install into venv and run the baked entrypoint
python mypackage.chub --venv ./myenv --run

# 13. Install and run a different entrypoint
python mypackage.chub --run othermodule.cli:main

# 14. Use `--exec` to run entrypoint directly without installing
python mypackage.chub --exec

# 15. Use `--exec` with a custom entrypoint
python mypackage.chub --exec --run othermodule.cli:main

# 16. Full verbose install + entrypoint run
python mypackage.chub --run --verbose

# 17. Silent install (minimal output)
python mypackage.chub --quiet

# 18. Show full version info
python mypackage.chub --version

# 19. Help message
python mypackage.chub --help
```

Unpacking and operating a `.chub` file has a significant number of CLI features
when compared to building a `.chub` file, but the usage should still be fairly
straightforward and intuitive. We think that it provides a lot of flexibility
without sacrificing ease of use. The list of examples, above, is fairly
comprehensive, although you can still come up with more combinations for your
own use cases.

---

## The `.chubconfig` metadata file

The `.chubconfig` file is a YAML text file that contains metadata about the
bundled wheels. It is used by the runtime CLI to determine what to extract,
and how to handle certain operations.

Here is an example `.chubconfig` file:

```yaml
---
name: requests
version: 2.31.0
entrypoint: requests.cli:main
post_install_scripts:
  - install_cert.sh
includes:
  - extra.cfg
  - config.json::conf
metadata:
  tags: [http, client]
  maintainer: someone@example.com

---
name: numpy
version: 1.26.4
entrypoint: numpy.start:main
post_install_scripts:
  - init_numpy.sh
metadata:
  tags: [math, array]
  optimized: true

---
name: mylib
version: 0.4.2
entrypoint: mylib.run:start
post_install_scripts: []
includes: []
metadata:
  tags: [internal]
  owner: steve
---
```

---

## Roadmap

| Status       | Feature                    | Notes                                           |
|--------------|----------------------------|-------------------------------------------------|
| ☐ Planned    | Pre-install hook support   | Would allow setup steps before wheel install.   |
| ☑ Done       | Post-install hook support  | Runs user-defined scripts after installation.   |
| ☑ Done       | Metadata via `.chubconfig` | Structured key-value metadata now supported.    |
| ☑ Done       | Multiple primary wheels    | Each wheel has its own libs, scripts, etc.      |
| ☐ Future     | Digital signature support  | Explore signing chub files for verification.    |
| ☐ Exploring  | Conda support              | Evaluate creating/targeting conda environments. |

---

## License

MIT
