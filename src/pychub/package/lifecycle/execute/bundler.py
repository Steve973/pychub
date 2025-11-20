from __future__ import annotations

import zipfile
from pathlib import Path

from pychub.model.build_event import audit, StageType
from pychub.model.buildplan_model import BuildPlan
from pychub.model.chubconfig_model import ChubConfig
from pychub.model.includes_model import Includes
from pychub.model.scripts_model import Scripts
from pychub.package.constants import (
    CHUB_PRE_INSTALL_SCRIPTS_DIR,
    CHUB_POST_INSTALL_SCRIPTS_DIR,
)
from pychub.package.context_vars import current_build_plan
from pychub.package.lifecycle.execute.metadata import infer_dist_identity, compute_pins_and_targets
from pychub.package.lifecycle.execute.stage_includes import copy_included_files
from pychub.package.lifecycle.execute.stage_runtime import copy_runtime_files
from pychub.package.lifecycle.execute.stage_scripts import copy_install_scripts
from pychub.package.lifecycle.execute.stage_wheels import copy_wheels_into_libs


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _get_build_plan() -> BuildPlan:
    """
    Retrieves the current active build plan from the context.

    This function fetches the active `BuildPlan` from the execution context. If no
    build plan is found, it raises a `RuntimeError`. This behavior is indicative
    of a programming error in lifecycle wiring where `INIT` or `PLAN` might not
    have executed correctly prior to this call.

    Raises:
        RuntimeError: If no active `BuildPlan` is found in the current context.

    Returns:
        BuildPlan: The currently active build plan.
    """
    plan = current_build_plan.get()
    # If this ever happens, it's a programming error in the lifecycle wiring.
    if plan is None:
        raise RuntimeError("No active BuildPlan in context; did INIT/PLAN run?")
    return plan


def _ensure_build_dirs(plan: BuildPlan) -> None:
    """
    Ensures that the necessary build directories for the given build plan are created.
    If the directories already exist, this function will not raise an error
    but will verify their existence.

    Args:
        plan: The build plan that contains the paths for the build directories
              to be created.

    """
    build_dir = plan.build_dir

    libs_dir = plan.bundled_libs_dir
    includes_dir = plan.bundled_includes_dir
    scripts_dir = plan.bundled_scripts_dir
    runtime_dir = plan.bundled_runtime_dir

    pre_dir = scripts_dir / CHUB_PRE_INSTALL_SCRIPTS_DIR
    post_dir = scripts_dir / CHUB_POST_INSTALL_SCRIPTS_DIR

    for d in (build_dir, libs_dir, includes_dir, scripts_dir, pre_dir, post_dir, runtime_dir):
        d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Bundling functions
# --------------------------------------------------------------------------- #


@audit(stage=StageType.EXECUTE, substage="write_chubconfig")
def write_chubconfig_file(
        dist_name: str,
        dist_ver: str,
        pinned_wheels: list[str],
        targets: list[str],
        includes: Includes,
        scripts: Scripts) -> Path:
    """
    Writes a ChubConfig file for the given distribution.

    This function generates and writes a ChubConfig file by combining the provided
    distribution name, version, pinned wheels, targets, includes, and scripts,
    along with the build plan and project metadata. The resulting configuration
    is validated and written to the bundled ChubConfig path.

    Args:
        dist_name (str): The distribution name.
        dist_ver (str): The version of the distribution.
        pinned_wheels (list[str]): A list of pinned wheels required for the build.
        targets (list[str]): A list of target platforms for the build.
        includes (Includes): The includes information, containing files to include in
            configuration.
        scripts (Scripts): The scripts information to include in the configuration.

    Returns:
        Path: The path to the written ChubConfig file.

    Raises:
        ValueError: If the generated ChubConfig fails validation.
        FileNotFoundError: If the write location does not exist or cannot be accessed.
    """
    plan = _get_build_plan()
    project = plan.project

    cfg = ChubConfig(
        name=dist_name,
        version=dist_ver,
        entrypoint=project.entrypoint,
        includes=includes.to_toml_inline(),
        scripts=scripts,
        pinned_wheels=pinned_wheels,
        targets=targets,
        metadata=project.metadata or {})

    cfg.validate()

    path = plan.bundled_chubconfig_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cfg.to_yaml(), encoding="utf-8")
    return path


@audit(stage=StageType.EXECUTE, substage="create_chub_archive")
def create_chub_archive(chub_build_dir: Path, chub_archive_path: Path) -> None:
    """
    Creates a ZIP archive containing the contents of a build directory.

    This function compresses all files and folders within the specified build
    directory into a ZIP archive, ensuring that the archive does not include itself
    if the archive path overlaps with the build directory.

    Args:
        chub_build_dir (Path): The directory containing files to be added to the
            ZIP archive.
        chub_archive_path (Path): The full path where the ZIP archive will be
            created.
    """
    chub_archive_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(chub_archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(
                chub_build_dir.rglob("*"),
                key=lambda p: p.relative_to(chub_build_dir).as_posix()):
            # Don't accidentally zip the archive into itself if paths overlap.
            if file_path.resolve() == chub_archive_path.resolve():
                continue
            arcname = file_path.relative_to(chub_build_dir)
            if file_path.is_file():
                zf.write(file_path, arcname.as_posix())


# --------------------------------------------------------------------------- #
# Bundler entrypoint
# --------------------------------------------------------------------------- #


@audit(stage=StageType.EXECUTE, substage="bundle_chub")
def bundle_chub() -> Path:
    """
    Executes the process of bundling a `chub` package by orchestrating various build steps.

    This function validates the build plan, creates necessary build directories, copies
    relevant files (wheels, includes, scripts, runtime resources), computes metadata
    (identity, pins, and targets), writes configuration files, and finally assembles
    the `.chub` archive into the designated directory.

    Returns:
        Path: The path to the assembled `.chub` archive.

    Raises:
        ValidationError: If the build plan fails validation.
        FileNotFoundError: If essential files for bundling are missing.
        IOError: If any file operations fail during the bundling process.
    """
    plan = _get_build_plan()
    plan.validate()

    # Ensure that the build directory structure exists
    _ensure_build_dirs(plan)

    # 1. wheels -> libs/
    copied_wheels = copy_wheels_into_libs()

    # 2. includes -> includes/
    includes = copy_included_files()

    # 3. scripts -> scripts/pre and scripts/post
    scripts = copy_install_scripts()

    # 4. runtime resources, if any
    copy_runtime_files()

    # 5. compute identity, pins, and targets
    dist_name, dist_ver = infer_dist_identity(plan, copied_wheels)
    pinned_wheels, targets = compute_pins_and_targets(plan, copied_wheels)

    # 6. write .chubconfig inside the build dir
    write_chubconfig_file(dist_name, dist_ver, pinned_wheels, targets, includes, scripts)

    # 7. assemble the final .chub archive
    project = plan.project
    if project.chub:
        output_path = Path(project.chub)
    else:
        output_path = plan.build_dir / f"{dist_name}-{dist_ver}.chub"

    create_chub_archive(plan.build_dir, output_path)

    return output_path
