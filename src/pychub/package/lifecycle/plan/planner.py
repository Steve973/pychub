from __future__ import annotations

from pathlib import Path

from pychub.model.build_event import audit, StageType
from pychub.model.wheels_model import WheelCollection
from pychub.package.constants import CHUB_WHEELS_DIR
from pychub.package.context_vars import current_build_plan
from pychub.package.lifecycle.plan.dep_resolution.wheel_resolver import resolve_wheels_for_project
from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.wheel_resolution_strategy_base import \
    WheelResolutionStrategy
from pychub.package.lifecycle.plan.resource_resolution.resource_resolver import resolve_pre_install_scripts, \
    resolve_post_install_scripts, resolve_includes


@audit(StageType.PLAN)
def plan_build(cache_dir: Path, strategies: list[WheelResolutionStrategy] | None = None, /) -> Path:
    """
    Generate and persist a BuildPlan for the ChubProject in cache_dir.

    Each strategy handles one resolution approach (path, index, native builder...).
    """
    build_plan = current_build_plan.get()
    project = build_plan.project

    # Stage runtime resources:

    # 1. wheels
    build_plan.wheels = WheelCollection(
        set(resolve_wheels_for_project(project.wheels, cache_dir / CHUB_WHEELS_DIR, strategies).values()))

    # 2. pre-install scripts
    resolve_pre_install_scripts()

    # 3. post-install scripts
    resolve_post_install_scripts()

    # 4. included files
    resolve_includes()

    # 5. persist the build plan
    plan_path = cache_dir / "buildplan.json"
    plan_path.write_text(build_plan.to_json(indent=2), encoding="utf-8")

    return plan_path
