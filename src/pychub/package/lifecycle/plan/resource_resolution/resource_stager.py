from __future__ import annotations

import re
import shutil
from pathlib import Path, PurePath
from typing import Union

from pychub.model.build_event import audit
from pychub.model.buildplan_model import BuildPlan
from pychub.model.includes_model import IncludeSpec
from pychub.package.constants import (
    RUNTIME_DIR
)

_ALLOWED = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize(p: str | PurePath) -> str:
    parts = [s for s in PurePath(p).parts if s not in ("", ".", "..", "/")]
    name = "_".join(parts) or "script"
    name = _ALLOWED.sub("_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "script"


def prefixed_script_names(paths: list[str | Path]) -> list[tuple[Path, str]]:
    """Return (src_path, dest_name) with a zero-padded index prefix.
    Lexical sort preserves input order; width grows when >=100 items.
    """
    width = max(2, len(str(max(len(paths) - 1, 0))))
    seen: dict[str, int] = {}
    out: list[tuple[Path, str]] = []
    for i, src in enumerate(paths):
        base = _sanitize(src)
        key = base.lower()
        n = seen.get(key, 0)
        seen[key] = n + 1
        if n:  # dedupe while preserving extension
            if "." in base:
                stem, dot, ext = base.rpartition(".")
                base = f"{stem}({n}){dot}{ext}"
            else:
                base = f"{base}({n})"
        out.append((Path(src), f"{i:0{width}d}_{base}"))
    return out


@audit(stage="PLAN", substage="copy_runtime_files")
def copy_runtime_files(plan: BuildPlan, runtime_dir: Path) -> None:
    """Copy runtime launcher and `__main__` entry into the build directory."""
    runtime_src = Path(__file__).resolve().parent.parent.parent / RUNTIME_DIR
    shutil.copytree(runtime_src, runtime_dir, dirs_exist_ok=True)


def absolutize_paths(paths: Union[str, list[str]], base_dir: Path) -> Union[str, list[str]]:
    """
    Ensures that each path is absolute. If a path is not absolute, it is joined with base_dir.
    If a single string is passed, a single string is returned. Otherwise, a list is returned.
    """
    is_single = isinstance(paths, str)
    path_list = [paths] if is_single else paths

    resolved = [
        str(Path(p)) if Path(p).is_absolute() else str((base_dir / p).resolve())
        for p in path_list
    ]

    return resolved[0] if is_single else resolved


@audit(stage="PLAN", substage="copy_included_files")
def copy_included_files(plan: BuildPlan, includes_dir: Path, includes: list[IncludeSpec]) -> None:
    """Copy arbitrary user-specified include files into the build tree."""
    if not includes:
        return

    included_files = []
    for inc_mod in (includes or []):
        inc = inc_mod.as_string()
        if "::" in inc:
            src, dest = inc.split("::", 1)
            included_files.append(f"{absolutize_paths(src, plan.project_dir)}::{dest}")
        else:
            included_files.append(f"{absolutize_paths(inc, plan.project_dir)}")

    includes_dir.mkdir(parents=True, exist_ok=True)

    for item in included_files:
        src_str, dest_str = (item.split("::", 1) + [""])[:2]
        src = Path(src_str).expanduser().resolve()
        if not src.is_file():
            raise FileNotFoundError(f"Included file not found: {src_str}")

        dest_path = includes_dir / (dest_str or src.name)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_path)


def copy_install_scripts(scripts_dir: Path, script_paths: list[str], script_type: str) -> None:
    """Copy pre- or post-install scripts into their target directories."""
    if not script_paths:
        return

    scripts = prefixed_script_names(script_paths)
    base = scripts_dir / script_type
    base.mkdir(parents=True, exist_ok=True)
    for src_path, dest_name in scripts:
        src = Path(src_path).expanduser().resolve()
        if not src.is_file():
            raise FileNotFoundError(f"{script_type}-install script not found: {src}")
        shutil.copy2(src, base / dest_name)


@audit(stage="PLAN", substage="copy_post_install_scripts")
def copy_post_install_scripts(plan: BuildPlan, scripts_dir: Path, script_paths: list[str]) -> None:
    copy_install_scripts(scripts_dir, script_paths, "post")


@audit(stage="PLAN", substage="copy_pre_install_scripts")
def copy_pre_install_scripts(plan: BuildPlan, scripts_dir: Path, script_paths: list[str]) -> None:
    copy_install_scripts(scripts_dir, script_paths, "pre")
