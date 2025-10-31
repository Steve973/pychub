from __future__ import annotations

from pathlib import Path

from packaging.utils import canonicalize_name

from pychub.model.build_event import audit, BuildEvent
from pychub.model.buildplan_model import BuildPlan
from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.wheel_resolution_strategy_base import \
    WheelResolutionStrategy


def _flatten(values):
    """Flatten lists that may be appended by argparse (list[list[str]]).
    Keeps non-list items as-is.
    """
    if not values:
        return []
    flat = []
    for v in values:
        if isinstance(v, (list, tuple)):
            flat.extend(v)
        else:
            flat.append(v)
    return flat


def _paths(values):
    """Convert a (possibly nested) list of paths to Path objects.
    Filters out non-existent files.
    """
    out: list[Path] = []
    for item in _flatten(values):
        p = Path(item).expanduser().resolve()
        if p.exists() and p.is_file():
            out.append(p)
    return out


@audit("PLAN", "stage_wheels")
def stage_wheels(build_plan: BuildPlan,
                 wheel_files: dict[str, list[str]],
                 project_wheels: set,
                 strategies: list[WheelResolutionStrategy]):
    wheels_staging_dir = build_plan.staging_dir / build_plan.wheels_dir
    # iterate over declared deps from the ChubProject
    wheel_paths = _paths(project_wheels)
    for wheel_path in wheel_paths:
        dep_name = canonicalize_name(Path(wheel_path).name.split("-")[0])
        for strategy in strategies:
            try:
                resolved = strategy.resolve(str(wheel_path), wheels_staging_dir)
                wheel_files.setdefault(dep_name, []).append(str(resolved))
                break
            except Exception as ex:
                build_plan.audit_log.append(
                    BuildEvent(
                        stage="PLAN",
                        substage="stage_wheels",
                        event_type="EXCEPTION",
                        message=f"Failed to resolve {wheel_path} with {strategy.__class__.__name__}: {ex}"))
                continue
        else:
            raise RuntimeError(f"Could not resolve dependency {dep_name}")
