from __future__ import annotations

import shutil
from pathlib import Path

from pychub.model.build_event import audit, StageType
from pychub.model.buildplan_model import BuildPlan
from pychub.model.scripts_model import Scripts, ScriptSpec, ScriptType
from pychub.package.constants import CHUB_PRE_INSTALL_SCRIPTS_DIR, CHUB_POST_INSTALL_SCRIPTS_DIR
from pychub.package.lifecycle.execute.bundler import _get_build_plan


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
