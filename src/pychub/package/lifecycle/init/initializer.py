from __future__ import annotations

import json
import sys
from argparse import Namespace
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Mapping, Any

from appdirs import user_cache_dir

from pychub.helper.toml_utils import load_toml_file
from pychub.model.build_event import audit, BuildEvent, StageType, EventType, LevelType
from pychub.model.chubproject_model import ChubProject
from pychub.model.chubproject_provenance_model import SourceKind
from pychub.model.compatibility_spec_model import CompatibilitySpec
from pychub.package.constants import CHUBPROJECT_FILENAME
from pychub.package.context_vars import current_build_plan
from pychub.package.lifecycle.init import immediate_operations
from pychub.package.lifecycle.plan.compatibility.compatibility_spec_loader import load_effective_compatibility_spec


class ImmediateOutcome(Enum):
    """
    Lists possible immediate outcomes for a process or action.

    This class provides predefined constants that represent the immediate
    result or state of a process or action. It is used primarily to standardize
    the representation of outcomes across different components or instances.

    Attributes:
        NONE: Represents the absence of an outcome or any specific result.
        EXIT: Indicates that the process or action should terminate or exit.
        CONTINUE: Denotes that the process or action should keep proceeding.
    """
    NONE = auto()
    EXIT = auto()
    CONTINUE = auto()


@audit(StageType.INIT, "check_immediate_operations")
def check_immediate_operations(args: Namespace, chubproject: ChubProject) -> ImmediateOutcome:
    """
    Executes immediate operations based on the provided arguments and ChubProject.

    This function determines which immediate operation to execute based on the
    input arguments. It may analyze compatibility, save the ChubProject, or
    display the version information. The function logs the respective operation
    performed as part of the build plan's audit log.

    Args:
        args (Namespace): Command-line arguments that define immediate operations
            to perform, such as analyzing compatibility, saving the ChubProject,
            or displaying version information.
        chubproject (ChubProject): Instance of the ChubProject that will be
            operated upon for the specified immediate action.

    Returns:
        ImmediateOutcome: An enumeration indicating the result of executing
        the immediate operation. It could be EXIT, CONTINUE, or NONE, based
        on the action taken or if no action was performed.
    """
    build_plan = current_build_plan.get()
    if args.analyze_compatibility:
        immediate_operations.execute_analyze_compatibility(chubproject)
        build_plan.audit_log.append(
            BuildEvent.make(
                StageType.INIT,
                EventType.ACTION,
                message="Invoked immediate action: analyze compatibility."))
        return ImmediateOutcome.EXIT
    elif args.chubproject_save:
        immediate_operations.execute_chubproject_save(chubproject, args.chubproject_save)
        build_plan.audit_log.append(
            BuildEvent.make(
                StageType.INIT,
                EventType.ACTION,
                message="Invoked immediate action: chubproject save."))
        return ImmediateOutcome.CONTINUE
    elif args.version:
        immediate_operations.execute_version()
        build_plan.audit_log.append(
            BuildEvent.make(
                StageType.INIT,
                EventType.ACTION,
                message="Invoked immediate action: version."))
        return ImmediateOutcome.EXIT
    return ImmediateOutcome.NONE


@audit(StageType.INIT, "create_project_cache")
def cache_project(chubproject: ChubProject) -> Path:
    """
    Caches a given ChubProject by creating a stable hash, ensuring the necessary directories,
    and saving project-related files. This function prepares the ChubProject for later
    build steps by writing the project configuration and metadata into a designated cache
    directory.

    Args:
        chubproject (ChubProject): Instance of ChubProject representing the target project to cache.

    Returns:
        Path: The path to the staging directory where the project cache is stored.
    """
    build_plan = current_build_plan.get()

    # Ensure cache_root is set (falls back to user_cache_dir if still default)
    if not build_plan.cache_root:
        build_plan.cache_root = Path(user_cache_dir("pychub"))

    # Compute a stable semantic hash from the ChubProject
    build_plan.project_hash = chubproject.mapping_hash()

    # Ensure the BuildPlan's staging dir exists
    project_staging_dir = build_plan.project_staging_dir
    project_staging_dir.mkdir(parents=True, exist_ok=True)

    # Write chubproject.toml using the model's own save logic
    project_path = project_staging_dir / CHUBPROJECT_FILENAME
    ChubProject.save_file(chubproject, path=project_path, overwrite=True)

    # Write a small meta.json that reflects the BuildPlan state
    (project_staging_dir / "meta.json").write_text(json.dumps(build_plan.meta_json, indent=2))

    return project_staging_dir


@audit(StageType.INIT, "load_compatibility_spec")
def load_compatibility_spec(project_toml_path: Path | None) -> CompatibilitySpec:
    """
    Loads the compatibility specification from a given project TOML file, if present. The
    function extracts settings such as the combination strategy, user-specified file, and
    any inline overrides. If no project TOML file is provided, default values are used.

    Args:
        project_toml_path (Path | None): The file path to the project TOML file. Can be None.

    Returns:
        CompatibilitySpec: A compatibility specification combining inputs from the project
        TOML file, specified user file, and inline overrides.

    Raises:
        ValueError: If the combination strategy specified in the TOML file is invalid.
    """
    build_plan = current_build_plan.get()
    combine_strategy: str = "merge"
    user_spec_path: Optional[Path] = None
    inline_overrides: Optional[Mapping[str, Any]] = None

    # Read the compatibility block from the project toml, if present
    if project_toml_path is not None:
        project_toml = load_toml_file(project_toml_path)
        compat_block = (
            project_toml
            .get("tool", project_toml)
            .get("pychub", project_toml)
            .get("compatibility", {})
        )

        # Get the specified strategy or default to "merge"
        raw_strategy = compat_block.pop("strategy", "merge")
        if raw_strategy not in ("merge", "override"):
            build_plan.audit_log.append(
                BuildEvent.make(
                    StageType.INIT,
                    EventType.VALIDATION,
                    LevelType.WARN,
                    message=(
                        f"CompatibilitySpec combination strategy '{raw_strategy}' must be "
                        "'merge' or 'override'; defaulting to 'merge'.")))
        else:
            combine_strategy = raw_strategy

        # A specified file has higher priority than the defaults
        raw_file = compat_block.pop("file", None)
        if isinstance(raw_file, str) and raw_file.strip():
            candidate = Path(raw_file)
            if not candidate.is_absolute():
                candidate = project_toml_path.parent / candidate
            user_spec_path = candidate

        # The highest precedence is from inline overrides
        override_mapping = dict(compat_block)
        inline_overrides = override_mapping or None

    return load_effective_compatibility_spec(
        strategy_name=combine_strategy,
        user_spec_path=user_spec_path,
        inline_overrides=inline_overrides)


@audit(StageType.INIT, "parse_chubproject")
def process_chubproject(chubproject_path: Path) -> ChubProject:
    """
    Parses a Chub project file and returns a ChubProject instance.

    This function processes a given path to a Chub project file, validates its
    existence, and loads its content as a ChubProject instance. If the specified
    file does not exist, an exception is raised.

    Args:
        chubproject_path (Path): The path to the Chub project file to be processed.

    Returns:
        ChubProject: An instance of the ChubProject loaded from the given file.

    Raises:
        FileNotFoundError: If the specified Chub project file does not exist.
    """
    if not chubproject_path.is_file():
        raise FileNotFoundError(f"Chub project file not found: {chubproject_path}")
    return ChubProject.from_file(chubproject_path)


@audit(StageType.INIT, "process_cli_options")
def process_options(args: Namespace) -> ChubProject:
    """
    Processes command-line interface (CLI) options and creates or updates a
    ChubProject instance based on the provided arguments. If a ChubProject file
    is specified, it processes and merges CLI options into the ChubProject,
    otherwise builds a new ChubProject directly from the mapping.

    Args:
        args (Namespace): CLI arguments containing user-specified options
            for ChubProject processing.

    Returns:
        ChubProject: An instance of ChubProject reflecting the merged or
            newly created state based on the provided CLI options.

    """
    cli_mapping = ChubProject.cli_to_mapping(args)
    cli_details = {"argv": sys.argv[1:]}
    if args.chubproject:
        chubproject_path = Path(args.chubproject).expanduser().resolve()
        chubproject = process_chubproject(chubproject_path)
        chubproject.merge_from_mapping(
            cli_mapping,
            source=SourceKind.CLI,
            details=cli_details)
        return chubproject
    else:
        return ChubProject.from_mapping(
            cli_mapping,
            source=SourceKind.CLI,
            details=cli_details)


@audit(StageType.INIT, "parse_cli")
def parse_cli() -> Namespace:
    """
    Parses command-line arguments and returns them as a Namespace object.

    This function is responsible for collecting and organizing command-line
    arguments provided by the user. It uses an internal mechanism to parse the
    arguments and returns them as a Namespace object for further processing.

    Returns:
        Namespace: An object containing all parsed command-line arguments as
        attributes.
    """
    return parse_cli()


@audit(StageType.INIT)
def init_project(chubproject_path: Path | None = None) -> tuple[Path, ImmediateOutcome]:
    """
    Initializes the project by processing both the build plan and provided project options.
    - it parses CLI
    - it populates build_plan.project and cache
    - it may indicate “exit early” via the returned bool

    This function manages the project initialization process by either directly using
    the `chubproject_path` provided or by parsing command-line arguments to determine
    the project setup. It updates the current build plan with the project configuration,
    caches the processed project, and checks for immediate operations that may require
    an early exit.

    Args:
        chubproject_path (Path | None): The path to a specific project, or None to use
            options derived from command-line arguments.

    Returns:
        tuple[Path, ImmediateOutcome]: A tuple containing the path to the cached project
            and an indication if an immediate operation requires the process to exit.
    """
    build_plan = current_build_plan.get()
    args = parse_cli()
    if chubproject_path:
        chubproject = process_chubproject(chubproject_path)
    else:
        chubproject = process_options(args)
    build_plan.project = chubproject
    build_plan.compatibility_spec = load_compatibility_spec(chubproject_path)
    project_cache_path = cache_project(chubproject)
    must_exit = check_immediate_operations(args, chubproject)
    return project_cache_path, must_exit
