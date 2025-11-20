from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple, List

from packaging.utils import parse_wheel_filename

from pychub.model.buildplan_model import BuildPlan
from pychub.model.wheels_model import WheelCollection, WheelArtifact


def infer_dist_identity(
        plan: BuildPlan,
        wheel_paths: Iterable[Path]) -> Tuple[str, str]:
    """
    Infers the distribution name and version based on the given BuildPlan or wheel paths.

    This function determines the distribution name and version using the following priority:
    1. Uses explicit project name and version if provided in the BuildPlan.
    2. Checks for primary artifacts within the WheelCollection of the BuildPlan, if available.
    3. Falls back to parsing the filename of the first provided wheel path.

    Args:
        plan (BuildPlan): The build plan containing project details and potentially a
            WheelCollection.
        wheel_paths (Iterable[Path]): An iterable of Path objects representing the
            wheel files.

    Returns:
        Tuple[str, str]: A tuple containing the inferred name and version of the
            distribution.

    Raises:
        ValueError: If the distribution name and version cannot be determined from the
            provided BuildPlan or wheel paths.
    """
    project = plan.project

    # 1. If the project explicitly names itself, trust that.
    if project.name and project.version:
        return project.name, project.version

    # 2. If we have a WheelCollection on the plan, try primary artifacts.
    wheels_collection = getattr(plan, "wheels", None)
    if isinstance(wheels_collection, WheelCollection) and len(wheels_collection):
        primaries: List[WheelArtifact] = wheels_collection.primary or list(wheels_collection)
        if primaries:
            w0 = primaries[0]
            return w0.name, str(w0.version)

    # 3. Fallback: parse the first wheel filename we actually copied.
    wheel_paths = list(wheel_paths)
    if wheel_paths:
        name, version, *_ = parse_wheel_filename(wheel_paths[0].name)
        return name, str(version)

    raise ValueError("Unable to infer distribution name/version from BuildPlan or wheels")


def compute_pins_and_targets(
        plan: BuildPlan,
        wheel_paths: Iterable[Path]) -> tuple[list[str], list[str]]:
    """
    Compute a set of pinned dependencies and a list of supported targets based on
    the provided build plan and wheel paths.

    If the `plan` contains a valid `WheelCollection`, it identifies primary
    wheels and determines their pinned dependencies and targets. Otherwise, it
    falls back to pinning all dependencies from the given wheel paths.

    Args:
        plan (BuildPlan): The build plan containing information about wheels
            and their compatibility.
        wheel_paths (Iterable[Path]): An iterable of wheel file paths used as
            a fallback if the `plan` lacks valid wheel information.

    Returns:
        Tuple[list[str], list[str]]: A tuple where the first element is a sorted
        list of pinned dependencies (formatted as `<name>==<version>`) and the
        second element is a list of supported target strings.
    """
    wheels_collection = getattr(plan, "wheels", None)
    pinned: set[str] = set()

    if isinstance(wheels_collection, WheelCollection) and len(wheels_collection):
        primaries = wheels_collection.primary or list(wheels_collection)
        for w in primaries:
            pinned.add(f"{w.name}=={w.version}")
        targets: list[str] = wheels_collection.supported_target_strings
        return sorted(pinned), targets

    # Fallback: just pin everything we copied, ignore compatibility for now.
    for p in wheel_paths:
        name, version, *_ = parse_wheel_filename(p.name)
        pinned.add(f"{name}=={version}")

    return sorted(pinned), []
