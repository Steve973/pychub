# Changelog

All notable changes to **pychub** will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),  
and this project adheres to [Semantic Versioning](https://semver.org/).

You can find more information in the [Release Notes](RELEASE_NOTES.md). 

---

## [2.0.0] Unreleased

Corresponds to the [2.0.0 Release Notes entry](RELEASE_NOTES.md#version-200).

### Added
- New `--table` option for `--chubproject-save` to control which table is used
  when writing configuration.
  - `flat` → no table, top-level document only (not valid with `pyproject.toml`).
  - `tool.pychub.package` → default table.
  - `pychub.package` and `package` → also valid choices.
- Validation improvements:
  - `pyproject.toml` is always locked to `tool.pychub.package`.
  - Only `*chubproject*.toml` files are accepted for alternative layouts.
  - Invalid table arguments or filenames raise clear errors.
- Compatibility with path / develop dependencies.
  - Instead of downloading from pypi, dependency wheels for path dependency
    projects are obtained from the dist directory in that path.

### Changed
- Strengthened configuration path resolution: filenames must explicitly match
  `*chubproject*.toml` (with `-`, `_`, or `.` as valid separators).

---

## [1.x.x] Initial Release / Updates

Corresponds to the [1.x.x Release Notes entry](RELEASE_NOTES.md#version-1xx).

### Added
- Core CLI for packaging Python wheels and dependencies into a single `.chub`.
- Support for:
  - `--add-wheel` to include additional wheel dependencies.
  - `--chub` to control the output `.chub` file name.
  - `--chubproject` and `--chubproject-save` for TOML-based build configuration.
  - `--entrypoint`, `--include`, `--metadata-entry` for runtime customization.
  - `--pre-script` and `--post-script` hooks.
- Integration tests ensuring roundtrip consistency of `chubproject.toml`.

### Notes
- The 1.x.x series represents the initial release and later
  enhancements/corrections leading up to the 2.0.0 refactor.

---

[2.0.0]: https://github.com/yourname/pychub/releases/tag/v2.0.0
[1.x.x]: https://github.com/yourname/pychub/releases/tag/v1.0.0
