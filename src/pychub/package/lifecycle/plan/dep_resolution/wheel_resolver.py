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
from pychub.model.wheels_model import WheelArtifact, WheelRoleType, WheelSourceType
from pychub.package.context_vars import current_build_plan
from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.wheel_resolution_strategy_base import (
    WheelResolutionStrategy,
)
from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.wheel_resolution_strategy_registry import load_strategies


def parse_requires_dist(wheel_path: Path) -> list[str]:
    """Extract Requires-Dist entries from a wheel's METADATA."""
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
        substage: str = "resolve_wheels") -> Path:
    """
    Ask each strategy in order to resolve a given spec (path or requirement)
    into a concrete wheel on disk, logging failures into the audit log.
    """
    plan = current_build_plan.get()
    last_exc: Exception | None = None

    for strat in strategies:
        try:
            resolved = strat.resolve(spec, output_dir)
            return Path(resolved).expanduser().resolve()
        except Exception as ex:
            last_exc = ex
            if plan is not None:
                plan.audit_log.append(
                    BuildEvent.make(
                        StageType.PLAN,
                        EventType.EXCEPTION,
                        LevelType.ERROR,
                        substage=substage,
                        message=(
                            f"Failed to resolve {spec!r} with "
                            f"{strat.__class__.__name__}: {ex}"
                        ),
                    )
                )
            continue

    msg = f"Could not resolve wheel spec {spec!r}"
    if last_exc is not None:
        raise RuntimeError(msg) from last_exc
    raise RuntimeError(msg)


@audit(StageType.PLAN, "resolve_wheels")
def resolve_wheels_for_project(
        project_wheels: list[str | Path],
        output_dir: Path,
        strategies: list[WheelResolutionStrategy] | None = None) -> dict[str, WheelArtifact]:
    """
    Resolve all primary wheels and their transitive dependencies into
    WheelArtifact instances.

    Returns a mapping of canonical project name -> WheelArtifact.

    Responsibilities:
    - Use strategies to resolve each user-supplied spec
      into a concrete wheel file under output_dir.
    - Walk Requires-Dist for each wheel to discover dependencies.
    - Avoid duplicates by canonical project name.
    - Mark user supplied roots as PRIMARY, transitive deps as DEPENDENCY.
    """

    if strategies is None or strategies == []:
        strategies = load_strategies()

    # Stack of (wheel_path, is_primary_root)
    stack: list[tuple[Path, bool]] = []

    # Seed stack from project_wheels (CLI or chubproject options)
    for spec in project_wheels:
        spec_str = str(spec)
        wheel_path = _resolve_spec_with_strategies(spec_str, output_dir, strategies)
        stack.append((wheel_path, True))

    artifacts_by_name: dict[str, WheelArtifact] = {}
    seen_names: set[str] = set()

    while stack:
        wheel_path, is_primary = stack.pop()

        # Build a WheelArtifact from this wheel
        artifact = WheelArtifact.from_path(
            wheel_path,
            is_primary=is_primary,
            source=WheelSourceType.PATH,
        )
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
            dep_path = _resolve_spec_with_strategies(str(req), output_dir, strategies)
            # Mark as dependency (not primary root)
            stack.append((dep_path, False))

    return artifacts_by_name
