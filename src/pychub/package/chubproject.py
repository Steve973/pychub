from __future__ import annotations

from pathlib import Path
from typing import Any

from pychub.model.chubproject_model import ChubProject

# --- reader: tomllib on 3.11+, tomli on 3.9–3.10 ---
try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

# --- optional writers: pick any one to be installed ---
_TOML_WRITER = None
for _name in ("tomli_w", "tomlkit", "toml"):
    try:
        _TOML_WRITER = __import__(_name)
        break
    except ModuleNotFoundError:
        pass


class ChubProjectError(Exception):
    pass


def load_chubproject(path: str | Path) -> ChubProject:
    """
    Load a chubproject TOML file from disk.

    - PATH is the filesystem path to the TOML file (e.g., passed via --chubproject PATH).
    - Supports flexible namespacing inside the file via ChubProject.from_toml_document:
        [package], [pychub.package], or any table ending with ".pychub.package".
    - After parsing, records the file's absolute path under metadata["__file__"].
    """
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise ChubProjectError(f"Project file not found: {p}")

    try:
        with p.open("rb") as f:
            doc = tomllib.load(f)
    except Exception as e:
        raise ChubProjectError(f"Failed to parse TOML at {p}") from e

    # Let the model handle namespace discovery inside the TOML document
    proj = ChubProject.from_toml_document(doc)

    return ChubProject.merge_from_cli_args(
        proj,
        {"metadata_entry": [f"__file__={p.as_posix()}"]})


def save_chubproject(
    project: ChubProject | dict,
    path: str | Path = "chubproject.toml",
    *,
    overwrite: bool = False,
    make_parents: bool = True) -> Path:
    if _TOML_WRITER is None:
        raise ChubProjectError(
            "Saving requires a TOML writer. Install one of:\n"
            "  pip install tomli-w   # preferred\n"
            "  pip install tomlkit   # also works\n"
            "  pip install toml      # legacy")

    # accept either a ChubProject or a raw mapping
    if isinstance(project, ChubProject):
        obj = project.to_mapping()
    else:
        # Parse from the mapping to validate, then return to mapping
        obj = ChubProject.from_mapping(project).to_mapping()
    obj = {"package": {k: v for k, v in obj.items() if v is not None}}

    p = Path(path).expanduser().resolve()
    if p.exists() and not overwrite:
        raise ChubProjectError(f"Refusing to overwrite without overwrite=True: {p}")
    if make_parents:
        p.parent.mkdir(parents=True, exist_ok=True)

    def _coerce(x: Any):
        if isinstance(x, Path):
            return x.as_posix()
        if isinstance(x, dict):
            return {str(k): _coerce(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [_coerce(v) for v in x]
        if isinstance(x, set):
            return sorted(_coerce(v) for v in x)
        return x

    text = _TOML_WRITER.dumps(_coerce(obj))  # type: ignore[attr-defined]
    p.write_text(text, encoding="utf-8")
    return p
