from __future__ import annotations

import sys
from pathlib import Path

from pychub.helper.sys_check_utils import check_python_version, verify_pip
from pychub.model.build_event import BuildEvent, StageType, EventType, audit
from pychub.model.buildplan_model import BuildPlan
from pychub.package.context_vars import current_build_plan
from pychub.package.lifecycle.execute.executor import execute_build
from pychub.package.lifecycle.init.initializer import init_project
from pychub.package.lifecycle.plan.audit.audit_emitter import emit_audit_log
from pychub.package.lifecycle.plan.planner import plan_build


@audit(StageType.LIFECYCLE, substage="system_check")
def system_check() -> None:
    """Perform host-specific checks."""
    check_python_version()
    verify_pip()

def run(chubproject_path: Path | None = None) -> BuildPlan:
    """
    Central orchestration entry point for pychub.

    High-level lifecycle:
      - perform host checks
      - create and register a BuildPlan in context
      - delegate to INIT (init_project), PLAN (plan_build), and EXECUTE (execute_build)
      - always emit the audit log
    """
    build_plan = BuildPlan()
    var_token = current_build_plan.set(build_plan)
    try:
        build_plan.audit_log.append(
            BuildEvent.make(
                StageType.LIFECYCLE,
                EventType.START,
                message="Starting pychub build"))
        system_check()
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
            plan_build(cache_path)
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
        current_build_plan.reset(var_token)
        emit_audit_log(build_plan)
    return build_plan


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
