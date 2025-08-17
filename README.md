# pychubby

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

## Why not just pip install?

- **Offline installs** – ship `.chub` to air-gapped systems.
- **Reproducibility** – `.chub` contains exact wheel artifacts.
- **No dependency download** – all wheels are included and ready to go.
- **Controlled installation** – no risk of dependency resolution changing under your feet.

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

- [x] Post-install hook support
- [x] Support metadata via `.chubconfig`
- [x] Multiple primary wheels in a single chub
- [ ] Digital signature support

---

## License

MIT
