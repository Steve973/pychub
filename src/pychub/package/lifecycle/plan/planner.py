from __future__ import annotations

from pathlib import Path

from pychub.model.build_event import audit
from pychub.model.buildplan_model import BuildPlan
from pychub.package.constants import (
    CHUB_INCLUDES_DIR,
    CHUB_POST_INSTALL_SCRIPTS_DIR,
    CHUB_PRE_INSTALL_SCRIPTS_DIR,
    CHUB_SCRIPTS_DIR,
    RUNTIME_DIR
)
from pychub.package.lifecycle.plan.resource_resolution.resource_stager import (
    copy_pre_install_scripts,
    copy_post_install_scripts,
    copy_included_files,
    copy_runtime_files
)
from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.wheel_resolution_strategy_base import WheelResolutionStrategy
from pychub.package.lifecycle.plan.dep_resolution.wheel_stager import stage_wheels


@audit("PLAN")
def plan_build(build_plan: BuildPlan, cache_dir: Path, strategies: list[WheelResolutionStrategy], /) -> Path:
    """
    Generate and persist a BuildPlan for the ChubProject in cache_dir.

    Each strategy handles one resolution approach (path, index, native builder...).
    """
    project = build_plan.project

    # Output structure: { dep_name: [wheel_paths...] }
    wheel_files: dict[str, list[str]] = {}

    # Stage runtime resources:

    # 1. wheels
    stage_wheels(build_plan, wheel_files, set(project.wheels), strategies)

    # 2. pre-install scripts
    copy_pre_install_scripts(build_plan, cache_dir / CHUB_SCRIPTS_DIR / CHUB_PRE_INSTALL_SCRIPTS_DIR,
                             project.scripts.pre)

    # 3. post-install scripts
    copy_post_install_scripts(build_plan, cache_dir / CHUB_SCRIPTS_DIR / CHUB_POST_INSTALL_SCRIPTS_DIR,
                              project.scripts.post)

    # 4. included files
    copy_included_files(build_plan, cache_dir / CHUB_INCLUDES_DIR, project.includes)

    # 5. runtime files
    copy_runtime_files(build_plan, cache_dir / RUNTIME_DIR)

    # 6. persist the build plan
    plan_path = cache_dir / "buildplan.json"
    plan_path.write_text(build_plan.to_json(indent=2), encoding="utf-8")

    return plan_path
