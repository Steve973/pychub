# pychub

## Table of Contents

- [Overview](#overview)
- [The Name](#the-name)
- [Why pychub?](#why-pychub)
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

**pychub** is a Python packaging tool that bundles your wheel and all of its
dependencies into a single self-extracting `.chub` file.

The `.chub` file can be executed directly with any compatible Python interpreter
(system Python, virtual environment, conda env, etc.) to install the package and
its dependencies into the current environment.

Optionally, it can run a specified entrypoint after installation, and this can
be done via an **ephemeral** venv.

---

## The Name

As you might guess, **pychub** is a combination of **py**thon and **chubby**.
While the standard wheels are quite a bit leaner, consisting of your application
and the metadata required to install it, **pychub** bundles all of your
dependencies into a single file. This results in a "thicker" file and, thus, the
**pychub** name was born.

Sometimes software developers like to have a little fun with naming, since
deadlines and testing and debugging are often fairly serious matters.

---

## Why pychub?

Most Python packaging tools fall into one of two extremes:

- **Frozen binaries** (PyInstaller, PyOxidizer, etc.) - lock you to a specific
  platform, bundle the Python runtime, and create large artifacts.
- **Wheel distribution only** - require manual `pip install` commands, assume
  users know how to manage dependencies.

**pychub** lives in between: it **avoids runtime bloat** by using the host
Python interpreter, but also **keeps the experience smooth** by shipping all
dependencies pre-downloaded and ready to install.

This makes it:

- **Build-tool agnostic** - Poetry, setuptools, Hatch, Flit, pygradle... if it
  spits out a wheel, pychub can package it.
- **Environment agnostic** - works in any Python environment that meets your
  `Requires-Python` spec.
- **Simple** - `python yourpackage.chub` installs everything; optionally runs
  your tool.

---

## Why Not Just Use [insert favorite tool name here]?

Well, you might be right! This is not a simple question, and I will not
presume that I can make that determination for you. You have the best knowledge
of your use case, and that means that you are in the best position to make that
decision.

There are several really great packaging tools available for python. Many of
them share a few overlapping capabilities, and they all have their own unique
features that help with the use cases that they were designed to solve. Pychub
is no exception. It shares some features with other tools, but it was designed
with a slightly different perspective to address particular use cases.

Here is a table that might help users decide which tool is the best fit for
their use case. (Hint: it might, or might not, be pychub!)

### Feature Comparison

| Feature/Need                | pychub                       | pex                                                          | shiv                              | zipapp                         | PyInstaller / PyOxidizer |
|-----------------------------|--------------------------------|--------------------------------------------------------------|-----------------------------------|--------------------------------|--------------------------|
| Single-file distribution    | Yes (`.chub`)                  | Yes (`.pex`, or native executables with `--scie`)            | Yes (`.pyz`)                      | Yes (`.pyz`)                   | Yes (binary)             |
| Includes Python interpreter | No - uses current environment  | Optional - `--scie` mode bundles an interpreter              | No - uses host interpreter        | No - uses host interpreter     | Yes - frozen binary      |
| Reproducible install        | Yes - exact wheel copies       | Yes - PEX-locked deps, hermetic builds                       | Installs into its own venv on run | Sometimes - zip structure      | No - binary blob         |
| Works in venv/conda/sys env | Yes - pip into any target      | Yes - any compatible interpreter; venv integration strong    | Yes - wheels embedded in zip      | Yes - but ephemeral venv       | Yes - embedded runtime   |
| Create a new venv           | Yes - ephemeral or persistent  | Yes - can build/run in ephemeral or existing venvs           | No - installs into current venv   | Yes - ephemeral only           | No - uses frozen runtime |
| Lifecycle script hooks      | Yes - user scripts at install  | No (limited setup only)                                      | No                                | No                             | Build-time hooks only    |
| Runtime execution           | Optional via entrypoint        | Yes - run apps or REPL directly                              | Yes - runs entrypoints            | Yes - run modules from archive | Yes - runs binary        |
| Cross-platform artifact     | Limited - wheels must be xplat | Yes - multi-platform PEX or scie supports platform targeting | Yes - pure-Python only            | Limited - depends on wheels    | No - per-platform build  |
| Network-free install        | Yes - offline ready            | Yes - offline ready                                          | No - pulls from PyPI if needed    | Sometimes - depends on config  | Yes - all-in-one binary  |
| Target audience             | Devs needing flexible installs | Devs needing sealed, reproducible apps                       | Devs wanting simple .pyz bundling | Devs shipping portable scripts | End-user binary delivery |

The table below shows how various packaging tools align with common deployment
needs. Rather than list features, it focuses on use cases so that you can choose
the tool that best fits your project’s real-world requirements. Each column
reflects how well a given tool supports that scenario, whether it’s a perfect
match, a partial fit, or better suited elsewhere.

### Use Case Alignment
| Use Case / Scenario                          | pychub | pex                                | shiv                             | zipapp    | PyInstaller / PyOxidizer |
|----------------------------------------------|----------|------------------------------------|----------------------------------|-----------|--------------------------|
| Distribute a CLI/lib in one file             | best fit | best fit                           | works                            | works     | overkill                 |
| Ship sealed GUI/CLI to users w/o Python      | n/a      | works (esp. with `--scie`)         | n/a                              | n/a       | best fit                 |
| Run directly from compressed archive         | yes⁷     | best fit                           | best fit                         | best fit  | n/a                      |
| Reproducible install without network         | best fit | best fit                           | no - pulls from PyPI if required | possible¹ | works                    |
| Install into *any* Python env                | best fit | yes (any compatible interpreter)   | yes - installs wheels into venv  | best fit  | n/a                      |
| Include Python interpreter in artifact       | n/a      | yes (`--scie` eager/lazy)          | no                               | n/a       | yes                      |
| Use lifecycle (pre/post) scripts             | runtime³ | n/a                                | n/a                              | n/a       | build-time⁴              |
| Install from wheels using pip                | yes      | yes                                | yes                              | optional  | no                       |
| Build Docker containers with no runtime pip⁶ | best fit | works                              | works                            | works     | works                    |
| Bundle for ephemeral one-off jobs            | yes      | best fit                           | best fit                         | best fit  | overkill                 |
| Deploy without re-downloading deps           | best fit | best fit                           | partial                          | partial   | yes                      |
| Target cross-platform deployment             | limited² | yes - multi-platform support built | limited - pure-Python only       | limited   | no                       |
| Package with Conda dependencies              | roadmap⁵ | n/a                                | n/a                              | n/a       | n/a                      |
| Support compile-time customization or setup  | limited³ | n/a                                | n/a                              | n/a       | yes (scriptable)         |

##### Notes:
¹ Zipapps can embed dependencies, but behavior varies depending on how you construct the archive.  
² pychub is only cross-platform if bundled wheels themselves are portable.  
³ Only pychub supports runtime post-install user scripts.  
⁴ PyOxidizer allows scripted setup at build time, not runtime.  
⁵ Conda support is exploratory/on the roadmap for pychub. 
⁶ Multi-stage Docker: install with pychub in a builder stage (e.g., in a venv) and copy only
  the venv/app into the runtime image; the final image contains no `pip` and performs no install.
⁷ Running a `.chub` with `--exec` uses an ephemeral venv and requires `pip`.

So the point isn’t that any of these are "best" or "wrong" tools. They’re all
excellent for the jobs they were built for. Pychub simply covers a different
slice of the space: *inherently reproducible, single-file, wheel-based bundles
that install into the current Python environment without pulling from the
network*.

---

## How It Works

**NOTE: The target environment must be Python 3.9+ and it must have `pip` installed.**

When the `.chub` file is created, its name is derived from the main wheel, if
the user does not provide a name with the `--chub` option. The name is derived
from the wheel metadata, and it is formatted as `<Name>-<Version>.chub`.

While it has been mentioned that `pychub` creates reproducible installs, it
should be understood that this is not making claims about the target host state.
This is about the bundled wheels that are installed into the target environment.

When you run `pychub`, it creates a structure like this:
```bash
libs/           # your main wheel and all dependency wheels
scripts/        # lifecycle scripts parent directory
  pre/          # pre-install scripts
  post/         # post-install scripts
includes/       # additional files to include in the bundle
runtime/        # bootstrap installer
.chubconfig     # metadata: ID, version, entrypoint, post-install
__main__.py     # entry that bootstraps the runtime
```

This happens through the following steps:

1. **Copy your wheel** into `libs/`.
2. **Resolve and download dependencies** using pip (also into `libs/`).
3. **Copy additional wheels** into `libs/`.
4. **Resolve and download dependencies** for each wheel using pip (also into `libs/`).
5. **Copy any additional user-specified files** to `includes/` (with relative paths).
6. **Copy any pre- and post-install scripts** to `scripts/pre/` and `scripts/post/`.
7. **Inject the pychub runtime** and include `__main__.py` to enable the runtime CLI
   and its operations.
8. **Update the `.chubconfig`** with these details, including a metadata entry for
   the `main_wheel`.
9. **Package everything** into a `.chub` file using `zip`.
10. **Append wheels and their dependencies** to an existing `.chub`:
    - Using a single `--add-wheel` option and a comma-delimited list:
      `--add-wheel dir/second.whl,dir2/third.whl --chub existing.chub`
    - Using repeated `--add-wheel` options:
      `--add-wheel dir1/second.whl --add-wheel dir2/third.whl --chub existing.chub`

---

## CLI Parameters

This section describes the CLI commands available in `pychub` for building,
and then operating, a `.chub` file.

### Building a Chub

The `pychub` build CLI packages your Python project’s wheel and its  
dependencies into a single `.chub` file.

    usage: pychub <wheel> [build options]

| Option               | Short Form | Description                                                | Repeatable |
|----------------------|------------|------------------------------------------------------------|------------|
| `<wheel>`            | N/A        | Path to the main wheel file to process                     | no         |
| `--add-wheel`        | `-a`       | Optional path to a wheel to add (plus deps)                | yes        |
| `--chub`             | `-c`       | Optional path to the output `.chub` file                   | no         |
| `--chubproject`      | N/A        | Optional path to `chubproject.toml` as build config source | no         |
| `--chubproject-save` | N/A        | Optional path to write build config to `chubproject.toml`  | no         |
| `--entrypoint`       | `-e`       | Optional entrypoint to run after install                   | no         |
| `--include`          | `-i`       | Optional list of files to include                          | yes        |
| `--metadata-entry`   | `-m`       | Optional metadata to include in `.chubconfig`              | yes        |
| `--post-script`      | `-o`       | Optional path to post-install script(s) to include         | yes        |
| `--pre-script`       | `-p`       | Optional path to pre-install script(s) to include          | yes        |
| `--verbose`          | `-v`       | Optionally show more information when building             | no         |
| `--version`          | N/A        | Show version info and exit                                 | no         |

Notes:
- `<wheel>`:
  - Mandatory argument (except with `--add-wheel`, `--chubconfig`, or `--version`).
  - Accepts an argument of any legal path to a wheel file.
- `--add-wheel`:
  - Optional for single invocation, but required when appending wheels to an
    existing `.chub`.
- `--chub`:
  - Optional for single invocation, but required when appending wheels to an
    existing `.chub`.
  - Defaults to `<Name>-<Version>.chub` derived from wheel metadata.
- `--chubproject`:
  - Optional.
  - Requires an argument specifying the path to a `chubproject.toml` file.
  - If specified, matching file entries are overridden by the corresponding
    values on the command line.
- `--chubproject-save`:
  - Optional.
  - Requires an argument specifying the path to the destination
    `chubproject.toml` file.
  - Can be specified along with `--chubproject` to preserve changes if you
    include additional CLI options and arguments.
- `--entrypoint`:
  - Optional.
  - The value is a single string, and quoted if it contains spaces.
  - May be overridden during runtime invocation.
  - Pychub does not parse or validate the inner arguments; they are stored
    and passed verbatim to the child process when `--run` or `--exec` is used
    at runtime.
  - Formats:
    - entrypoint target:
      - `module:function [args]` (optional arguments supported).
    - console script entrypoint (PEP 621):
      - `console-script-name [args]` (optional arguments supported).
- `--include`:
  - Optional.
  - Repeatable option to supply multiple files.
  - Any legal path to a file.
  - May specify a destination relative to the installation directory.
  - Formats:
    - Single option with single file:
      `--include /path/to/file[::dest]`
    - Single option with multiple files:
      `--include /path/to/file1[::dest] /path/to/file2[::dest] /path/to/fileN[::dest]`
    - Multiple options for multiple files:
      `--include /path/to/file1[::dest] --include /path/to/file2[::dest] --include /path/to/fileN[::dest]`
- `--metadata-entry`:
  - Optional.
  - Repeatable option to supply multiple key-value pairs.
  - Values can be single items or space‑separated lists.
  - Lists are parsed as YAML arrays in the `.chubconfig` file. 
  - Formats:
    - Single option with a single key-value pair:
      `--metadata-entry key=value`
    - Single option with multiple key-value pairs:
      `--metadata-entry key1=value1 key2=value2 keyN=valueN`
    - Multiple options for multiple key-value pairs:
      `--metadata-entry key1=value1 --metadata-entry key2=value2 --metadata-entry keyN=valueN`
- `--post-script`:
  - Optional.
  - Runs after the installation, but before the entrypoint.
  - Repeatable option to supply multiple post-install scripts.
  - Any legal path to a script file.
  - Formats:
    - Single option with a single script:
      `--post-script /path/to/script.sh`
    - Single option with multiple scripts:
      `--post-script /path/to/script1.sh,/path/to/script2.sh,/path/to/scriptN.sh`
    - Multiple options for multiple scripts:
      `--post-script /path/to/script1.sh --post-script /path/to/script2.sh --post-script /path/to/scriptN.sh`
- `--pre-script`:
  - Optional.
  - Runs before installation.
  - Repeatable option to supply multiple pre-install scripts.
  - Any legal path to a script file.
  - Formats:
    - Single option with a single script:
      `--pre-script /path/to/script.sh`
    - Single option with multiple scripts:
      `--pre-script /path/to/script1.sh,/path/to/script2.sh,/path/to/scriptN.sh`
    - Multiple options for multiple scripts:
      `--pre-script /path/to/script1.sh --pre-script /path/to/script2.sh --pre-script /path/to/scriptN.sh`

#### Example Usage (build)

The usage of `pychub` should be fairly straightforward and intuitive, as you
can see in the following examples:

1. Basic build
   ```bash
   pychub dist/mypackage-1.0.0-py3-none-any.whl
   ```

2. Custom output file
   ```bash
   pychub dist/mypackage-1.0.0-py3-none-any.whl \
        --chub dist/app.chub
   ```

3. Simple callable spec (no args, and no spaces, so no quotes necessary)
   ```bash
   pychub dist/app.whl \
         --entrypoint mypkg.cli:main
   ```

4. Callable spec with arguments (quotes are required because of spaces)
   ```bash
    pychub dist/app.whl \
         --entrypoint "mypkg.cli:main --mode train --limit 100"
   ```

5. Console script with arguments (quotes are required because of spaces)
   ```bash
    pychub dist/app.whl \
         --entrypoint "mypackage-cli --verbose --config conf.yml"
   ```

6. Include a single file
   ```bash
   pychub dist/mypackage-1.0.0-py3-none-any.whl \
         --include ./extra.cfg
   ```

7. Include with destination path relative to install dir
   ```bash
   pychub dist/mypackage-1.0.0-py3-none-any.whl \
         --include README.md::docs
   ```

8. Multiple includes (comma-separated in a single flag)
   ```bash
   pychub dist/mypackage-1.0.0-py3-none-any.whl \
         --include a.txt::conf,b.json::data,c.ini
   ```

9. Multiple includes (repeat the flag)
   ```bash
   pychub dist/mypackage-1.0.0-py3-none-any.whl \
         --include a.txt \
         --include b.json::data \
         --include c.ini
   ```

10. Add pre-install scripts
    ```bash
    pychub dist/mypackage-1.0.0-py3-none-any.whl \
          --pre-script ./scripts/check_env.sh
    ```

11. Add post-install scripts (multiple via comma-separated list)
    ```bash
    pychub dist/mypackage-1.0.0-py3-none-any.whl \
         --post-script init.sh,finish.sh
    ```

12. Combine pre/post scripts with includes and entrypoint
    ```bash
    pychub dist/mypackage-1.0.0-py3-none-any.whl \
         --pre-script pre.sh \
         --post-script post.sh \
         --include config.toml::conf \
         --entrypoint mypackage.cli:main
    ```

13. Add metadata entries (single)
    ```bash
    pychub dist/mypackage-1.0.0-py3-none-any.whl \
         --metadata-entry maintainer:me@example.com
    ```

14. Add metadata entries (list value and multiple pairs in one flag)
    ```bash
    pychub dist/mypackage-1.0.0-py3-none-any.whl \
         --metadata-entry tags:http,client,cli,priority \
         --metadata-entry team:platform
    ```

15. Verbose build
    ```bash
    pychub dist/mypackage-1.0.0-py3-none-any.whl \
         --verbose
    ```

16. Append an additional wheel to an existing .chub (repeatable flag)
    ```bash
    pychub --chub dist/app.chub \
         --add-wheel dist/extras/tool-2.0.0-py3-none-any.whl \
         --add-wheel dist/extras/helper-1.2.3-py3-none-any.whl
    ```

17. Append additional wheels via a single comma-separated flag
    ```bash
    pychub --chub dist/app.chub \
         --add-wheel dist/extras/tool-2.0.0-py3-none-any.whl,dist/extras/helper-1.2.3-py3-none-any.whl
    ```

18. Show version and exit
    ```bash
    pychub --version
    ```

19. “Everything together” example
    ```bash
    pychub dist/mypackage-1.0.0-py3-none-any.whl \
         --chub dist/multi.chub \
         --entrypoint mypackage.cli:main \
         --include config.toml::conf,README.md::docs \
         --pre-script pre.sh \
         --post-script post.sh \
         --metadata-entry maintainer:me@example.com,tags:http,client \
         --verbose
    ```

### Configuring a Chub Build With `chubproject.toml`

It may be more convenient to configure a build with a `chubproject.toml` file.
As you may have guessed, its name is similar to `pyproject.toml`, and it follows
a format that is identical to what you would use in the `tool` namespace of a
`pyproject.toml` file.

Here is an example `chubproject.toml` file that includes all possible options,
and it is a bit similar to the "Everything Together" example above:

```toml
[package]
chub = "dist/mybundle.chub"
wheel = "dist/app-1.2.3.whl"
entrypoint = "pkg.cli:main"
add_wheels = ["dist/addon.whl"]
includes = [
  "docs/README.md",                  # Copies to includes/README.md
  "docs/README.md::manuals/",        # Copies to includes/manuals/README.md
  "docs/README.md::manuals/guide.md" # Copies to includes/manuals/guide.md
]
[scripts]
pre  = ["scripts/pre_check.sh"]
post = ["scripts/post_install.sh"]

[metadata]
maintainer = "you@example.com"
tags = ["http", "client"]
```

Notes:

- This example uses the "table" format. TOML syntax also accepts the "inline"
format, which is a bit more compact. While this *is* valid and acceptable, we
recommend using the "table" format for clarity. In "inline" format, the previous
example would be written as:
  ```toml
  [package]
  chub = "dist/mybundle.chub"
  wheel = "dist/app-1.2.3.whl"
  entrypoint = "pkg.cli:main"
  add_wheels = ["dist/addon.whl"]
  includes = ["README.md::docs", "config/extra.cfg::conf"]
  scripts = {pre = ["scripts/pre_check.sh"], post = ["scripts/post_install.sh"]}
  metadata = {maintainer = "you@example.com", tags = ["http", "client"]}
  ```
- The `package` namespace is optional. Not only is it optional, but namespaces
like `tool.pychub.package` are also permissible. If you do include a namespace
it must be `package`, `pychub.package`, or it must end with
`.pychub.package` (e.g., `tool.pychub.package`).
- Using a `chubproject.toml` file implies that the `.chub` build is one-shot.
While you *can* append additional wheels to an existing `.chub` file, the file
entries can only include items at initial build time. If you specify an existing
`.chub` file in the `chubproject.toml` file, pychub will exit with an error.

### Operating a Chub

When you run a `.chub` file directly with Python, it operates in  
**runtime mode** and installs its bundled wheels into the current  
Python environment (system Python, venv, conda env, etc.).

    usage: python /path/to/some.chub [runtime options] [-- [entrypoint-args...]]

The `--` token is the POSIX end‑of‑options marker. Everything after `--` is
*not* parsed by pychub and is forwarded unchanged to the entrypoint process
selected by `--run` (or the baked‑in entrypoint if none is provided).

| Option               | Short Form | Description                                        |
|----------------------|------------|----------------------------------------------------|
| `--dry-run`          | `-d`       | Show actions without performing them               |
| `--exec`             | `-e`       | Run entrypoint in a temporary venv (deleted after) |
| `--help`             | `-h`       | Show help and exit                                 |
| `--info`             | `-i`       | Display `.chub` info and exit                      |
| `--list`             | `-l`       | List bundled wheels and exit                       |
| `--no-post-scripts`  |            | Skip post install scripts                          |
| `--no-pre-scripts`   |            | Skip pre install scripts                           |
| `--no-scripts`       |            | Skip pre/post install scripts                      |
| `--quiet`            | `-q`       | Suppress output wherever possible                  |
| `--run [ENTRYPOINT]` | `-r`       | Run the baked-in or specified `ENTRYPOINT`         |
| `--show-scripts`     | `-s`       | Show the pre/post install scripts and exit         |
| `--unpack [DIR]`     | `-u`       | Extract `.chubconfig` and all wheel-related files  |
| `--venv DIR`         |            | Create a venv and install wheels into it           |
| `--version`          |            | Show version info and exit                         |
| `--verbose`          | `-v`       | Extra logs wherever possible                       |

Notes:
- `--dry-run`:
  - Prevents any changes from being made to the environment.
- `--exec`:
  - Runs as an ephemeral venv installation that is wiped after execution.
  - Runs in a **strictly temporary** venv.
  - Implies a no-arg `--run` unless explicitly provided.
  - State is not preserved between runs.
  - Since no state is preserved, this option implies `--no-scripts`
    (i.e., `--no-pre-scripts` and `--no-post-scripts`)
- `--help`:
  - Shows help and exit.
- `--info`:
  - Shows `.chubconfig` metadata.
  - When used with `--verbose`:
    - shows pre/post install scripts (like with `--show-scripts`).
    - includes `--version` information.
- `--list`:
  - Lists bundled wheels and exit.
  - Wheels are listed in the order they were added to the `.chub` file.
  - Included dependency wheels are shown under the dependent wheel:
      ```yaml
      included-wheel.whl:
      - dep1.whl
      - dep2.whl
      - depN.whl
      ```
- `--no-post-scripts`:
  - Skips post-install scripts.
- `--no-pre-scripts`:
  - Skips pre-install scripts.
- `--no-scripts`:
  - Implies `--no-post-scripts` and `--no-pre-scripts`.
- `-q`, `--quiet`:
  - Overrides `--verbose`.
  - Compatible with any other option, though results may vary.
- `--run [ENTRYPOINT]`:
  - If provided, `ENTRYPOINT` overrides the baked‑in default.
  - If omitted, it uses the baked‑in entrypoint (if present).
  - If omitted and no baked‑in entrypoint exists, **warns** and exits with
    code 0.
  - `ENTRYPOINT` format:
    - `module:function`
    - `console-script-name`
  - To pass arguments to the entrypoint, place them **after** `--` so
    pychub does not interpret them.
  - Virtual environment option compatibility:
    - `--exec` (for ephemeral venv)
    - `--venv` (for persistent venv)
- `--show-scripts`:
  - Allows verification of arbitrary pre/post install script content.
- `--unpack [DIR]`:
  - Wheels, scripts, includes, and the `.chubconfig` are extracted.
  - Specify a directory as `DIR` to extract to the specified directory.
  - If no directory is specified, the current working directory is used, and
    a directory derived from the `.chub` file name is created.
- `--version`:
  - Shows version information, regardless of verbosity, (then exits) for:
    - current environment's Python interpreter
    - pychub
    - bundled wheels
- `--venv DIR`:
  - Creates a virtual environment at path `DIR` and installs wheels into it.
- `--verbose`:
  - Ignored if `--quiet` is used.
  - Compatible with any other option, though results may vary.

# Runtime Options Compatibility Matrix

This table is a helpful compatibility matrix for runtime options.

|                   | `dry-run` | `exec` | `help` | `info` | `list` | `no-post-scripts` | `no-pre-scripts` | `no-scripts` | `quiet` | `run` | `show-scripts` | `unpack` | `venv` | `version` | `verbose` |
|-------------------|-----------|--------|--------|--------|--------|-------------------|------------------|--------------|---------|-------|----------------|----------|--------|-----------|-----------|
| `dry-run`         | —         | Yes    | No     | No     | No     | Yes               | Yes              | Yes          | Yes     | Yes   | No             | Yes      | Yes    | No        | Yes       |
| `exec`            | Yes       | —      | No     | No     | No     | Yes               | Yes              | Yes          | Yes     | Yes   | No             | No       | No     | No        | Yes       |
| `help`            | No        | No     | —      | No     | No     | No                | No               | No           | No      | No    | No             | No       | No     | No        | No        |
| `info`            | No        | No     | No     | —      | Yes    | No                | No               | No           | Yes     | No    | No             | No       | No     | No        | Yes       |
| `list`            | No        | No     | No     | Yes    | —      | No                | No               | No           | Yes     | No    | No             | No       | No     | No        | Yes       |
| `no-post-scripts` | Yes       | Yes    | No     | No     | No     | —                 | Yes              | Yes          | Yes     | Yes   | No             | No       | Yes    | No        | Yes       |
| `no-pre-scripts`  | Yes       | Yes    | No     | No     | No     | Yes               | —                | Yes          | Yes     | Yes   | No             | No       | Yes    | No        | Yes       |
| `no-scripts`      | Yes       | Yes    | No     | No     | No     | Yes               | Yes              | —            | Yes     | Yes   | No             | No       | Yes    | No        | Yes       |
| `quiet`           | Yes       | Yes    | No     | Yes    | Yes    | Yes               | Yes              | Yes          | —       | Yes   | No             | Yes      | Yes    | Yes       | Yes       |
| `run`             | Yes       | Yes    | No     | No     | No     | Yes               | Yes              | Yes          | Yes     | —     | No             | No       | Yes    | No        | Yes       |
| `show-scripts`    | No        | No     | No     | No     | No     | No                | No               | No           | No      | No    | —              | No       | No     | No        | No        |
| `unpack`          | Yes       | No     | No     | No     | No     | No                | No               | No           | Yes     | No    | No             | —        | No     | No        | Yes       |
| `venv`            | Yes       | Yes    | No     | No     | No     | Yes               | Yes              | Yes          | Yes     | Yes   | No             | No       | —      | No        | Yes       |
| `version`         | No        | No     | No     | No     | No     | No                | No               | No           | Yes     | No    | No             | No       | No     | —         | Yes       |
| `verbose`         | Yes       | Yes    | No     | Yes    | Yes    | Yes               | Yes              | Yes          | Yes     | Yes   | No             | Yes      | Yes    | Yes       | —         |

#### Example Usage (runtime)

Unpacking and operating a `.chub` file has a significant number of CLI features
when compared to building a `.chub` file, but the usage should still be fairly
straightforward and intuitive. We think that it provides a lot of flexibility
without sacrificing ease of use. The list of examples, below, is fairly
comprehensive, although you can still come up with more combinations for your
own use cases.

1. Install everything to the current environment
   ```bash
   python mypackage.chub
   ```

2. Dry-run install (no changes)
   ```bash
   python mypackage.chub --dry-run
   ```

3. Dry-run install with all pre- and post-scripts skipped
   ```bash
   python mypackage.chub \
        --dry-run \
        --no-scripts
   ```

4. Install into a new virtual environment
   ```bash
   python mypackage.chub --venv ./myenv
   ```

5. Create a venv and skip pre- and post-scripts
   ```bash
   python mypackage.chub \
        --venv ./myenv \
        --no-scripts
   ```

6. Create a venv and run the baked-in entrypoint
   ```bash
   python mypackage.chub \
        --venv ./myenv \
        --run
   ```

7. Create a venv and run a different entrypoint (module:function)
   ```bash
   python mypackage.chub \
        --venv ./myenv \
        --run othermodule.cli:main
   ```

8. Create a venv and run a different entrypoint (console script)
   ```bash
   python mypackage.chub \
        --venv ./myenv \
        --run other-cli
   ```

9. Dry-run venv creation and entrypoint run (plan only)
   ```bash
   python mypackage.chub \
        --dry-run \
        --venv ./planned-env \
        --run
   ```

10. Invoke the baked-in entrypoint with arguments
    ```bash
    python mypackage.chub --run -- --mode train --limit 100
    ```

11. Run a different entrypoint (module:function) with arguments
    ```bash
    python mypackage.chub \
         --run othermodule.cli:main \
         -- --mode train --limit 100
    ```

12. Run a different entrypoint (console script) with arguments
    ```bash
    python mypackage.chub \
         --run other-cli \
         -- --mode train --limit 100
    ```

13. Execute the baked-in entrypoint via **ephemeral install**
    ```bash
    python mypackage.chub --exec
    ```

14. Execute the baked-in entrypoint with arguments via **ephemeral install**
    ```bash
    python mypackage.chub --exec -- --mode train --limit 100
    ```

15. Execute a custom entrypoint via **ephemeral install**
    ```bash
    python mypackage.chub \
         --exec \
         --run othermodule.cli:main
    ```

16. Execute a custom entrypoint with arguments via **ephemeral install**
    ```bash
    python mypackage.chub \
         --exec \
         --run othermodule.cli:main \
         -- --mode train --limit 100
    ```

17. List bundled wheels (names)
    ```bash
    python mypackage.chub --list
    ```

18. List bundled wheels quietly
    ```bash
    python mypackage.chub \
         --list \
         --quiet
    ```

19. Unpack all contents to a directory
    ```bash
    python mypackage.chub --unpack ./tmp
    ```

20. Dry-run unpack (see what would be extracted)
    ```bash
    python mypackage.chub \
         --dry-run \
         --unpack ./tmp
    ```

21. Show chub info (metadata)
    ```bash
    python mypackage.chub --info
    ```

22. Show chub info with extra details (scripts and versions)
    ```bash
    python mypackage.chub \
         --info \
         --verbose
    ```

23. Show pre/post install scripts without running anything
    ```bash
    python mypackage.chub --show-scripts
    ```

24. Install and run baked entrypoint with verbose logs
    ```bash
    python mypackage.chub \
         --run \
         --verbose
    ```

25. Quiet install (minimal output)
    ```bash
    python mypackage.chub --quiet
    ```

26. Show full version info and exit
    ```bash
    python mypackage.chub --version
    ```

27. Help message
    ```bash
    python mypackage.chub --help
    ```
---

## Pre-install and Post-install Scripts

**NOTE: Pre-install and post-install scripts pose a security risk!**

Someone could include malicious actions when they include these scripts,
and if you run the `.chub` file with elevated privileges, they could cause
damage to your system. Either ensure that you *completely trust* the vendor
that provided the `.chub` file, or verify the script contents before you
execute/install the `.chub` file.

When pychub runs your pre- and post-install scripts, it does so as simply and
predictably as possible. Pre-install scripts run first, in the order you list
them. Post-install scripts run afterward, also in order. If any script fails
(returns a non‑zero exit code), pychub immediately stops and reports which
script has failed. Missing scripts won’t blow up the run. They’re skipped with
a warning so that you don’t get stuck on a typo.

Scripts are launched via the system shell. On POSIX, we use `/bin/sh` to launch
the script. On Windows, it’s `cmd.exe`. If you’re on Linux or macOS, and your
file contains a shebang (like `#!/usr/bin/env bash` or `#!/usr/bin/env python3`),
that shebang will control which interpreter actually runs it. On Windows, `.sh`
files won’t magically work unless you’ve got a POSIX-like shell (e.g., Git Bash
or WSL2) on your `PATH`. If you want a pain-free cross‑platform story, prefer
`.cmd`/`.bat`/`.ps1` on Windows and shell/Python scripts on POSIX, or just write
Python scripts and run them with `python`.

Please be aware that `pychub` behavior on Windows is untested. The recommended
approach for Windows users, at this time, is to use WSL2, or another POSIX-like
shell. If native Windows support is important to you, please file an issue, and
reach out to collaborate, if possible.

Finally, a word about runtime flags: `--no-scripts` disables both phases, and
`--no-pre-scripts` and `--no-post-scripts` let you skip just one side or the
other.

---

## The `.chubconfig` Metadata File

The `.chubconfig` file is a YAML text file that contains metadata about the
bundled wheels. It is used by the runtime CLI to determine what to extract,
and how to handle certain operations. Note that the metadata contains a key
of `main_wheel` that indicates the main wheel.

Here is an example `.chubconfig` file:

```yaml
---
name: my-app
version: 1.2.3
entrypoint: myapp.cli:main
scripts:
  pre:
    - install_cert.sh
  post:
    - cleanup.sh
includes:
  - extra.cfg
  - config.json::conf
wheels:
  myapp-1.2.3-py3-none-any.whl:
    - requests-2.31.0-py3-none-any.whl
    - requests_toolbelt-0.9.1-py3-none-any.whl
  mylib-0.4.2-py3-none-any.whl:
    - somedep-3.2.1-py3-none-any.whl
    - someotherdep-2.3.4-py3-none-any.whl
  otherlib-1.26.4-py3-none-any.whl: []
metadata:
  main_wheel: myapp-1.2.3-py3-none-any.whl
  tags: [http, client]
  maintainer: someone@example.com
```

---

## Roadmap

| Status      | Feature                     | Notes                                                           |
|-------------|-----------------------------|-----------------------------------------------------------------|
| In Progress | Support TOML for options    | Read/Write TOML files for options.                              |
| Planned     | Build tool support          | Support integration with `pyproject.toml`.                      |
| Planned     | Quick-start guide           | Convenience for getting started quickly.                        |
| Planned     | Handle dependency conflicts | Provide multiple-version/duplicate-wheel dependency strategies. |
| Exploring   | c/native support            | Explore facilitating c/native support (maybe with conda).       |
| Exploring   | Wheel extras support        | Explore handling extras for wheels (w/Requires-Dist).           |
| Exploring   | Conda support               | Evaluate creating/targeting conda environments.                 |
| Future      | Digital signature support   | Explore signing chub files for verification.                    |

---

## License

The MIT License (MIT)
Copyright © 2025 Steve Storck <steve973@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the “Software”), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.