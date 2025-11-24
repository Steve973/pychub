import sys
from importlib.metadata import PackageNotFoundError, version as get_version
from pathlib import Path

from pychub.model.build_event import audit, StageType
from pychub.model.chubproject_model import ChubProject
from pychub.model.wheels_model import WheelCollection
from pychub.package.context_vars import current_build_plan
from pychub.package.lifecycle.plan.dep_resolution.wheel_resolver import resolve_wheels_for_project


@audit(StageType.EXECUTE, substage="execute_analyze_compatibility")
def execute_analyze_compatibility(chubproject: ChubProject):
    """
    Executes analysis of compatibility for the given ChubProject and resolves the
    common compatibility targets. Constructs the staged wheels directory, reuses
    the resolver to discover strategies, and validates compatibility of resolved
    wheels.

    Args:
        chubproject (ChubProject): The ChubProject instance containing the wheel
            files for which compatibility analysis will be performed.

    Raises:
        RuntimeError: If there is no active BuildPlan in the current context during
            compatibility analysis.
    """
    build_plan = current_build_plan.get()
    if build_plan is None:
        raise RuntimeError("No active BuildPlan in context during compatibility analysis.")

    # Use the same staging location PLAN uses for wheels.
    wheels_dir = build_plan.staged_wheels_dir
    wheels_dir.mkdir(parents=True, exist_ok=True)

    # Reuse the existing resolver (with strategy discovery by default).
    artifacts_by_name = resolve_wheels_for_project(
        project_wheels=chubproject.wheels,
        output_dir=wheels_dir)

    # Wrap in WheelCollection to use its compatibility helpers.
    collection = WheelCollection(set(artifacts_by_name.values()))

    # Let it scream if there is no common target at all.
    collection.validate_buildable()

    targets = collection.supported_target_strings

    if not targets:
        print("No common compatibility targets could be inferred from the resolved wheels.")
        return

    print("[compatibility]")
    if collection.is_fully_universal:
        print('targets = ["universal"]')
    else:
        print("targets = [")
        for t in targets:
            print(f'  "{t}",')
        print("]")


@audit(StageType.EXECUTE, substage="execute_chubproject_save")
def execute_chubproject_save(chubproject: ChubProject, path: Path | str):
    ChubProject.save_file(chubproject, path, overwrite=True, make_parents=True)


@audit(StageType.EXECUTE, substage="execute_version")
def execute_version():
    print(f"Python: {sys.version.split()[0]}")
    try:
        version = get_version("pychub")
    except PackageNotFoundError:
        version = "(source)"
    print(f"pychub: {version}")
