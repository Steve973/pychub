from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from typing import Iterable, Tuple, List

from packaging.utils import parse_wheel_filename

from pychub.model.build_event import audit, StageType
from pychub.model.buildplan_model import BuildPlan
from pychub.model.chubconfig_model import ChubConfig
from pychub.model.includes_model import Includes
from pychub.model.scripts_model import Scripts, ScriptSpec, ScriptType
from pychub.model.wheels_model import WheelCollection, WheelArtifact
from pychub.package.constants import (
    CHUB_PRE_INSTALL_SCRIPTS_DIR,
    CHUB_POST_INSTALL_SCRIPTS_DIR,
)
from pychub.package.context_vars import current_build_plan


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


def _infer_dist_identity(
        plan: BuildPlan,
        wheel_paths: Iterable[Path]) -> Tuple[str, str]:
    """
    Infers the distribution name and version based on the given BuildPlan or wheel paths.

    This function determines the distribution name and version using the following priority:
    1. Uses explicit project name and version if provided in the BuildPlan.
    2. Checks for primary artifacts within the WheelCollection of the BuildPlan, if available.
    3. Falls back to parsing the filename of the first provided wheel path.

    Args:
        plan (BuildPlan): The build plan containing project details and potentially a
            WheelCollection.
        wheel_paths (Iterable[Path]): An iterable of Path objects representing the
            wheel files.

    Returns:
        Tuple[str, str]: A tuple containing the inferred name and version of the
            distribution.

    Raises:
        ValueError: If the distribution name and version cannot be determined from the
            provided BuildPlan or wheel paths.
    """
    project = plan.project

    # 1. If the project explicitly names itself, trust that.
    if project.name and project.version:
        return project.name, project.version

    # 2. If we have a WheelCollection on the plan, try primary artifacts.
    wheels_collection = getattr(plan, "wheels", None)
    if isinstance(wheels_collection, WheelCollection) and len(wheels_collection):
        primaries: List[WheelArtifact] = wheels_collection.primary or list(wheels_collection)
        if primaries:
            w0 = primaries[0]
            return w0.name, str(w0.version)

    # 3. Fallback: parse the first wheel filename we actually copied.
    wheel_paths = list(wheel_paths)
    if wheel_paths:
        name, version, *_ = parse_wheel_filename(wheel_paths[0].name)
        return name, str(version)

    raise ValueError("Unable to infer distribution name/version from BuildPlan or wheels")


def _compute_pins_and_targets(
        plan: BuildPlan,
        wheel_paths: Iterable[Path]) -> Tuple[list[str], list[str]]:
    """
    Compute a set of pinned dependencies and a list of supported targets based on
    the provided build plan and wheel paths.

    If the `plan` contains a valid `WheelCollection`, it identifies primary
    wheels and determines their pinned dependencies and targets. Otherwise, it
    falls back to pinning all dependencies from the given wheel paths.

    Args:
        plan (BuildPlan): The build plan containing information about wheels
            and their compatibility.
        wheel_paths (Iterable[Path]): An iterable of wheel file paths used as
            a fallback if the `plan` lacks valid wheel information.

    Returns:
        Tuple[list[str], list[str]]: A tuple where the first element is a sorted
        list of pinned dependencies (formatted as `<name>==<version>`) and the
        second element is a list of supported target strings.
    """
    wheels_collection = getattr(plan, "wheels", None)
    pinned: set[str] = set()

    if isinstance(wheels_collection, WheelCollection) and len(wheels_collection):
        primaries = wheels_collection.primary or list(wheels_collection)
        for w in primaries:
            pinned.add(f"{w.name}=={w.version}")
        targets: list[str] = wheels_collection.supported_target_strings
        return sorted(pinned), targets

    # Fallback: just pin everything we copied, ignore compatibility for now.
    for p in wheel_paths:
        name, version, *_ = parse_wheel_filename(p.name)
        pinned.add(f"{name}=={version}")

    return sorted(pinned), []


def _stage_includes(plan: BuildPlan) -> Includes:
    """
    Normalize and retrieves the includes for a given build plan.

    This function checks if the provided build plan contains pre-stored
    normalized include files. If available, it directly returns them.
    Otherwise, it normalizes and derives them from the raw project
    configuration.

    Args:
        plan (BuildPlan): The build plan containing project and configuration
            details required to determine the included files.

    Returns:
        Includes: An instance of the Includes object representing the
            normalized include files for the given plan.
    """
    project = plan.project
    project_dir = plan.project_dir

    # If PLAN eventually stores normalized Includes on the plan, prefer that.
    includes = getattr(plan, "include_files", None)
    if isinstance(includes, Includes):
        return includes

    # Otherwise, normalize from the raw project configuration.
    return Includes.from_toml(project.includes, base_dir=project_dir)


def _stage_scripts(plan: BuildPlan) -> Scripts:
    """
    Normalizes and stages scripts for installation based on the provided build plan.

    This function handles the preparation of script specifications by analyzing the
    project's pre-installation and post-installation scripts, resolving their paths,
    determining their types, and returning a `Scripts` object that encapsulates the
    staged scripts. If the build plan already contains predefined install scripts,
    those are used instead.

    Args:
        plan (BuildPlan): The build plan containing all the configuration and project
            details needed for staging scripts.

    Returns:
        Scripts: An object encapsulating the normalized and deduplicated script
            specifications for installation.
    """
    project = plan.project
    project_dir = plan.project_dir

    # If PLAN eventually stores Scripts on the plan, prefer that.
    scripts = getattr(plan, "install_scripts", None)
    if isinstance(scripts, Scripts):
        return scripts

    # Otherwise, normalize directly from the project-level lists.
    items: list[ScriptSpec] = []

    for s in project.pre_scripts or []:
        src = Path(s)
        if not src.is_absolute():
            src = (project_dir / src).expanduser().resolve()
        items.append(ScriptSpec(src=src, script_type=ScriptType.PRE))

    for s in project.post_scripts or []:
        src = Path(s)
        if not src.is_absolute():
            src = (project_dir / src).expanduser().resolve()
        items.append(ScriptSpec(src=src, script_type=ScriptType.POST))

    return Scripts(_items=Scripts.dedup(items))


# --------------------------------------------------------------------------- #
# EXECUTE substages
# --------------------------------------------------------------------------- #


@audit(stage=StageType.EXECUTE, substage="copy_wheels")
def copy_wheels_into_libs() -> list[Path]:
    """
    Copies all wheel files from the staged directory into the directory of bundled libraries.

    This function retrieves the build plan and identifies the staged wheels directory and the
    target-bundled libraries directory. It ensures that the directory containing the staged
    wheel files exists, then iterates through all the `.whl` files in the directory, copying
    each one into the target-bundled libraries directory. It also ensures that the required
    directories in the target location are created if they do not already exist. The function
    returns a sorted list of paths to the copied wheel files.

    Returns:
        list[Path]: A sorted list of paths to the copied wheel files.

    Raises:
        FileNotFoundError: If the directory containing the staged wheel files does not exist.
    """
    plan = _get_build_plan()
    staged_root = plan.staged_wheels_dir
    libs_dir = plan.bundled_libs_dir

    if not staged_root.exists():
        raise FileNotFoundError(f"Missing staged wheels at {staged_root}")

    copied: list[Path] = []
    for wheel_path in staged_root.rglob("*.whl"):
        dest = libs_dir / wheel_path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wheel_path, dest)
        copied.append(dest)

    return sorted(copied)


@audit(stage=StageType.EXECUTE, substage="copy_includes")
def copy_included_files() -> Includes:
    """
    Copies and stages all included files as specified in the build plan.

    This function manages the process of copying included files, ensuring that
    the destination directories are correctly created if necessary, and then
    copies the source files to their resolved destination. The inclusion process
    is guided by a pre-defined plan retrieved from the build system.

    Returns:
        Includes: An object containing the staged included files.
    """
    plan = _get_build_plan()
    includes_dir = plan.bundled_includes_dir

    includes = _stage_includes(plan)

    for spec in includes.items:
        dest = spec.resolved_dest(includes_dir)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(spec.src, dest)

    return includes


@audit(stage=StageType.EXECUTE, substage="copy_install_scripts")
def copy_install_scripts() -> Scripts:
    """
    Copies pre-install and post-install scripts to their corresponding directories
    based on the build plan. This function retrieves the build plan, resolves the
    required scripts, and places them in the specified directories within the
    bundled scripts directory.

    Returns:
        Scripts: An object containing lists of pre-install and post-install
            script specifications.

    """
    plan = _get_build_plan()
    scripts_dir = plan.bundled_scripts_dir

    pre_dir = scripts_dir / CHUB_PRE_INSTALL_SCRIPTS_DIR
    post_dir = scripts_dir / CHUB_POST_INSTALL_SCRIPTS_DIR

    scripts = _stage_scripts(plan)

    for spec in scripts.pre:
        dest = pre_dir / spec.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(spec.src, dest)

    for spec in scripts.post:
        dest = post_dir / spec.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(spec.src, dest)

    return scripts


@audit(stage=StageType.EXECUTE, substage="copy_runtime_files")
def copy_runtime_files() -> None:
    """
    Copies runtime resources from the staged directory to the bundled destination.

    This function retrieves the build plan, identifies the staged runtime resources
    directory, and copies its contents to the designated bundled runtime directory.
    If the staged runtime directory does not exist, it assumes that runtime resources
    are currently optional and exits without performing any operations.

    Args:
        N/A

    Returns:
        None
    """
    plan = _get_build_plan()
    staged_runtime = plan.staged_runtime_dir
    runtime_dest = plan.bundled_runtime_dir

    if not staged_runtime.exists():
        # Runtime resources are optional for now.
        return

    shutil.copytree(staged_runtime, runtime_dest, dirs_exist_ok=True)


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
        # Store includes in their normalized FILE[::dest] string form.
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
# Top-level EXECUTE entry
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
    dist_name, dist_ver = _infer_dist_identity(plan, copied_wheels)
    pinned_wheels, targets = _compute_pins_and_targets(plan, copied_wheels)

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
