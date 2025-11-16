from __future__ import annotations

import sys
from importlib.metadata import version as get_version
from pathlib import Path

from pychub.model.build_event import BuildEvent, StageType, EventType
from pychub.model.buildplan_model import BuildPlan
from pychub.package.context_vars import current_build_plan
from pychub.package.lifecycle.execute.executor import execute_build
from pychub.package.lifecycle.init.initializer import init_project
from pychub.package.lifecycle.plan.audit.audit_emitter import emit_audit_log
from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.index_resolution_strategy import IndexResolutionStrategy
from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.local_resolution_strategy import LocalResolutionStrategy
from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.path_resolution_strategy import PathResolutionStrategy
from pychub.package.lifecycle.plan.planner import plan_build


def run(chubproject_path: Path | None = None) -> None:
    """
    Central orchestration entry point for pychub.
    - Parses CLI args if needed
    - Initializes a ChubProject
    - Optionally executes plan or build phases
    """
    build_plan = BuildPlan()
    current_build_plan.set(build_plan)
    try:
        build_plan.pychub_version = get_version("pychub")
        build_plan.audit_log.append(
            BuildEvent.make(
                StageType.LIFECYCLE,
                EventType.START,
                message="Starting pychub build"))
        if chubproject_path:
            opts_msg = f"Build invoked with chubproject path: {chubproject_path}"
            build_plan.project_dir = Path(chubproject_path).expanduser().resolve().parent
        else:
            opts_msg = "Build will use CLI options"
        build_plan.audit_log.append(
            BuildEvent.make(
                StageType.LIFECYCLE,
                EventType.INPUT,
                message=opts_msg))
        cache_path, must_exit = init_project(chubproject_path)
        if must_exit:
            build_plan.audit_log.append(
                BuildEvent.make(
                    StageType.LIFECYCLE,
                    EventType.ACTION,
                    message="Completed immediate operation and exiting"))
        else:
            plan_build(cache_path, [IndexResolutionStrategy(), PathResolutionStrategy(), LocalResolutionStrategy()])
            chub_file_path = execute_build()
            build_plan.audit_log.append(
                BuildEvent.make(
                    StageType.LIFECYCLE,
                    EventType.OUTPUT,
                    message=f"Chub file built and located at: {chub_file_path}"))
            build_plan.audit_log.append(
                BuildEvent.make(
                    StageType.LIFECYCLE,
                    EventType.COMPLETE,
                    message="Completed pychub build"))
    except Exception as e:
        build_plan.audit_log.append(
            BuildEvent.make(
                StageType.LIFECYCLE,
                EventType.FAIL,
                message=str(e)))
        raise
    finally:
        emit_audit_log()


def main() -> None:
    try:
        run()
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        print(f"pychub: error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
