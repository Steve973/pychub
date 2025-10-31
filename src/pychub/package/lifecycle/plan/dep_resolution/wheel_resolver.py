import zipfile
from email.parser import Parser
from pathlib import Path
from typing import List, Dict, Set

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from pychub.package.lifecycle.plan.dep_resolution.wheeldeps.wheel_resolution_strategy_base import WheelResolutionStrategy


def parse_requires_dist(wheel_path: Path) -> List[str]:
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


def resolve_dependency_graph(
    root_wheels: List[Path],
    output_dir: Path,
    strategies: List[WheelResolutionStrategy]) -> Dict[str, Path]:
    """
    Resolve all dependencies (depth-first).

    Each strategy must implement:
        resolve(requirement: str, output_dir: Path) -> Path
    """
    resolved: Dict[str, Path] = {}
    seen: Set[str] = set()
    stack: List[Path] = list(root_wheels)

    while stack:
        wheel_path = stack.pop()
        name = canonicalize_name(wheel_path.name.split("-")[0])
        if name in seen:
            continue

        seen.add(name)
        resolved[name] = wheel_path

        for dep_spec in parse_requires_dist(wheel_path):
            req = Requirement(dep_spec)
            dep_name = canonicalize_name(req.name)
            if dep_name in seen:
                continue

            for strat in strategies:
                try:
                    dep_wheel = strat.resolve(str(req), output_dir)
                    # enqueue that wheel for further resolution
                    stack.append(dep_wheel)
                    break
                except Exception:
                    continue
            else:
                raise RuntimeError(f"Could not resolve dependency {dep_name}")

    return resolved
