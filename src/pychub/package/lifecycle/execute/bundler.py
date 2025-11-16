from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from packaging.utils import parse_wheel_filename

from pychub.model.build_event import audit, StageType
from pychub.model.chubconfig_model import ChubConfig
from pychub.package.constants import (
    CHUB_BUILD_DIR,
    CHUB_LIBS_DIR,
    CHUBCONFIG_FILENAME,
    CHUB_BUILD_DIR_STRUCTURE,
    CHUB_SCRIPTS_DIR, CHUB_INCLUDES_DIR, RUNTIME_DIR,
)
from pychub.package.context_vars import current_build_plan


@audit(stage=StageType.EXECUTE, substage="write_chubconfig_file")
def write_chubconfig_file(
        dist_name: str,
        dist_ver: str,
        pinned_wheels: list[str],
        targets: list[str],
        chub_build_dir: Path) -> None:
    build_plan = current_build_plan.get()
    chubconfig_model = ChubConfig.from_mapping({
        "name": dist_name,
        "version": dist_ver,
        "entrypoint": build_plan.project.entrypoint,
        "includes": build_plan.project.includes or [],
        "scripts": {
            "pre": [n for _, n in build_plan.project.scripts.pre],
            "post": [n for _, n in build_plan.project.scripts.post]
        },
        "pinned_wheels": pinned_wheels,
        "compatibility": {"targets": targets},
        "metadata": build_plan.project.metadata
    })
    chubconfig_model.validate()
    chubconfig_file = Path(chub_build_dir / CHUBCONFIG_FILENAME).resolve()
    chubconfig_file.write_text(chubconfig_model.to_yaml(), encoding="utf-8")


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


def prepare_build_dirs(main_wheel_path: Path, chub_path: Path | None) -> tuple[Path, Path, Path]:
    chub_build_dir = create_chub_build_dir(main_wheel_path, chub_path)
    wheel_libs_dir = chub_build_dir / CHUB_LIBS_DIR
    wheel_libs_dir.mkdir(parents=True, exist_ok=True)
    path_cache_dir = chub_build_dir / ".wheel_cache"
    path_cache_dir.mkdir(parents=True, exist_ok=True)
    return chub_build_dir, wheel_libs_dir, path_cache_dir


@audit(stage=StageType.EXECUTE, substage="copy_runtime_files")
def copy_runtime_files(runtime_files_dest_dir: Path) -> None:
    """Copy runtime launcher and `__main__` entry into the build directory."""
    build_plan = current_build_plan.get()
    staged_runtime_files_dir = build_plan.cache_root / RUNTIME_DIR
    shutil.copytree(staged_runtime_files_dir, runtime_files_dest_dir, dirs_exist_ok=True)


@audit(stage=StageType.EXECUTE, substage="copy_included_files")
def copy_included_files(includes_dest_dir: Path) -> None:
    """Copy arbitrary user-specified include files into the build tree."""
    build_plan = current_build_plan.get()
    staged_includes_dir = build_plan.cache_root / CHUB_INCLUDES_DIR
    shutil.copytree(staged_includes_dir, includes_dest_dir, dirs_exist_ok=True)


@audit(stage=StageType.EXECUTE, substage="copy_install_scripts")
def copy_install_scripts(scripts_dest_dir: Path) -> None:
    """Copy pre- or post-install scripts into their target directories."""
    build_plan = current_build_plan.get()
    staged_scripts_dir = build_plan.cache_root / CHUB_SCRIPTS_DIR
    shutil.copytree(staged_scripts_dir, scripts_dest_dir, dirs_exist_ok=True)


@audit(stage=StageType.EXECUTE, substage="create_chub_archive")
def create_chub_archive(chub_build_dir: Path, chub_archive_path: Path) -> Path:
    """Create a ZIP-based .chub archive."""
    with zipfile.ZipFile(chub_archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(chub_build_dir.rglob("*"), key=lambda p: p.relative_to(chub_build_dir).as_posix()):
            if file_path.resolve() == Path(chub_archive_path).resolve():
                continue
            arcname = file_path.relative_to(chub_build_dir)
            zf.write(file_path, arcname)
    return chub_archive_path


@audit(stage=StageType.EXECUTE, substage="bundle_chub")
def bundle_chub() -> Path:
    """Bundle the final .chub archive using the prepared BuildPlan."""
    build_plan = current_build_plan.get()
    build_dir = build_plan.cache_root / CHUB_BUILD_DIR
    build_dir.mkdir(parents=True, exist_ok=True)
    libs_dir = build_dir / CHUB_LIBS_DIR
    libs_dir.mkdir(exist_ok=True)

    # Copy staged wheels from the plan's staged wheels dir
    staged_wheels_root = build_plan.staged_wheels_dir
    if not staged_wheels_root.exists():
        raise FileNotFoundError(f"Missing staged wheels: {staged_wheels_root}")

    for wheel_path in staged_wheels_root.rglob("*.whl"):
        shutil.copy2(wheel_path, libs_dir / wheel_path.name)

    # Determine primary dist info
    project = build_plan.project
    wheels = project.wheels
    if project.name and project.version:
        dist_name = project.name
        dist_ver = project.version
    elif project.wheels and len(project.wheels) >= 1:
        dist_name, dist_ver, *_ = parse_wheel_filename(wheels[0])
    else:
        raise ValueError("Missing distribution name and version")

    # Copy additional assets
    copy_runtime_files(build_dir / RUNTIME_DIR)
    copy_included_files(build_dir / CHUB_INCLUDES_DIR)
    copy_install_scripts(build_dir / CHUB_SCRIPTS_DIR)

    # Write config
    wheels_and_versions = [f"{name}=={ver}" for wheel in wheels for name, ver, *_ in [parse_wheel_filename(wheel)]]
    targets = [p.name for p in staged_wheels_root.iterdir() if p.is_dir()]
    write_chubconfig_file(dist_name, dist_ver, wheels_and_versions, targets, build_dir)

    # Assemble .chub archive
    output_path = build_plan.project.chub or (build_dir / f"{dist_name}-{dist_ver}.chub")
    output_path = create_chub_archive(build_dir, Path(output_path))

    print(f"Built {output_path}")
    return output_path
