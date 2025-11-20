from __future__ import annotations

from pathlib import Path

from pychub.model.build_event import audit, StageType
from pychub.model.includes_model import Includes
from pychub.model.scripts_model import Scripts, ScriptSpec, ScriptType
from pychub.package.context_vars import current_build_plan


@audit(stage=StageType.PLAN, substage="resolve_includes")
def resolve_includes() -> None:
    """
    Resolves and processes all include files specified in the project's configuration.

    This function retrieves the current build plan and processes project include files
    defined in the configuration. The included files are resolved relative to the project's
    directory, and the build plan is updated accordingly.

    Args:
        None

    Raises:
        None
    """
    build_plan = current_build_plan.get()
    project = build_plan.project
    project_dir = build_plan.project_dir
    build_plan.include_files = Includes.from_toml(project.includes, base_dir=project_dir)


def resolve_scripts(scripts: list[str] | None, script_type: ScriptType, project_dir: Path) -> Scripts:
    """
    Resolves and processes the given scripts into a standardized format suitable for further
    operations. The function ensures absolute paths for all scripts, associates them with
    the specified script type, and deduplicates the list of results.

    Args:
        scripts (list[str] | None): A list of script file paths, optionally relative. Can
            also be None if no scripts are provided.
        script_type (ScriptType): The type of the scripts to associate with, used to
            categorize or handle the scripts appropriately.
        project_dir (Path): The root directory to resolve relative paths of the provided
            scripts.

    Returns:
        Scripts: A collection of deduplicated, processed script specifications.
    """
    items: list[ScriptSpec] = []

    for s in scripts or []:
        src = Path(s)
        if not src.is_absolute():
            src = (project_dir / src).expanduser().resolve()
        items.append(ScriptSpec(src=src, script_type=script_type))

    return Scripts(_items=Scripts.dedup(items))


@audit(stage=StageType.PLAN, substage="resolve_post_install_scripts")
def resolve_post_install_scripts() -> None:
    """
    Resolve post-installation scripts for the current build plan.

    This function processes and resolves post-installation scripts specified in
    the current build plan. It adds the resolved scripts to the install_scripts
    list under the build plan's items. The scripts are categorized as post-install
    scripts and are associated with a specific project directory.

    Raises:
        AttributeError: If the current build plan or any required attribute is not set or accessible.
    """
    build_plan = current_build_plan.get()
    chubproject = build_plan.project
    build_plan.install_scripts.items.append(
        resolve_scripts(chubproject.post_scripts, ScriptType.POST, build_plan.project_dir))


@audit(stage=StageType.PLAN, substage="resolve_pre_install_scripts")
def resolve_pre_install_scripts() -> None:
    """
    Resolves and appends pre-install scripts to the build plan.

    This function fetches the current build plan and processes the pre-install
    scripts specified in the project configuration. The resolved scripts are
    then appended to the build plan's list of install script items.

    Raises:
        KeyError: If the current build plan is not available in the context.

    Returns:
        None
    """
    build_plan = current_build_plan.get()
    chubproject = build_plan.project
    build_plan.install_scripts.items.append(
        resolve_scripts(chubproject.pre_scripts, ScriptType.PRE, build_plan.project_dir))
