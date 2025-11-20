from __future__ import annotations

import zipfile
from email.parser import Parser
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from pychub.model.build_event import (
    audit,
    BuildEvent,
    StageType,
    EventType,
    LevelType,
)
from pychub.model.wheels_model import WheelArtifact, WheelRoleType, WheelSourceType, UNORDERED
from pychub.package.context_vars import current_build_plan
from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.wheel_resolution_strategy_base import (
    WheelResolutionStrategy,
)
from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.wheel_resolution_strategy_registry import load_strategies


def parse_requires_dist(wheel_path: Path) -> list[str]:
    """
    Parses the `Requires-Dist` field from the METADATA file in a Python wheel file.

    This function extracts dependencies listed in the `Requires-Dist` field
    from the METADATA file, which is contained in the `.dist-info` directory
    of a Python wheel package.

    Args:
        wheel_path (Path): The file path to the wheel file.

    Returns:
        list[str]: A list of strings, each representing a dependency specified in the
        `Requires-Dist` field. Returns an empty list if no dependencies are found or
        if the METADATA file does not exist.
    """
    with zipfile.ZipFile(wheel_path) as z:
        meta_filename = next(
            (n for n in z.namelist() if n.endswith(".dist-info/METADATA")), None
        )
        if not meta_filename:
            return []
        meta_text = z.read(meta_filename).decode("utf-8", errors="replace")
    msg = Parser().parsestr(meta_text)
    return msg.get_all("Requires-Dist") or []


def _resolve_spec_with_strategies(
        spec: str,
        output_dir: Path,
        strategies: list[WheelResolutionStrategy],
        substage: str = "resolve_wheels") -> list[Path]:
    """
    Resolves a given wheel specification using provided resolution strategies.

    This function attempts to resolve a wheel specification using a list of wheel
    resolution strategies. The first strategy that succeeds in resolving the
    specification is used, and its result is returned. If all strategies fail, an
    error is raised. During the resolution process, audit logs are updated to
    record any encountered exceptions.

    Args:
        spec (str): The wheel specification string to be resolved.
        output_dir (Path): The directory where resolved wheel outputs will be stored.
        strategies (list[WheelResolutionStrategy]): A list of strategies to be used
            for resolving the wheel specification, ordered by priority.
        substage (str, optional): A label for the current build substage used in
            audit logs. Defaults to "resolve_wheels".

    Returns:
        list[Path]: A list of resolved paths to the wheel files.

    Raises:
        RuntimeError: If none of the resolution strategies succeed in resolving the
            wheel specification.
    """
    plan = current_build_plan.get()
    last_exc: Exception | None = None

    for strat in strategies:
        try:
            return [Path(r).expanduser().resolve() for r in strat.resolve(spec, output_dir)]
        except Exception as ex:
            last_exc = ex
            plan.audit_log.append(
                BuildEvent.make(
                    StageType.PLAN,
                    EventType.EXCEPTION,
                    LevelType.ERROR,
                    substage=substage,
                    message=(
                        f"Failed to resolve {spec!r} with "
                        f"{strat.__class__.__name__}: {ex}")))
            continue

    msg = f"Could not resolve wheel spec {spec!r}"
    if last_exc is not None:
        raise RuntimeError(msg) from last_exc
    raise RuntimeError(msg)


@audit(StageType.PLAN, "resolve_wheels")
def resolve_wheels_for_project(
        project_wheels: list[str],
        output_dir: Path,
        strategies: list[WheelResolutionStrategy] | None = None) -> dict[str, WheelArtifact]:
    """
    Resolve all primary wheels and their transitive dependencies into WheelArtifact
    instances.

    This function processes a list of wheels by using provided or default strategies
    to resolve each user-supplied wheel into a concrete file under an output directory.
    It further traverses and resolves the dependencies for each wheel while avoiding
    duplicates, ensuring proper categorization of user-supplied wheels as primary roots
    and their dependencies as transitive dependencies.

    Args:
        project_wheels (list[str]): List of user-supplied wheel specifications.
        output_dir (Path): Directory where the resolved wheels are stored.
        strategies (list[WheelResolutionStrategy] | None): Optional list of
            resolution strategies. Defaults to loading the default strategies.

    Returns:
        dict[str, WheelArtifact]: Mapping of canonical project name to
        WheelArtifact instances representing the resolved wheels and their
        dependencies.
    """

    if not strategies:
        strategies = load_strategies()

    # Stack of (wheel_path, is_primary)
    stack: list[tuple[Path, bool]] = []

    # Seed stack from project_wheels (CLI or chubproject options)

    for spec in project_wheels:
        spec_str = str(spec)
        for wheel_path in _resolve_spec_with_strategies(spec_str, output_dir, strategies):
            stack.append((wheel_path, True))

    artifacts_by_name: dict[str, WheelArtifact] = {}
    seen_names: set[str] = set()

    idx: int = 0
    while stack:
        wheel_path, is_primary = stack.pop()
        idx = idx + 1 if is_primary else idx
        order = UNORDERED if not is_primary else idx

        # Build a WheelArtifact from this wheel
        artifact = WheelArtifact.from_path(
            wheel_path,
            is_primary=is_primary,
            source=WheelSourceType.PATH,
            order=order)
        name = canonicalize_name(artifact.name)

        existing = artifacts_by_name.get(name)
        if existing is not None:
            # If anything ever saw this as a primary, keep that role
            if is_primary and existing.role != WheelRoleType.PRIMARY:
                existing.role = WheelRoleType.PRIMARY
            # No need to traverse dependencies again
            continue

        artifacts_by_name[name] = artifact
        seen_names.add(name)

        # Walk Requires-Dist entries for this artifact
        for req_str in artifact.requires:
            try:
                req = Requirement(req_str)
            except Exception:
                # If the requirement line is malformed or unsupported, skip it
                continue

            dep_name = canonicalize_name(req.name)
            if dep_name in seen_names:
                continue

            # Resolve dependency with the same strategies
            for dep_path in _resolve_spec_with_strategies(str(req), output_dir, strategies):
                # Mark as dependency (not primary root)
                stack.append((dep_path, False))

    return artifacts_by_name
