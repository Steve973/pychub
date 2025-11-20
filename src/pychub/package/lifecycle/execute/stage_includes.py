from __future__ import annotations

import shutil

from pychub.model.build_event import audit, StageType
from pychub.model.buildplan_model import BuildPlan
from pychub.model.includes_model import Includes
from pychub.package.lifecycle.execute.bundler import _get_build_plan


def _stage_includes(plan: BuildPlan) -> Includes:
    """
    Retrieves normalized includes for a given build plan.

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
