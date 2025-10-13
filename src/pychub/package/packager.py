from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import zipfile
from email.parser import Parser
from pathlib import Path
from pathlib import PurePath
from typing import Union, List

import yaml
from packaging.tags import Tag
from packaging.utils import parse_wheel_filename

from .compatibility import compute_per_combo_wheel_map, enumerate_valid_combos, tag_to_str
from .constants import (
    CHUB_BUILD_DIR,
    CHUB_LIBS_DIR,
    CHUB_SCRIPTS_DIR,
    CHUBCONFIG_FILENAME,
    RUNTIME_DIR,
    CHUB_POST_INSTALL_SCRIPTS_DIR,
    CHUB_PRE_INSTALL_SCRIPTS_DIR,
    CHUB_BUILD_DIR_STRUCTURE,
    CHUB_INCLUDES_DIR)
from .pathdeps.discover import collect_path_dependencies
from ..helper.stream import Stream
from ..model.chubconfig_model import ChubConfig
from ..model.chubproject_model import ChubProject
from ..model.project_context import ProjectContext

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
            stem, dot, ext = base.rpartition(".")
            base = f"{(stem or base)}({n}){dot}{ext}"
        out.append((Path(src), f"{i:0{width}d}_{base}"))
    return out


def _flatten(values):
    """Flatten lists that may be appended by argparse (list[list[str]]).
    Keeps non-list items as-is.
    """
    if not values:
        return []
    flat = []
    for v in values:
        if isinstance(v, (list, tuple)):
            flat.extend(v)
        else:
            flat.append(v)
    return flat


def _paths(values):
    """Convert a (possibly nested) list of paths to Path objects.
    Filters out non-existent files.
    """
    out: list[Path] = []
    for item in _flatten(values):
        p = Path(item).expanduser().resolve()
        if p.exists() and p.is_file():
            out.append(p)
    return out


def _includes(values):
    """Return raw include strings (preserving `src::dest`).
    Also validates that `src` exists.
    """
    out: list[str] = []
    for item in _flatten(values):
        s = str(item)
        src = s.split("::", 1)[0]
        p = Path(src).expanduser().resolve()
        if not p.exists() or not p.is_file():
            continue
        # Preserve the original token including ::dest
        out.append(s)
    return out


def create_chub_archive(chub_build_dir: Path, chub_archive_path: Path) -> Path:
    with zipfile.ZipFile(chub_archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(chub_build_dir.rglob("*"), key=lambda p: p.relative_to(chub_build_dir).as_posix()):
            if file_path.resolve() == Path(chub_archive_path).resolve():
                continue
            arcname = file_path.relative_to(chub_build_dir)
            zf.write(file_path, arcname)
    return chub_archive_path


def analyze_compatibility(chubproject: ChubProject) -> list[str]:
    """
    Given a ChubProject, return a deduplicated list of valid
    (interpreter-abi-platform) combo strings for which the bundle would
    be compatible. Used for --analyze-compatibility reporting.
    """
    wheel_files, _, _ = resolve_all_dependency_wheels(chubproject, reuse_cache=Path(".wheel_cache"))
    return (
        Stream(enumerate_valid_combos(wheel_files))
        .map(lambda tag: tag_to_str(Tag(tag[0], tag[1], tag[2])))
        .distinct()
        .to_list())


def write_chubconfig_files(
        dist_name: str,
        dist_ver: str,
        project_context: ProjectContext,
        per_combo_wheel_map: dict[str, dict[str, str]],
        chub_build_dir: Path) -> None:
    chubconfig_model = ChubConfig.from_mapping({
        "name": dist_name,
        "version": dist_ver,
        "entrypoint": project_context.entrypoint,
        "includes": project_context.includes or [],
        "scripts": {
            "pre": [n for _, n in project_context.pre_scripts],
            "post": [n for _, n in project_context.post_scripts]
        },
        "compatibility": {"targets": list(per_combo_wheel_map.keys())},
        "metadata": project_context.metadata
    })
    chubconfig_model.validate()
    chubconfig_file = Path(chub_build_dir / CHUBCONFIG_FILENAME).resolve()
    chubconfig_file.write_text(chubconfig_model.to_yaml(), encoding="utf-8")

    (
        Stream(per_combo_wheel_map.items())
        .filter(lambda pair: bool(pair[1]))
        .for_each(
            lambda pair: Path(chub_build_dir, f"{pair[0]}.chubconfig").write_text(
                yaml.dump({"wheels": sorted(pair[1].values())}, indent=2),
                encoding="utf-8"))
    )


def copy_runtime_files(chub_build_dir: Path) -> None:
    candidates = [
        Path(__file__).resolve().parent.parent / RUNTIME_DIR,  # src/pychub/runtime
        Path(__file__).resolve().parent / RUNTIME_DIR,         # src/pychub/package/runtime (legacy)
    ]
    runtime_src = next((p for p in candidates if p.exists()), None)
    if runtime_src is None:
        tried = " | ".join(str(p) for p in candidates)
        raise FileNotFoundError(
            f"Runtime directory not found. Looked in: {tried}")

    runtime_dst = chub_build_dir / RUNTIME_DIR
    shutil.copytree(runtime_src, runtime_dst, dirs_exist_ok=True)

    # Ensure archive runs via `python test_pkg.chub`
    chub_main_py = chub_build_dir / "__main__.py"
    chub_main_py.write_text(
        f"import runpy; runpy.run_module('{RUNTIME_DIR}', run_name='__main__')",
        encoding="utf-8")


def copy_included_files(chub_base: Path, included_files: list[str] | []) -> None:
    if not included_files:
        return

    for item in included_files:
        if "::" in item:
            src_str, dest_str = item.split("::", 1)
        else:
            src_str, dest_str = item, ""

        src = Path(src_str).expanduser().resolve()
        if not src.is_file():
            raise FileNotFoundError(f"Included file not found: {src_str}")

        includes_dir = chub_base / CHUB_INCLUDES_DIR
        if dest_str and dest_str.endswith(("/", "\\")):
            # It's a directory target, so append the filename
            dest_path = (includes_dir / dest_str / src.name).resolve()
        elif dest_str:
            # It's a filename target
            dest_path = (includes_dir / dest_str).resolve()
        else:
            # No destination given — default to src.name
            dest_path = (includes_dir / src.name).resolve()

        # Prevent directory traversal
        if not str(dest_path).startswith(str(includes_dir)):
            raise ValueError(f"Destination '{dest_path}' escapes chub includes directory '{includes_dir}'")

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_path)


def copy_install_scripts(
    scripts_base: Path,
    install_scripts: list[tuple[Path, str]] | [],
    scripts_type: str) -> None:
    if not install_scripts:
        return

    script_base = scripts_base / scripts_type
    for item in install_scripts:
        path, name = item
        src = Path(path).expanduser().resolve()
        if not src.is_file():
            raise FileNotFoundError(f"The {scripts_type}-install script was not found: {item}")
        dest_path = (script_base / name).resolve()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_path)


def download_wheel_deps(
    wheel_path: str | Path,
    dest: str | Path,
    only_binary: bool = True,
    extra_pip_args: list[str] | None = None,
    find_links: Path | None = None,
    no_index: bool = False,) -> list[str]:
    wheel_path = str(Path(wheel_path).resolve())
    dest = Path(dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    before = set(dest.glob("*.whl"))

    cmd = [sys.executable, "-m", "pip", "download", wheel_path, "--dest", str(dest)]
    if only_binary:
        cmd += ["--only-binary", ":all:"]
    if find_links:
        cmd += ["--find-links", str(find_links)]
    if no_index:
        cmd += ["--no-index"]
    if extra_pip_args:
        cmd += list(extra_pip_args)

    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"pip download failed:\n{result.stderr}")
    after = set(dest.glob("*.whl"))
    return sorted(f.name for f in (after - before))


def get_wheel_metadata(wheel_path: str | Path,
                       *,
                       normalize_name: bool = True) -> tuple[str, str]:
    wheel_path = Path(wheel_path)
    if wheel_path.suffix != ".whl":
        raise ValueError(f"Not a wheel: {wheel_path}")
    with zipfile.ZipFile(wheel_path) as z:
        meta_filename = next(
            (n for n in z.namelist() if n.endswith(".dist-info/METADATA")),
            None)
        if not meta_filename:
            raise ValueError("METADATA file not found in wheel")
        meta_text = z.read(meta_filename).decode("utf-8", errors="replace")
    msg = Parser().parsestr(meta_text)
    name = msg.get("Name")
    version = msg.get("Version")
    if not name or not version:
        raise ValueError("Missing Name or Version in METADATA")
    if normalize_name:
        name = name.replace("_", "-").replace(" ", "-").lower()
    return name, version


def resolve_wheel_recursive(
    wheel_path: Path,
    libs_dir: Path,
    cache_dir: Path,
    mode: str = "cache-first",  # or "pypi-only"
    seen: set[tuple[str, str]] | None = None) -> None:
    if seen is None:
        seen = set()

    name, version = get_wheel_metadata(wheel_path)
    key = (name, version)
    if key in seen:
        return
    seen.add(key)

    # 1) Try local-only first when in cache-first mode
    touched_pypi = False
    try:
        if mode == "cache-first":
            new_files = download_wheel_deps(
                wheel_path, libs_dir, find_links=cache_dir, no_index=True)
        else:
            new_files = download_wheel_deps(wheel_path, libs_dir)
    except RuntimeError:
        # Local-only failed => flip this branch to PyPI
        touched_pypi = True
        new_files = download_wheel_deps(wheel_path, libs_dir)

    # 2) Recurse into newly downloaded deps
    for fname in new_files:
        dep_path = libs_dir / fname
        dep_name, dep_version = get_wheel_metadata(dep_path)
        dep_key = (dep_name, dep_version)
        if dep_key in seen:
            continue

        # once we’ve touched PyPI in this branch, stay PyPI-only downstream
        next_mode = "pypi-only" if (touched_pypi or mode == "pypi-only") else "cache-first"
        resolve_wheel_recursive(dep_path, libs_dir, cache_dir, next_mode, seen)


def create_chub_build_dir(wheel_path: str | Path,
                          chub_path: str | Path | None = None) -> Path:
    wheel_path = Path(wheel_path).resolve()
    if wheel_path.suffix != ".whl":
        raise ValueError(f"Not a wheel: {wheel_path}")
    chub_build_root = wheel_path.parent if chub_path is None else Path(chub_path).resolve().parent
    for dir_item in CHUB_BUILD_DIR_STRUCTURE:
        (chub_build_root / dir_item).mkdir(parents=True, exist_ok=True)
    chub_build_dir = Path(chub_build_root / CHUB_BUILD_DIR).resolve()
    Path(chub_build_dir / CHUBCONFIG_FILENAME).resolve().touch(exist_ok=True)
    return chub_build_dir


def verify_pip() -> None:
    """Ensure pip is available for the current Python.

    We verify `python -m pip --version` instead of relying on a `pip` script on
    PATH.
    """
    code = subprocess.call([sys.executable, "-m", "pip", "--version"])  # noqa: S603
    if code != 0:
        raise RuntimeError(
            "pip not found. Ensure 'python -m pip' works in this environment.")


def validate_files_exist(files: list[str] | [], context: str) -> None:
    for file in files:
        src = file.split("::", 1)[0] if "::" in file else file
        path = Path(src).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"{context} file not found: {src}")


def validate_chub_structure(chub_build_dir: Path,
                            post_install_scripts: list[str] | [],
                            pre_install_scripts: list[str] | [],
                            included_files: list[str] | []) -> None:
    # 1. Ensure the build dir exists and has a .chubconfig
    chubconfig_file = chub_build_dir / CHUBCONFIG_FILENAME
    if not chubconfig_file.exists():
        raise FileNotFoundError(f"Missing {CHUBCONFIG_FILENAME} in {chub_build_dir}")

    # 2. Confirm no leftover junk in libs/scripts
    libs = chub_build_dir / CHUB_LIBS_DIR
    if libs.exists() and any(p.is_file() for p in libs.iterdir()):
        raise FileExistsError(f"libs/ in {chub_build_dir} is not empty")
    scripts = chub_build_dir / CHUB_SCRIPTS_DIR
    if scripts.exists() and any(p.is_file() for p in scripts.iterdir()):
        raise FileExistsError(f"scripts/ in {chub_build_dir} is not empty")

    # 3. Validate included files
    if included_files:
        validate_files_exist(included_files, context="Include")

    # 4. Validate pre- and post-install scripts
    for script_tuple in [("post", post_install_scripts), ("pre", pre_install_scripts)]:
        script_type, scripts = script_tuple
        validate_files_exist(scripts, context=f"{script_type}-install")


def absolutize_paths(paths: Union[str, List[str]], base_dir: Path) -> Union[str, List[str]]:
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


def prepare_project(chubproject: ChubProject) -> ProjectContext:
    entrypoint = chubproject.entrypoint
    metadata = chubproject.metadata or {}
    project_dir = (
        Path(metadata["__file__"]).parent.resolve()
        if "__file__" in metadata
        else Path(".").resolve())
    wheel_paths: list[Path] = []
    if chubproject.wheel:
        wheel_paths.append(Path(chubproject.wheel).expanduser().resolve())
    wheel_paths.extend(_paths(chubproject.add_wheels))

    post_install_scripts = prefixed_script_names(absolutize_paths(chubproject.scripts.post, project_dir)) if chubproject.scripts.post else []
    pre_install_scripts = prefixed_script_names(absolutize_paths(chubproject.scripts.pre, project_dir)) if chubproject.scripts.pre else []

    included_files = []
    for inc_mod in (chubproject.includes or []):
        inc = inc_mod.as_string()
        if "::" in inc:
            src, dest = inc.split("::", 1)
            included_files.append(f"{absolutize_paths(src, project_dir)}::{dest}")
        else:
            included_files.append(f"{absolutize_paths(inc, project_dir)}")

    return ProjectContext(project_dir=project_dir,
                          entrypoint=entrypoint,
                          metadata=metadata,
                          wheel_paths=wheel_paths,
                          post_scripts=post_install_scripts,
                          pre_scripts=pre_install_scripts,
                          includes=included_files)


def prepare_build_dirs(main_wheel_path: Path, chub_path: Path | None) -> tuple[Path, Path, Path]:
    chub_build_dir = create_chub_build_dir(main_wheel_path, chub_path)
    wheel_libs_dir = chub_build_dir / CHUB_LIBS_DIR
    wheel_libs_dir.mkdir(parents=True, exist_ok=True)
    path_cache_dir = chub_build_dir / ".wheel_cache"
    path_cache_dir.mkdir(parents=True, exist_ok=True)
    return chub_build_dir, wheel_libs_dir, path_cache_dir


def stage_path_dependencies(project_dir: Path, cache_dir: Path) -> None:
    path_projects = collect_path_dependencies(project_dir / "pyproject.toml")
    for proj_root, strategy in path_projects.items():
        dist_dir = proj_root / "dist"
        if not dist_dir.exists():
            raise FileNotFoundError(f"[{strategy}] {proj_root} has no dist/ directory")
        wheels = list(dist_dir.glob("*.whl"))
        if not wheels:
            raise FileNotFoundError(f"[{strategy}] {proj_root} has no wheel in dist/")
        for w in wheels:
            shutil.copy2(w, cache_dir / w.name)


def resolve_wheels(
    wheel_paths: list[Path],
    libs_dir: Path,
    cache_dir: Path) -> dict[str, list[str]]:
    seen: set[tuple[str, str]] = set()
    wheels_map: dict[str, list[str]] = {}
    for wp in wheel_paths:
        shutil.copy2(wp, libs_dir / wp.name)
        resolve_wheel_recursive(wp, libs_dir, cache_dir, "cache-first", seen)
        wheels_map[wp.name] = [f for f in os.listdir(libs_dir) if f.endswith(".whl")]
    return wheels_map


def resolve_all_dependency_wheels(
    chubproject: ChubProject,
    reuse_cache: Path | None = None) -> tuple[dict[str, list[str]], Path, ProjectContext]:
    """
    Resolves all dependency wheels for a ChubProject, handling path deps.
    Returns (wheel_files mapping, cache_dir used, and the ProjectContext).
    """
    project_context = prepare_project(chubproject)
    if not project_context.wheel_paths:
        raise ValueError("No wheels provided")

    # Use a real or temp cache dir
    if reuse_cache:
        path_cache_dir = Path(reuse_cache).resolve()
        path_cache_dir.mkdir(parents=True, exist_ok=True)
    else:
        import tempfile
        path_cache_dir = Path(tempfile.mkdtemp())

    # Stage path deps (for local wheel resolution)
    stage_path_dependencies(project_context.project_dir, path_cache_dir)

    # Download/resolve all wheels
    wheel_files = resolve_wheels(
        project_context.wheel_paths,
        path_cache_dir,  # use as libs_dir for analysis
        path_cache_dir)

    return wheel_files, path_cache_dir, project_context


def build_chub(chubproject: ChubProject) -> Path:
    verify_pip()

    # Use the new utility to resolve all wheels (and get build context)
    wheel_files, path_cache_dir, project_context = resolve_all_dependency_wheels(chubproject, reuse_cache=None)

    # Create the build dirs as before
    main_wheel_name = str(project_context.metadata.get("main_wheel", Path(project_context.wheel_paths[0]).name))
    main_wheel_path = next(
        (p for p in project_context.wheel_paths if p.name == main_wheel_name),
        project_context.wheel_paths[0])
    chub_build_dir, wheel_libs_dir, _ = prepare_build_dirs(main_wheel_path, chubproject.chub)

    validate_chub_structure(
        chub_build_dir,
        [str(p) for p, _ in project_context.post_scripts],
        [str(p) for p, _ in project_context.pre_scripts],
        project_context.includes)

    (
        Stream(wheel_files.values())
        .flat_map(lambda ws: ws)
        .for_each(lambda wheel_name: (
            shutil.copy2(path_cache_dir / wheel_name, wheel_libs_dir / wheel_name)
            if not (wheel_libs_dir / wheel_name).exists() else None))
    )

    stage_path_dependencies(project_context.project_dir, path_cache_dir)
    wheels_map = resolve_wheels(project_context.wheel_paths, wheel_libs_dir, path_cache_dir)
    per_combo_wheel_map = compute_per_combo_wheel_map(wheels_map)
    dist_name, dist_ver, *_ = parse_wheel_filename(main_wheel_name)
    dist_name, dist_ver = chubproject.name or dist_name, chubproject.version or dist_ver
    script_base = chub_build_dir / CHUB_SCRIPTS_DIR
    copy_install_scripts(script_base, project_context.post_scripts, CHUB_POST_INSTALL_SCRIPTS_DIR)
    copy_install_scripts(script_base, project_context.pre_scripts,  CHUB_PRE_INSTALL_SCRIPTS_DIR)
    copy_included_files(chub_build_dir, project_context.includes)
    copy_runtime_files(chub_build_dir)
    write_chubconfig_files(dist_name, dist_ver, project_context, per_combo_wheel_map, chub_build_dir)
    chub_path = chubproject.chub or (chub_build_dir / f"{dist_name}-{dist_ver}.chub")
    output_path = create_chub_archive(chub_build_dir, Path(chub_path))
    print(f"Built {output_path}")
    return output_path
