from __future__ import annotations

import sys
from importlib.metadata import version as get_version
from pathlib import Path

from pychub.model.build_event import BuildEvent
from pychub.model.buildplan_model import BuildPlan
from pychub.package.lifecycle.execute.bundler import bundle_chub
from pychub.package.lifecycle.execute.executor import execute_build
from pychub.package.lifecycle.init.initializer import init_project
from pychub.package.lifecycle.plan.audit.audit_emitter import emit_audit_log
from pychub.package.lifecycle.plan.planner import plan_build


def run(chubproject_path: Path | None = None) -> None:
    """
    Central orchestration entry point for pychub.
    - Parses CLI args if needed
    - Initializes a ChubProject
    - Optionally executes plan or build phases
    """
    build_plan = BuildPlan()
    try:
        build_plan.pychub_version = get_version("pychub")
        build_plan.audit_log.append(BuildEvent(stage="LIFECYCLE", event_type="START", message="Starting pychub build"))
        if chubproject_path:
            opts_msg = f"Build invoked with chubproject path: {chubproject_path}"
            build_plan.project_dir = Path(chubproject_path).expanduser().resolve().parent
        else:
            opts_msg = "Build will use CLI options"
        build_plan.audit_log.append(BuildEvent(stage="LIFECYCLE", event_type="INPUT", message=opts_msg))
        cache_path = init_project(build_plan, chubproject_path)
        plan_build(build_plan, cache_path)
        bundle_chub(build_plan)
        chub_file_path = execute_build(build_plan)
        build_plan.audit_log.append(BuildEvent(stage="LIFECYCLE", event_type="OUTPUT", message=f"Chub file built and located at: {chub_file_path}"))
        build_plan.audit_log.append(BuildEvent(stage="LIFECYCLE", event_type="COMPLETE", message="Completed pychub build"))
    except Exception as e:
        build_plan.audit_log.append(BuildEvent(stage="LIFECYCLE", event_type="FAIL", message=str(e)))
        raise
    finally:
        emit_audit_log(build_plan)


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
