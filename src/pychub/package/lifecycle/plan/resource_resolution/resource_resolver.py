from __future__ import annotations

from pathlib import Path

from pychub.model.build_event import audit, StageType
from pychub.model.includes_model import Includes
from pychub.model.scripts_model import Scripts, ScriptSpec, ScriptType
from pychub.package.context_vars import current_build_plan


@audit(stage=StageType.PLAN, substage="resolve_includes")
def resolve_includes() -> None:
    """
    Normalize project.includes (raw FILE[::dest] strings) into an Includes object,
    using project_dir as the base for relative paths.
    """
    build_plan = current_build_plan.get()
    project = build_plan.project
    project_dir = build_plan.project_dir
    build_plan.include_files = Includes.from_toml(project.includes, base_dir=project_dir)


def resolve_scripts(scripts: list[str], script_type: ScriptType, project_dir: Path) -> Scripts:
    """
    Normalize project.pre_scripts / project.post_scripts (raw strings)
    into a Scripts collection with fully resolved ScriptSpec entries.
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
    build_plan = current_build_plan.get()
    chubproject = build_plan.project
    build_plan.install_scripts.items.append(
        resolve_scripts(chubproject.post_scripts, ScriptType.POST, build_plan.project_dir))


@audit(stage=StageType.PLAN, substage="resolve_pre_install_scripts")
def resolve_pre_install_scripts() -> None:
    build_plan = current_build_plan.get()
    chubproject = build_plan.project
    build_plan.install_scripts.items.append(
        resolve_scripts(chubproject.pre_scripts, ScriptType.PRE, build_plan.project_dir))
